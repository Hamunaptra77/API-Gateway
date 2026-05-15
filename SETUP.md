# API Gateway - Vollständige Dokumentation

## Überblick

Das API Gateway ist ein Nginx-basierter Reverse Proxy, der alle Microservices hinter einer zentralen Schnittstelle aggregiert. Dies ermöglicht:

- **Vereinfachte Client-Integration** - Ein einziger Endpunkt statt 5
- **Zentralisierte Authentifizierung** - Optional erweiterbar
- **Rate Limiting** - Verhindert Service-Übernutzung
- **CORS-Handling** - Automatisch konfiguriert
- **Health Checking** - Monitoring der Services
- **Request/Response Logging** - Für Debugging

## Architecture

```
Client Requests
    ↓
┌─────────────────────────────┐
│   API Gateway (Port 8080)   │
│  (Nginx Reverse Proxy)      │
└─────────────────────────────┘
    ↓ ↓ ↓ ↓ ↓
    │ │ │ │ └─→ Summarizer API (8004)
    │ │ │ └───→ Filesystem API (8003)
    │ │ └─────→ Vector Memory API (8002)
    │ └───────→ Memory API (8001)
    └─────────→ Terminal API (8000)
```

## Installation & Setup

### 1. Services starten

```bash
cd /home/ki-projekt
docker-compose up -d
```

Das API Gateway wird automatisch mit den anderen Services gestartet.

### 2. Überprüfen dass alles läuft

```bash
# Logs anschauen
docker-compose logs -f api-gateway

# Status abfragen
curl http://localhost:8080/health
```

### 3. Gateway-Info abrufen

```bash
curl http://localhost:8080/api-info
```

## Verfügbare Endpunkte

### Health Check
- **URL:** `GET /health`
- **Response:** `OK`
- **Timeout:** 1s
- **Zweck:** Verfügbarkeit des Gateways überprüfen

### Gateway Info
- **URL:** `GET /api-info`
- **Response:** JSON mit verfügbaren Services
- **Zweck:** Discoverable Service-Listing

### Terminal API → `/api/terminal/*`

**Upstream Server:** `open-terminal-api:8000`
**Pfad-Umschreibung:** `/api/terminal/...` → `http://open-terminal-api:8000/...`
**Rate Limit:** 50 req/s (burst 20)
**Timeout:** 60s
**Max Body Size:** 50MB
**Nutzung:** Terminal/Shell-Operationen

**Beispiele:**
```bash
# Sessions auflisten
curl http://localhost:8080/api/terminal/sessions

# Eine Session ausführen
curl -X POST http://localhost:8080/api/terminal/execute \
  -H "Content-Type: application/json" \
  -d '{"command":"ls -la"}'
```

### Memory API → `/api/memory/*`

**Upstream Server:** `memory-api:8001` (PostgreSQL + pgvector)
**Pfad-Umschreibung:** `/api/memory/...` → `http://memory-api:8001/...`
**Rate Limit:** 100 req/s (burst 50)
**Timeout:** 30s
**Nutzung:** Speicherverwaltung und Abrufen von Erinnerungen

**Beispiele:**
```bash
# Alle Memories abrufen
curl http://localhost:8080/api/memory/memories

# Ein Memory erstellen
curl -X POST http://localhost:8080/api/memory/memories \
  -H "Content-Type: application/json" \
  -d '{"content":"Wichtige Information","tags":["work","important"]}'

# Memory nach ID abrufen
curl http://localhost:8080/api/memory/memories/1
```

### Vector Memory API → `/api/vector/*`

**Upstream Server:** `vector-memory-api:8002` (Qdrant)
**Pfad-Umschreibung:** `/api/vector/...` → `http://vector-memory-api:8002/...`
**Rate Limit:** 100 req/s (burst 50)
**Timeout:** 30s
**Nutzung:** Vektorbasierte Ähnlichkeitssuche

**Beispiele:**
```bash
# Ähnliche Vektoren suchen
curl -X POST http://localhost:8080/api/vector/search \
  -H "Content-Type: application/json" \
  -d '{"vector":[0.1, 0.2, 0.3, ...], "limit":10}'

# Collection-Info
curl http://localhost:8080/api/vector/collections
```

### Filesystem API → `/api/filesystem/*`

**Upstream Server:** `filesystem-api:8003`
**Pfad-Umschreibung:** `/api/filesystem/...` → `http://filesystem-api:8003/...`
**Rate Limit:** 100 req/s (burst 50)
**Timeout:** 120s
**Max Body Size:** 50MB
**Buffering:** Aus (für Datei-Uploads)
**Nutzung:** Datei-Speicherung und Management

