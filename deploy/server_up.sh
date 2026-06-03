#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

cp -n config/odoo.conf.example config/odoo.conf || true

docker compose up -d db
docker compose up -d web n8n dograh-postgres dograh-redis dograh-minio dograh-api dograh-ui

echo "Services started."
echo "Odoo:    http://127.0.0.1:8070"
echo "Dograh:  http://127.0.0.1:3010"
echo "API:     http://127.0.0.1:8000/api/v1/health"
