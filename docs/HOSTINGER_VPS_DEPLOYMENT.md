# MetaMind AI - Hostinger VPS Production Deployment Guide

This guide details the step-by-step instructions to deploy **MetaMind AI** on a **Hostinger Linux VPS** running Ubuntu 24.04 LTS with Docker Compose, NGINX reverse proxy, PostgreSQL 16, Redis 7, Celery background workers, and Let's Encrypt SSL on a custom domain.

---

## 📋 Infrastructure & Architecture Overview

```
Custom Domain (HTTPS) 
       │
       ▼
   [ NGINX Reverse Proxy ] (Ports 80 & 443 with Let's Encrypt SSL)
       ├──> / (Next.js Standalone Frontend Container - Port 3000)
       └──> /api/ (FastAPI Python Backend Container - Port 8000)
                ├──> PostgreSQL 16 Database
                ├──> Redis 7 Cache & Task Broker
                ├──> Celery Worker (Meta Marketing API Sync)
                └──> Celery Beat Scheduler (Token Auto-Refresh)
```

---

## 🚀 Step 1: Initial VPS Configuration (Ubuntu 24.04 LTS)

1. **SSH into your Hostinger VPS**:
   ```bash
   ssh root@<your-vps-ip>
   ```

2. **Update system packages & install prerequisites**:
   ```bash
   sudo apt update && sudo apt upgrade -y
   sudo apt install -y curl git ufw htop gzip
   ```

3. **Configure Firewall (UFW)**:
   ```bash
   sudo ufw allow 22/tcp
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   sudo ufw enable
   ```

---

## 🐳 Step 2: Install Docker & Docker Compose

Run the official Docker setup:
```bash
curl -fsSL https://get.docker.com | sh
sudo systemctl enable docker
sudo systemctl start docker
```

---

## 📂 Step 3: Clone Repository & Configure Environment

1. Clone your MetaMind AI repository to `/opt/metamind-ai`:
   ```bash
   cd /opt
   git clone <your-git-repo-url> metamind-ai
   cd metamind-ai
   ```

2. Copy the production environment template:
   ```bash
   cp .env.production.example .env
   ```

3. Edit `.env` with your custom domain and production passwords:
   ```bash
   nano .env
   ```
   *Fill in `DOMAIN_NAME`, `POSTGRES_PASSWORD`, `META_APP_ID`, `META_APP_SECRET`, and `GEMINI_API_KEY`.*

---

## 🌐 Step 4: Configure Domain DNS Records

Log into your domain registrar (or Hostinger DNS Zone Editor) and point your domain:

| Type | Name | Content / Value | TTL |
| ---- | ---- | --------------- | --- |
| A | `@` | `<Your Hostinger VPS IP>` | 300 |
| A | `www` | `<Your Hostinger VPS IP>` | 300 |

---

## 🔒 Step 5: Provision Let's Encrypt SSL & Launch Stack

1. Make scripts executable:
   ```bash
   chmod +x scripts/*.sh
   ```

2. Run the automated SSL setup script:
   ```bash
   ./scripts/init-letsencrypt.sh
   ```

3. Launch the full production stack:
   ```bash
   ./scripts/deploy-vps.sh
   ```

---

## ⏰ Step 6: Set Up Automated Database Backups (Cron)

Set up a daily automated PostgreSQL backup at 03:00 AM:

```bash
crontab -e
```

Add this line:
```cron
0 3 * * * /bin/bash /opt/metamind-ai/scripts/backup-db.sh >> /var/log/metamind_backup.log 2>&1
```

---

## 🔍 Useful VPS Operations & Commands

| Task | Command |
| ---- | ------- |
| **Check service status** | `docker compose ps` |
| **View real-time logs** | `docker compose logs -f --tail=100` |
| **View FastAPI logs** | `docker compose logs -f backend` |
| **View Celery sync logs** | `docker compose logs -f celery_worker` |
| **Restart NGINX** | `docker compose restart nginx` |
| **Restore DB backup** | `./scripts/restore-db.sh ./backups/postgres/<backup_file>.sql.gz` |
