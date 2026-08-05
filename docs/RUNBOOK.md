# Enterprise Production Runbook

## Overview
This runbook contains operational procedures for managing MetaMind AI in a live production environment on Hostinger VPS.

---

## Service Management Commands

### Check All Container Statuses
```bash
docker compose ps
```

### View Live Combined Logs
```bash
docker compose logs -f
```

### View Specific Container Logs
```bash
docker compose logs -f backend
docker compose logs -f cel_worker
docker compose logs -f nginx
```

### Restart Services
```bash
docker compose restart backend
docker compose restart cel_worker
docker compose restart nginx
```

---

## Database & Persistence Management

### Perform Manual Database Backup
```bash
./scripts/backup-db.sh
```

### Restore Database from Backup
```bash
./scripts/restore-db.sh /path/to/backup_file.sql.gz
```

### Apply Alembic Migrations
```bash
docker compose run --rm backend alembic upgrade head
```

---

## Queue & Background Worker Monitoring

### Inspect Celery Queue Status
```bash
docker compose exec cel_worker celery -A app.core.celery_app inspect active
```

### Purge Pending Queue Tasks (Emergency)
```bash
docker compose exec cel_worker celery -A app.core.celery_app purge
```