**Beispiele:**
```bash
# Dateien auflisten
curl http://localhost:8080/api/filesystem/files

# Datei hochladen
curl -F "file=@/path/to/file.txt" http://localhost:8080/api/filesystem/upload

# Datei herunterladen
curl http://localhost:8080/api/filesystem/download/filename.txt
```

### Summarizer API → `/api/summarizer/*`

**Upstream Server:** `summarizer-api:8004` (Ollama + LLM)
**Pfad-Umschreibung:** `/api/summarizer/...` → `http://summarizer-api:8004/...`
**Rate Limit:** 100 req/s (burst 30)
**Timeout:** 300s (5 Minuten - für LLM-Verarbeitung)
**Nutzung:** Text-Zusammenfassung mit LLM

**Beispiele:**
```bash
# Text zusammenfassen
curl -X POST http://localhost:8080/api/summarizer/summarize \
  -H "Content-Type: application/json" \
  -d '{"text":"Langer Text hier...", "max_length":100}'

# Zusammenfassung mit Kontext
curl -X POST http://localhost:8080/api/summarizer/summarize-context \
  -H "Content-Type: application/json" \
  -d '{"text":"Text...", "context":"Kontext..."}'
```

## Features & Konfiguration

### Rate Limiting

Das Gateway implementiert 2 Rate-Limit-Zonen:

1. **Terminal Zone:** 50 req/s (mit 20er Burst)
2. **Standard Zone:** 100 req/s (mit 50er Burst)

Limits können in `nginx.conf` angepasst werden:

```nginx
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=100r/s;
limit_req zone=api_limit burst=50 nodelay;
```

### CORS Support

CORS-Header werden automatisch hinzugefügt:

```nginx
add_header 'Access-Control-Allow-Origin' '*' always;
add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, DELETE, OPTIONS, PATCH' always;
add_header 'Access-Control-Allow-Headers' '...' always;
```

### Request Header

Das Gateway fügt folgende Header hinzu:

```
X-Real-IP: <Client IP>
X-Forwarded-For: <Client IP>
X-Forwarded-Proto: <http|https>
X-API-Gateway: true
```

### Response Buffering

- **Memory APIs:** Buffering aktiviert (schneller)
- **Filesystem API:** Buffering deaktiviert (für große Dateien)

### Client Body Size

Maximum 50MB für alle Uploads:

```nginx
client_max_body_size 50M;
```

## Monitoring & Debugging

### 1. Status-Monitor starten

```bash
# Voraussetzung: pip install requests
python3 /home/ki-projekt/api-gateway/monitor.py
```

Output:
```
================================================================================
API Gateway Status Monitor
================================================================================
Time: 2024-05-10 14:30:45
================================================================================

Gateway Status: ✓ RUNNING
URL: http://localhost:8080

Service Status:
  ✓ Terminal              OK
  ✓ Memory                OK
  ✓ Vector Memory         OK
  ✓ Filesystem            OK
  ✓ Summarizer            OK

Available Endpoints:
  • /api/terminal/     - Terminal/Shell Operations
  • /api/memory/       - Memory Management (PostgreSQL)
  • /api/vector/       - Vector Memory (Qdrant)
  • /api/filesystem/   - File Storage Operations
  • /api/summarizer/   - Text Summarization (LLM)
```

### 2. Logs anschauen

```bash
# Gateway Logs
docker-compose logs -f api-gateway

# Access Logs (im Container)
docker exec api-gateway tail -f /var/log/nginx/access.log

# Error Logs (im Container)
docker exec api-gateway tail -f /var/log/nginx/error.log
```

### 3. Health Checks

```bash
# Gateway Health
curl -v http://localhost:8080/health

# Service Health (einzeln)
curl http://localhost:8080/api/terminal/health
curl http://localhost:8080/api/memory/health
curl http://localhost:8080/api/vector/health
curl http://localhost:8080/api/filesystem/health
curl http://localhost:8080/api/summarizer/health
```

### 4. Response Headers überprüfen

```bash
curl -i http://localhost:8080/api-info
```

Wichtige Header:
- `Access-Control-Allow-Origin` - CORS
- `Server` - Nginx
- `X-Forwarded-For` - Client-IP

## Performance-Tuning

### 1. Buffer-Größen anpassen

```nginx
proxy_buffer_size 4k;
proxy_buffers 8 4k;  # Für Summarizer: 16 4k
```

### 2. Timeouts für langsame Services

```nginx
proxy_connect_timeout 30s;  # Verbindung aufbauen
proxy_send_timeout 30s;     # Request senden
proxy_read_timeout 30s;     # Response empfangen
```

Summarizer braucht längere Timeouts (300s) für LLM-Verarbeitung.

