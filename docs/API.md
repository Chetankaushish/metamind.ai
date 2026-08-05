# MetaMind AI API v1 Specification

## REST API Endpoints Overview

All API endpoints are prefixed with `/api/v1`.

### Health & System
- `GET /api/v1/health` - Backend health status, DB connectivity, Redis latency
- `GET /api/v1/system/health` - Infrastructure telemetry

### Authentication
- `POST /api/v1/auth/login` - User login & JWT issuance
- `POST /api/v1/auth/signup` - Register user & tenant organization
- `GET /api/v1/auth/me` - Get current authenticated user profile

### Meta Marketing Campaigns
- `GET /api/v1/campaigns` - List Meta marketing campaigns
- `POST /api/v1/campaigns` - Create a new Meta marketing campaign
- `PATCH /api/v1/campaigns/{id}` - Update campaign budget, status, or bid strategy
- `DELETE /api/v1/campaigns/{id}` - Delete/archive campaign

### Meta Marketing Ad Sets & Ads
- `GET /api/v1/adsets` - List ad sets
- `POST /api/v1/adsets` - Create ad set
- `GET /api/v1/ads` - List ad creatives & performance

### Gemini AI Copilot
- `POST /api/v1/copilot/chat` - Interactive marketing strategy assistant powered by Gemini
- `POST /api/v1/copilot/generate-ad-copy` - AI ad creative copywriter

### Real-Time WebSockets
- `WS /api/v1/ws?token={JWT_TOKEN}` - Real-time campaign telemetry stream & live rule triggers
