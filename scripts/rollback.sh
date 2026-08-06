#!/bin/bash

set -e

PROJECT_DIR="/opt/metamind.ai"

echo "======================================="
echo "↩️ AdsPilot Rollback"
echo "======================================="

cd $PROJECT_DIR

docker compose -f docker-compose.prod.yml down

git pull origin main

docker compose -f docker-compose.prod.yml up -d --build

echo ""
echo "✅ Rollback Completed"