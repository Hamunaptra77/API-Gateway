#!/bin/bash

# API Gateway Quick Start Script

set -e

GATEWAY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$GATEWAY_DIR")"

echo "╔════════════════════════════════════════════╗"
echo "║   API Gateway - Quick Start                ║"
echo "╚════════════════════════════════════════════╝"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ Docker ist nicht installiert!${NC}"
    exit 1
fi

echo -e "${BLUE}1. Starte alle Services...${NC}"
cd "$PROJECT_DIR"

if docker-compose up -d 2>/dev/null; then
    echo -e "${GREEN}✓ Services gestartet${NC}"
else
    echo -e "${RED}✗ Fehler beim Starten der Services${NC}"
    exit 1
fi

echo ""
echo -e "${BLUE}2. Warte auf Services zum Starten...${NC}"
sleep 5

# Check Gateway Health
echo ""
echo -e "${BLUE}3. Überprüfe Gateway-Status...${NC}"

for i in {1..30}; do
    if curl -s http://localhost:8080/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ API Gateway läuft auf Port 8080${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}✗ Gateway antwortet nicht${NC}"
        exit 1
    fi
    echo "  Warte... ($i/30)"
    sleep 1
done

# Display Info
echo ""
echo -e "${BLUE}4. Gateway-Informationen:${NC}"
echo ""

GATEWAY_INFO=$(curl -s http://localhost:8080/api-info)
echo -e "${YELLOW}$GATEWAY_INFO${NC}"
echo ""

# Test Endpoints
echo -e "${BLUE}5. Teste Endpunkte...${NC}"
echo ""

ENDPOINTS=(
    "Terminal|/api/terminal/"
    "Memory|/api/memory/"
    "Vector Memory|/api/vector/"
    "Filesystem|/api/filesystem/"
    "Summarizer|/api/summarizer/"
)

for endpoint_info in "${ENDPOINTS[@]}"; do
    IFS='|' read -r name path <<< "$endpoint_info"
    
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080$path)
    
    if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "404" ]; then
        echo -e "${GREEN}✓${NC} $name ($HTTP_CODE)"
    else
        echo -e "${YELLOW}⚠${NC} $name ($HTTP_CODE)"
    fi
done

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   API Gateway erfolgreich gestartet!      ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════╝${NC}"
echo ""

# Display helpful info
echo -e "${BLUE}Nützliche Befehle:${NC}"
echo ""
echo "  Health Check:"
echo -e "    ${YELLOW}curl http://localhost:8080/health${NC}"
echo ""
echo "  Gateway Info:"
echo -e "    ${YELLOW}curl http://localhost:8080/api-info${NC}"
echo ""
echo "  Service-Status Monitor:"
echo -e "    ${YELLOW}python3 $GATEWAY_DIR/monitor.py${NC}"
echo ""
echo "  Logs anschauen:"
echo -e "    ${YELLOW}docker-compose logs -f api-gateway${NC}"
echo ""
echo "  Alle Services stoppen:"
echo -e "    ${YELLOW}docker-compose down${NC}"
echo ""
echo -e "${BLUE}Verfügbare Endpunkte:${NC}"
echo ""
echo "  Terminal API:        http://localhost:8080/api/terminal/"
echo "  Memory API:          http://localhost:8080/api/memory/"
echo "  Vector Memory API:   http://localhost:8080/api/vector/"
echo "  Filesystem API:      http://localhost:8080/api/filesystem/"
echo "  Summarizer API:      http://localhost:8080/api/summarizer/"
echo ""
echo -e "${BLUE}Dokumentation:${NC}"
echo ""
echo "  README:    $GATEWAY_DIR/README.md"
echo "  SETUP:     $GATEWAY_DIR/SETUP.md"
echo ""
