# Cloud Forge

A lightweight micro-PaaS platform that accepts Python application archives (ZIP), dynamically synthesises isolated Docker container images, and executes them within strict Linux kernel cgroup boundaries.

Built with **FastAPI · React 19 · PostgreSQL · Docker · Nginx · AWS CloudFormation**.

---

## Architecture Overview

Cloud Forge is designed to run seamlessly both as a local development tool and as an automated cloud-native deployment on Amazon Web Services (AWS) in `ap-southeast-2` (Sydney).

```
[ Browser / Client ]
         │ (HTTP Port 80)
         ▼
[ Nginx Reverse Proxy & Rate Limiter ]
   ├── Static Single Page App (/var/www/cloudforge - React 19)
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
       • Memory quota: 128 MiB ceiling
       • CPU ceiling: 0.5 vCPU (500,000,000 nano-CPUs)
       • Process ceiling: 64 PIDs
       • Root filesystem: Read-only
       • Linux capabilities: ALL dropped
       • User: nobody (UID 65534)
       • Network: Disabled (network_disabled=True)
       • Watchdog: 30-second execution cutoff timeout
```

See [`docs/architecture.mmd`](docs/architecture.mmd) for the detailed Mermaid cloud architecture diagram.

---

## Features

1. **Safe Archive Ingestion:** Enforces a 10 MB upload ceiling, Zip-Slip path traversal prevention, symlink rejection, 100-file count ceiling, and real-time streaming zip-bomb decompressed byte counting (25 MB maximum).
2. **Deterministic Build Synthesis:** Auto-generates an unprivileged `python:3.13-slim` Dockerfile template. Discards any user-supplied Dockerfile instructions. Compiles with `network_mode="none"`.
3. **Defense-in-Depth Container Sandbox:** Executes containers with dropped capabilities, read-only root filesystems, unprivileged user `nobody`, and no network interfaces.
4. **Cloud-Native AWS Integration:**
   * **AWS CloudFormation (`infra/cloudforge.yaml`):** Reproduces the entire cloud infrastructure (VPC, public subnet, route tables, security groups, EC2 t3.micro, IAM role, S3 bucket, CloudWatch alarms, and AWS Budgets).
   * **AWS Systems Manager (SSM):** Key-less administration via Session Manager (`AmazonSSMManagedInstanceCore`) and secure parameter secret injection.
   * **Amazon S3:** Private bucket with AES-256 SSE, Block Public Access, and 30-day lifecycle expiration.
   * **Amazon CloudWatch & SNS:** CPU > 80% alarms, Status Check failure alarms, and email alerts.
   * **AWS Budgets:** Monthly cost ceiling alert ($5.00 threshold).
   * **IMDSv2 Enforced:** HttpTokens required with hop limit 1.
5. **Local Fallbacks:** Every AWS service (S3, SSM) falls back automatically to local equivalents (disk directory, `.env` file) when AWS environment variables are unset.

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
# Verify DATABASE_URL in .env
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
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

### 5. Run the React Frontend
```bash
cd frontend
npm install
npm run dev
```
Open **http://localhost:5173/** in your browser. The Vite dev server automatically proxies `/projects` and `/health` to `http://127.0.0.1:8000`.

---

## AWS CloudFormation Deployment

Deploy the entire architecture with a single command using the provided script:

```bash
# Make helper scripts executable
chmod +x scripts/*.sh

# Run interactive deployment
./scripts/deploy.sh
```

Or deploy manually via the AWS CLI:
```bash
aws cloudformation deploy \
  --template-file infra/cloudforge.yaml \
  --stack-name cloudforge \
  --region ap-southeast-2 \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides \
      AdminCidr="$(curl -s https://checkip.amazonaws.com)/32" \
      AlertEmail="your-email@example.com"
```

To tear down all resources and prevent charges:
```bash
./scripts/destroy.sh
```
See [`docs/cost.md`](docs/cost.md) for full pricing details in `ap-southeast-2`.

---

