#!/usr/bin/env bash
# =============================================================================
# MetaMind AI - PostgreSQL Automated Backup Script
# =============================================================================
set -e

if [ -f .env ]; then
  source .env
fi

BACKUP_DIR="./backups/postgres"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/metamind_backup_${TIMESTAMP}.sql.gz"

mkdir -p "$BACKUP_DIR"

echo "💾 Starting PostgreSQL backup..."
docker compose exec -T postgres pg_dump -U ${POSTGRES_USER:-metamind_user} ${POSTGRES_DB:-metamind_production} | gzip > "$BACKUP_FILE"

echo "✅ Backup successfully created at: ${BACKUP_FILE}"

# Keep only the last 30 backups to save disk space on VPS
echo "🧹 Cleaning up backups older than 30 days..."
find "$BACKUP_DIR" -type f -name "*.sql.gz" -mtime +30 -delete
