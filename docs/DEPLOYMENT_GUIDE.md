# Enterprise Production Deployment Guide

## Overview
This document provides complete instructions for deploying **MetaMind AI** to a production **Hostinger VPS** using Docker Compose, NGINX reverse proxy, automated Alembic database migrations, and GitHub Actions CI/CD.

---

## Architecture Overview
- **Frontend**: Next.js / Vite SPA served via NGINX on port 443 / SSL
- **Backend API**: FastAPI asynchronous REST & WebSocket service
- **Database**: PostgreSQL 16 with Connection Pooling & Volume Persistence
- **Caching & Message Broker**: Redis 7
- **Background Workers**: Celery Workers & Celery Beat Scheduler
- **Observability**: Prometheus & Grafana monitoring stack

---

## Prerequisites
1. Hostinger VPS running Ubuntu 22.04 LTS (minimum 4GB RAM, 2 vCPUs recommended).
2. Domain name pointed to VPS IP (`A Record` for `@` and `www`).
3. Meta Developer App registered with OAuth Redirect URIs set to `https://yourdomain.com/api/v1/auth/callback`.

---

## Quick Start Deployment

1. **Clone Repository on VPS**:
   ```bash
   git clone https://github.com/your-org/metamind-ai.git /opt/metamind-ai
   cd /opt/metamind-ai
   ```

2. **Configure Environment Variables**:
   ```bash
   cp .env.example .env
   nano .env
   ```

3. **Validate Environment Configuration**:
   ```bash
   chmod +x scripts/*.sh
   ./scripts/validate_env.sh
   ```

4. **Execute Automated Deployment**:
   ```bash
   ./scripts/deploy-vps.sh
   ```

5. **Initialize SSL Certificate**:
   ```bash
   ./scripts/init-letsencrypt.sh
   ```

---

## CI/CD Pipeline Integration

The pipeline is automated via `.github/workflows/ci-cd.yml`:
1. Every **Pull Request** triggers linting, typechecking, vulnerability scanning, and Docker build verification.
2. Every **Push to `main`** executes SSH automated deployment on Hostinger VPS, runs database migrations (`alembic upgrade head`), and verifies health checks at `/api/v1/system/health`.
