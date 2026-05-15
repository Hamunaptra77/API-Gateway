# API Gateway Makefile

.PHONY: help build up down logs status test clean

DOCKER_COMPOSE := docker-compose
GATEWAY_DIR := $(shell pwd)

help:
	@echo "API Gateway - Verfügbare Befehle"
	@echo ""
	@echo "  make build       - Image bauen"
	@echo "  make up          - Services starten"
	@echo "  make down        - Services stoppen"
	@echo "  make restart     - Services neu starten"
	@echo "  make logs        - Live Logs anschauen"
	@echo "  make status      - Service Status überprüfen"
	@echo "  make test        - Gateway testen"
	@echo "  make health      - Health Check durchführen"
	@echo "  make monitor     - Status Monitor starten"
	@echo "  make shell       - In Container gehen"
	@echo "  make config-test - Nginx Config testen"
	@echo ""
	@echo "HTTPS / Let's Encrypt:"
	@echo "  make certbot-setup    - Let's Encrypt Zertifikat generieren"
	@echo "  make certbot-renew    - Zertifikat erneuern"
	@echo "  make certbot-status   - Zertifikat Status prüfen"
	@echo ""
	@echo "  make clean       - Container und Images löschen"
	@echo ""

build:
	@echo "🔨 Baue API Gateway Image..."
	@cd .. && $(DOCKER_COMPOSE) build api-gateway
	@echo "✓ Image gebaut"

up:
	@echo "🚀 Starte Services..."
	@cd .. && $(DOCKER_COMPOSE) up -d
	@echo "✓ Services gestartet"
	@echo "Gateway läuft auf http://localhost:8080"

down:
	@echo "🛑 Stoppe Services..."
	@cd .. && $(DOCKER_COMPOSE) down
	@echo "✓ Services gestoppt"

restart:
	@echo "🔄 Starte Services neu..."
	@cd .. && $(DOCKER_COMPOSE) restart api-gateway
	@echo "✓ Gateway neugestartet"

logs:
	@cd .. && $(DOCKER_COMPOSE) logs -f api-gateway

status:
	@cd .. && $(DOCKER_COMPOSE) ps

test:
	@echo "🧪 Teste Gateway..."
	@echo ""
	@echo "1. Health Check:"
	@curl -s http://localhost:8080/health && echo "" || echo "FAIL"
	@echo ""
	@echo "2. Gateway Info:"
	@curl -s http://localhost:8080/api-info && echo "" || echo "FAIL"
	@echo ""
	@echo "3. Endpoints:"
	@curl -s http://localhost:8080/api/terminal/ > /dev/null && echo "  ✓ Terminal API" || echo "  ✗ Terminal API"
	@curl -s http://localhost:8080/api/memory/ > /dev/null && echo "  ✓ Memory API" || echo "  ✗ Memory API"
	@curl -s http://localhost:8080/api/vector/ > /dev/null && echo "  ✓ Vector API" || echo "  ✗ Vector API"
	@curl -s http://localhost:8080/api/filesystem/ > /dev/null && echo "  ✓ Filesystem API" || echo "  ✗ Filesystem API"
	@curl -s http://localhost:8080/api/summarizer/ > /dev/null && echo "  ✓ Summarizer API" || echo "  ✗ Summarizer API"

health:
	@echo "🏥 Gateway Health Check"
	@curl -v http://localhost:8080/health

monitor:
	@echo "📊 Starte Status Monitor..."
	python3 monitor.py

shell:
	@echo "🐚 Öffne Gateway Container Shell..."
	@cd .. && docker-compose exec api-gateway bash

config-test:
	@echo "✔️ Teste Nginx Konfiguration..."
	@cd .. && docker-compose exec api-gateway nginx -t

# HTTPS / Let's Encrypt targets
certbot-setup:
	@echo "🔐 Richte Let's Encrypt Zertifikat ein..."
	@chmod +x certbot-setup.sh
	@./certbot-setup.sh

certbot-renew:
	@echo "🔄 Erneuere Let's Encrypt Zertifikat..."
	@chmod +x certbot-renew.sh
	@./certbot-renew.sh

certbot-status:
	@echo "📋 Let's Encrypt Zertifikat Status:"
	@openssl x509 -in ssl/live/deine-domain.de/fullchain.pem -noout -dates 2>/dev/null || echo "❌ Kein Zertifikat gefunden. Führe 'make certbot-setup' aus."

clean:
	@echo "🧹 Räume auf..."
	@cd .. && $(DOCKER_COMPOSE) down -v
	@echo "✓ Aufgeräumt"

.DEFAULT_GOAL := help
