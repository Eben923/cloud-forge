# Cloud Forge

A lightweight micro-PaaS prototype that accepts Python source-code archives, synthesises sandboxed Docker images, and executes containers under strict Linux resource limits.

Built with **FastAPI · React 19 · PostgreSQL · Docker**.

---

## What it does

1. **Upload** — submit a ZIP file containing a Python script (`main.py` or a single `.py` file).
2. **Build** — Cloud Forge generates a minimal `python:3.13-slim` Dockerfile and builds a tagged image via the local Docker daemon. No user-supplied Dockerfile is used.
3. **Deploy** — the image runs in an isolated container with cgroup limits (128 MiB RAM, 0.5 CPU, 64 PIDs), a read-only root filesystem, all Linux capabilities dropped, and network access disabled.
4. **Audit** — exit code, stdout/stderr, and timestamps are persisted in PostgreSQL.

> **Scope:** Only self-contained Python scripts are supported. Projects that require `pip install` at runtime cannot be used because the build step runs with `network_mode="none"` and the generated Dockerfile contains no `RUN` steps.

---

## Prerequisites

| Tool | Minimum version | Notes |
|------|----------------|-------|
| Python | 3.13 | Backend runtime |
| Node.js | 22 | Frontend build |
| Docker Desktop | any recent | Must be running |
| PostgreSQL | 15+ | Can run in Docker (see below) |

---

## Quick start

### 1. Clone

```bash
git clone https://github.com/Eben923/cloud-forge.git
cd cloud-forge
```

### 2. Start PostgreSQL

```bash
docker run -d \
  --name cloudforge-db \
  -e POSTGRES_USER=cloudforge \
  -e POSTGRES_PASSWORD=<choose-a-password> \
  -e POSTGRES_DB=cloudforge \
  -p 5432:5432 \
  postgres:15-alpine
```

### 3. Configure the backend

```bash
cp .env.example .env
# Edit .env and set DATABASE_URL to match the credentials above
```

### 4. Create the virtual environment and install dependencies

```bash
python -m venv .venv

# Windows
.venv\Scripts\pip install fastapi uvicorn[standard] sqlalchemy psycopg[binary] docker python-dotenv alembic pydantic-settings

# macOS / Linux
.venv/bin/pip install fastapi uvicorn[standard] sqlalchemy psycopg[binary] docker python-dotenv alembic pydantic-settings
```

> A `requirements.txt` is not yet committed to the repository. Use the package list above until one is added.

### 5. Run the backend

```bash
# Windows
.venv\Scripts\python -m uvicorn main:app --host 127.0.0.1 --port 8000

# macOS / Linux
.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000
```

### 6. Install and run the frontend

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173** in your browser.

---

## Sample test application

A minimal Hello-World app is included in [`test-app/`](test-app/):

```
test-app/
  app.py          # print("Hello from Cloud Forge!")
  Dockerfile      # reference only — Cloud Forge generates its own
```

To test an end-to-end deployment:

1. Zip the contents of `test-app/` (not the folder itself): `app.py` must be at the ZIP root.
2. Create a project in the dashboard.
3. Upload the ZIP, click **Build**, then **Deploy**.
4. Expect exit code `0` and output `Hello from Cloud Forge!`.

---

## Environment variables

| Variable | Required | Example | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | `postgresql+psycopg://user:pass@localhost:5432/cloudforge` | SQLAlchemy connection string using psycopg 3 driver |
| `CORS_ORIGINS` | No | `http://localhost:5173` | Comma-separated list of allowed CORS origins |

---

## Security notes

- Docker containers share the host kernel. The cgroup limits and dropped capabilities reduce standard attack surface but do not provide microVM-grade isolation.
- Never expose the backend port publicly without authentication.
- Rotate database credentials before any production or shared use.

---

## Project structure

```
cloud-forge/
├── main.py               # FastAPI application — all API routes
├── database.py           # SQLAlchemy engine / session setup
├── models.py             # ORM models (Project, Deployment)
├── test_db.py            # Quick database connectivity test
├── .env.example          # Configuration template
├── .gitignore
├── frontend/             # React 19 + Vite SPA
│   ├── src/
│   │   └── App.jsx
│   ├── package.json
│   └── vite.config.js
├── test-app/             # Sample Hello-World Python app
│   ├── app.py
│   └── Dockerfile        # Reference only
└── migrations/           # Alembic database migrations
```

---

## Author

**Eben John Jose** — Registration Number 24BCE2459  
[Programme / Branch placeholder] · [Institution placeholder]
