#!/usr/bin/env bash
# =============================================================================
# MetaMind AI - Environment Variable Validation Script
# =============================================================================
set -e

echo "🔍 Validating Production Environment Variables..."

if [ ! -f .env ]; then
  echo "❌ Missing .env file!"
  exit 1
fi

source .env

REQUIRED_VARS=(
  "DOMAIN_NAME"
  "POSTGRES_USER"
  "POSTGRES_PASSWORD"
  "POSTGRES_DB"
  "JWT_SECRET"
  "META_APP_ID"
  "META_APP_SECRET"
  "META_WEBHOOK_VERIFY_TOKEN"
)

MISSING_COUNT=0

for VAR in "${REQUIRED_VARS[@]}"; do
  if [ -z "${!VAR}" ]; then
    echo "❌ Missing required environment variable: $VAR"
    MISSING_COUNT=$((MISSING_COUNT+1))
  else
    echo "  [OK] $VAR is configured."
  fi
done

if [ $MISSING_COUNT -gt 0 ]; then
  echo "❌ Environment validation failed with $MISSING_COUNT missing variable(s)."
  exit 1
else
  echo "✅ Environment validation passed successfully!"
fi
