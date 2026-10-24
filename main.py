
import io
import os
import re
import uuid
import zipfile
from pathlib import Path

from fastapi import UploadFile, File

import time

import docker
from docker.errors import DockerException, ImageNotFound
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session
from sqlalchemy import (
    MetaData, Table, Column, Integer, String, Text, DateTime,
    func, select, insert,
)

from database import SessionLocal
from models import Project, Deployment


# --------------------------------------------------
# PERSISTENT DOCKER BUILD TRACKING
# --------------------------------------------------

build_metadata = MetaData()

BuildImage = Table(
    "cloudforge_build_images",
    build_metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("project_id", Integer, nullable=False, index=True),
    Column("image_name", String(255), nullable=False),
    Column("saved_name", String(255), nullable=False),
    Column("entrypoint", String(255), nullable=False),
    Column("build_logs", Text, nullable=False, default=""),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)


def ensure_build_table(db: Session):
    from sqlalchemy import text

    # Lock table creation so concurrent requests do not race.
    db.execute(text("SELECT pg_advisory_xact_lock(834725190)"))

    # Reuse the current session transaction.
    BuildImage.metadata.create_all(
        bind=db.connection(),
        checkfirst=True,
    )


def serialize_build(row):
    return {
        "id": row["id"],
        "project_id": row["project_id"],
        "image_name": row["image_name"],
        "saved_name": row["saved_name"],
        "entrypoint": row["entrypoint"],
        "build_logs": row["build_logs"].splitlines() if row["build_logs"] else [],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
    }


# --------------------------------------------------
# 1. CREATE FASTAPI APPLICATION
# --------------------------------------------------

app = FastAPI(
    title="Cloud Forge API",
    description="Cloud application deployment and monitoring platform",
    version="0.4.0",
)


# --------------------------------------------------
# 2. ENABLE CORS FOR THE REACT FRONTEND
# --------------------------------------------------

def get_allowed_origins() -> list[str]:
    raw_origins = os.getenv("CORS_ORIGINS")
    default_origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    if not raw_origins:
        return default_origins
    origins = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]
    return origins if origins else default_origins


app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------
# 3. AUTHENTICATION & SECURITY (OPTIONAL API KEY)
# --------------------------------------------------

from fastapi.security import APIKeyHeader

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)
REQUIRED_API_KEY = os.getenv("API_KEY")


def verify_api_key(api_key: str | None = Depends(API_KEY_HEADER)):
    """
    Enforce X-API-Key authentication when API_KEY environment variable is configured.
    Falls back to unauthenticated access when API_KEY is unset (for seamless local development).
    """
    if REQUIRED_API_KEY:
        if not api_key or api_key != REQUIRED_API_KEY:
            raise HTTPException(
                status_code=401,
                detail="Invalid or missing X-API-Key authentication header.",
            )
    return api_key


# --------------------------------------------------
# 4. DATABASE SESSION
# --------------------------------------------------

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --------------------------------------------------
# 5. PYDANTIC SCHEMAS
# --------------------------------------------------

class ProjectCreate(BaseModel):
    name: str
    app_type: str = "python"
    repository_url: str | None = None


class ProjectResponse(BaseModel):
    id: int
    name: str
    app_type: str
    repository_url: str | None = None

    model_config = ConfigDict(from_attributes=True)


class DeploymentResponse(BaseModel):
    id: int
    project_id: int
    status: str
    logs: str | None = None

    model_config = ConfigDict(from_attributes=True)


# --------------------------------------------------
# 5. HOME AND HEALTH ENDPOINTS
# --------------------------------------------------

@app.get("/")
def home():
    return {
        "message": "Welcome to Cloud Forge API",
        "status": "running",
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}


# --------------------------------------------------
# 6. PROJECT ENDPOINTS
# --------------------------------------------------

@app.post(
    "/projects",
    response_model=ProjectResponse,
    status_code=201,
    dependencies=[Depends(verify_api_key)],
)
def create_project(
    project_data: ProjectCreate,
    db: Session = Depends(get_db),
):
    project = Project(
        name=project_data.name,
        app_type=project_data.app_type,
        repository_url=project_data.repository_url,
    )

    db.add(project)
    db.commit()
    db.refresh(project)

    return project


