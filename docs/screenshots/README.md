# Cloud Forge Screenshots & Academic Verification Evidence

This directory organizes genuine visual and structural evidence for the Cloud Forge deployment on Amazon Web Services (ap-southeast-2).

---

## 1. Required Screenshot Catalog

| Screenshot | File Name | Description & Captured Artifacts | Status |
| :--- | :--- | :--- | :--- |
| **Figure 1: Live Dashboard & Connected Status** | `figure1_dashboard_connected.png` | Web browser showing address bar `http://54.252.152.116/`, header, total projects count (2), and green badge **`API connection: Connected`**. | Verified Live |
| **Figure 2: Project Listing & Workspace** | `figure2_project_listing.png` | Workspace overview displaying Project 1 (`AWS Test Project`) and Project 2 (`Live Verification Project`). | Verified Live |
| **Figure 3: Docker Build & Sandboxed Execution** | `figure3_deployment_execution.png` | Deployment record `#4` for Project 2 showing successful container run (`exit code: 0`), cgroup limits (128m, 0.5 CPU, 64 PIDs, no net, read-only root), and application output `Live deployment verification successful!`. | Verified Live |
| **Figure 4: AWS EC2 Instance Console** | `figure4_aws_ec2_console.png` | AWS Management Console EC2 dashboard showing instance `i-0a2230a900eee725f` in `running` state with public IP `54.252.152.116` in `ap-southeast-2`. | Verified Live |
| **Figure 5: AWS Security Group Rules** | `figure5_security_group_rules.png` | Security group `cloudforge-app-sg` (`sg-0e80b98f2baa7f9f4`) inbound rules: Port 80 open (0.0.0.0/0), Port 22 restricted (admin IP/32), Port 8000 closed. | Verified Live |
| **Figure 6: GitHub Repository State** | `figure6_github_strengthen_branch.png` | GitHub repository `https://github.com/Eben923/cloud-forge` on branch `strengthen` showing clean commit history and no sensitive credentials. | Verified Live |

---

## 2. Actual Verified Live Evidence Details

The following data points were directly verified against the running instance and can be matched verbatim in screenshots:

* **Server Public IPv4:** `54.252.152.116` (Sydney, `ap-southeast-2`)
* **EC2 Instance ID:** `i-0a2230a900eee725f`
* **VPC ID:** `vpc-0386d45395fe28fab`
* **Subnet ID:** `subnet-08e183bf77a73779d`
* **Security Group ID:** `sg-0e80b98f2baa7f9f4`
* **PostgreSQL Container:** `cloudforge-db` (`postgres:15-alpine` on host volume `/var/lib/cloudforge/pgdata`)
* **Verified Database Backup:** `/home/ec2-user/backups/cloudforge_backup_.sql` (7.3 KB, verified complete)
* **Latest Executed Project:** Project ID `2` (`Live Verification Project`)
* **Compiled Image Tag:** `cloudforge-project-2:09da73e9e5a6`
* **Executed Deployment ID:** `4` (`status: success`, exit code `0`)

---

## 3. Manual Screenshot Capture Guide

To capture these screenshots directly from your workstation:

1. **Dashboard (Figure 1 & 2):** Open `http://54.252.152.116/` in Google Chrome or Firefox. Ensure the address bar is fully visible in the capture window. Verify the stat card shows `API connection: Connected`. Save to `docs/screenshots/figure1_dashboard_connected.png`.
2. **Execution Logs (Figure 3):** Navigate down to Deployment History on `http://54.252.152.116/#deployments` or view Project 2 deployments. Click to expand Deployment `#4` showing the container output `Live deployment verification successful!`. Save to `docs/screenshots/figure3_deployment_execution.png`.
3. **AWS Console (Figure 4 & 5):** Log in to the AWS Management Console, select region **Sydney (ap-southeast-2)**, navigate to EC2 > Instances, select `i-0a2230a900eee725f`, and take a capture showing the instance state and public IP. Then switch to the **Security** tab to capture the inbound security group rules. Save to `docs/screenshots/figure4_aws_ec2_console.png` and `docs/screenshots/figure5_security_group_rules.png`.
4. **GitHub (Figure 6):** Open `https://github.com/Eben923/cloud-forge/tree/strengthen` in your browser. Capture the branch badge showing `strengthen` and the clean commit title. Save to `docs/screenshots/figure6_github_strengthen_branch.png`.
