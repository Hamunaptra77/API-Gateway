#!/bin/bash
set -e

DOMAIN="${1:-deine-domain.de}"
EMAIL="${2:-admin@deine-domain.de}"
SSL_DIR="$(cd "$(dirname "$0")" && pwd)/ssl"
CERTBOT_DIR="$(cd "$(dirname "$0")" && pwd)/certbot"

mkdir -p "$SSL_DIR" "$CERTBOT_DIR"

echo "🔐 Setting up Let's Encrypt certificate for $DOMAIN"
echo "📧 Using email: $EMAIL"
echo "📁 SSL dir: $SSL_DIR"
echo "📁 Certbot dir: $CERTBOT_DIR"

# First, ensure nginx is running for ACME challenge
echo "🚀 Starting api-gateway for ACME challenge..."
cd "$(dirname "$(cd "$(dirname "$0")" && pwd)")"
docker compose up -d api-gateway
sleep 5

# Run certbot
echo "📜 Running certbot..."
docker run --rm \
  -v "$SSL_DIR:/etc/letsencrypt" \
  -v "$CERTBOT_DIR:/var/www/certbot" \
  certbot/certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    --email "$EMAIL" \
    --agree-tos \
    --no-eff-email \
    --force-renewal \
    -d "$DOMAIN" \
    -d "www.$DOMAIN"

# Copy cert to expected location
echo "✅ Certificate obtained successfully!"
echo "📌 Certificate path: $SSL_DIR/live/$DOMAIN/fullchain.pem"
echo "🔑 Private key path: $SSL_DIR/live/$DOMAIN/privkey.pem"

# Restart api-gateway to load new certificate
echo "♻️  Restarting api-gateway..."
cd "$(dirname "$(cd "$(dirname "$0")" && pwd)")"
docker compose restart api-gateway
sleep 3

echo "✨ Done! Your domain is now HTTPS-enabled."
echo ""
echo "💡 To auto-renew every 60 days, add this to crontab:"
echo "   0 3 * * 0 cd $(cd "$(dirname "$(cd "$(dirname "$0")" && pwd)")" && pwd) && docker compose exec -T api-gateway nginx -s reload"