@app.get(
    "/projects",
    response_model=list[ProjectResponse],
    dependencies=[Depends(verify_api_key)],
)
def list_projects(db: Session = Depends(get_db)):
    return db.query(Project).order_by(Project.id.desc()).all()


@app.get(
    "/projects/{project_id}",
    response_model=ProjectResponse,
    dependencies=[Depends(verify_api_key)],
)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(
        Project.id == project_id
    ).first()

    if project is None:
        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )

    return project


# --------------------------------------------------
# 7. RUN A CONTROLLED DOCKER DEPLOYMENT
# --------------------------------------------------

@app.post(
    "/projects/{project_id}/deployments",
    response_model=DeploymentResponse,
    status_code=201,
    dependencies=[Depends(verify_api_key)],
)
def create_deployment(
    project_id: int,
    image_name: str,
    db: Session = Depends(get_db),
):
    """
    Run the image built for this project.

    The image_name query parameter must match the Cloud Forge naming
    convention for this project. This prevents the endpoint from being
    used to launch an arbitrary image name.
    """
    project = db.query(Project).filter(
        Project.id == project_id
    ).first()

    if project is None:
        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )

    # Only accept an image tag generated by this project's build endpoint.
    expected_pattern = rf"cloudforge-project-{project_id}:[a-f0-9]{{12}}"
    if not re.fullmatch(expected_pattern, image_name):
        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid image name. Build the uploaded ZIP for this project "
                "and deploy the resulting image tag."
            ),
        )

    deployment = Deployment(
        project_id=project_id,
        status="queued",
        logs=f"Deployment requested for image: {image_name}",
    )
    db.add(deployment)
    db.commit()
    db.refresh(deployment)

    container = None
    client = None

    try:
        client = docker.from_env()
        client.ping()

        # Confirm the exact image exists locally before starting a container.
        client.images.get(image_name)

        deployment.status = "running"
        deployment.logs = (
            f"Starting project image: {image_name}\n"
            "Container limits: memory=128 MiB, CPU=0.5, PIDs=64, "
            "network disabled, read-only root filesystem.\n"
        )
        db.commit()

        container = client.containers.run(
            image=image_name,
            detach=True,
            network_disabled=True,
            mem_limit="128m",
            nano_cpus=500_000_000,
            pids_limit=64,
            read_only=True,
            cap_drop=["ALL"],
            security_opt=["no-new-privileges:true"],
            user="nobody",
            auto_remove=False,
            labels={
                "cloudforge.managed": "true",
                "cloudforge.deployment_id": str(deployment.id),
                "cloudforge.project_id": str(project_id),
            },
        )

        # Wait at most 30 seconds for this short-running demo application.
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            container.reload()
            if container.status in ("exited", "dead"):
                break
            time.sleep(0.5)
        else:
            container.stop(timeout=2)
            deployment.status = "failed"
            deployment.logs += (
                "\nDeployment failed: execution exceeded 30 seconds."
            )
            db.commit()
            return deployment

        output = container.logs(
            stdout=True,
            stderr=True,
        ).decode("utf-8", errors="replace")
        exit_code = container.attrs["State"]["ExitCode"]

        deployment.logs += (
            "\nApplication output:\n"
            + (output or "(No output produced.)")
            + f"\nContainer exit code: {exit_code}"
        )

        if exit_code == 0:
            deployment.status = "success"
            deployment.logs += "\nApplication completed successfully."
        else:
            deployment.status = "failed"
            deployment.logs += "\nApplication exited with an error."

        db.commit()
        db.refresh(deployment)

    except ImageNotFound:
        deployment.status = "failed"
        deployment.logs += (
            f"\nDocker image not found locally: {image_name}. "
            "Build the uploaded project first."
        )
        db.commit()

    except DockerException as exc:
        deployment.status = "failed"
        deployment.logs += f"\nDocker error: {str(exc)[:1000]}"
        db.commit()

    except Exception as exc:
        deployment.status = "failed"
        deployment.logs += f"\nUnexpected deployment error: {str(exc)[:1000]}"
        db.commit()

    finally:
        if container is not None:
            try:
                container.remove(force=True)
            except DockerException:
                pass

        if client is not None:
            client.close()

    db.refresh(deployment)
    return deployment


