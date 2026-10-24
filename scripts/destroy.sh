#!/usr/bin/env bash
set -euo pipefail

# Cloud Forge CloudFormation Teardown Helper

REGION="${AWS_REGION:-ap-southeast-2}"
STACK_NAME="${STACK_NAME:-cloudforge}"

echo "=========================================================="
echo " Cloud Forge AWS Stack Teardown"
echo " Region:     ${REGION}"
echo " Stack Name: ${STACK_NAME}"
echo "=========================================================="

read -r -p "Are you sure you want to permanently delete stack '${STACK_NAME}'? (yes/no): " CONFIRM
if [[ "${CONFIRM}" != "yes" ]]; then
  echo "Aborting teardown."
  exit 0
fi

echo "Checking for S3 artifact bucket to empty before deletion..."
BUCKET_NAME=$(aws cloudformation describe-stacks \
  --stack-name "${STACK_NAME}" \
  --region "${REGION}" \
  --query "Stacks[0].Outputs[?OutputKey=='ArtifactBucketName'].OutputValue" \
  --output text 2>/dev/null || true)

if [[ -n "${BUCKET_NAME}" && "${BUCKET_NAME}" != "None" ]]; then
  echo "Emptying S3 bucket 's3://${BUCKET_NAME}'..."
  aws s3 rm "s3://${BUCKET_NAME}" --recursive --region "${REGION}" || true
fi

echo "Deleting CloudFormation stack '${STACK_NAME}'..."
aws cloudformation delete-stack \
  --stack-name "${STACK_NAME}" \
  --region "${REGION}"

echo "Waiting for stack deletion to complete..."
aws cloudformation wait stack-delete-complete \
  --stack-name "${STACK_NAME}" \
  --region "${REGION}"

echo "Stack '${STACK_NAME}' and all associated AWS resources have been successfully deleted."
