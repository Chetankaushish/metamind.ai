# MetaMind AI — Enterprise Marketing Analytics & AI Copilot Platform

MetaMind AI is an enterprise-grade AI marketing analytics and automation platform powered by FastAPI, React, PostgreSQL, Redis, Celery, and Meta Marketing API v21.0.

---

## 🌟 Key Features

- **Real-Time Marketing Analytics**: Live ROAS, CPA, CTR, Spend, and Revenue telemetry synced with Meta Marketing API.
- **AI Copilot**: Natural language campaign insights powered by PostgreSQL analytics and Gemini AI. Zero hallucinated metrics.
- **Autonomous AI Agents**: Multi-agent orchestration for creative fatigue detection, audience overlap, and budget optimization.
- **Execution Guardrails**: Automated execution plans with required human confirmation before making live changes to Meta campaigns.
- **Enterprise Security**: JWT authentication, OAuth state token validation, RBAC, and encrypted credential storage.

---

## 🚀 Architecture

```text
               ┌────────────────────────┐
               │    NGINX Web Proxy     │
               │   (SSL / Certbot 80/443)│
               └───────────┬────────────┘
                           │
             ┌─────────────┴─────────────┐
             ▼                           ▼
   ┌──────────────────┐        ┌──────────────────┐
   │  React Frontend  │        │  FastAPI Backend │
   │   (Vite Port 3000)│        │   (Uvicorn 8000) │
   └──────────────────┘        └─────────┬────────┘
                                         │
                   ┌─────────────────────┼─────────────────────┐
                   ▼                     ▼                     ▼
         ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
         │ PostgreSQL 16 DB │  │   Redis 7 Cache  │  │ Celery Workers   │
         │ (Persisted State)│  │ (PubSub/Sessions)│  │ (Sync Scheduler) │
         └──────────────────┘  └──────────────────┘  └──────────────────┘
```

---

## 📦 Quick Start (Docker Compose)

```bash
# 1. Clone repository
git clone https://github.com/your-org/metamind-ai.x.git
cd metamind-ai

# 2. Configure environment
cp .env.example .env
# Edit .env with your credentials

# 3. Launch full stack
docker-compose up -d --build
```

---

## 📄 Documentation

Detailed operational documentation is available in `/docs`:

- [`ARCHITECTURE.md`](/docs/ARCHITECTURE.md): System design & data flow
- [`HOSTINGER_VPS_DEPLOYMENT.md`](/docs/HOSTINGER_VPS_DEPLOYMENT.md): Production deployment guide
- [`META_MARKETING_API_SETUP.md`](/docs/META_MARKETING_API_SETUP.md): Meta App setup & OAuth scopes
- [`ENVIRONMENT.md`](/docs/ENVIRONMENT.md): Full environment variable reference
- [`API.md`](/docs/API.md): FastAPI REST API endpoints

---

## 🛡️ License & Support

Developed for **Volzad Tech and Service**. Confidential & Proprietary.
