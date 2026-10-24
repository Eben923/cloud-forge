#!/usr/bin/env bash
set -euo pipefail

# Cloud Forge CloudFormation Deployment Helper

REGION="${AWS_REGION:-ap-southeast-2}"
STACK_NAME="${STACK_NAME:-cloudforge}"
TEMPLATE_FILE="$(dirname "$0")/../infra/cloudforge.yaml"

echo "=========================================================="
echo " Cloud Forge AWS CloudFormation Deployment"
echo " Region:     ${REGION}"
echo " Stack Name: ${STACK_NAME}"
echo "=========================================================="

# Prompt for Admin CIDR
MY_IP=$(curl -s https://checkip.amazonaws.com || echo "0.0.0.0")
DEFAULT_ADMIN_CIDR="${MY_IP}/32"
read -r -p "Enter your Admin CIDR for SSH access [default: ${DEFAULT_ADMIN_CIDR}]: " ADMIN_CIDR
ADMIN_CIDR="${ADMIN_CIDR:-$DEFAULT_ADMIN_CIDR}"

# Prompt for Alert Email
read -r -p "Enter your email for CloudWatch and Budget alerts [default: admin@example.com]: " ALERT_EMAIL
ALERT_EMAIL="${ALERT_EMAIL:-admin@example.com}"

echo ""
echo "Deploying CloudFormation stack '${STACK_NAME}'..."

aws cloudformation deploy \
  --template-file "${TEMPLATE_FILE}" \
  --stack-name "${STACK_NAME}" \
  --region "${REGION}" \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides \
      AdminCidr="${ADMIN_CIDR}" \
      AlertEmail="${ALERT_EMAIL}"

echo ""
echo "Stack deployed successfully. Fetching outputs..."
aws cloudformation describe-stacks \
  --stack-name "${STACK_NAME}" \
  --region "${REGION}" \
  --query "Stacks[0].Outputs" \
  --output table
