# MetaMind AI Architecture & System Specification

## Overview
MetaMind AI is an enterprise-grade Meta Marketing API management platform with autonomous Gemini 1.5 Pro AI Copilot guardrails, CAPI sync, and white-label multi-tenant capabilities. The system is architected as a clean monorepo optimized for deployment on a single Hostinger Ubuntu 24.04 VPS containerized via Docker Compose.

```
                    ┌───────────────────────────────────────────────┐
                    │               NGINX Proxy                      │
                    │   SSL Termination & Rate Limiting (80/443)    │
                    └───────────────────────┬───────────────────────┘
                                            │
                    ┌───────────────────────┴───────────────────────┐
                    │                                               │
                    ▼                                               ▼
         ┌─────────────────────┐                         ┌────────────────────┐
         │  Frontend (Vite)    │                         │  Backend (FastAPI) │
         │ React + Tailwind    │                         │  Python + Uvicorn  │
         └─────────────────────┘                         └──────────┬─────────┘
                                                                    │
                                       ┌────────────────────────────┼────────────────────────────┐
                                       │                            │                            │
                                       ▼                            ▼                            ▼
                            ┌─────────────────────┐      ┌─────────────────────┐      ┌────────────────────┐
                            │ PostgreSQL Database │      │  Redis Cache Broker │      │  Celery Workers    │
                            │  Async SQLAlchemy   │      │ Metrics / WebSockets│      │ Background Jobs    │
                            └─────────────────────┘      └─────────────────────┘      └────────────────────┘
```

## Core Monorepo Components

1. **Frontend (`/frontend`)**: Single Page Application built with React 19, Vite, Tailwind CSS v4, Lucide icons, and Recharts. Serves real-time Meta Marketing telemetry, campaign controls, audience builder, and AI copilot drawer.
2. **Backend (`/backend`)**: Asynchronous FastAPI service supporting RESTful API v1 and WebSocket channels. Features JWT authentication, Redis rate limiting, SQLAlchemy async ORM, and Pydantic schemas.
3. **Database (`/backend/app/database`)**: PostgreSQL 16 database storing multi-tenant organizations, Meta campaign records, ad set budget guardrails, audit logs, and user credentials.
4. **Task Queue (`/backend/app/tasks`)**: Celery background worker and beat scheduler for automated Meta Graph API sync every 15 minutes, token lifecycle renewals, and rule execution.
5. **Reverse Proxy (`/nginx`)**: NGINX server with SSL termination via Let's Encrypt / Certbot, gzip compression, HTTP/2 support, and API proxying.
