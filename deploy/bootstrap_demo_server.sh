#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

DB_NAME="${ODOO_DB_NAME:-odoo19}"

echo "1. Build images"
./deploy/build_images.sh

echo "2. Start base services"
./deploy/server_up.sh

echo "3. Restore database and filestore"
./deploy/restore_demo_data.sh

echo "4. Restore Dograh data"
./deploy/restore_dograh_data.sh

echo "5. Apply demo config"
./deploy/apply_demo_config.sh

echo "6. Upgrade PortalOps demo module"
docker compose exec -T web /bin/bash -lc "python3 /opt/odoo/odoo-bin -c /etc/odoo/odoo.conf -d ${DB_NAME} -u portalops_demo --stop-after-init --no-http"

echo "7. Restart web after module upgrade"
docker compose restart web

echo "8. Smoke checks"
echo "Odoo page:"
curl -I "http://127.0.0.1:8070/p/atl-midtown" || true
echo
echo "Dograh API:"
curl "http://127.0.0.1:8000/api/v1/health" || true
echo
echo "Bootstrap complete."
