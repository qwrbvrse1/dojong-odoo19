#!/usr/bin/env bash
# testenv/reset.sh — self-escalating reset before every shot.
# Fast path: drop + recreate odoo19 DB, reinstall core modules.
# Deep path: tear down all containers + volumes, full bootstrap.
# Always ends verified-healthy or exits nonzero.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
TESTENV="$(dirname "$0")"

CORE_MODULES="dojo_core,subscription_oca,dojo_subscriptions,dojo_onboarding,bi_all_digital_sign,dojo_sign"

fast_reset() {
  echo "reset: fast path — dropping and recreating odoo19"

  # Drop and recreate the database
  docker compose exec -T db psql -U odoo -d postgres -qtAc \
    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='odoo19' AND pid <> pg_backend_pid();" \
    >/dev/null 2>&1 || true
  docker compose exec -T db psql -U odoo -d postgres -qtAc \
    "DROP DATABASE IF EXISTS odoo19;" >/dev/null
  docker compose exec -T db psql -U odoo -d postgres -qtAc \
    "CREATE DATABASE odoo19 OWNER odoo;" >/dev/null

  # Reinstall core modules
  docker compose run --rm --entrypoint /opt/odoo/odoo-bin web \
    -c /etc/odoo/odoo.conf \
    -d odoo19 \
    --workers=0 --no-http \
    -i "${CORE_MODULES}" \
    --stop-after-init \
    >/dev/null 2>&1
}

deep_reset() {
  echo "reset: escalating to deep reset"
  docker compose down -v 2>/dev/null || true
  docker compose up -d --wait 2>/dev/null || docker compose up -d
  # Wait for db to be ready before module install
  for i in $(seq 1 30); do
    docker compose exec -T db psql -U odoo -d postgres -qtAc "SELECT 1" >/dev/null 2>&1 && break
    sleep 2
  done
  "$TESTENV/bootstrap.sh"
}

if fast_reset && "$TESTENV/verify.sh"; then
  echo "reset: fast path ok"
else
  deep_reset
  "$TESTENV/verify.sh"   # bootstrap must leave it healthy or we fail loudly
fi
