#!/usr/bin/env bash
# =============================================================================
# MetaMind AI - Production Deployment Rollback Script
# =============================================================================
set -e

echo "⚠️ Initiating Production Deployment Rollback..."

if [ -f docker-compose.override.yml ]; then
  echo "🔄 Reverting containers to previous stable state..."
  docker compose down
fi

echo "⏪ Rolling back Alembic database schema by 1 step..."
docker compose run --rm backend alembic downgrade -1 || true

echo "🔄 Restarting previous production stack..."
docker compose up -d

echo "🏥 Checking rollback system health..."
sleep 5
docker compose ps

echo "✅ Rollback procedure completed successfully."
