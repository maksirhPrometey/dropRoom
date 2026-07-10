#!/usr/bin/env bash
# Usage:
#   bash deploy/docker/deploy.sh          # HTTP (docker-compose.yml)
#   bash deploy/docker/deploy.sh prod     # HTTPS (docker-compose.prod.yml)
set -euo pipefail

MODE="${1:-}"
if [ "$MODE" = "prod" ]; then
    COMPOSE_FILE="docker-compose.prod.yml"
else
    COMPOSE_FILE="docker-compose.yml"
fi

echo "==> Deploy mode: ${MODE:-http} | compose: $COMPOSE_FILE"

echo "==> Stopping host nginx/gunicorn (free ports 80/443)..."
systemctl stop nginx 2>/dev/null && systemctl disable nginx 2>/dev/null || true
fuser -k 80/tcp 2>/dev/null || true
fuser -k 443/tcp 2>/dev/null || true

echo "==> Building and starting containers..."
docker compose -f "$COMPOSE_FILE" up -d --build --remove-orphans --force-recreate nginx web

echo "==> Waiting for web service..."
sleep 8

HEALTHY=0
for i in $(seq 1 15); do
    if docker compose -f "$COMPOSE_FILE" exec -T web python -c \
        "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz/', timeout=5)" \
        > /dev/null 2>&1; then
        echo "==> Healthcheck OK"
        HEALTHY=1
        break
    fi
    echo "    Waiting... ($i/15)"
    sleep 4
done

if [ "$HEALTHY" -eq 0 ]; then
    echo "ERROR: Healthcheck failed. Logs:"
    docker compose -f "$COMPOSE_FILE" logs --tail=40 web
    exit 1
fi

echo "==> Pruning old images..."
docker image prune -f

echo "==> Running containers:"
docker compose -f "$COMPOSE_FILE" ps
