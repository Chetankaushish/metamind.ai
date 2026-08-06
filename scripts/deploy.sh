#!/bin/bash

set -e

echo "======================================="
echo "🚀 AdsPilot Production Deployment"
echo "======================================="

PROJECT_DIR="/opt/metamind.ai"

cd $PROJECT_DIR

echo ""
echo "📥 Pulling latest code..."
git pull origin main

echo ""
echo "🛑 Stopping old containers..."
docker compose -f docker-compose.prod.yml down

echo ""
echo "🧹 Removing unused images..."
docker image prune -f

echo ""
echo "🏗️ Building containers..."
docker compose -f docker-compose.prod.yml build --no-cache

echo ""
echo "🚀 Starting services..."
docker compose -f docker-compose.prod.yml up -d

echo ""
echo "⏳ Waiting for services..."
sleep 20

echo ""
echo "📊 Container Status"
docker ps

echo ""
echo "❤️ Health Check"

curl -I http://localhost || true

curl -I http://localhost:8000/api/v1/health || true

echo ""
echo "======================================="
echo "✅ AdsPilot Deployment Completed"
echo "======================================="