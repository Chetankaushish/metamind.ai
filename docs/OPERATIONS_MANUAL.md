# Production Operations Manual

## System Health & Observability
- **Prometheus Scrape Endpoint**: `http://backend:8000/api/v1/system/metrics`
- **Liveness Probe**: `http://backend:8000/api/v1/system/liveness`
- **Readiness Probe**: `http://backend:8000/api/v1/system/readiness`
- **Full System Health Check**: `http://backend:8000/api/v1/system/health`
- **System Status Dashboard Data**: `http://backend:8000/api/v1/system/status`

## Automated Security Scans
- **Dependency Scan**: Performed on every CI pipeline execution using `safety` and `npm audit`.
- **Static Analysis**: Code linting and typechecking via `tsc` and `flake8`.
- **SSL Auto-Renewal**: Cron job managed by certbot in Let's Encrypt stack container.
