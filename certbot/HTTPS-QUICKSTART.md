# 🔐 HTTPS Setup für deine-domain.de - Schnellstart

## ✅ Abgeschlossene Konfiguration

Das API Gateway ist nun vollständig für **HTTPS mit Let's Encrypt** vorbereitet.

### Neue Komponenten:

| Datei | Funktion |
|-------|----------|
| `certbot-setup.sh` | Generiert iniziales Let's Encrypt Zertifikat |
| `certbot-renew.sh` | Erneuert Zertifikat manuell |
| `setup-cron.sh` | Installiert automatische Erneuerung via Cron |
| `docker-entrypoint.sh` | Nutzt echte Certs oder fallback auf self-signed |
| `HTTPS-SETUP.md` | Vollständige Dokumentation |
| `docker-compose.certbot.yml` | Optional: Automatischer Renewal-Service |
| `Makefile` | einfache Befehle: `make certbot-setup`, etc. |

---

## 🚀 Schnellstart (3 Befehle)

```bash
# 1. Im API-Gateway Verzeichnis
cd /home/ki-projekt/api-gateway

# 2. Let's Encrypt Zertifikat generieren
./certbot-setup.sh

# 3. (Optional) Automatische Erneuerung via Cron
sudo chmod +x setup-cron.sh
sudo ./setup-cron.sh
```

**Das war's!** Dein Gateway ist jetzt unter `https://deine-domain.de` erreichbar.

---

## 📋 Makefile Shortcuts

```bash
# Zertifikat generieren
make certbot-setup

# Zertifikat manuell erneuern
make certbot-renew

# Zertifikat-Status prüfen
make certbot-status

# Gateway neu starten
make restart

# Logs anschauen
make logs
```

---

## 🔗 URLs nach Setup

| URL | Status |
|-----|--------|
| `https://deine-domain.de` | ✅ HTTPS (Port 443) |
| `http://deine-domain.de` | ✅ Redirect zu HTTPS |
| `http://localhost:8080` | ✅ Fallback |
| `https://deine-domain.de/api-info` | ✅ Gateway-APIs |
| `https://deine-domain.de/api/terminals` | ✅ Terminal-API |

---

## 🔄 Automatische Erneuerung

Nach `sudo ./setup-cron.sh` wird das Zertifikat automatisch erneuert:
- **Zeitpunkt**: Jeden Sonntag um 3:00 Uhr
- **Log**: `/var/log/certbot-renew.log`
- **Bedingung**: 30 Tage vor Ablauf

---

## ⚠️ Wichtig

1. **Port 80 und 443 müssen erreichbar sein** für Let's Encrypt Validierung
2. **DNS-Einträge** müssen auf deinen Server zeigen (bereits der Fall: deine-domain.de → 188.138.122.125)
3. **Firewall**: Port 80 und 443 müssen erlaubt sein
4. **E-Mail**: Certbot benötigt eine gültige E-Mail für Zertifikat-Alarme

---

## 📞 Support

Bei Problemen:

```bash
# Logs prüfen
docker compose logs api-gateway

# Zertifikat Status
docker run --rm -v /home/ki-projekt/api-gateway/ssl:/etc/letsencrypt \
  certbot/certbot certificates --config-dir /etc/letsencrypt

# Manuelle Renewal
cd /home/ki-projekt/api-gateway
./certbot-renew.sh deine-domain.de

# Detaillierte Doku
cat HTTPS-SETUP.md
```

---

## 🎉 Nächste Schritte

1. **Sofort**: Gateway neu bauen und testen
   ```bash
   docker compose build api-gateway
   docker compose up -d api-gateway
   curl https://deine-domain.de/api-info
   ```

2. **Optionale Automationen**:
   - Cron-Job installieren: `sudo ./setup-cron.sh`
   - Certbot-Renewal-Service: `docker-compose -f docker-compose.yml -f docker-compose.certbot.yml up -d`

3. **Überwachen**:
   - Zertifikat-Status: `make certbot-status`
   - Gateway-Logs: `make logs`

---

**Generiert:** 2026-05-10  
**Gateway:** `deine-domain.de` (188.138.122.125)  
**Status:** ✅ Bereit für HTTPS-Produktion

