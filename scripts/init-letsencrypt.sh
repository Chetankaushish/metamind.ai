#!/usr/bin/env bash
# =============================================================================
# MetaMind AI - Let's Encrypt SSL Provisioning Script for Hostinger VPS
# =============================================================================
set -e

if [ ! -f .env ]; then
  echo "❌ .env file not found! Copy .env.production.example to .env first."
  exit 1
fi

source .env

DOMAIN="${DOMAIN_NAME}"
EMAIL="${SSL_EMAIL:-admin@${DOMAIN}}"

if [ -z "$DOMAIN" ] || [ "$DOMAIN" == "yourdomain.com" ]; then
  echo "❌ Please set DOMAIN_NAME in .env before running SSL setup."
  exit 1
fi

echo "🔒 Provisioning Let's Encrypt SSL Certificate for ${DOMAIN}..."

# Create local directories for certbot
mkdir -p ./nginx/ssl/live/metamind
mkdir -p ./nginx/certbot/www

# Generate self-signed certificate placeholder for initial NGINX boot
if [ ! -f "./nginx/ssl/live/metamind/fullchain.pem" ]; then
  echo "🔑 Generating temporary self-signed SSL cert for boot..."
  openssl req -x509 -nodes -newkey rsa:2048 -days 1 \
    -keyout "./nginx/ssl/live/metamind/privkey.pem" \
    -out "./nginx/ssl/live/metamind/fullchain.pem" \
    -subj "/CN=localhost"
fi

# Start NGINX
docker compose up -d nginx

# Request Let's Encrypt Certificate via Certbot Docker
echo "📡 Requesting official SSL certificate from Let's Encrypt..."
docker run --rm \
  -v "$(pwd)/nginx/ssl:/etc/letsencrypt" \
  -v "$(pwd)/nginx/certbot/www:/var/www/certbot" \
  certbot/certbot certonly --webroot \
  --webroot-path=/var/www/certbot \
  --email "$EMAIL" \
  --agree-tos \
  --no-eff-email \
  -d "$DOMAIN" \
  -d "www.$DOMAIN" || true

# Reload NGINX
echo "🔄 Reloading NGINX with Let's Encrypt SSL Certificate..."
docker compose exec nginx nginx -s reload

echo "✅ SSL Certificate provisioned successfully for https://${DOMAIN}!"
