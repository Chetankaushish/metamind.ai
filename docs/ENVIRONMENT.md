# MetaMind AI Environment Reference

This document describes all required and optional environment variables for MetaMind AI monorepo deployment.

| Variable Name | Required | Default Value | Description |
|---------------|----------|---------------|-------------|
| `DOMAIN_NAME` | Yes | `localhost` | VPS domain name for SSL & CORS origins |
| `POSTGRES_USER` | Yes | `metamind` | PostgreSQL database username |
| `POSTGRES_PASSWORD` | Yes | - | PostgreSQL secret password |
| `POSTGRES_DB` | Yes | `metamind_prod` | PostgreSQL database name |
| `JWT_SECRET` | Yes | - | 32+ character key for signing JWT tokens |
| `META_APP_ID` | Yes | - | Meta App ID from Meta Developers Dashboard |
| `META_APP_SECRET` | Yes | - | Meta App Secret key |
| `META_WEBHOOK_VERIFY_TOKEN` | Yes | - | Custom secret token for Meta CAPI webhooks |
| `GEMINI_API_KEY` | Optional | - | Google Gemini API key for AI Copilot |
| `REDIS_URL` | Yes | `redis://redis:6379/0` | Redis URI for Celery and caching |
