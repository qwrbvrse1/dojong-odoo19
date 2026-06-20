#!/usr/bin/env bash
# testenv/verify.sh — exit 0 = env healthy. Must complete in < 10s.
# Called by: harness baseline_gate, reset.sh, bootstrap.sh
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

# 1. Docker services running
docker compose ps --services --filter status=running 2>/dev/null | grep -q "^web$" \
  || { echo "verify: web service not running"; exit 1; }
docker compose ps --services --filter status=running 2>/dev/null | grep -q "^db$" \
  || { echo "verify: db service not running"; exit 1; }

# 2. Odoo web responding
curl -sf --max-time 5 http://127.0.0.1:8070/web/login >/dev/null \
  || { echo "verify: Odoo web not responding on port 8070"; exit 1; }

# 3. Database accessible
docker compose exec -T db psql -U odoo -d odoo19 -qtAc "SELECT 1" >/dev/null 2>&1 \
  || { echo "verify: odoo19 database not accessible"; exit 1; }

echo "verify: healthy"
