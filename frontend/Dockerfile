# ==========================
# AdsPilot Frontend Builder
# ==========================

FROM node:22-alpine AS builder

WORKDIR /app

COPY package*.json ./

RUN npm ci

COPY . .

RUN npm run build

# --------------------------------------------------
# Build artifact only
# Nginx production container will serve /dist
# --------------------------------------------------

FROM alpine:3.21

WORKDIR /dist

COPY --from=builder /app/dist .

CMD ["sh", "-c", "echo 'AdsPilot frontend build is ready in /dist' && sleep infinity"]