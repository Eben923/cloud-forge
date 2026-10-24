import io
import zipfile
import pytest


def test_reject_non_zip_file(client):
    project_res = client.post("/projects", json={"name": "Test Project"})
    project_id = project_res.json()["id"]

    response = client.post(
        f"/projects/{project_id}/upload",
        files={"file": ("test.txt", io.BytesIO(b"not a zip"), "text/plain")},
    )
    assert response.status_code == 400
    assert "Please upload a ZIP file." in response.json()["detail"]


def test_reject_zip_without_python_files(client):
    project_res = client.post("/projects", json={"name": "Test Project"})
    project_id = project_res.json()["id"]

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as z:
        z.writestr("notes.txt", "hello world")
    buffer.seek(0)

    response = client.post(
        f"/projects/{project_id}/upload",
        files={"file": ("project.zip", buffer, "application/zip")},
    )
    assert response.status_code == 400
    assert "at least one Python" in response.json()["detail"]


def test_reject_zip_slip_path_traversal(client):
    project_res = client.post("/projects", json={"name": "Test Project"})
    project_id = project_res.json()["id"]

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as z:
        z.writestr("../../../evil.py", "print('evil')")
    buffer.seek(0)

    response = client.post(
        f"/projects/{project_id}/upload",
        files={"file": ("evil.zip", buffer, "application/zip")},
    )
    assert response.status_code == 400
    assert "unsafe file path" in response.json()["detail"]


def test_reject_zip_with_too_many_files(client):
    project_res = client.post("/projects", json={"name": "Test Project"})
    project_id = project_res.json()["id"]

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as z:
        for i in range(105):
            z.writestr(f"file_{i}.py", "print(1)")
    buffer.seek(0)

    response = client.post(
        f"/projects/{project_id}/upload",
        files={"file": ("too_many.zip", buffer, "application/zip")},
    )
    assert response.status_code == 400
    assert "too many entries" in response.json()["detail"]


def test_reject_zip_bomb_exceeding_extracted_limit(client):
    project_res = client.post("/projects", json={"name": "Test Project"})
    project_id = project_res.json()["id"]

    # 26 MB uncompressed content, highly compressed in ZIP
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("app.py", b"0" * (26 * 1024 * 1024))
    buffer.seek(0)

    response = client.post(
        f"/projects/{project_id}/upload",
        files={"file": ("zip_bomb.zip", buffer, "application/zip")},
    )
    assert response.status_code == 413
    assert "25 MB" in response.json()["detail"]
