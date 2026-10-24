# Cloud Forge — Comprehensive Academic Report

**Project Title:** Cloud Forge: Micro-PaaS Platform with Cgroup Container Sandboxing and Cloud-Native AWS Automation
**Author / Developer:** Eben John Jose (eben.johnjose2024@vitstudent.ac.in)
**Registration Number:** 24BCE2459
**Degree Program:** B.Tech Computer Science and Engineering (CORE), School of Computer Science and Engineering, VIT Vellore
**Repository:** [https://github.com/Eben923/cloud-forge](https://github.com/Eben923/cloud-forge)
**Branch:** `strengthen`
**Commit Associated:** `182c25146b15caeb04a9c8519466fe047f1ed758`
**Live Application URL:** [http://54.252.152.116/](http://54.252.152.116/)
**Deployment Region:** Amazon Web Services (AWS) `ap-southeast-2` (Sydney)

---

## 1. Executive Summary & Problem Statement

Deploying and executing arbitrary, user-submitted code in multi-tenant environments presents severe systems engineering and security challenges [1, 2]:
1. **Host Compromise:** Unchecked binaries or scripts can execute system calls, access the root filesystem, or escalate privileges [6].
2. **Resource Exhaustion (Denial of Service):** Malicious archives or runaway loops can consume CPU, exhaust RAM, flood the process table (fork bombs), or flood the local disk [1, 2].
3. **Network Pivot Attacks:** Uploaded code can attempt lateral movement, internal network scanning, or unauthorized outbound command-and-control communication [4].

**Cloud Forge** resolves these challenges by implementing an automated **micro-Platform-as-a-Service (micro-PaaS)**. It ingests Python application source archives (ZIP), dynamically synthesizes an unprivileged Docker image template, and executes the compiled application inside an ephemeral container constrained by strict Linux kernel cgroups and namespace boundaries [6, 7].

---

## 2. Distinction: Live Deployment vs. Infrastructure-as-Code

To ensure complete academic transparency, Cloud Forge maintains a strict separation between what is actively deployed and running on AWS, and what is provided as validated Infrastructure-as-Code:

| Dimension | Live AWS Deployment Prototype | Infrastructure-as-Code (`infra/cloudforge.yaml`) |
| :--- | :--- | :--- |
| **AWS Status** | **Active & Live** at `http://54.252.152.116/` | **Validated & Verified** via `cfn-lint 1.58.0` (0 errors), not deployed as a stack |
| **Topology** | Single EC2 `t3.micro` instance (`i-0a2230a900eee725f`) in Sydney | Lean VPC (`10.0.0.0/16`), PublicSubnet (`10.0.1.0/24`), IGW, RouteTable, SecurityGroup, S3, IAM, CloudWatch, SNS, Budgets |
| **SSH Access** | Locked via AWS EC2 security group rules | Parameter `AdminCidr` enforces explicit CIDR block between `/16` and `/32` (world-open `0.0.0.0/0` disallowed) |
| **Reverse Proxy** | Nginx with rate limiting (`10 req/s`, burst 20) & security headers (`nosniff`, `DENY`) | Automated UserData configuration of Nginx reverse proxy |
| **Application Layer** | FastAPI running via systemd (`cloudforge.service`) on `127.0.0.1:8000` (Python 3.11 host runtime) | Automated virtual environment setup and systemd unit installation |
| **Web Client** | Modern React 19 Single Page Application served from `/var/www/cloudforge` | Automated production build deployment to web root |
| **Database** | Persistent PostgreSQL 15 container (`cloudforge-db`) on `/var/lib/cloudforge/pgdata` | PostgreSQL 15 container with host volume mapping initialized via UserData |
| **Secret Management** | Local environment file (`/home/ec2-user/app/.env`, permission 600) | AWS Systems Manager (SSM) Parameter Store SecureString dynamic bootstrapping |
| **Storage & Alarms** | Local host volume storage; verified backup at `/home/ec2-user/backups/` | S3 artifact bucket (30-day lifecycle expiration); CloudWatch CPU (1 period of 300s >80%) & status check alarms |
| **Budget Ceiling** | Monitored manually via AWS Billing Console | `AWS::Budgets::Budget` enforcing **$5.00/month** limit with direct email alert at 80% ($4.00) |

---

## 3. System Architecture & Ingestion Security

The system employs a layered defense-in-depth architecture:

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
     ├── Relational Persistence: PostgreSQL 15 via SQLAlchemy & Psycopg 3
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

### Ingestion Validation Pipeline (`main.py`)
1. **Upload Size Cap:** Reads at most `MAX_UPLOAD_SIZE + 1` bytes (**10 MB**). Excess uploads raise HTTP 413 immediately.
2. **Directory Traversal (Zip-Slip):** Backslashes are normalized to forward slashes. Any entry starting with `/`, containing `..`, empty segments, or drive letters (`:`) raises HTTP 400 [3].
3. **Entry Count Threshold:** Archives containing more than **100 entries** raise HTTP 400 to prevent inode exhaustion.
4. **Symlink Rejection:** POSIX mode bits (`entry.external_attr >> 16 & 0o170000 == 0o120000`) are inspected; symlinks raise HTTP 400.
5. **Streaming Bomb Guard:** Decompressed streams are processed in 64 KB chunks; cumulative bytes are strictly capped at `MAX_EXTRACTED_SIZE` (**25 MB**). Excess streams raise HTTP 413.
6. **Required Python Source:** Archives must contain at least one `.py` file. The engine selects `main.py` or `app.py` as entrypoint.

---

## 4. Image Synthesis & Sandbox Execution Engine

### Synthetic Dockerfile Generation
To eliminate build-time privilege escalation, Cloud Forge completely discards any uploaded `Dockerfile` and dynamically synthesizes:
```dockerfile
FROM python:3.13-slim
WORKDIR /app
COPY . /app
CMD ["python", "{entrypoint}"]
```
*Note on Base Image Tag:* The base image `python:3.13-slim` is a mutable tag upstream. In a high-assurance production environment, pinning to an immutable SHA-256 digest (e.g., `python:3.13-slim@sha256:...`) is recommended to ensure reproducible, tamper-proof builds.

### Build Isolation
Container images are compiled with `network_mode="none"`, preventing any network egress or IMDS metadata probing during the compilation phase:
```python
image, log_stream = client.images.build(
    path=str(build_path),
    tag=image_name,
    rm=True,
    forcerm=True,
    network_mode="none",
)
```

### Linux Kernel Cgroup Execution Sandbox
Containers run under rigid cgroup v2 boundaries and security options:
```python
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
    labels={"cloudforge.managed": "true", "cloudforge.project_id": str(project_id)},
)
```
An active polling watchdog terminates hanging tasks if execution exceeds 30 seconds (`container.stop(timeout=2)`).

---

## 5. Authentication Configuration & Security Limitations

### Current Live Authentication Status
* **Backend Capability:** The backend implementation in `main.py` provides an API key authentication dependency (`verify_api_key`) inspecting the `X-API-Key` HTTP header against the `API_KEY` environment variable.
* **Live Server Configuration:** In the current live demonstration at `http://54.252.152.116/`, the `API_KEY` environment variable is **intentionally unset**.
* **Critical Architectural Vulnerability for Public Deployments:**
  * When `API_KEY` is unset, `verify_api_key` permits open access across all 9 sensitive routes (`/projects`, `/upload`, `/build`, `/deployments`).
  * This was chosen for the live academic prototype to enable seamless review and interaction without requiring examiners to configure or inject HTTP header tokens in static client browsers.
  * **Security Limitation:** The live demonstration API is unauthenticated, and traffic is transmitted over unencrypted HTTP (port 80). Anyone with network access can create projects and trigger container executions. In production, HTTPS (TLS) and mandatory authentication (OAuth2 / JWT / API keys) are essential.

---

## 6. Database Durability & Safe Decommissioning

### Persistence Architecture
* **Engine:** PostgreSQL 15.19 Alpine running in Docker container `cloudforge-db`.
* **Host Mount:** Volume mapped directly from `/var/lib/cloudforge/pgdata` to `/var/lib/postgresql/data`.
* **Durability:** Container restarts (`--restart unless-stopped`) or service recycles do not impact the underlying relational tables.
* **Verified Backup:** Logical SQL backup created via `pg_dump` at `/home/ec2-user/backups/cloudforge_backup_.sql` (7,382 bytes).

### Critical Data Safety Notice: Docker Volume Pruning
A frequent administrator mistake is running `docker system prune -af --volumes`. The `--volumes` flag purges **all unattached Docker volumes**. In standard Docker database configurations, this destroys persistent database files. While Cloud Forge uses a host bind mount (`/var/lib/cloudforge/pgdata`), blind volume pruning remains an extreme hazard.

### Tiered Safe Decommissioning Procedure
1. **Mandatory Backup:** Verify database backup:
   ```bash
   pg_dump -h 127.0.0.1 -U cloudforge cloudforge > /home/ec2-user/backups/pre_teardown.sql
   ```
2. **Stop Application Daemons:**
   ```bash
   sudo systemctl stop cloudforge.service && sudo systemctl stop nginx
   ```
3. **Controlled Container Termination (Preserving Storage):**
   ```bash
   docker stop cloudforge-db && docker rm cloudforge-db
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

*Test Pass Rate vs. Code Coverage:* The suite achieved a **100% pass rate (9 passed out of 9 tests)**. Statement and branch code coverage were not instrumented with `pytest-cov`, and 100% code coverage is not claimed.

### B. CloudFormation Linting (`cfn-lint 1.58.0`)
* Executed against `infra/cloudforge.yaml`: **0 errors, 0 warnings**.

### C. Live Server End-to-End Verification (Exit Code 0)
* **Frontend Access:** HTTP 200 with Nginx security headers (`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Server: nginx`).
* **Health Probe:** `GET /health` returned `{"status":"healthy"}`.
* **Project Query:** `GET /projects` successfully retrieved active projects from PostgreSQL.
* **Execution Verification:** Uploaded and executed a verified Python application (`cloudforge-project-2:09da73e9e5a6`). Output produced: `"Live deployment verification successful!"` with container exit code `0`.

---

## 8. Academic References

1. Rosen, R. (2014). *Linux Kernel Networking: Implementation and Theory*. Apress.
2. Menage, P. (2007). Adding Generic Process Containers to the Linux Kernel. In *Proceedings of the Linux Symposium* (Vol. 2, pp. 45-57).
3. Snyk Security Research. (2018). *Zip Slip Vulnerability: Arbitrary File Overwrite Through Directory Traversal*. Available at: https://snyk.io/research/zip-slip-vulnerability .
4. Amazon Web Services. (2024). *AWS Well-Architected Framework: Security Pillar*. AWS Whitepapers.
5. Open Web Application Security Project (OWASP). (2023). *Top 10 API Security Risks*. OWASP Foundation. Available at: https://owasp.org/API-Security/ .
6. Docker Documentation. (2024). *Runtime Privilege and Linux Capabilities in Docker Engine*. Docker Inc. Available at: https://docs.docker.com/engine/security/ .
7. Ramirez, S. (2024). *FastAPI: Modern, High-Performance Web Framework for Python*. Available at: https://fastapi.tiangolo.com .
8. Bayer, M. (2024). *SQLAlchemy: The Database Toolkit for Python*. Available at: https://www.sqlalchemy.org .
9. Amazon Web Services. (2024). *AWS CloudFormation User Guide: Resource Specification*. AWS Documentation.
10. Sysoev, I., & Nginx Authors. (2024). *Nginx Web Server Documentation: Rate Limiting and Reverse Proxy*. F5 Inc. Available at: https://nginx.org/en/docs/ .
11. You, E., & Vite Contributors. (2024). *Vite: Next Generation Frontend Tooling*. Available at: https://vite.dev .
12. PostgreSQL Global Development Group. (2024). *PostgreSQL 15 Documentation: Reliability and Data Durability*. Available at: https://www.postgresql.org/docs/15/ .
