# Cloud Forge — Comprehensive Academic Report

**Project Title:** Cloud Forge: Micro-PaaS Platform with Cgroup Container Sandboxing and Cloud-Native AWS Automation  
**Author / Developer:** Eben (eben.johnjose2024@vitstudent.ac.in)  
**Repository:** [https://github.com/Eben923/cloud-forge](https://github.com/Eben923/cloud-forge)  
**Branch:** `strengthen`  
**Live Application URL:** [http://54.252.152.116/](http://54.252.152.116/)  
**Deployment Region:** Amazon Web Services (AWS) `ap-southeast-2` (Sydney)  

---

## 1. Executive Summary & Problem Statement

Deploying and executing arbitrary user-submitted code in multi-tenant environments presents severe security challenges:
1. **Host Compromise:** Unchecked binaries or scripts can execute system calls, access the root filesystem, or escalate privileges.
2. **Resource Exhaustion (Denial of Service):** Malicious archives or runaway loops can consume CPU, exhaust RAM, flood the process table (fork bombs), or flood the local disk.
3. **Network Pivot Attacks:** Uploaded code can attempt lateral movement, internal network scanning, or unauthorized outbound command-and-control communication.

**Cloud Forge** resolves these challenges by implementing an automated **micro-Platform-as-a-Service (micro-PaaS)**. It ingests Python application source archives (ZIP), dynamically synthesizes an unprivileged Docker image template, and executes the compiled application inside an ephemeral container constrained by strict Linux kernel cgroups and namespace boundaries.

---

## 2. Distinction: Live Deployment vs. Infrastructure-as-Code

To ensure complete academic transparency, Cloud Forge maintains a strict separation between what is actively deployed and running on AWS, and what is provided as validated Infrastructure-as-Code:

| Dimension | Live AWS Deployment Prototype | Infrastructure-as-Code (`infra/cloudforge.yaml`) |
| :--- | :--- | :--- |
| **AWS Status** | **Active & Live** at `http://54.252.152.116/` | **Validated & Verified** via `cfn-lint` (0 errors), not deployed as a stack |
| **Topology** | Single EC2 `t3.micro` instance (`i-0a2230a900eee725f`) in Sydney | Multi-resource VPC, public subnet, IGW, RouteTable, SecurityGroup, S3, IAM, CloudWatch, SNS, Budgets |
| **Reverse Proxy** | Nginx with rate limiting (`10 req/s`) & security headers (`nosniff`, `DENY`) | Automated UserData configuration of Nginx reverse proxy |
| **Application Layer** | FastAPI running via systemd (`cloudforge.service`) on `127.0.0.1:8000` | Automated virtual environment setup and systemd unit installation |
| **Web Client** | Modern React 19 Single Page Application served from `/var/www/cloudforge` | Automated production build deployment to web root |
| **Database** | Persistent PostgreSQL 15 container (`cloudforge-db`) on `/var/lib/cloudforge/pgdata` | PostgreSQL 15 container with persistent volume mapping |
| **Secret Management** | Local environment file (`/home/ec2-user/app/.env`, permission 600) | AWS Systems Manager (SSM) Parameter Store SecureString dynamic bootstrapping |
| **Storage & Alarms** | Local host volume storage; verified backup at `/home/ec2-user/backups/` | S3 artifact bucket (30-day lifecycle expiration); CloudWatch CPU & status check alarms |

---

## 3. System Architecture & Component Responsibilities

The system employs a layered defense-in-depth architecture:

```
[ User Browser / HTTP Client ]
             │ (Port 80 TCP)
             ▼
[ Nginx Reverse Proxy (Frontend & Rate Limiter) ]
     ├── Serves Static SPA (/var/www/cloudforge - React 19)
     ├── Applies Security Headers (nosniff, DENY, XSS-Protection, Referrer-Policy)
     ├── Rate Limiting: 10 requests/sec with burst buffer of 20
     └── Reverse Proxies API calls (/health, /projects) to 127.0.0.1:8000
             │
             ▼
[ FastAPI Backend (Python 3.11 Systemd Service) ]
     ├── Ingestion & Validation: 10 MB limit, Zip-Slip check, streaming 25 MB bomb abort
     ├── Relational Persistence: PostgreSQL 15 via SQLAlchemy & Psycopg 3
     ├── Build Engine: Template Dockerfile synthesis (python:3.13-slim)
     └── Execution Manager: Docker SDK sandbox runner with strict cgroups
             │
             ▼
[ Ephemeral Sandboxed Container ]
     ├── Memory Limit: 128 MiB strict ceiling
     ├── CPU Quota: 0.5 vCPU (500,000,000 nano-CPUs)
     ├── Process Ceiling: 64 PIDs
     ├── Network Isolation: Disabled (network_disabled=True)
     ├── Filesystem: Read-only root (read_only=True)
     ├── User Privileges: Non-root user `nobody` (UID 65534)
     ├── Linux Capabilities: ALL dropped (cap_drop=["ALL"])
     └── Execution Watchdog: 30-second hard execution cutoff timeout
```

---

## 4. Defense-in-Depth Security Controls (Verified in Code)

Every security control below has been verified through unit and integration tests:

1. **Streaming Archive Bomb Defense (`main.py`):**
   * Pre-read file size check: maximum 10 MB.
   * Maximum entry count: 100 entries.
   * Path Traversal Check: Rejects filenames starting with `/`, containing `..`, or containing drive letters (`:`).
   * Symlink Elimination: Rejects entries where `(mode & 0o170000) == 0o120000`.
   * **Real-Time Streaming Byte Counter:** Extracts in 64 KB chunks, immediately raising HTTP 413 if accumulated decompressed bytes exceed 25 MB. This prevents spoofed header attacks.
2. **Deterministic Image Synthesis (`main.py`):**
   * Discards any uploaded `Dockerfile`.
   * Synthesizes a fresh Dockerfile:
     ```dockerfile
     FROM python:3.13-slim
     WORKDIR /app
     COPY . /app
     CMD ["python", "<entrypoint>"]
     ```
   * Compiles the image using `network_mode="none"` to block network access during Docker image building.
3. **Execution Sandbox Boundary (`main.py`):**
   * Memory: `mem_limit="128m"`
   * CPU: `nano_cpus=500_000_000` (0.5 vCPU)
   * Process Table: `pids_limit=64` (mitigates fork bombs)
   * Network: `network_disabled=True` (blocks outbound sockets, internal LAN scanning, and DNS requests)
   * Filesystem: `read_only=True` (prevents persistence and modification of container image)
   * User: `user="nobody"` (runs as unprivileged UID 65534)
   * Capabilities: `cap_drop=["ALL"]` (removes root capabilities including `CAP_NET_ADMIN`, `CAP_SYS_ADMIN`)
   * Timeout Watchdog: 30-second hard cutoff loop terminating stalled processes.

---

## 5. Authentication Configuration & Security Limitations

### Current Live Authentication Status
* **Backend Capability:** The backend implementation in `main.py` provides an optional API key authentication dependency (`verify_api_key`) inspecting the `X-API-Key` HTTP header against the `API_KEY` environment variable.
* **Live Server Configuration:** In the current live demonstration at `http://54.252.152.116/`, the `API_KEY` environment variable is **intentionally unset**.
* **Reason & Risk Identification:**
  * When `API_KEY` is unset, the backend permits open access to `/projects` and deployment routes.
  * This was chosen for the live academic prototype to enable seamless review and interaction without requiring examiners to configure or inject HTTP header tokens in static client browsers.
  * **Security Limitation:** The live API is currently unauthenticated. Anyone with network access to port 80 can create projects and trigger isolated executions. In a production commercial PaaS, this must be protected with user identity (e.g., OAuth2, JWT, or mandatory API keys).

---

## 6. Database Durability & Backup Verification

### Persistence Architecture
* **Engine:** PostgreSQL 15.19 Alpine running in Docker container `cloudforge-db`.
* **Host Mount:** Volume mapped directly from `/var/lib/cloudforge/pgdata` to `/var/lib/postgresql/data`.
* **Durability:** Container restarts (`--restart unless-stopped`) or service recycles do not impact the underlying relational tables.

### Verified Backup
* **Backup Location on Server:** `/home/ec2-user/backups/cloudforge_backup_.sql` (7,382 bytes).
* **Backup Method:** Standard logical export via `pg_dump -U cloudforge cloudforge`.
* **Integrity Check:** Dump file inspected and verified complete (`-- PostgreSQL database dump complete`).
* **Web Isolation:** Probed via Nginx — `/home/ec2-user/backups/` is located strictly outside `/var/www/cloudforge/` and returns the SPA index page (HTTP 200 via `try_files`), ensuring raw SQL dump data is never exposed over HTTP.

### External Offsite Backup Retention Procedure
To retain a secure offsite copy outside the AWS instance:
```bash
# Securely download the backup to a local machine
scp -i ~/.ssh/cloudforge-sydney-kp.pem ec2-user@54.252.152.116:/home/ec2-user/backups/cloudforge_backup_.sql ./backup_$(date +%Y%m%d).sql
```

---

## 7. Testing Methodology & Verification Results

The test suite covers unit, integration, linting, and live end-to-end operational checks.

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

### B. CloudFormation Linting (`cfn-lint`)
* Executed against `infra/cloudforge.yaml`: **0 errors**.

### C. Live Server End-to-End Verification (Exit Code 0)
* **Frontend Access:** HTTP 200 with Nginx security headers (`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Server: nginx`).
* **Health Probe:** `GET /health` returned `{"status":"healthy"}`.
* **Project Query:** `GET /projects` successfully retrieved active projects from PostgreSQL.
* **Execution Verification:** Uploaded and executed a verified Python application (`cloudforge-project-2:09da73e9e5a6`). Output produced: `"Live deployment verification successful!"` with container exit code `0`.

---

## 8. Known Limitations & Future Improvements

1. **Transport Layer Security (HTTPS):**
   * *Current State:* The live prototype operates over plain HTTP (port 80).
   * *Future Work:* Attach an AWS Application Load Balancer with an ACM TLS certificate, or configure Let's Encrypt Certbot on Nginx.
2. **Authentication for Multi-Tenancy:**
   * *Current State:* API key authentication is implemented in code but left unset for the public demo.
   * *Future Work:* Implement user accounts with JWT session cookies and user-scoped project isolation.
3. **Execution Runtime Coverage:**
   * *Current State:* Focuses on single-file and entrypoint Python applications with standard library dependencies.
   * *Future Work:* Support multi-runtime workers (Node.js, Go) and pre-compiled dependency wheel caching.
4. **CloudFormation Stack Deployment:**
   * *Current State:* CloudFormation template is fully developed and validated, but undeployed to avoid duplicating AWS EC2 billing.
   * *Future Work:* Deploy the stack to provision auto-scaling groups and S3 lifecycle storage.