### 3. Rate Limits anpassen

```nginx
# 500 requests pro Sekunde statt 100
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=500r/s;
```

## Fehlerbehandlung

### Gateway antwortet nicht

```bash
# Status abfragen
docker-compose ps api-gateway

# Container neustarten
docker-compose restart api-gateway

# Logs anschauen
docker-compose logs api-gateway
```

### Service antwortet nicht (502 Bad Gateway)

```bash
# Upstream Service überprüfen
curl http://localhost:8000  # terminal
curl http://localhost:8001  # memory
curl http://localhost:8002  # vector
curl http://localhost:8003  # filesystem
curl http://localhost:8004  # summarizer

# Service neustarten
docker-compose restart open-terminal-api
```

### Rate Limit überschritten (429 Too Many Requests)

Dies ist normal wenn zu viele Requests gesendet werden. Limit-Zonen anpassen in `nginx.conf`:

```nginx
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=200r/s;  # Erhöht von 100
```

### CORS-Fehler im Browser

Das Gateway sollte CORS automatisch handhaben. Falls nicht, überprüfen Sie:

```bash
curl -i -H "Origin: http://localhost:3000" http://localhost:8080/api/memory/
```

Response sollte enthalten:
```
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS, PATCH
```

## Erweiterte Konfiguration

### Mit SSL/TLS (Optional)

1. Ordner für Zertifikate und ACME-Challenges erstellen:
```bash
mkdir -p /home/ki-projekt/api-gateway/ssl
mkdir -p /home/ki-projekt/api-gateway/certbot
```

2. Die API-Gateway-Konfiguration verwendet jetzt `/etc/nginx/ssl/fullchain.pem` und `/etc/nginx/ssl/privkey.pem`.
   - Wenn dort keine Zertifikate vorhanden sind, erzeugt der Start des Containers automatisch ein selbstsigniertes Zertifikat.
   - Für ein echtes Let's Encrypt-Zertifikat kann der Let's Encrypt-Webroot genutzt werden.

3. Beispiel für die Zertifikatsausgabe mit Certbot:
```bash
docker run --rm \
  -v "$PWD/api-gateway/ssl:/etc/letsencrypt" \
  -v "$PWD/api-gateway/certbot:/var/www/certbot" \
  certbot/certbot certonly --webroot \
  --webroot-path=/var/www/certbot \
  --email your-email@example.com \
  --agree-tos --no-eff-email \
  -d deine-domain.de -d www.deine-domain.de
```

4. Nach erfolgreicher Erstellung startet das Gateway mit echtem HTTPS.

### Mit Authentifizierung (Optional)

1. .htpasswd erstellen:
```bash
htpasswd -c .htpasswd username
```

2. Nginx-Config:
```nginx
auth_basic "API Gateway";
auth_basic_user_file /etc/nginx/.htpasswd;
```

### Mit Custom Endpoints

Neue Service hinzufügen zu `nginx.conf`:

```nginx
upstream new_service {
    server new-service:8005;
}

location /api/new-service/ {
    proxy_pass http://new_service/;
    proxy_set_header Host $host;
    # ... rest
}
```

Dann docker-compose.yml aktualisieren.

## Docker-Befehle

```bash
# Gateway-Container anschauen
docker ps -a | grep api-gateway

# Logs (live)
docker-compose logs -f api-gateway

# In Container gehen
docker exec -it api-gateway bash

# Nginx-Config testen
docker exec api-gateway nginx -t

# Config neu laden (ohne Neustart)
docker exec api-gateway nginx -s reload

# Gateway neustarten
docker-compose restart api-gateway

# Gateway mit Rebuild
docker-compose up -d --build api-gateway
```

## Troubleshooting Checklist

- [ ] Docker Container laufen? `docker-compose ps`
- [ ] Alle Services sind erreichbar? `python3 monitor.py`
- [ ] Port 8080 ist frei? `netstat -tuln | grep 8080`
- [ ] Nginx-Config ist gültig? `docker exec api-gateway nginx -t`
- [ ] Firewall blockiert nicht? `telnet localhost 8080`
- [ ] Logs zeigen Fehler? `docker-compose logs api-gateway`

## Zusammenfassung

Das API Gateway bietet:

✅ Zentrale Schnittstelle für alle Microservices
✅ Automatisches Load Balancing
✅ Rate Limiting & DDoS Protection
✅ CORS Support
✅ Request/Response Logging
✅ Health Checking
✅ Simple Konfiguration
✅ Einfache Erweiterung

**Einziger Endpunkt für Clients:** `http://localhost:8080`

Alle Services sind über `/api/<service>/` erreichbar!

