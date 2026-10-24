# Cloud Forge

A lightweight micro-PaaS platform that accepts Python source-code archives, synthesises sandboxed Docker images, and executes containers under strict Linux resource limits.

Built with **FastAPI · React 19 · PostgreSQL · Docker · Nginx · AWS EC2**.

---

## Live AWS Deployment

Cloud Forge is actively deployed on **Amazon Web Services (AWS)** in `ap-southeast-2` (Sydney):

* **Live Dashboard:** [http://54.252.152.116/](http://54.252.152.116/)
* **Health API Endpoint:** [http://54.252.152.116/health](http://54.252.152.116/health)
* **REST Projects Endpoint:** [http://54.252.152.116/projects](http://54.252.152.116/projects)
* **AWS Architecture:** EC2 Nitro (`t3.micro`), Amazon Linux 2023, Amazon VPC, Nginx reverse proxy, and Docker containerized PostgreSQL 15 with persistent EBS host volumes.

---

## What It Does

1. **Upload** — Submit a ZIP file containing Python application code (`main.py` or a single `.py` file).
2. **Build** — Cloud Forge generates a clean, minimal `python:3.13-slim` Dockerfile and builds a tagged image via the local Docker daemon. No untrusted user-supplied Dockerfile instructions are executed.
3. **Deploy** — The container launches under strict Linux isolation primitives (128 MiB RAM, 0.5 CPU quota, 64 PIDs ceiling), read-only root filesystem, dropped Linux capabilities (`cap_drop=["ALL"]`), unprivileged user (`nobody`), and network disabled (`network_disabled=True`).
4. **Audit** — Execution logs, container exit codes, and timestamps are saved relationally to PostgreSQL.

---

## Prerequisites

| Tool | Minimum Version | Notes |
| :--- | :--- | :--- |
| **Python** | 3.11+ / 3.13 | Backend runtime environment |
| **Node.js** | 20+ / 22 | Frontend Vite build tooling |
| **Docker** | 24+ / 25+ | Required for builds and sandboxed runs |
| **PostgreSQL** | 15+ | Runs via Docker container with volume persistence |

---

## Quick Start (Local Setup)

### 1. Clone the Repository
```bash
git clone https://github.com/Eben923/cloud-forge.git
cd cloud-forge
```

### 2. Configure Environment Variables
```bash
cp .env.example .env
# Set your DATABASE_URL in .env
```

### 3. Start PostgreSQL Container
```bash
docker run -d \
  --name cloudforge-db \
  --restart unless-stopped \
  -e POSTGRES_USER=cloudforge \
  -e POSTGRES_PASSWORD=your_secure_password \
  -e POSTGRES_DB=cloudforge \
  -v cloudforge-pgdata:/var/lib/postgresql/data \
  -p 127.0.0.1:5432:5432 \
  postgres:15-alpine
```

### 4. Setup Python Virtual Environment
```bash
python -m venv .venv

# Windows
.\.venv\Scripts\activate
pip install -r requirements.txt

# Linux / macOS
source .venv/bin/activate
pip install -r requirements.txt
```

### 5. Start Backend API
```bash
uvicorn main:app --host 127.0.0.1 --port 8000
```

### 6. Start React Frontend
```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173** to access the local dashboard.

---

## Sample Test Application

A reproducible test application is provided in [`test-app/`](test-app/):
```
test-app/
  ├── app.py          # print("Hello from Cloud Forge!")
  └── Dockerfile      # Reference Dockerfile
```

---

## Project Structure

```
cloud-forge/
├── main.py               # FastAPI application endpoints and container orchestration
├── database.py           # SQLAlchemy database session engine
├── models.py             # Relational data models (Project, Deployment)
├── requirements.txt      # Python dependencies
├── .env.example          # Safe configuration template
├── .gitignore            # Git exclusion rules
├── frontend/             # React 19 + Vite dashboard
│   ├── src/
│   │   └── App.jsx
│   ├── package.json
│   └── vite.config.js
├── test-app/             # Sample deployment project
└── report-output/        # Academic Case Study documentation (PDF, HTML, MD)
```

---

## Security Model

* **Kernel Sharing:** Standard Docker containers share the host Linux kernel. Cgroup resource caps, capability dropping, and read-only filesystems mitigate basic escalation, but multi-tenant cloud platforms require microVM technologies (e.g. AWS Firecracker or gVisor).
* **Port Isolation:** Port 8000 is blocked from external access and is exposed strictly via the local reverse proxy (Nginx).
* **Credential Hygiene:** No credentials, tokens, or private keys are committed to Git.

---

## Academic Details

* **Author:** Eben John Jose
* **Registration Number:** 24BCE2459
* **Live Deployment URL:** http://54.252.152.116/
* **Repository:** https://github.com/Eben923/cloud-forge
