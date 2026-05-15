# API Gateway

Ein FastAPI-basiertes API Gateway, das alle Microservices hinter einer einzigen Schnittstelle aggregiert.

## Verfügbare Endpunkte

Das API Gateway läuft auf Port `80`, `443` (HTTPS) und zusätzlich lokal auf `8080`.

### Terminal API
- **Pfad:** `/api/terminal/*`
- **Upstream:** `open-terminal-api:8000`
- **Limit:** 50 req/s

### Memory API
- **Pfad:** `/api/memory/*`
- **Upstream:** `memory-api:8001`
- **Limit:** 100 req/s

### Vector Memory API
- **Pfad:** `/api/vector/*`
- **Upstream:** `vector-memory-api:8002`
- **Limit:** 100 req/s

### Filesystem API
- **Pfad:** `/api/filesystem/*`
- **Upstream:** `filesystem-api:8003`
- **Limit:** 100 req/s

### Summarizer API
- **Pfad:** `/api/summarizer/*`
- **Upstream:** `summarizer-api:8004`
- **Limit:** 100 req/s

## Health Check

- **Endpoint:** `GET /health`
- **Response:** `OK`

## Gateway Info

- **Endpoint:** `GET /api-info`
- **Response:** JSON mit verfügbaren Services

## Dashboard

- **Web UI:** `GET /dashboard/`
- Darstellung von Gateway-Status, API-Health und Service-Routing

## OpenAPI

- **OpenAPI Spec:** `GET /openapi.json`
- Stellt die Gateway-Endpunkte als JSON-OpenAPI-Beschreibung bereit

## API Key Schutz

- Der Gateway erwartet einen gültigen API-Schlüssel für alle API-Anfragen und Dokumentationsendpunkte.
- **Header:** `X-API-KEY: <key>`
- **Alternativ:** `Authorization: Bearer <key>` oder `?api_key=<key>`
- Setze den Schlüssel über die Umgebungsvariable `API_KEY`.
- Für das Dashboard kann der Key optional als URL-Parameter `?api_key=<key>` übergeben werden.

## Features

✅ **Reverse Proxy** - Routet alle Anfragen an die richtigen Services
✅ **CORS Support** - Vollständige CORS-Header
✅ **Rate Limiting** - Verhindert Übernutzung
✅ **Health Check** - Automatische Gesundheitsprüfung
✅ **Request/Response Buffering** - Optimierte Performance
✅ **Custom Header** - Tracking durch API Gateway
✅ **Error Handling** - Konsistente Fehlerformate
✅ **Structured JSON Logging** - Standardisierte Logs für Observability
✅ **Prometheus Metrics** - `/metrics` Endpoint zur Überwachung
✅ **Circuit Breaker** - Schutz gegen instabile Upstream-Services

## Verwendungsbeispiele

```bash
# Health Check
curl http://localhost:8080/health

# Gateway Info
curl http://localhost:8080/api-info

# Terminal API
curl http://localhost:8080/api/terminal/sessions

# Memory API
curl -X POST http://localhost:8080/api/memory/memories \
  -H "Content-Type: application/json" \
  -d '{"content":"Beispiel Memory"}'

# Vector Memory API
curl http://localhost:8080/api/vector/search

# Filesystem API
curl http://localhost:8080/api/filesystem/files

# Summarizer API
curl -X POST http://localhost:8080/api/summarizer/summarize \
  -H "Content-Type: application/json" \
  -d '{"text":"Zu zusammenfassender Text"}'
```

## Konfiguration

Die Routing-Logik und das Verhalten des Gateways sind in `main.py` definiert.

- **Rate Limiting:** Wird derzeit durch den FastAPI-Proxy selbst nicht explizit getestet, kann aber später in `main.py` ergänzt werden.
- **Timeouts:** Der Proxy verwendet einen 60s-Timeout für Backend-Anfragen.
- **Dashboard / OpenAPI:** Statischer Inhalt wird von FastAPI aus `dashboard/` bereitgestellt.
- **Client Body Size:** Standardmäßig durch Uvicorn/Starlette begrenzt, kann bei Bedarf in `main.py` angepasst werden.

## Docker

```bash
# Image bauen
docker build -t api-gateway .

# Container starten
docker run -p 8080:8080 --network ai-net api-gateway
```

## Logs

FastAPI startet im Container. Logs sind über Docker abrufbar, z. B.:
- `docker-compose logs -f api-gateway`

## Monitoring

Das Gateway exponiert folgende Metriken (optional mit `prometheus-client`):

- HTTP Response Codes
- Request Count pro Endpoint
- Request-Latenz
- Upstream-Fehler
- Circuit Breaker Zustand
- Rate Limit Violations

### Prometheus Endpoint
- **Endpoint:** `GET /metrics`
- Exponiert Prometheus-Metriken, wenn `prometheus-client` installiert und `API_GATEWAY_METRICS_ENABLED=true` gesetzt ist.

### Logging
- Strukturierte Logs werden als JSON ausgegeben.
- Jede Anfrage enthält `X-Request-ID`.
- Upstream-Fehler werden inklusive Service und Retry-Versuchen geloggt.