## Environment Variables Reference

| Variable | Required | Default / Example | Purpose |
| :--- | :--- | :--- | :--- |
| `DATABASE_URL` | Yes | `postgresql+psycopg://user:pass@127.0.0.1:5432/cloudforge` | PostgreSQL connection string |
| `SSM_DB_PASSWORD_PARAM` | No | `/cloudforge/db_password` | SSM Parameter Store key to retrieve DB password |
| `S3_BUCKET` | No | `cloudforge-artifacts-xxxx-ap-southeast-2` | S3 bucket for uploaded archive persistence |
| `API_KEY` | No | `your_secret_api_key_here` | When set, enforces `X-API-Key` auth header |
| `CORS_ORIGINS` | No | `http://localhost,http://127.0.0.1` | Comma-separated list of allowed CORS origins |
| `AWS_REGION` | No | `ap-southeast-2` | AWS region for boto3 SDK clients |

---

## Dockerfile Template & Dependency Handling

Cloud Forge enforces an immutable build template:
```dockerfile
FROM python:3.13-slim
WORKDIR /app
COPY . /app
CMD ["python", "{entrypoint}"]
```

### Handling Dependencies
1. **No Build-Time Code Execution:** The Dockerfile contains **no `RUN` steps**. Only `COPY` and layer metadata are generated at build time. User code is never executed during image synthesis.
2. **Network Mode `none`:** `client.images.build` is executed with `network_mode="none"`. Outbound internet access is disabled during compilation.
3. **Self-Contained Code:** Because network access is disabled during builds, applications requiring third-party libraries must vendor dependencies within their archive or use standard Python library modules.

---

## Security Model & Sandboxing

* **Kernel Sharing Limitation:** Standard Docker containers share the host Linux kernel. Cgroup resource ceilings, capability drops, and read-only filesystems mitigate standard privilege escalation, but multi-tenant cloud platforms require microVM technologies (e.g. AWS Firecracker or gVisor).
* **Port Isolation:** Port 8000 is blocked from external access. All external traffic is routed through Nginx on Port 80 with rate limiting (`10r/s`, `burst=20`) and security headers.
* **Zip-Bomb & Traversal Protection:** Validates paths against `..`, leading slashes, Windows colons, and symlinks. Tracks decompressed bytes during extraction, aborting with HTTP 413 if accumulated content exceeds 25 MB.
* **Credential Protection:** Secrets are never hardcoded. No keys or tokens are tracked in Git.

---

## Automated Testing & CI

Run the automated test suite locally:
```bash
# Run backend pytest suite
pytest tests/ -v

# Validate CloudFormation template
python -c "import pathlib, cfnlint.api; m = cfnlint.api.lint_file(pathlib.Path('infra/cloudforge.yaml')); print('CFN Errors:', len(m))"

# Build and lint frontend
cd frontend
npm run lint
npm run build
```

Every push triggers `.github/workflows/ci.yml`, running `pytest`, `cfn-lint`, and frontend linting/building in GitHub Actions.

---

## Limitations

* **Single Instance Architecture:** Designed as an educational/demonstration micro-PaaS prototype on a single EC2 host; does not provide horizontal autoscaling.
* **Shared Host Kernel:** Relies on Docker cgroups and dropped capabilities rather than hardware-virtualized microVMs (e.g. AWS Firecracker).
* **HTTP Only by Default:** Deployed on standard Port 80 behind Nginx. Production internet use requires configuring an SSL certificate via Let's Encrypt / Certbot or an AWS Application Load Balancer.

---

## Academic Information

* **Author:** Eben John Jose
* **Registration Number:** 24BCE2459
* **Branch:** B.Tech in Computer Science and Engineering (CORE)
* **Institution:** School of Computer Science and Engineering, Vellore Institute of Technology (VIT)
* **Live Deployment:** [http://54.252.152.116/](http://54.252.152.116/)
* **Repository:** [https://github.com/Eben923/cloud-forge](https://github.com/Eben923/cloud-forge)
