#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

ODOO_IMAGE="${ODOO_IMAGE:-odoo-saas-19-2:latest}"

echo "Building Odoo image: $ODOO_IMAGE"
docker build -t "$ODOO_IMAGE" .

echo "Pulling supporting images referenced by docker-compose.yml"
docker compose pull db n8n dograh-postgres dograh-redis dograh-minio dograh-api dograh-ui

echo "Build complete."