# --------------------------------------------------
# 8. LIST DEPLOYMENTS FOR A PROJECT
# --------------------------------------------------

@app.get(
    "/projects/{project_id}/deployments",
    response_model=list[DeploymentResponse],
    dependencies=[Depends(verify_api_key)],
)
def list_project_deployments(
    project_id: int,
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(
        Project.id == project_id
    ).first()

    if project is None:
        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )

    return (
        db.query(Deployment)
        .filter(Deployment.project_id == project_id)
        .order_by(Deployment.id.desc())
        .all()
    )


# --------------------------------------------------
# 9. GET ONE DEPLOYMENT
# --------------------------------------------------

@app.get(
    "/deployments/{deployment_id}",
    response_model=DeploymentResponse,
    dependencies=[Depends(verify_api_key)],
)
def get_deployment(
    deployment_id: int,
    db: Session = Depends(get_db),
):
    deployment = db.query(Deployment).filter(
        Deployment.id == deployment_id
    ).first()

    if deployment is None:
        raise HTTPException(
            status_code=404,
            detail="Deployment not found",
        )

    return deployment


# --------------------------------------------------
# 10. UPLOAD AND VALIDATE A PYTHON PROJECT ZIP
# --------------------------------------------------

UPLOAD_DIR = Path(__file__).resolve().parent / "uploaded_projects"

MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_EXTRACTED_SIZE = 25 * 1024 * 1024  # 25 MB
MAX_ARCHIVE_FILES = 100

S3_BUCKET = os.getenv("S3_BUCKET")


def get_s3_client():
    if not S3_BUCKET:
        return None
    try:
        import boto3
        region = os.getenv("AWS_REGION", "ap-southeast-2")
        return boto3.client("s3", region_name=region)
    except Exception:
        return None


@app.post(
    "/projects/{project_id}/upload",
    dependencies=[Depends(verify_api_key)],
)
async def upload_project(
    project_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(
        Project.id == project_id
    ).first()

    if project is None:
        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )

    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(
            status_code=400,
            detail="Please upload a ZIP file.",
        )

    try:
        # Read at most 10 MB plus one byte to detect oversized files.
        contents = await file.read(MAX_UPLOAD_SIZE + 1)

        if len(contents) > MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=413,
                detail="ZIP file exceeds the 10 MB limit.",
            )

        try:
            archive = zipfile.ZipFile(io.BytesIO(contents))
        except (zipfile.BadZipFile, OSError):
            raise HTTPException(
                status_code=400,
                detail="The uploaded file is not a valid ZIP archive.",
            )

        with archive:
            entries = archive.infolist()

            if not entries:
                raise HTTPException(
                    status_code=400,
                    detail="The ZIP archive is empty.",
                )

            if len(entries) > MAX_ARCHIVE_FILES:
                raise HTTPException(
                    status_code=400,
                    detail="The archive contains too many entries.",
                )

            total_size = 0
            python_files = 0

            for entry in entries:
                name = entry.filename.replace("\\", "/")
                parts = name.split("/")

                # Reject absolute paths and directory traversal.
                if (
                    name.startswith("/")
                    or any(part in ("", ".", "..") for part in parts[:-1])
                    or (parts and ":" in parts[0])
                ):
                    raise HTTPException(
                        status_code=400,
                        detail="The archive contains an unsafe file path.",
                    )

                # Reject symbolic links.
                mode = entry.external_attr >> 16
                if (mode & 0o170000) == 0o120000:
                    raise HTTPException(
                        status_code=400,
                        detail="Symbolic links are not allowed.",
                    )

                if entry.flag_bits & 0x1:
                    raise HTTPException(
                        status_code=400,
                        detail="Encrypted ZIP entries are not allowed.",
                    )

                if entry.is_dir():
                    continue

                total_size += entry.file_size

                if total_size > MAX_EXTRACTED_SIZE:
                    raise HTTPException(
                        status_code=413,
                        detail="The uncompressed archive exceeds 25 MB.",
                    )

                if name.lower().endswith(".py"):
                    python_files += 1

            if python_files == 0:
                raise HTTPException(
                    status_code=400,
                    detail="The ZIP must contain at least one Python (.py) file.",
                )

            # Zip-bomb protection: verify decompressed stream chunk-by-chunk and enforce 25 MB limit
            # on actual decompressed bytes, preventing spoofed header sizes.
            streamed_total = 0
            for entry in entries:
                if not entry.is_dir():
                    with archive.open(entry) as stream:
                        while True:
                            chunk = stream.read(64 * 1024)
                            if not chunk:
                                break
                            streamed_total += len(chunk)
                            if streamed_total > MAX_EXTRACTED_SIZE:
                                raise HTTPException(
                                    status_code=413,
                                    detail="The uncompressed archive exceeds the 25 MB limit.",
                                )

        # Save the original archive using a generated filename.
        # The user's filename is never used as a filesystem path.
        project_dir = UPLOAD_DIR / str(project_id)
        project_dir.mkdir(parents=True, exist_ok=True)

        saved_name = f"{uuid.uuid4().hex}.zip"
        saved_path = project_dir / saved_name
        saved_path.write_bytes(contents)

        # Optional S3 persistence (fallback to local if S3_BUCKET is unset or upload fails)
        s3 = get_s3_client()
        if s3:
            try:
                s3_key = f"uploads/{project_id}/{saved_name}"
                s3.put_object(
                    Bucket=S3_BUCKET,
                    Key=s3_key,
                    Body=contents,
                    ContentType="application/zip",
                )
            except Exception as exc:
                import logging
                logging.getLogger("cloudforge").warning(f"S3 upload sync failed: {exc}")

        return {
            "message": "ZIP uploaded and validated successfully.",
            "project_id": project_id,
            "filename": file.filename,
            "saved_name": saved_name,
            "size_bytes": len(contents),
            "status": "uploaded",
            "note": "The archive has not been extracted, built, or executed.",
        }

    finally:
        await file.close()


