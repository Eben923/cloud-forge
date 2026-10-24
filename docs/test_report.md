# Cloud Forge Automated & Live Test Verification Report

**Date of Execution:** 2026-10-24  
**Target Environment:** Local Python 3.13 venv & AWS Sydney (`54.252.152.116`)  
**Branch:** `strengthen`  

---

## 1. Automated Unit & Integration Tests (Pytest)

Executed via: `pytest tests/ -v`

```text
============================= test session starts =============================
platform win32 -- Python 3.13.15, pytest-9.1.1, pluggy-1.7.0
rootdir: C:\Users\hp\Downloads\cloud-forge
plugins: anyio-4.15.1, asyncio-1.4.0
collected 9 items

tests/test_auth.py::test_api_key_auth_enforced_when_configured PASSED    [ 11%]
tests/test_deployments.py::test_reject_invalid_image_tag_name PASSED     [ 22%]
tests/test_deployments.py::test_successful_sandboxed_deployment_execution PASSED [ 33%]
tests/test_health.py::test_health_check_returns_healthy PASSED           [ 44%]
tests/test_security_zip.py::test_reject_non_zip_file PASSED              [ 55%]
tests/test_security_zip.py::test_reject_zip_without_python_files PASSED  [ 66%]
tests/test_security_zip.py::test_reject_zip_slip_path_traversal PASSED   [ 77%]
tests/test_security_zip.py::test_reject_zip_with_too_many_files PASSED   [ 88%]
tests/test_security_zip.py::test_reject_zip_bomb_exceeding_extracted_limit PASSED [100%]

======================== 9 passed, 1 warning in 0.42s =========================
```

---

## 2. Infrastructure as Code Validation (CloudFormation)

Executed via: `python -c "import pathlib, cfnlint.api; m = cfnlint.api.lint_file(pathlib.Path('infra/cloudforge.yaml')); print(len(m))"`

```text
Target: infra/cloudforge.yaml
Result: 0 errors detected. Template is valid AWS CloudFormation syntax.
```

---

## 3. Frontend Linting & Production Build (Vite)

Executed in `frontend/`:
* `npm run lint`: **0 ESLint errors**.
* `npm run build`: Output bundle `dist/assets/index-2mS8BsEF.js` (236.95 kB, gzip 73.14 kB). Build succeeded in 241ms.

---

## 4. Live Server End-to-End Operational Tests (`54.252.152.116`)

Executed against live AWS Sydney instance `i-0a2230a900eee725f`:

### Test 1: Health Check
```bash
curl -s http://54.252.152.116/health
```
**Response (HTTP 200):**
```json
{"status":"healthy"}
```

### Test 2: Security Headers Verification
```bash
curl -I -s http://54.252.152.116/health
```
**Headers Observed:**
```text
HTTP/1.1 200 OK
Server: nginx
Date: Sat, 24 Oct 2026 16:05:00 GMT
Content-Type: application/json
Content-Length: 20
Connection: keep-alive
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
```

### Test 3: Relational Persistence (Projects List)
```bash
curl -s http://54.252.152.116/projects
```
**Response (HTTP 200):**
```json
[
  {"id": 2, "name": "Live Verification Project", "app_type": "python", "repository_url": null},
  {"id": 1, "name": "AWS Test Project", "app_type": "python", "repository_url": null}
]
```

### Test 4: Container Build & Sandbox Execution
```bash
curl -s http://54.252.152.116/projects/2/deployments
```
**Response (HTTP 200):**
```json
[
  {
    "id": 4,
    "project_id": 2,
    "status": "success",
    "logs": "Starting project image: cloudforge-project-2:09da73e9e5a6\nContainer limits: memory=128 MiB, CPU=0.5, PIDs=64, network disabled, read-only root filesystem.\n\nApplication output:\nLive deployment verification successful!\n\nContainer exit code: 0\nApplication completed successfully."
  }
]
```

### Test 5: Ingress Port 8000 Blocked
```powershell
Test-NetConnection -ComputerName "54.252.152.116" -Port 8000
```
**Result:**
```text
WARNING: TCP connect to (54.252.152.116 : 8000) failed
TcpTestSucceeded : False
```
Confirmed that the backend port 8000 is not exposed to the public internet.
