# Hostinger Ubuntu 24.04 VPS Deployment Guide

This guide provides a step-by-step walkthrough for deploying MetaMind AI on a Hostinger Ubuntu 24.04 VPS using Docker Compose and NGINX.

## Prerequisites

- Hostinger Ubuntu 24.04 KVM VPS (2+ vCPU, 4GB+ RAM recommended)
- A domain name pointing to your VPS IP address (e.g., `app.yourdomain.com`)
- Root or sudo user access

## Step-by-Step Installation

### 1. Initial VPS Setup & Docker Installation

Run the automated Hostinger deployment script:

```bash
# Clone repository onto VPS
git clone https://github.com/your-org/metamind.git /opt/metamind
cd /opt/metamind

# Run automated Hostinger VPS installer
chmod +x scripts/deploy-vps.sh
./scripts/deploy-vps.sh --domain app.yourdomain.com --email admin@yourdomain.com
```

### 2. Configure Environment Variables

Edit `/opt/metamind/.env` with your production keys:

```env
DOMAIN_NAME=app.yourdomain.com
POSTGRES_USER=metamind
POSTGRES_PASSWORD=YourSecurePassword123!
POSTGRES_DB=metamind_prod
JWT_SECRET=Your32CharJWTSecretKeyHere!!
META_APP_ID=1092840192840
META_APP_SECRET=YourMetaAppSecretHere
META_WEBHOOK_VERIFY_TOKEN=metamind_verify_secret_123
GEMINI_API_KEY=YourGeminiAPIKeyHere
```

### 3. Build & Boot Containers

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

### 4. Verify System Health

Run the diagnostic health script:

```bash
python3 monitoring/health_check.py
```