# --------------------------------------------------
# 11. SAFELY EXTRACT A ZIP AND BUILD A DOCKER IMAGE
# --------------------------------------------------

import shutil


BUILD_DIR = Path(__file__).resolve().parent / "build_projects"


@app.get(
    "/projects/{project_id}/builds",
    dependencies=[Depends(verify_api_key)],
)
def list_project_builds(
    project_id: int,
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found.")

    ensure_build_table(db)
    rows = db.execute(
        select(BuildImage)
        .where(BuildImage.c.project_id == project_id)
        .order_by(BuildImage.c.id.desc())
    ).mappings().all()

    return [serialize_build(row) for row in rows]


@app.post(
    "/projects/{project_id}/build",
    dependencies=[Depends(verify_api_key)],
)
def build_uploaded_project(
    project_id: int,
    saved_name: str,
    db: Session = Depends(get_db),
):
    ensure_build_table(db)
    # Confirm that the project exists.
    project = db.query(Project).filter(
        Project.id == project_id
    ).first()

    if project is None:
        raise HTTPException(
            status_code=404,
            detail="Project not found.",
        )

    # Accept only the generated ZIP filenames created by the upload endpoint.
    if not re.fullmatch(r"[a-f0-9]{32}\.zip", saved_name):
        raise HTTPException(
            status_code=400,
            detail="Invalid uploaded ZIP filename.",
        )

    zip_path = UPLOAD_DIR / str(project_id) / saved_name

    # If local file does not exist, check if it can be retrieved from S3
    if not zip_path.is_file():
        s3 = get_s3_client()
        if s3:
            try:
                s3_key = f"uploads/{project_id}/{saved_name}"
                zip_path.parent.mkdir(parents=True, exist_ok=True)
                s3.download_file(S3_BUCKET, s3_key, str(zip_path))
            except Exception as exc:
                import logging
                logging.getLogger("cloudforge").warning(f"S3 download failed for key {s3_key}: {exc}")

    if not zip_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Uploaded ZIP not found for this project.",
        )

    client = None
    build_path = None

    try:
        # Validate the archive again before extracting it.
        with zipfile.ZipFile(zip_path, "r") as archive:
            entries = archive.infolist()

            if not entries or len(entries) > MAX_ARCHIVE_FILES:
                raise HTTPException(
                    status_code=400,
                    detail="The archive is empty or contains too many entries.",
                )

            total_size = 0
            python_files = []

            for entry in entries:
                name = entry.filename.replace("\\", "/")
                parts = name.split("/")
                mode = entry.external_attr >> 16

                if (
                    name.startswith("/")
                    or any(part in ("", ".", "..") for part in parts[:-1])
                    or (parts and ":" in parts[0])
                    or (mode & 0o170000) == 0o120000
                    or entry.flag_bits & 0x1
                ):
                    raise HTTPException(
                        status_code=400,
                        detail="The archive contains an unsafe entry.",
                    )

                if entry.is_dir():
                    continue

                total_size += entry.file_size

                if total_size > MAX_EXTRACTED_SIZE:
                    raise HTTPException(
                        status_code=413,
                        detail="Extracted files would exceed 25 MB.",
                    )

                if name.lower().endswith(".py"):
                    python_files.append(name)

            if not python_files:
                raise HTTPException(
                    status_code=400,
                    detail="The ZIP must contain at least one Python file.",
                )

            # Choose a clear entry point.
            if "main.py" in python_files:
                entrypoint = "main.py"
            elif len(python_files) == 1:
                entrypoint = python_files[0]
            else:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Multiple Python files found. Add a main.py file "
                        "at the ZIP root to identify the entry point."
                    ),
                )

            # Create a fresh, unique build directory.
            build_id = uuid.uuid4().hex
            build_path = BUILD_DIR / str(project_id) / build_id
            build_path.mkdir(parents=True, exist_ok=False)

            # Extract each file manually with real-time extracted byte counting (Zip-bomb defense)
            extracted_bytes = 0
            for entry in entries:
                if entry.is_dir():
                    continue

                name = entry.filename.replace("\\", "/")
                destination = (build_path / name).resolve()

                if not destination.is_relative_to(build_path.resolve()):
                    raise HTTPException(
                        status_code=400,
                        detail="Unsafe extraction path detected.",
                    )

                destination.parent.mkdir(
                    parents=True,
                    exist_ok=True,
                )

                with archive.open(entry) as source:
                    with destination.open("wb") as target:
                        while True:
                            chunk = source.read(64 * 1024)
                            if not chunk:
                                break
                            extracted_bytes += len(chunk)
                            if extracted_bytes > MAX_EXTRACTED_SIZE:
                                raise HTTPException(
                                    status_code=413,
                                    detail="Extracted files exceed the 25 MB limit.",
                                )
                            target.write(chunk)

        # Generate our own Dockerfile; ignore any uploaded Dockerfile.
        dockerfile = (
            "FROM python:3.13-slim\n"
            "WORKDIR /app\n"
            "COPY . /app\n"
            f'CMD ["python", "{entrypoint}"]\n'
        )

        (build_path / "Dockerfile").write_text(
            dockerfile,
            encoding="utf-8",
        )

        # Build the image using the local Docker Engine.
        image_name = f"cloudforge-project-{project_id}:{build_id[:12]}"
        client = docker.from_env()

        build_logs = []

        image, log_stream = client.images.build(
            path=str(build_path),
            tag=image_name,
            rm=True,
            forcerm=True,
            network_mode="none",
        )

        # Return a compact summary rather than unlimited build output.
        for event in log_stream:
            if "stream" in event:
                build_logs.append(event["stream"].rstrip())

            if "error" in event:
                raise RuntimeError(event["error"])

        final_image_name = image.tags[0] if image.tags else image_name
        db.execute(
            insert(BuildImage).values(
                project_id=project_id,
                image_name=final_image_name,
                saved_name=saved_name,
                entrypoint=entrypoint,
                build_logs="\\n".join(build_logs[-40:]),
            )
        )
        db.commit()

        return {
            "message": "Docker image built successfully and saved to build history.",
            "project_id": project_id,
            "image": final_image_name,
            "entrypoint": entrypoint,
            "status": "built",
            "build_logs": build_logs[-40:],
            "note": (
                "The image was built but the uploaded Python program "
                "has not been executed."
            ),
        }

    except HTTPException:
        raise

    except DockerException as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Docker build failed: {str(exc)[:1000]}",
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Build failed: {str(exc)[:1000]}",
        )

    finally:
        if client is not None:
            client.close()
