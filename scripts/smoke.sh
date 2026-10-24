#!/usr/bin/env bash
set -euo pipefail

# Cloud Forge Smoke Test Script

TARGET_HOST="${1:-http://localhost}"
API_KEY="${2:-}"

echo "=========================================================="
echo " Cloud Forge Smoke Test against: ${TARGET_HOST}"
echo "=========================================================="

echo -n "1. Checking /health endpoint... "
HEALTH_RESP=$(curl -s -w "\n%{http_code}" "${TARGET_HOST}/health")
HTTP_CODE=$(echo "$HEALTH_RESP" | tail -n1)
BODY=$(echo "$HEALTH_RESP" | head -n -1)

if [[ "$HTTP_CODE" == "200" && "$BODY" == *"healthy"* ]]; then
  echo "PASS (HTTP 200: ${BODY})"
else
  echo "FAIL (HTTP ${HTTP_CODE}: ${BODY})"
  exit 1
fi

echo -n "2. Checking /projects endpoint... "
AUTH_HEADER=""
if [[ -n "$API_KEY" ]]; then
  AUTH_HEADER="-H X-API-Key: ${API_KEY}"
fi

PROJECTS_RESP=$(curl -s -w "\n%{http_code}" ${AUTH_HEADER} "${TARGET_HOST}/projects")
P_CODE=$(echo "$PROJECTS_RESP" | tail -n1)
P_BODY=$(echo "$PROJECTS_RESP" | head -n -1)

if [[ "$P_CODE" == "200" ]]; then
  echo "PASS (HTTP 200: returned projects list)"
else
  echo "FAIL (HTTP ${P_CODE}: ${P_BODY})"
  exit 1
fi

echo ""
echo "All smoke tests passed successfully!"
