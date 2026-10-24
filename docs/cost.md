# Cloud Forge: AWS Cost Breakdown & Teardown Guide

**Target Region:** `ap-southeast-2` (Sydney)  
**Architecture:** Single `t3.micro` EC2 instance with attached EBS volume, private S3 artifact bucket, CloudWatch monitoring, and AWS Budgets cost guardrails.

---

## 1. Estimated Monthly Costs

All calculations assume standard AWS on-demand pricing in Sydney (`ap-southeast-2`).

| Component | Resource Specification | Free Tier Allocation | Estimated Monthly Cost (Free Tier Active) | Estimated Monthly Cost (After Free Tier / On-Demand) |
| :--- | :--- | :--- | :--- | :--- |
| **Compute (EC2)** | 1 × `t3.micro` (2 vCPU, 1 GiB RAM) | 750 hours/month free for 12 months | **$0.00** | **$9.64** ($0.0132/hr × 730 hrs) |
| **Storage (EBS)** | 20 GB gp3 root volume | 30 GB gp3/gp2 free for 12 months | **$0.00** | **$1.92** ($0.096/GB-month × 20 GB) |
| **Object Storage (S3)** | Artifact Bucket (uploads/ lifecycle 30d, < 1 GB) | 5 GB Standard Storage + 2,000 PUT + 20,000 GET | **$0.00** | **< $0.05** |
| **Monitoring (CloudWatch)** | 1 Log Group (14-day retention, < 500 MB logs), 2 Alarms | 5 GB log ingestion + 10 metric alarms free | **$0.00** | **$0.20** ($0.10/alarm for 2 custom alarms) |
| **Networking & Data Transfer**| Outbound Internet Traffic (< 5 GB/month) | 100 GB/month always free outbound data transfer | **$0.00** | **$0.00** |
| **AWS Budgets** | 1 Monthly Cost Budget | 2 budgets always free per account | **$0.00** | **$0.00** |
| **Total Estimated Spend** | | | **$0.00 / month** | **~$11.81 / month (~₹990/month)** |

### Cost Assumptions
1. Single instance running continuously 24/7 (730 hours/month).
2. The account is within its first 12 months of AWS Free Tier eligibility.
3. Uploaded code archives expire after 30 days via S3 lifecycle rules.
4. Administrative SSH traffic and public HTTP traffic remain within reasonable demo usage (< 5 GB/month).

---

## 2. Cost Guardrail: AWS Budgets & CloudWatch Alarms

The CloudFormation template automatically provisions:
1. **AWS Budget (`cloudforge-monthly-cost`):** Default limit set to **$5.00 USD/month**. An alert notification is delivered to `AlertEmail` as soon as forecasted or actual spend crosses 80% ($4.00).
2. **CloudWatch High CPU Alarm:** Triggers if CPU utilization exceeds 80% for 5 consecutive minutes (mitigating compute runaway).
3. **CloudWatch Status Check Alarm:** Triggers if the EC2 hypervisor or OS status check fails.

---

## 3. Safe Teardown Instructions

To completely stop all charges and delete all AWS resources provisioned by the stack:

### Step 1: Empty the S3 Artifact Bucket (Required before bucket deletion)
CloudFormation will not delete an S3 bucket that still contains objects. Run:
```bash
# Retrieve bucket name from stack outputs
BUCKET_NAME=$(aws cloudformation describe-stacks \
  --stack-name cloudforge \
  --region ap-southeast-2 \
  --query "Stacks[0].Outputs[?OutputKey=='ArtifactBucketName'].OutputValue" \
  --output text)

# Empty bucket contents
aws s3 rm "s3://${BUCKET_NAME}" --recursive --region ap-southeast-2
```

### Step 2: Delete CloudFormation Stack
```bash
aws cloudformation delete-stack \
  --stack-name cloudforge \
  --region ap-southeast-2
```

### Step 3: Verify Deletion
```bash
aws cloudformation wait stack-delete-complete \
  --stack-name cloudforge \
  --region ap-southeast-2

echo "Stack 'cloudforge' has been completely deleted. 0 resources remain."
```
