#!/usr/bin/env bash
# testenv/bootstrap.sh — idempotent. Run once per VM (or after a deep reset).
# From a bare checkout: builds the Odoo image, starts Docker Compose services,
# installs core modules, and verifies the environment is healthy.
# Wraps the logic from scripts/prepare-vm.sh for harness compatibility.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
TESTENV="$(dirname "$0")"

ODOO_IMAGE="odoo-saas-19-2:latest"
CORE_MODULES="dojo_core,subscription_oca,dojo_subscriptions,dojo_onboarding,bi_all_digital_sign,dojo_sign"

# Ensure dev odoo.conf exists (gitignored; must be created per-VM)
if [ ! -f config/odoo.conf ]; then
  echo "bootstrap: config/odoo.conf not found — generating dev default"
  mkdir -p config
  cat > config/odoo.conf << 'CONF'
[options]
addons_path = /mnt/extra-addons,/opt/odoo/addons
data_dir = /var/lib/odoo

db_host = db
db_port = 5432
db_name = odoo19
db_user = odoo
db_password = odoo

http_port = 8069
workers = 0

logfile = False
log_level = info
CONF
  echo "bootstrap: config/odoo.conf created (dev defaults — do not copy to production)"
fi

echo "bootstrap: building Odoo image"
docker compose build --quiet

echo "bootstrap: starting services"
docker compose up -d

echo "bootstrap: waiting for web service to be healthy (max 120s)"
for i in $(seq 1 60); do
  curl -sf --max-time 3 http://127.0.0.1:8070/web/login >/dev/null 2>&1 && break
  sleep 2
done

# Confirm web is actually up before module install
curl -sf --max-time 5 http://127.0.0.1:8070/web/login >/dev/null \
  || { echo "bootstrap: Odoo web did not come up in time"; exit 1; }

echo "bootstrap: waiting for DB to accept connections"
for i in $(seq 1 30); do
  docker compose exec -T db psql -U odoo -d postgres -qtAc "SELECT 1" >/dev/null 2>&1 && break
  sleep 2
done

echo "bootstrap: installing core modules (${CORE_MODULES})"
docker compose run --rm --entrypoint /opt/odoo/odoo-bin web \
  -c /etc/odoo/odoo.conf \
  -d odoo19 \
  --workers=0 --no-http \
  -i "${CORE_MODULES}" \
  --stop-after-init

echo "bootstrap: verifying"
"$TESTENV/verify.sh"
echo "bootstrap: complete"
