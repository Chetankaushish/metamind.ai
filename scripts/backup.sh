#!/bin/bash

set -e

PROJECT_DIR="/opt/metamind.ai"
BACKUP_DIR="/opt/backups/adspilot"
DATE=$(date +"%Y-%m-%d_%H-%M-%S")

echo "======================================="
echo "💾 AdsPilot Backup"
echo "======================================="

mkdir -p $BACKUP_DIR

cd $PROJECT_DIR

echo ""
echo "📦 Backing up source code..."

tar -czf $BACKUP_DIR/adspilot_source_$DATE.tar.gz \
    --exclude=.git \
    --exclude=node_modules \
    --exclude=frontend/node_modules \
    --exclude=backend/__pycache__ \
    .

echo ""
echo "🐘 Backing up PostgreSQL..."

docker exec metamind_postgres pg_dump \
    -U ${POSTGRES_USER:-metamind} \
    ${POSTGRES_DB:-metamind_prod} \
    > $BACKUP_DIR/postgres_$DATE.sql

echo ""
echo "🗑 Removing backups older than 7 days..."

find $BACKUP_DIR -type f -mtime +7 -delete

echo ""
echo "======================================="
echo "✅ Backup Completed"
echo "======================================="