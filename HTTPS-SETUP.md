# API Gateway HTTPS Setup

## Automatische Let's Encrypt Integration

Das API Gateway ist nun vollständig für HTTPS mit automatischer Let's Encrypt Zertifikat-Verwaltung vorbereitet.

## Schnellstart

### 1. Initiales Zertifikat generieren

```bash
cd /home/ki-projekt/api-gateway
chmod +x certbot-setup.sh
./certbot-setup.sh deine-domain.de admin@deine-domain.de
```

Diese Aktion:
- Startet das Gateway
- Führt Certbot aus, um ein Let's Encrypt Zertifikat zu besorgen
- Speichert das Zertifikat im Verzeichnis `api-gateway/ssl/`
- Startet das Gateway neu, um das neue Zertifikat zu laden

### 2. Automatische Zertifikat-Erneuerung (Optional)

Um Zertifikate automatisch 30 Tage vor dem Ablauf zu erneuern, füge eine Cron-Job hinzu:

```bash
# Öffne crontab
crontab -e

# Füge diese Zeile hinzu (läuft täglich um 3 Uhr morgens)
0 3 * * * cd /home/ki-projekt && docker compose exec -T api-gateway nginx -s reload > /dev/null 2>&1

# Oder nutze das Renewal-Skript direkt
0 3 * * 0 cd /home/ki-projekt/api-gateway && ./certbot-renew.sh deine-domain.de > /var/log/certbot-renew.log 2>&1
```

## Verzeichnisstruktur

```
api-gateway/
├── ssl/                      # Let's Encrypt Zertifikate (Docker Volume)
│   ├── live/
│   │   └── deine-domain.de/
│   │       ├── fullchain.pem (→ nginx)
│   │       └── privkey.pem   (→ nginx)
│   └── archive/              # Historische Versionen
├── certbot/                  # ACME Challenge Verzeichnis
├── nginx.conf                # Nginx Konfiguration mit HTTPS
├── docker-entrypoint.sh      # Startskript (Cert-Fallback + Nginx)
├── certbot-setup.sh          # Initiale Zertifikat-Generierung
├── certbot-renew.sh          # Manuelle Zertifikat-Erneuerung
└── Dockerfile                # Docker Image mit SSL-Support
```

## URL-Schema

| Schema | Port | Verhalten |
|--------|------|-----------|
| `http://deine-domain.de` | 80 | ➡️ `https://deine-domain.de` |
| `https://deine-domain.de` | 443 | ✅ Gateway-APIs |
| `http://localhost:8080` | 8080 | ✅ Fallback (lokal) |

## API Endpoints (HTTPS)

```bash
# Health Check
curl https://deine-domain.de/health

# Gateway Info
curl https://deine-domain.de/api-info

# Terminal API
curl https://deine-domain.de/api/terminals

# Memory API
curl https://deine-domain.de/api/memory/

# Vector Memory API
curl https://deine-domain.de/api/vector/

# Filesystem API
curl https://deine-domain.de/api/filesystem/

# Summarizer API
curl https://deine-domain.de/api/summarizer/
```

## Zertifikat-Status prüfen

```bash
# Zertifikat-Ablauf-Datum
docker run --rm -v /home/ki-projekt/api-gateway/ssl:/etc/letsencrypt certbot/certbot \
  certificates --config-dir /etc/letsencrypt

# Oder direkt mit openssl
openssl x509 -in /home/ki-projekt/api-gateway/ssl/live/deine-domain.de/fullchain.pem -noout -dates
```

## Manuelle Zertifikat-Erneuerung

```bash
cd /home/ki-projekt/api-gateway
./certbot-renew.sh deine-domain.de
```

## Fehlerbehebung

### Zertifikat wird nicht gefunden

```bash
# Stelle sicher, dass die ssl/ Ordner korrekt gemountet sind
docker inspect api-gateway | grep -A 5 '"Mounts"'

# Prüfe die Nginx-Logs
docker compose logs api-gateway --tail 50
```

### Certbot-Fehler: "Unable to find a virtual host matching server_name"

Dies ist normal — das Zertifikat wird trotzdem generiert. Der Fehler ist nur, wenn die Domain-Validierung fehlschlägt.

### Port 80 oder 443 ist belegt

```bash
# Prüfe, was auf diesen Ports läuft
sudo lsof -i :80
sudo lsof -i :443

# Stoppe Konflikte, z.B. Apache, andere Nginx Instanzen, etc.
```

## Fortgeschrittene Konfiguration

### Mehrere Domains

Passe `certbot-setup.sh` oder `docker-entrypoint.sh` an, um mehrere Domains zu unterstützen:

```bash
# In certbot-setup.sh
docker run --rm ... certbot/certbot certonly \
  -d deine-domain.de \
  -d www.deine-domain.de \
  -d api.deine-domain.de \
  ...
```

### Wildcard-Domain

```bash
docker run --rm ... certbot/certbot certonly \
  --dns-cloudflare \  # oder ein anderer DNS Provider
  -d deine-domain.de \
  -d '*.deine-domain.de'
```

### DNS-01 Challenge (für interne Netzwerke)

Wenn Port 80/443 nicht erreichbar sind, nutze DNS-01:

```bash
docker run --rm ... certbot/certbot certonly \
  --dns-digitalocean \  # oder dein DNS Provider
  --dns-digitalocean-credentials /path/to/credentials \
  -d deine-domain.de
```

## Sicherheit

### HSTS aktiviert

Das Gateway sendet automatisch den `Strict-Transport-Security` Header. Dies bedeutet:
- Browser erinnern sich, dass deine Domain nur per HTTPS erreichbar ist
- 1 Jahr lang (31536000 Sekunden)

### SSL Protokolle

Unterstützte Versionen: **TLSv1.2** und **TLSv1.3** (moderne Standards)

### Cipher-Suites

Nginx wählt die stärksten Cipher automatisch.

## Support

Bei Fragen oder Problemen:

1. Prüfe die Nginx-Logs: `docker compose logs api-gateway`
2. Prüfe die Certbot-Logs: `docker inspect api-gateway` → SSL-Volumes
3. Teste manuell: `openssl s_client -connect deine-domain.de:443`

