# Cloud Forge — Comprehensive Academic Report

**Project Title:** Cloud Forge: Micro-PaaS Platform with Cgroup Container Sandboxing and Cloud-Native AWS Automation
**Author / Developer:** Eben John Jose (eben.johnjose2024@vitstudent.ac.in)
**Registration Number:** 24BCE2459
**Degree Program:** B.Tech Computer Science and Engineering (CORE), School of Computer Science and Engineering, VIT Vellore
**Repository:** [https://github.com/Eben923/cloud-forge](https://github.com/Eben923/cloud-forge)
**Branch:** `strengthen`
**Base Verified Commit SHA:** `1cbe9f498d73277f3dcff1614ee339fa79b2e158`
**Live Application URL:** [http://54.252.152.116/](http://54.252.152.116/)
**Deployment Region:** Amazon Web Services (AWS) `ap-southeast-2` (Sydney)

---

## Table of Contents
1. Executive Abstract
2. Introduction & Motivation
3. System Architecture & Component Interconnect
4. Delineation: Live Deployment vs. Infrastructure-as-Code
5. Ingestion Security & Archive Verification Engine
6. Docker Image Build Engine & Synthetic Dockerfile
7. Container Execution Sandbox & Linux Cgroup Boundaries
8. Relational Database Models & Persistence Mechanisms
9. Frontend Architecture: React Components & Workflow UI
10. Backend Architecture: FastAPI Services & Execution Pipeline
11. End-to-End Request Flow & Lifecycle Sequence
12. Live Application Demonstration: Frontend & Backend Interfaces
13. Nginx Edge Reverse Proxy & Rate Limiting
14. AWS Infrastructure as Code & Cloud Security Architecture
15. Testing Methodology, Test Suites & Verification Results
16. Cost Modeling, Budget Guardrails & Safe Teardown Procedures
17. Known Limitations, Security Posture & Conclusions
18. Formal Academic References

---

## 1. Executive Abstract

Modern cloud computing platforms increasingly require the capability to ingest, compile, and execute untrusted user-submitted source code in multi-tenant environments. However, traditional multi-tenant execution frameworks present significant attack surfaces, including kernel privilege escalation, resource exhaustion attacks (e.g., memory exhaustion, CPU starvation, and process table flooding), arbitrary file overwrite attacks (Zip Slip), and unauthorized lateral network reconnaissance [1, 2, 3].

Cloud Forge addresses these fundamental systems engineering challenges by implementing an automated micro-Platform-as-a-Service (micro-PaaS). Developed in Python using FastAPI, React 19, and PostgreSQL 15, Cloud Forge automates the end-to-end lifecycle of user code execution. The platform ingests source code archives, validates them against directory traversal and compression bomb vulnerabilities, synthesizes unprivileged container image definitions, compiles images in total network isolation, and executes workloads within strictly bounded Linux cgroups and namespace sandboxes [6, 7].

The prototype is operational on Amazon Web Services (AWS) in the Sydney region (`ap-southeast-2`), while a companion CloudFormation template establishes an enterprise-grade Infrastructure-as-Code specification with automated monitoring and cost guardrails [4, 9].

---

## 2. Introduction & Motivation

The democratization of cloud computing has transformed software development, allowing engineering teams to deploy microservices rapidly through containerized workflows. However, in educational environments, automated grading systems, developer sandboxes, and shared PaaS platforms, executing code submitted by unverified third parties introduces critical operational vulnerabilities [1, 5]:

1. **Host Privilege Escalation:** Arbitrary scripts can invoke kernel system calls, inspect memory, or attempt container escapes [6].
2. **Resource Starvation (Denial of Service):** Unconstrained processes can exhaust system memory, starve the CPU scheduler, or spawn recursive fork-bombs [2].
3. **Network Pivot Attacks:** Untrusted workloads can probe internal VPC resources, query cloud instance metadata services (IMDS), or launch external distributed denial-of-service (DDoS) campaigns [4].

Cloud Forge was engineered to provide a self-hosted, lightweight micro-PaaS that bridges the gap between total security and minimal infrastructure overhead. By leveraging Linux kernel primitives—specifically Control Groups (cgroups v2) and Namespaces—within an automated container lifecycle, Cloud Forge achieves enterprise-grade isolation on standard commodity cloud compute instances.

---

## 3. System Architecture & Component Interconnect

Cloud Forge follows a modular client-server architecture deployed within an AWS EC2 instance (`t3.micro`, Sydney region):

```
[ User Browser / HTTP Client ]
             │ (Port 80 TCP)
             ▼
[ Nginx Reverse Proxy (Frontend & Rate Limiter) ]
     ├── Serves Static SPA (/var/www/cloudforge - React 19)
     ├── Applies Security Headers (nosniff, DENY, XSS-Protection, Referrer-Policy)
     ├── Rate Limiting: 10 requests/sec with burst buffer of 20 (api_limit zone)
     └── Reverse Proxies API calls (/health, /projects) to 127.0.0.1:8000
             │
             ▼
[ FastAPI Backend (Python 3.11 Systemd Daemon) ]
     ├── Ingestion & Validation: 10 MB upload cap, Zip-Slip path check, 25 MB decompression limit
     ├── Relational Persistence: PostgreSQL 15 via SQLAlchemy 2.0 & Psycopg 3
     ├── Build Engine: Template Dockerfile synthesis (python:3.13-slim, network_mode="none")
     └── Execution Manager: Docker SDK sandbox runner with strict Linux cgroups
             │
             ▼
[ Ephemeral Sandboxed Container ]
     ├── Memory Limit: 128 MiB strict ceiling (kernel OOM terminates if exceeded)
     ├── CPU Quota: 0.5 vCPU (500,000,000 nano-CPUs)
     ├── Process Ceiling: 64 PIDs (fork bomb mitigation)
     ├── Network Isolation: Disabled (network_disabled=True)
     ├── Filesystem: Read-only root (read_only=True)
     ├── User Privileges: Non-root user `nobody` (UID 65534)
     ├── Linux Capabilities: ALL dropped (cap_drop=["ALL"])
     ├── Security Options: no-new-privileges:true
     └── Execution Watchdog: 30-second hard execution cutoff timeout
```

### Architectural Interconnect & Defense-in-Depth Rationale
The four tiers operate in strict unidirectional communication hierarchies. Untrusted clients interact exclusively with Nginx on port 80. Nginx handles static asset delivery and request throttling, isolating the backend FastAPI process from direct Internet exposure. FastAPI enforces application-level validation and coordinates Docker container execution using the local Unix socket. Ephemeral execution containers have no network interfaces or host volume mounts, ensuring that compromised container processes cannot reach the host filesystem, the PostgreSQL database, or other tenant workloads [1, 6].

---

## 4. Delineation: Live Deployment vs. Infrastructure-as-Code

To ensure complete academic transparency, Cloud Forge maintains a strict separation between what is actively deployed and running on AWS, and what is provided as validated Infrastructure-as-Code:

| Architectural Dimension | Live AWS Prototype (`54.252.152.116`) | CloudFormation Specification (`infra/cloudforge.yaml`) |
| :--- | :--- | :--- |
| **Operational State** | **Active & Live** in Sydney (`ap-southeast-2`) | **Validated** via `cfn-lint 1.58.0` (0 errors), not deployed as a stack |
| **Target Host** | EC2 `t3.micro` instance (`i-0a2230a900eee725f`) | AWS EC2 `t3.micro` configured via declarative template |
| **Network Topology** | Default VPC (`172.31.0.0/16`), Public Subnet | Dedicated custom VPC (`10.0.0.0/16`), PublicSubnet (`10.0.1.0/24`), IGW, RouteTable |
| **SSH Management** | Locked security group rules | Parameter `AdminCidr` enforces explicit CIDR between `/16` and `/32` (`0.0.0.0/0` rejected) |
| **Ingress Controller** | Nginx reverse proxy with rate limiting & security headers | Automated Nginx reverse proxy configured via CloudFormation UserData |
| **Application Layer** | FastAPI systemd daemon (`127.0.0.1:8000`), Python 3.11 host | Automated systemd service installation with Python virtual environment |
| **Frontend Assets** | React 19 Single Page Application built to `/var/www/cloudforge` | Automated deployment of compiled static assets to web root |
| **Relational Database** | PostgreSQL 15 container (`cloudforge-db`) on `/var/lib/cloudforge/pgdata` | PostgreSQL 15 container with host volume mapping initialized via UserData |
| **Secret Provisioning** | Host environment file (`/home/ec2-user/app/.env`, mode 600) | AWS Systems Manager (SSM) Parameter Store SecureString bootstrapping |
| **Storage & Alarms** | Local host volume; verified backup at `/home/ec2-user/backups/` | S3 artifact bucket (30-day lifecycle); CloudWatch CPU & status alarms |
| **Budget Ceiling** | Monitored manually via AWS Billing Console | `AWS::Budgets::Budget` enforcing **$5.00/month** limit with direct email alert at 80% ($4.00) |

---

## 5. Ingestion Security & Archive Verification Engine

The file upload endpoint (`POST /projects/{id}/upload`) is the primary untrusted data ingress into the platform. A multi-stage validation pipeline implemented in `main.py` sanitizes archives before processing:

1. **Upload Size Cap:** Reads at most `MAX_UPLOAD_SIZE + 1` bytes (**10 MB**). Excess uploads raise HTTP 413 immediately.
2. **Directory Traversal (Zip-Slip):** Backslashes are normalized to forward slashes. Any entry starting with `/`, containing `..`, empty segments, or drive letters (`:`) raises HTTP 400.
3. **Entry Count Threshold:** Archives containing more than **100 entries** raise HTTP 400 to prevent inode exhaustion.
4. **Symlink Rejection:** POSIX mode bits (`entry.external_attr >> 16 & 0o170000 == 0o120000`) are inspected; symlinks raise HTTP 400.
5. **Streaming Bomb Guard:** Decompressed streams are processed in 64 KB chunks; cumulative bytes are strictly capped at `MAX_EXTRACTED_SIZE` (**25 MB**). Excess streams raise HTTP 413.
6. **Required Python Source:** Archives must contain at least one `.py` file. The engine selects `main.py` or `app.py` as entrypoint.

```python
# Excerpt from main.py - Path Sanitization and Bomb Guard
for entry in entries:
    name = entry.filename.replace("\\", "/")
    parts = name.split("/")

    # Reject absolute paths, traversal segments, and drive letters
    if (name.startswith("/") or
        any(part in ("", ".", "..") for part in parts[:-1]) or
        (parts and ":" in parts[0])):
        raise HTTPException(status_code=400,
                            detail="Unsafe file path in archive.")

    # Reject symbolic links via POSIX file mode bits
    mode = entry.external_attr >> 16
    if (mode & 0o170000) == 0o120000:
        raise HTTPException(status_code=400,
                            detail="Symbolic links are not allowed.")

# Streaming decompression bomb check (enforces 25 MB ceiling)
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
                    raise HTTPException(status_code=413,
                        detail="Uncompressed archive exceeds 25 MB limit.")
```

---

## 6. Docker Image Build Engine & Synthetic Dockerfile

Allowing users to supply arbitrary Dockerfiles represents an unacceptable security vulnerability, as Dockerfiles can introduce malicious `RUN` commands, mount sensitive host sockets, or configure root privileges.

Cloud Forge resolves this by **completely discarding user-provided Dockerfiles** and dynamically synthesizing a deterministic, unprivileged Dockerfile template:

```dockerfile
FROM python:3.13-slim
WORKDIR /app
COPY . /app
CMD ["python", "{entrypoint}"]
```

*Note on Base Image Tag:* The base image `python:3.13-slim` is a mutable tag upstream. In a high-assurance production environment, pinning to an immutable SHA-256 digest (e.g., `python:3.13-slim@sha256:...`) is recommended to ensure reproducible, tamper-proof builds.

### Compilation in Total Network Isolation
Container images are compiled with `network_mode="none"`:

```python
# Excerpt from main.py - Network-Isolated Container Compilation
image, log_stream = client.images.build(
    path=str(build_path),
    tag=image_name,
    rm=True,
    forcerm=True,
    network_mode="none"  # Complete network isolation during build
)
```

By enforcing `network_mode="none"`, the build process cannot establish outbound connections, exfiltrate data, or query AWS instance metadata service (`http://169.254.169.254`).

---

## 7. Container Execution Sandbox & Linux Cgroup Boundaries

When a deployment is triggered (`POST /projects/{id}/deployments`), the Docker engine launches an ephemeral container with strict Linux cgroup and namespace boundaries:

```python
# Excerpt from main.py - Linux Cgroup Sandboxing and Execution Watchdog
container = client.containers.run(
    image=image_name, detach=True, network_disabled=True,
    mem_limit="128m", nano_cpus=500_000_000, pids_limit=64,
    read_only=True, cap_drop=["ALL"],
    security_opt=["no-new-privileges:true"],
    user="nobody", auto_remove=False,
    labels={"cloudforge.managed": "true",
            "cloudforge.project_id": str(project_id)}
)
# Active watchdog loop with 30-second hard cutoff
deadline = time.monotonic() + 30
while time.monotonic() < deadline:
    container.reload()
    if container.status in ("exited", "dead"):
        break
    time.sleep(0.5)
else:
    container.stop(timeout=2)
    deployment.status = "failed"
```

| Security Boundary | Configuration | Mechanism & Attack Mitigation |
| :--- | :--- | :--- |
| **Memory Ceiling** | `mem_limit="128m"` | Linux `memory.max` cgroup limit; kernel OOM terminates processes exceeding 128 MB |
| **CPU Quota** | `nano_cpus=500_000_000` | Linux CFS bandwidth control allocating maximum 50% of 1 CPU core |
| **Process Table Cap** | `pids_limit=64` | `pids.max` cgroup limit; prevents fork bomb denial-of-service attacks |
| **Filesystem State** | `read_only=True` | Root filesystem mounted read-only; blocks unauthorized disk writes |
| **Network Egress** | `network_disabled=True` | Isolated network namespace without default gateway; blocks external egress |
| **Kernel Capabilities** | `cap_drop=["ALL"]` | Drops all Linux capabilities (e.g., `CAP_SYS_ADMIN`, `CAP_NET_RAW`) |
| **Privilege Escalation**| `no-new-privileges:true` | Prohibits `setuid`/`setgid` binary execution and privilege transitions |
| **Execution User** | `user="nobody"` | Runs under unprivileged UID 65534 instead of container root |
| **Watchdog Cutoff** | 30-second polling loop | Terminates runaway processes if execution exceeds 30 seconds |

---

## 8. Relational Database Models & Persistence Mechanisms

Cloud Forge utilizes PostgreSQL 15 as its persistent relational datastore, accessed via SQLAlchemy 2.0 and the modern Psycopg 3 driver [8, 12].

### Database Schema Models (`models.py` & `main.py`)

```python
# models.py - Relational Models for Projects and Deployments
class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    app_type = Column(String(50), nullable=False, default="python")
    repository_url = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    deployments = relationship("Deployment", back_populates="project",
                               cascade="all, delete-orphan")

class Deployment(Base):
    __tablename__ = "deployments"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"),
                        nullable=False)
    status = Column(String(30), nullable=False, default="queued")
    logs = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    project = relationship("Project", back_populates="deployments")
```

In addition, `main.py` defines the `cloudforge_build_images` table tracking compiled Docker image tags associated with each project.

### Connection Pooling & Concurrency Protection (`database.py`)

```python
# database.py - Connection Factory with SSM Parameter Store Fallback
DATABASE_URL = os.getenv("DATABASE_URL")
ssm_param_name = os.getenv("SSM_DB_PASSWORD_PARAM")
if ssm_param_name:
    try:
        ssm = boto3.client("ssm", region_name=os.getenv("AWS_REGION", "ap-southeast-2"))
        response = ssm.get_parameter(Name=ssm_param_name, WithDecryption=True)
        db_password = response["Parameter"]["Value"]
        DATABASE_URL = (
            f"postgresql+psycopg://{db_user}:{db_password}@"
            f"{db_host}:{db_port}/{db_name}"
        )
    except Exception as exc:
        logging.getLogger("cloudforge").error(f"SSM fetch failed: {exc}")
        if not DATABASE_URL:
            raise RuntimeError("No database credentials available.")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
```

Schema migrations are synchronized across multi-worker deployments using PostgreSQL transaction-scoped advisory locks:

```python
# main.py - Concurrency Protection for Table Schema Creation
def ensure_build_table(db: Session):
    # Acquire advisory transaction lock to serialize schema initialization
    db.execute(text("SELECT pg_advisory_xact_lock(834725190)"))
    BuildImage.metadata.create_all(bind=db.connection(), checkfirst=True)
```

### Persistence, Backup & Cascading Deletions
* **Container:** PostgreSQL 15.19 Alpine running in Docker container `cloudforge-db`.
* **Host Mount:** Volume mapped directly from `/var/lib/cloudforge/pgdata` to `/var/lib/postgresql/data`.
* **Verified Backup:** Logical SQL backup created via `pg_dump` at `/home/ec2-user/backups/cloudforge_backup_*.sql` (7,382 bytes).
* **Cascading Deletions:** Configured with `ondelete="CASCADE"`. Deleting a project via `DELETE /projects/{id}` automatically purges associated deployment runs and build image records in an atomic transaction.

---

## 9. Frontend Architecture: React Components & Workflow UI

The Cloud Forge user interface is implemented in React 19 using Vite as the modern frontend build toolchain [11]. The single-page application (`frontend/src/App.jsx`) provides a responsive, component-driven dashboard organized into four distinct functional views: Overview, Projects, Upload Project, and Deployments.

### Component State Architecture
The top-level `App` component manages centralized state:

```javascript
// frontend/src/App.jsx - Centralized Dashboard State Management
const [projects, setProjects] = useState([])
const [deployments, setDeployments] = useState([])
const [buildImages, setBuildImages] = useState({})
const [apiStatus, setApiStatus] = useState('Checking...')
const [selectedZip, setSelectedZip] = useState(null)
const [uploading, setUploading] = useState(false)
const [building, setBuilding] = useState(false)
const [buildLogs, setBuildLogs] = useState([])
```

### Client-Side ZIP File Selection & Validation
Before uploading, the frontend validates the file extension and enforces the 10 MiB limit:

```javascript
// frontend/src/App.jsx - Client-Side Validation and Upload
function selectZip(event) {
  const file = event.target.files?.[0]
  if (!file) return
  if (!file.name.toLowerCase().endsWith('.zip')) {
    setMessage('Please select a ZIP file.')
    event.target.value = ''
    return
  }
  if (file.size > MAX_ZIP_SIZE) { // 10 * 1024 * 1024 bytes
    setMessage('The ZIP file must be 10 MB or smaller.')
    event.target.value = ''
    return
  }
  setSelectedZip(file)
  setMessage(`${file.name} is ready to upload.`)
}

async function uploadProjectZip() {
  const formData = new FormData()
  formData.append('file', selectedZip)
  setUploading(true)
  const response = await fetch(
    `${API_URL}/projects/${uploadProjectId}/upload`,
    { method: 'POST', body: formData }
  )
  const result = await response.json()
  setSavedZipName(result.saved_name)
}
```

### Build & Deployment Invocation
The frontend provides dedicated triggers to compile images and execute deployments via REST:

```javascript
// frontend/src/App.jsx - Build Invocation and Sandboxed Deployment
async function buildUploadedProject() {
  setBuilding(true)
  const query = encodeURIComponent(sourceZipName)
  const response = await fetch(
    `${API_URL}/projects/${uploadProjectId}/build?saved_name=${query}`,
    { method: 'POST' }
  )
  const result = await response.json()
  setBuildLogs(result.build_logs || [])
}

async function deployProject(project) {
  const savedBuild = buildImages[String(project.id)]
  const imageTag = encodeURIComponent(savedBuild.image_name)
  const response = await fetch(
    `${API_URL}/projects/${project.id}/deployments?image_name=${imageTag}`,
    { method: 'POST' }
  )
  const result = await response.json()
  setMessage(`Deployment #${result.id} for ${project.name}: ${result.status}.`)
}
```

---

## 10. Backend Architecture: FastAPI Services & Execution Pipeline

The backend service (`main.py`) is implemented in FastAPI, running as a systemd background daemon on `127.0.0.1:8000` [7]. It exposes 11 endpoints orchestrating archive validation, image compilation, and sandboxed Docker execution.

### Complete Verified API Endpoint Routing Table

| HTTP Method | Path / Endpoint | Authentication Status | Functional Responsibility |
| :--- | :--- | :--- | :--- |
| `GET` | `/` | Open / Public | API metadata, platform status, and documentation pointers |
| `GET` | `/health` | Open / Public | Liveness probe returning `{"status": "healthy"}` |
| `POST` | `/projects` | Requires API Key (bypass if unset) | Creates a new project entity in PostgreSQL |
| `GET` | `/projects` | Requires API Key (bypass if unset) | Lists all registered projects with metadata |
| `GET` | `/projects/{project_id}` | Requires API Key (bypass if unset) | Retrieves metadata for a specific project by ID |
| `POST` | `/projects/{project_id}/upload` | Requires API Key (bypass if unset) | Ingests, sanitizes, and decompresses user ZIP archive |
| `POST` | `/projects/{project_id}/build` | Requires API Key (bypass if unset) | Synthesizes Dockerfile and compiles container image |
| `GET` | `/projects/{project_id}/builds` | Requires API Key (bypass if unset) | Returns historical build image records and logs |
| `POST` | `/projects/{project_id}/deployments` | Requires API Key (bypass if unset) | Executes sandboxed container with strict cgroups |
| `GET` | `/projects/{project_id}/deployments` | Requires API Key (bypass if unset) | Lists deployment history and execution status |
| `GET` | `/deployments/{deployment_id}` | Requires API Key (bypass if unset) | Queries execution logs and exit code for a run |

### Whitelisting Image Tags & Watchdog Execution Loop

```python
# main.py - Strict Image Tag Whitelisting before Execution
@app.post("/projects/{project_id}/deployments",
          dependencies=[Depends(verify_api_key)])
def create_deployment(project_id: int, image_name: str,
                      db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Image tag must strictly match Cloud Forge project build pattern
    expected_pattern = rf"^cloudforge-project-{project_id}:[a-f0-9]{{12}}$"
    if not re.fullmatch(expected_pattern, image_name):
        raise HTTPException(status_code=400,
                            detail="Invalid image name for this project.")

# Execution watchdog loop (main.py)
deadline = time.monotonic() + 30
while time.monotonic() < deadline:
    container.reload()
    if container.status in ("exited", "dead"):
        break
    time.sleep(0.5)
else:
    container.stop(timeout=2)
    deployment.status = "failed"
    deployment.logs += "\nDeployment failed: execution exceeded 30 seconds."
    db.commit()
```

---

## 11. End-to-End Request Flow & Lifecycle Sequence

The lifecycle of an application deployment traverses multiple security boundaries:

```
[Browser / User]
       │
       │ 1. POST /projects/{id}/upload (ZIP archive)
       ▼
[Nginx Reverse Proxy]
       │ 2. Enforces client_max_body_size (10M), rate limit (10 r/s)
       ▼
[FastAPI Daemon]
       │ 3. Sanitizes entries, checks Zip-Slip, extracts < 25 MB
       │ 4. Synthesizes standard Dockerfile (python:3.13-slim)
       ▼
[Docker Daemon (Build)]
       │ 5. Compiles image with network_mode="none"
       │ 6. Registers image tag in cloudforge_build_images
       ▼
[FastAPI Daemon]
       │ 7. Invokes client.containers.run() with cgroups & dropped caps
       ▼
[Ephemeral Container]
       │ 8. Executes unprivileged workload (UID 65534, 128 MB RAM, 0.5 CPU)
       │ 9. Emits stdout/stderr logs
       ▼
[PostgreSQL Database]
       │ 10. Persists Deployment entity (status, logs, execution time)
       ▼
[React 19 SPA]
       │ 11. Displays real-time logs and deployment completion status
```

---

## 12. Live Application Demonstration: Frontend & Backend Interfaces

To demonstrate the complete operational fidelity of Cloud Forge, this section documents the actual, running web interfaces captured directly from the live AWS demonstration deployment (`http://54.252.152.116/`) and the local API development environment.

### 12.1 Web Dashboard & Project Overview
Figure 1 illustrates the Cloud Forge dashboard loaded in a browser. The interface displays real-time connection status (Connected to API), project summary metrics, and the project creation modal:

![Figure 1: Cloud Forge web dashboard overview](docs/screenshots/01_dashboard_overview.png)
*Figure 1: Cloud Forge web dashboard overview (captured live from AWS EC2 instance at http://54.252.152.116/).*

### 12.2 Project Management & Multi-Tenant Inventory
Figure 2 shows the active project inventory retrieved from the PostgreSQL 15 database. Each project card indicates the unique project ID, target runtime (Python 3.13), and action triggers:

![Figure 2: Project management interface](docs/screenshots/02_projects_list.png)
*Figure 2: Project management interface showing verified test projects persisted in PostgreSQL 15.*

### 12.3 Source Archive Ingestion Interface (ZIP Upload)
Figure 3 displays the client-side archive upload interface. The UI enforces the 10 MB file ceiling and performs pre-flight validation on the selected archive before initiating the HTTP POST transfer:

![Figure 3: Client-side ZIP upload workflow interface](docs/screenshots/03_upload_interface.png)
*Figure 3: Client-side ZIP upload workflow interface before file submission (10 MB upload ceiling enforced).*

### 12.4 Container Image Compilation & Build Logs
Figure 4 depicts the Docker image build execution output. The interface displays sequential Dockerfile build steps (FROM python:3.13-slim, WORKDIR, COPY, CMD) compiled in total network isolation:

![Figure 4: Real-time Docker image build execution result](docs/screenshots/04_build_result.png)
*Figure 4: Real-time Docker image build execution result showing synthesized 4-step compilation output.*

### 12.5 Sandboxed Deployment Execution & Runtime Logs
Figure 5 presents the deployment execution result and runtime audit log for an untrusted application workload. The log explicitly confirms all 7 kernel constraints and clean container termination:

![Figure 5: Deployment execution result card](docs/screenshots/05_deployment_result.png)
*Figure 5: Deployment execution result card displaying captured application output and exit code 0.*

### 12.6 Interactive FastAPI Swagger API Documentation (/docs)
Figure 6 shows the interactive OpenAPI / Swagger UI interface exposed by FastAPI at `/docs`. It provides real-time schema inspection, endpoint testing, and parameter documentation for all 11 API routes:

![Figure 6: Interactive FastAPI OpenAPI documentation interface](docs/screenshots/06_fastapi_swagger_docs.png)
*Figure 6: Interactive FastAPI OpenAPI documentation interface (/docs) showing all registered endpoints.*

---

## 13. Nginx Edge Reverse Proxy & Rate Limiting

Nginx functions as the edge ingress controller on standard HTTP port 80 [10]. It serves pre-compiled React static assets directly from `/var/www/cloudforge` and reverse-proxies API requests (`/health`, `/projects`) to the local FastAPI backend listening on `127.0.0.1:8000`.

### Security Hardening Headers
Nginx injects protective HTTP response headers on every transaction:
```nginx
add_header X-Content-Type-Options "nosniff" always;
add_header X-Frame-Options "DENY" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
```

### Rate Limiting Configuration
To mitigate volumetric denial-of-service attacks, Nginx defines a shared memory zone:
```nginx
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
limit_req zone=api_limit burst=20 nodelay;
```

---

## 14. AWS Infrastructure as Code & Cloud Security Architecture

Cloud Forge defines its cloud architecture through an infrastructure-as-code template (`infra/cloudforge.yaml`) validated with `cfn-lint 1.58.0` (0 errors) [9].

### Secure SSH Ingress Configuration
To prevent accidental world-open administrative access, the template enforces an explicit administrator CIDR block between `/16` and `/32`:

```yaml
AdminCidr:
  Type: String
  Description: CIDR block allowed SSH access. Defaults to VPC CIDR. Must be a valid IPv4 CIDR (/16 to /32).
  Default: 10.0.0.0/16
  AllowedPattern: ^(10\.\d{1,3}|172\.(1[6-9]|2\d|3[01])|192\.168)\.\d{1,3}\.\d{1,3}/(1[6-9]|2\d|3[0-2])$|^([1-9]\d{0,2})\.\d{1,3}\.\d{1,3}\.\d{1,3}/(1[6-9]|2\d|3[0-2])$
  ConstraintDescription: Must be a valid IPv4 CIDR between /16 and /32. World-open 0.0.0.0/0 is disallowed.
```

### Automated Monitoring & CloudWatch Alarms
* **EC2 CPU Utilization Alarm:** Triggers when average CPU exceeds 80% over 1 evaluation period of 300 seconds (`EvaluationPeriods: 1`, `Period: 300`).
* **EC2 Status Check Alarm:** Alerts immediately on hardware or hypervisor status check failure (`EvaluationPeriods: 1`, `Period: 60`).
* **S3 Artifact Storage:** Configures 30-day lifecycle expiration rule (`ExpirationInDays: 30`) to purge stale build artifacts automatically.

---

## 15. Testing Methodology, Test Suites & Verification Results

Verification was conducted across four verification domains: local unit and integration tests, static template analysis, frontend compilation checks, and live cloud end-to-end operational validation.

### A. Automated Local Pytest Suite (9/9 Passed)
* `test_reject_non_zip_file`: Validates HTTP 400 rejection for non-archive payloads.
* `test_reject_zip_without_python_files`: Rejects archives lacking Python code.
* `test_reject_zip_slip_path_traversal`: Blocks directory traversal attempts (`../../evil.py`).
* `test_reject_zip_with_too_many_files`: Enforces 100-file maximum ceiling.
* `test_reject_zip_bomb_exceeding_extracted_limit`: Confirms real-time chunk streaming aborts archives exceeding 25 MB with HTTP 413.
* `test_reject_invalid_image_tag_name`: Blocks attempts to deploy non-whitelisted container tags.
* `test_successful_sandboxed_deployment_execution`: Mocks Docker engine and asserts all 7 security isolation parameters (`mem_limit`, `nano_cpus`, `pids_limit`, `read_only`, `network_disabled`, `cap_drop`, `user`).
* `test_health_check_returns_healthy`: Verifies `/health` responds with HTTP 200.
* `test_api_key_auth_enforced_when_configured`: Verifies 401 rejection and valid key bypass when `API_KEY` is set.

*Test Pass Rate vs. Code Coverage:* The suite achieved a **100% pass rate (9 passed out of 9 tests)**. Statement and branch code coverage were not instrumented with `pytest-cov`, and 100% code coverage is not claimed.

### B. CloudFormation Linting (`cfn-lint 1.58.0`)
Executed against `infra/cloudforge.yaml`: **0 errors, 0 warnings**.

### C. Frontend Compilation & Linting
* `eslint`: **0 errors, 0 warnings**.
* `vite build`: Successfully transformed 17 modules, producing production assets (`dist/index.html`, `dist/assets/`).

### D. Live Server End-to-End Operational Verification (Exit Code 0)
* **Frontend Access:** HTTP 200 with Nginx security headers (`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Server: nginx`).
* **Health Probe:** `GET /health` returned `{"status":"healthy"}`.
* **Project Query:** `GET /projects` successfully retrieved active projects from PostgreSQL.
* **Execution Verification:** Uploaded and executed a verified Python application (`cloudforge-project-2:09da73e9e5a6`). Output produced: `"Live deployment verification successful!"` with container exit code `0`.

---

## 16. Cost Modeling, Budget Guardrails & Safe Teardown Procedures

To prevent unexpected cloud expenditures, Cloud Forge was architected to operate strictly within the AWS Free Tier [4]:

| Service Component | Configuration & Usage | Free Tier Allocation | Estimated Monthly Cost |
| :--- | :--- | :--- | :--- |
| **Amazon EC2** | 1 × `t3.micro` instance (Sydney) | 750 hours/month (12 months) | **$0.00** (Free Tier) / ~$7.45/mo |
| **Amazon EBS** | 1 × 20 GiB gp3 root volume | 30 GiB-months gp2/gp3 | **$0.00** (Free Tier) / ~$1.60/mo |
| **Amazon S3** | Build artifact storage (<1 GB) | 5 GB standard storage | **$0.00** (Free Tier) / ~$0.02/mo |
| **CloudWatch & SNS** | 2 metrics alarms, 1 SNS topic | 10 alarms, 1M requests | **$0.00** |
| **Total Estimated Cloud Expenditure** | | | **$0.00/month** (Free Tier) |

### CloudWatch Budget Guardrail
The template provisions an explicit `AWS::Budgets::Budget` resource setting a hard **$5.00/month** limit. When forecast expenditures cross 80% ($4.00), an automated alert notification is triggered.

### Safe Decommissioning Procedure & Volume Preservation Notice
A frequent administrator mistake is running `docker system prune -af --volumes`. The `--volumes` flag purges **all unattached Docker volumes**. In standard Docker database configurations, this destroys persistent database files. While Cloud Forge uses a host bind mount (`/var/lib/cloudforge/pgdata`), blind volume pruning remains an extreme hazard.

1. **Mandatory Backup:** Verify database backup:
   ```bash
   pg_dump -h 127.0.0.1 -U cloudforge cloudforge > /home/ec2-user/backups/pre_teardown_backup.sql
   ```
2. **Stop Application Daemons:**
   ```bash
   sudo systemctl stop cloudforge.service && sudo systemctl stop nginx
   ```
3. **Controlled Container Termination (Preserving Storage):**
   ```bash
   docker stop cloudforge-db && docker rm cloudforge-db  # Preserves /var/lib/cloudforge/pgdata
   ```
4. **Safe Image Pruning (Excluding Volumes):**
   ```bash
   docker image prune -f  # Do NOT use --volumes
   ```
5. **EC2 Instance Decommissioning:**
   ```bash
   aws ec2 terminate-instances --instance-ids i-0a2230a900eee725f --region ap-southeast-2
   ```

---

## 17. Known Limitations, Security Posture & Conclusions

### 17.1 Known Limitations of Live Demonstration
1. **Unenforced API-Key Authentication:** On the live prototype (`http://54.252.152.116/`), `API_KEY` is intentionally unset, permitting public access to all 11 endpoints to facilitate academic evaluation.
2. **Plaintext HTTP Transmission:** Traffic is transmitted unencrypted over port 80. Production deployments require TLS/SSL certificates (e.g., Let's Encrypt or AWS ACM).
3. **Template Status:** The CloudFormation template (`infra/cloudforge.yaml`) has been validated via `cfn-lint 1.58.0` with 0 errors, but has not been deployed as a live stack.

### 17.2 Security Posture Summary
Cloud Forge achieves defense-in-depth isolation across ingestion (10 MB upload cap, Zip-Slip guard, 25 MB stream extraction ceiling), compilation (synthetic Dockerfile, `network_mode="none"`), and execution (`mem_limit="128m"`, `nano_cpus=500_000_000`, `pids_limit=64`, `read_only=True`, `cap_drop=["ALL"]`, `user="nobody"`).

### 17.3 Conclusions
Cloud Forge successfully demonstrates an automated micro-PaaS combining rigorous application-level validation with Linux kernel-level containment. The platform proves that multi-tenant code execution can be made resilient and cost-effective within resource-constrained cloud environments.

---

## 18. Formal Academic References

1. Rosen, R. (2014). *Linux Kernel Networking: Implementation and Theory*. Apress. https://doi.org/10.1007/978-1-4302-6197-1
2. Menage, P. (2007). Adding Generic Process Containers to the Linux Kernel. In *Proceedings of the Linux Symposium* (Vol. 2, pp. 45-57).
3. Snyk Security Research. (2018). *Zip Slip Vulnerability: Arbitrary File Overwrite Through Directory Traversal*. Snyk Research. Available at: https://snyk.io/research/zip-slip-vulnerability
4. Amazon Web Services. (2024). *AWS Well-Architected Framework: Security Pillar*. AWS Whitepapers. Available at: https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/
5. Open Web Application Security Project (OWASP). (2023). *Top 10 API Security Risks*. OWASP Foundation. Available at: https://owasp.org/API-Security/
6. Docker Documentation. (2024). *Runtime Privilege and Linux Capabilities in Docker Engine*. Docker Inc. Available at: https://docs.docker.com/engine/security/
7. Ramirez, S. (2024). *FastAPI: Modern, High-Performance Web Framework for Python*. Available at: https://fastapi.tiangolo.com
8. Bayer, M. (2024). *SQLAlchemy: The Database Toolkit for Python*. Available at: https://www.sqlalchemy.org
9. Amazon Web Services. (2024). *AWS CloudFormation User Guide: Resource Specification*. AWS Documentation. Available at: https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/
10. Sysoev, I., & Nginx Authors. (2024). *Nginx Web Server Documentation: Rate Limiting and Reverse Proxy*. F5 Inc. Available at: https://nginx.org/en/docs/
11. You, E., & Vite Contributors. (2024). *Vite: Next Generation Frontend Tooling*. Available at: https://vite.dev
12. PostgreSQL Global Development Group. (2024). *PostgreSQL 15 Documentation: Reliability and Data Durability*. Available at: https://www.postgresql.org/docs/15/
