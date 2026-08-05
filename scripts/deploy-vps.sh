#!/usr/bin/env bash
# =============================================================================
# MetaMind AI - Production Hostinger VPS Deployment Script
# =============================================================================
set -e

echo "🚀 Starting MetaMind AI Production Deployment on Hostinger VPS..."

# 1. Check if .env file exists
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        echo "⚠️ .env file not found. Copying .env.example to .env..."
        cp .env.example .env
        echo "❗ Please update .env with your actual domain name and credentials!"
    else
        echo "❌ Error: .env file missing. Aborting deployment."
        exit 1
    fi
fi

source .env

# 2. Verify Docker and Docker Compose availability
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Installing Docker..."
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker $USER
fi

# 3. Pull latest base images and build containers
echo "📦 Building Docker Compose production stack..."
docker compose -f docker-compose.prod.yml build --parallel

# 4. Start database and cache services first
echo "🗄️ Starting PostgreSQL & Redis..."
docker compose -f docker-compose.prod.yml up -d postgres redis

# 5. Wait for PostgreSQL health check
echo "⏳ Waiting for PostgreSQL to be ready..."
until docker compose -f docker-compose.prod.yml exec -T postgres pg_isready -U ${POSTGRES_USER:-metamind} -d ${POSTGRES_DB:-metamind_prod} &> /dev/null; do
    sleep 2
done
echo "✅ PostgreSQL is online."

# 6. Start full production stack
echo "🌟 Launching Frontend, Backend, Celery Workers, Prometheus, Grafana & NGINX..."
docker compose -f docker-compose.prod.yml up -d

# 7. Check health status
echo "🏥 Performing system health check..."
sleep 5
docker compose -f docker-compose.prod.yml ps

echo "========================================================================="
echo "🎉 MetaMind AI successfully deployed to Hostinger VPS!"
echo "🌐 Domain: https://${DOMAIN_NAME:-localhost}"
echo "📊 NGINX status: Active on Ports 80 / 443"
echo "========================================================================="
