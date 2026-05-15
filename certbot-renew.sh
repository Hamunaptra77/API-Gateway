#!/bin/bash
# Renewal helper script - runs certbot renewal inside the api-gateway container

set -e

DOMAIN="${1:-deine-domain.de}"
SSL_DIR="$(cd "$(dirname "$0")" && pwd)/ssl"
CERTBOT_DIR="$(cd "$(dirname "$0")" && pwd)/certbot"

echo "🔄 Running Certbot renewal for $DOMAIN..."

# Renewal (runs with --non-interactive and --quiet flags)
docker run --rm \
  -v "$SSL_DIR:/etc/letsencrypt" \
  -v "$CERTBOT_DIR:/var/www/certbot" \
  certbot/certbot renew \
    --non-interactive \
    --quiet \
    --webroot \
    --webroot-path=/var/www/certbot

# Reload nginx to pick up new cert
cd "$(dirname "$(cd "$(dirname "$0")" && pwd)")"
docker compose exec -T api-gateway nginx -s reload || true

echo "✅ Certificate renewal complete!"

