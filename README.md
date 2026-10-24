# Cloud Forge

A lightweight micro-PaaS platform that accepts Python application archives (ZIP), dynamically synthesises isolated Docker container images, and executes them within strict Linux kernel cgroup boundaries.

Built with **FastAPI · React 19 · PostgreSQL · Docker · Nginx · AWS CloudFormation**.

**Live AWS Prototype:** [http://54.252.152.116/](http://54.252.152.116/)  
**Deployment Region:** AWS Sydney (`ap-southeast-2`)  
**Target Branch:** `strengthen`  

---

## Architecture Overview

Cloud Forge runs both as a local developer sandbox and as an automated cloud-native deployment on Amazon Web Services (AWS) in `ap-southeast-2` (Sydney).

```
[ Browser / Client ]
         │ (HTTP Port 80)
         ▼
[ Nginx Reverse Proxy & Rate Limiter ]
   ├── Static Single Page App (/var/www/cloudforge - React 19)
   ├── Security Headers (nosniff, DENY, X-XSS-Protection, Referrer-Policy)
   └── Internal Reverse Proxy (/projects, /health)
         │
         ▼ (127.0.0.1:8000)
[ FastAPI Application Backend (systemd daemon) ]
   ├── PostgreSQL 15 Relational DB (Docker host volume /var/lib/cloudforge/pgdata)
   ├── S3 Artifacts Bucket (uploads/ with 30-day lifecycle) [Fallback: local disk]
   ├── SSM Parameter Store (DB credentials) [Fallback: local .env]
   └── Docker Engine Daemon (/var/run/docker.sock)
         │
         ▼ (docker run with strict cgroup constraints)
   [ Sandboxed Execution Container ]
       ├── Memory quota: 128 MiB ceiling
       ├── CPU ceiling: 0.5 vCPU (500,000,000 nano-CPUs)
       ├── Process ceiling: 64 PIDs
       ├── Root filesystem: Read-only
       ├── Linux capabilities: ALL dropped
       ├── User: nobody (UID 65534)
       ├── Network: Disabled (network_disabled=True)
       └── Watchdog: 30-second execution cutoff timeout
```

See [`docs/architecture.mmd`](docs/architecture.mmd) for the detailed Mermaid cloud architecture diagram.

---

## Live Deployment vs. Infrastructure-as-Code

To ensure clarity for evaluation and academic review, Cloud Forge distinguishes between the running demonstration server and its infrastructure code:

1. **Live AWS Deployment Prototype:**
   * Runs on a single EC2 `t3.micro` instance (`i-0a2230a900eee725f`) in Sydney (`ap-southeast-2`) at `http://54.252.152.116/`.
   * Hosts Nginx, FastAPI, PostgreSQL 15 in Docker, and the React frontend.
   * PostgreSQL data is persisted on host volume `/var/lib/cloudforge/pgdata`. A verified full database backup is stored at `/home/ec2-user/backups/cloudforge_backup_.sql`.
   * Nginx applies active rate limiting (`10 req/s`) and strict security headers.
   * Backend port 8000 is closed to public ingress; SSH (port 22) is restricted to the administrator IP.
2. **Infrastructure-as-Code (`infra/cloudforge.yaml`):**
   * A complete, validated CloudFormation template defining an isolated VPC, public subnet, Internet Gateway, Route Table, Security Group, S3 Artifact Bucket, IAM Instance Profile, CloudWatch Alarms, and an AWS Budget ($5/mo).
   * Passed `cfn-lint` with 0 errors.
   * **Note:** The template represents reusable IaC for automated multi-region deployment or disaster recovery; it has not been deployed as a second AWS stack to prevent redundant cloud billing.

---

## Security Model & Verified Controls

* **Safe Archive Ingestion:** Enforces a 10 MB upload ceiling, Zip-Slip path traversal prevention, symlink elimination, and a 100-file count ceiling.
* **Real-Time Streaming Bomb Defense:** Unpacks entries in 64 KB chunks, immediately raising HTTP 413 if accumulated decompressed bytes exceed 25 MB (preventing spoofed header attacks).
* **Deterministic Build Synthesis:** Auto-generates an unprivileged `python:3.13-slim` Dockerfile template. Discards any user-supplied Dockerfile instructions. Compiles with `network_mode="none"`.
* **Container Sandbox Boundaries:** Runs with memory limit 128 MiB, 0.5 CPU quota, 64 PIDs, dropped capabilities (`CAP_DROP=ALL`), read-only rootfs, unprivileged user `nobody`, disabled network, and a 30-second timeout.
* **Credential Protection:** Zero credentials committed to Git. Database passwords are dynamically managed via AWS Systems Manager Parameter Store in production, with fallback to local `.env` for local laptop development.

### Authentication Status & Known Security Limitation
* The FastAPI backend contains an optional API key authentication dependency (`verify_api_key`) inspecting `X-API-Key` against the `API_KEY` environment variable.
* **Known Limitation:** On the public live demo server, `API_KEY` is currently unset to permit review and evaluation of the React dashboard without requiring browser token injections. In a commercial environment, mandatory user authentication and HTTPS (TLS) are required before public multi-tenant production use.

---

## Documentation Links

* [Comprehensive Academic Report](docs/academic_report.md)
* [Automated & Live Test Verification Report](docs/test_report.md)
* [Screenshot Catalog & Submission Evidence](docs/screenshots/README.md)
* [AWS Cost Breakdown & Teardown Guide](docs/cost.md)
* [Mermaid Architecture Diagram](docs/architecture.mmd)

---

## Local Development Setup

### Prerequisites
* Python 3.11+ / 3.13
* Node.js 20+ / 22
* Docker Desktop running locally
* PostgreSQL 15+

### 1. Configure Local Environment
```bash
cp .env.example .env
# Set DATABASE_URL in .env
```

### 2. Start PostgreSQL via Docker
```bash
docker run -d \
  --name cloudforge-db \
  --restart unless-stopped \
  -e POSTGRES_USER=cloudforge \
  -e POSTGRES_PASSWORD=<YOUR_LOCAL_DB_PASSWORD> \
  -e POSTGRES_DB=cloudforge \
  -p 127.0.0.1:5432:5432 \
  postgres:15-alpine
```

### 3. Setup Python Backend
```bash
python -m venv .venv

# Windows
.\.venv\Scripts\activate
pip install -r requirements.txt

# Linux / macOS
source .venv/bin/activate
pip install -r requirements.txt
```

### 4. Run the Backend API
```bash
uvicorn main:app --reload --port 8000
```

### 5. Run the Frontend (Vite)
```bash
cd frontend
npm install
npm run dev
```

---

## Running Automated Validation Tests

```bash
# Run backend pytest test suite
pytest tests/ -v

# Validate CloudFormation IaC template
python -c "import pathlib, cfnlint.api; m = cfnlint.api.lint_file(pathlib.Path('infra/cloudforge.yaml')); print(len(m))"

# Build and lint frontend
cd frontend
npm run lint
npm run build
```
