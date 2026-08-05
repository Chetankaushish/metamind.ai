# Incident Recovery & Emergency Procedures

## Overview
This document outlines response protocols and disaster recovery actions for MetaMind AI production incidents.

---

## Escalation Flow & Severity Levels

| Severity | Definition | Recovery Time Objective (RTO) |
|---|---|---|
| **SEV-1 (Critical)** | Entire System Down / Database Unavailable / Data Loss Risk | < 15 minutes |
| **SEV-2 (High)** | Meta Sync Failure / Automation Engine Stalled | < 1 hour |
| **SEV-3 (Medium)** | Slow Reporting Performance / Non-critical API Degradation | < 4 hours |

---

## Emergency Playbooks

### Playbook 1: Production Deployment Failure (Rollback)
If a deployment fails health check validation or causes 5xx errors:
```bash
cd /opt/metamind-ai
./scripts/rollback.sh
```

### Playbook 2: Database Outage or Connection Exhaustion
1. Check database container logs:
   ```bash
   docker compose logs --tail=100 postgres
   ```
2. Restart PostgreSQL:
   ```bash
   docker compose restart postgres
   ```
3. If database corruption occurs, restore from the latest automated backup:
   ```bash
   ./scripts/restore-db.sh $(ls -t /opt/metamind-ai/backups/*.sql.gz | head -n 1)
   ```

### Playbook 3: Redis Memory Limit Exceeded
1. Connect to Redis CLI and inspect memory usage:
   ```bash
   docker compose exec redis redis-cli info memory
   ```
2. Flush non-essential cache keys:
   ```bash
   docker compose exec redis redis-cli FLUSHDB
   ```

### Playbook 4: Meta Marketing API Rate Limit Exceeded (HTTP 429)
1. Check Prometheus metric: `meta_api_rate_limit_percent`.
2. Temporary increase sync interval in Celery Beat or pause non-critical background jobs until Meta rate limit window resets (60 minutes).
