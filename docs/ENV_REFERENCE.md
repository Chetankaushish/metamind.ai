# Environment Variable Reference

## Mandatory Production Variables

| Variable | Description | Example / Default |
|---|---|---|
| `DOMAIN_NAME` | Fully qualified domain name pointing to VPS | `app.metamind.ai` |
| `SSL_EMAIL` | Email address for Let's Encrypt SSL certificates | `devops@metamind.ai` |
| `POSTGRES_USER` | PostgreSQL superuser username | `metamind_user` |
| `POSTGRES_PASSWORD` | PostgreSQL superuser password | `SuperSecurePassword123!` |
| `POSTGRES_DB` | Primary application database name | `metamind_db` |
| `REDIS_PASSWORD` | Redis authentication password | `RedisSecretKey123!` |
| `SECRET_KEY` | JWT signing secret key (min 32 chars) | `e9f8a7b6c5d4e3f210a9b8c7d6e5f4a3` |
| `META_CLIENT_ID` | Meta App ID from Meta Developer Dashboard | `123456789012345` |
| `META_CLIENT_SECRET` | Meta App Secret Key | `a1b2c3d4e5f6g7h8i9j0` |
| `GRAFANA_ADMIN_PASSWORD` | Grafana administrator password | `AdminGrafanaSecret123!` |
| `ENVIRONMENT` | Runtime environment mode | `production` |
