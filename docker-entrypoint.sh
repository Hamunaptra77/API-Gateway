#!/bin/sh
set -e

SSL_DIR="/etc/ssl"
CERT="$SSL_DIR/fullchain.pem"
KEY="$SSL_DIR/privkey.pem"

mkdir -p "$SSL_DIR"

# Check for Let's Encrypt certificate first (live symlink)
if [ -L "$SSL_DIR/live" ] || [ -d "$SSL_DIR/live" ]; then
  LIVE_CERT="$SSL_DIR/live/deine-domain.de/fullchain.pem"
  LIVE_KEY="$SSL_DIR/live/deine-domain.de/privkey.pem"

  if [ -f "$LIVE_CERT" ] && [ -f "$LIVE_KEY" ]; then
    echo "Using Let's Encrypt certificate from $LIVE_CERT"
    ln -sf "$LIVE_CERT" "$CERT"
    ln -sf "$LIVE_KEY" "$KEY"
  fi
fi

# If no Let's Encrypt cert, generate self-signed
if [ ! -f "$CERT" ] || [ ! -f "$KEY" ]; then
  echo "Generating self-signed TLS certificate for deine-domain.de"
  openssl req -x509 -nodes -days 365 \
    -newkey rsa:2048 \
    -subj "/CN=deine-domain.de" \
    -keyout "$KEY" \
    -out "$CERT"
fi

uvicorn main:app --host 0.0.0.0 --port 80 &
UVICORN_HTTP_PID=$!

uvicorn main:app --host 0.0.0.0 --port 443 --ssl-keyfile "$KEY" --ssl-certfile "$CERT" &
UVICORN_HTTPS_PID=$!

trap 'kill -TERM "$UVICORN_HTTP_PID" "$UVICORN_HTTPS_PID" 2>/dev/null' INT TERM

wait "$UVICORN_HTTP_PID" "$UVICORN_HTTPS_PID"

