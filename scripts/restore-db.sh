#!/usr/bin/env bash
# =============================================================================
# MetaMind AI - PostgreSQL Database Restore Script
# =============================================================================
set -e

if [ -f .env ]; then
  source .env
fi

if [ -z "$1" ]; then
  echo "Usage: ./scripts/restore-db.sh <path_to_backup_file.sql.gz>"
  exit 1
fi

BACKUP_FILE="$1"

if [ ! -f "$BACKUP_FILE" ]; then
  echo "❌ Error: Backup file '$BACKUP_FILE' does not exist."
  exit 1
fi

echo "⚠️ WARNING: This will overwrite the current PostgreSQL database!"
read -p "Are you sure you want to proceed? (y/N): " confirm

if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
  echo "Restore cancelled."
  exit 0
fi

echo "♻️ Restoring PostgreSQL database from $BACKUP_FILE..."
gunzip -c "$BACKUP_FILE" | docker compose exec -T postgres psql -U ${POSTGRES_USER:-metamind_user} -d ${POSTGRES_DB:-metamind_production}

echo "✅ Database restore completed successfully!"
