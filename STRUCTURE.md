# API Gateway - Dateistruktur

```
api-gateway/
├── Dockerfile          # Container Image Definition
├── docker-compose.yml  # (Parent) Docker Compose Orchestrierung
├── nginx.conf          # Nginx Reverse Proxy Konfiguration
├── README.md           # Hauptdokumentation
├── SETUP.md            # Ausführliche Setup & Troubleshooting Guide
├── Makefile            # Nützliche Befehle
├── start.sh            # Quick Start Script
├── monitor.py          # Status Monitor Tool
├── client.py           # Python Client Bibliothek
└── .dockerignore       # Docker Ignore Datei
```

## Datei Beschreibungen

### Core Files

| Datei | Zweck | Format |
|-------|-------|--------|
| `Dockerfile` | Container Image für API Gateway | Dockerfile |
| `nginx.conf` | Nginx Reverse Proxy Konfiguration mit allen Routes | NGINX Config |
| `.dockerignore` | Files die nicht in Docker Image kopiert werden | Plain Text |

### Dokumentation

| Datei | Zweck | Format |
|-------|-------|--------|
| `README.md` | Übersicht und Quick Reference | Markdown |
| `SETUP.md` | Ausführliche Setup- und Troubleshooting-Anleitung | Markdown |
| `Makefile` | Nützliche Make-Befehle für tägliche Aufgaben | Makefile |

### Tools & Utilities

| Datei | Zweck | Sprache |
|-------|-------|---------|
| `start.sh` | Automatisiertes Quick Start Script | Bash |
| `monitor.py` | Status Monitor für alle Services | Python 3 |
| `client.py` | Python Client Bibliothek | Python 3 |

## Quick Start

### 1. Services starten
```bash
cd /home/ki-projekt/api-gateway
./start.sh
```

### 2. Status überprüfen
```bash
python3 monitor.py
```

### 3. Mit Makefile arbeiten
```bash
make help      # Alle Befehle anschauen
make up        # Services starten
make logs      # Logs anschauen
make test      # Gateway testen
```

## Verfügbare Ports

| Service | Port | Interne Route |
|---------|------|---------------|
| API Gateway | 8080 | - |
| Terminal API | 8000 | /api/terminal/ |
| Memory API | 8001 | /api/memory/ |
| Vector Memory API | 8002 | /api/vector/ |
| Filesystem API | 8003 | /api/filesystem/ |
| Summarizer API | 8004 | /api/summarizer/ |

## Wichtigste URLs

```
Gateway Health:  http://localhost:8080/health
Gateway Info:    http://localhost:8080/api-info
Terminal:        http://localhost:8080/api/terminal/
Memory:          http://localhost:8080/api/memory/
Vector Memory:   http://localhost:8080/api/vector/
Filesystem:      http://localhost:8080/api/filesystem/
Summarizer:      http://localhost:8080/api/summarizer/
```

## Features

✅ **Nginx Reverse Proxy** - Routet alle Requests an die richtigen Services  
✅ **Rate Limiting** - Verhindert Service-Übernutzung  
✅ **CORS Support** - Vorkonfiguriert für Browser-Requests  
✅ **Health Checking** - Automatische Verfügbarkeitsprüfung  
✅ **Request Logging** - Alle Requests werden geloggt  
✅ **Buffering** - Optimiert für unterschiedliche Datenmengen  
✅ **Custom Headers** - Tracking über X-API-Gateway Header  

## Entwicklung

### Config ändern
1. `nginx.conf` bearbeiten
2. Container neu bauen: `docker-compose build api-gateway`
3. Services neu starten: `docker-compose restart api-gateway`

### Neuen Service hinzufügen
1. Service zu `docker-compose.yml` hinzufügen
2. Upstream in `nginx.conf` definieren
3. Location block für die Route hinzufügen
4. Container neu starten

### Python Client nutzen
```python
from client import APIGatewayClient

client = APIGatewayClient()

# Memory API
memories = client.memory.list_memories()
client.memory.create_memory("Wichtig", tags=["work"])

# Filesystem API
files = client.filesystem.list_files()

# Summarizer API
summary = client.summarizer.summarize("Langer Text...")
```

## Troubleshooting

### Gateway antwortet nicht?
```bash
docker-compose logs -f api-gateway
docker-compose restart api-gateway
```

### Service 502 Error?
```bash
curl http://localhost:8000  # Terminal
curl http://localhost:8001  # Memory
# etc...
```

### Rate Limit erreicht?
Limits in `nginx.conf` erhöhen und neu bauen.

## Siehe auch

- [README.md](README.md) - Hauptdokumentation
- [SETUP.md](SETUP.md) - Ausführliche Anleitung
- [Makefile](Makefile) - Alle verfügbaren Befehle
- [client.py](client.py) - Python Client Examples
