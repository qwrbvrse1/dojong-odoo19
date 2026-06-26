#!/usr/bin/env bash
# testenv/reset.sh — self-escalating reset before every shot.
# Fast path: drop + recreate odoo19 DB, reinstall core modules.
# Deep path: restart web container, force-drop DB, reinstall core modules.
# NOTE: deep path never calls docker compose down -v or docker compose up -d.
# Running those from a worktree would (a) destroy shared data volumes and
# (b) mount ./config/odoo.conf relative to the worktree (no file there →
# Docker creates a directory, breaking bootstrap). Container lifecycle is
# managed from /opt/repos; the harness only manages database state.
# Always ends verified-healthy or exits nonzero.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
TESTENV="$(dirname "$0")"

CORE_MODULES="dojo_core,subscription_oca,dojo_subscriptions,dojo_onboarding,bi_all_digital_sign,dojo_sign,dojo_theme,dojo_kiosk,dojo_instructor_dashboard,dojo_belt_progression,dojo_members,dojo_communications"

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

  # Load demo seed data
  docker compose exec -T db psql -U odoo -d odoo19 -f - < "$TESTENV/seed-demo.sql" >/dev/null 2>&1
}

deep_reset() {
  echo "reset: escalating to deep reset"
  # Restart web only — do not call down -v or up -d (see header comment)
  docker compose restart web 2>/dev/null || true
  for i in $(seq 1 30); do
    curl -sf --max-time 3 http://127.0.0.1:8070/web/login >/dev/null 2>&1 && break
    sleep 2
  done
  # Force-terminate stuck connections then drop and recreate the database
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

  # Load demo seed data
  docker compose exec -T db psql -U odoo -d odoo19 -f - < "$TESTENV/seed-demo.sql" >/dev/null 2>&1
}

if fast_reset && "$TESTENV/verify.sh"; then
  echo "reset: fast path ok"
else
  deep_reset
  "$TESTENV/verify.sh"   # bootstrap must leave it healthy or we fail loudly
fi
