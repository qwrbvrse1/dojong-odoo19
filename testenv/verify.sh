#!/usr/bin/env bash
# testenv/verify.sh — exit 0 = env healthy.
# Normally fast; bootstraps the Odoo schema when reset leaves an empty DB.
# Called by: harness baseline_gate, reset.sh, bootstrap.sh
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

CORE_MODULES="dojo_core,subscription_oca,dojo_subscriptions,dojo_onboarding,bi_all_digital_sign,dojo_sign,dojo_theme,dojo_kiosk,dojo_instructor_dashboard,dojo_belt_progression,dojo_members,dojo_communications"

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

# 4. Odoo schema and required kiosk modules installed
schema_ready=$(
  docker compose exec -T db psql -U odoo -d odoo19 -qtAc \
    "SELECT to_regclass('public.ir_module_module') IS NOT NULL;" 2>/dev/null | xargs || true
)
if [ "$schema_ready" != "t" ]; then
  echo "verify: Odoo schema missing; bootstrapping required modules"
  docker compose exec -T web /opt/odoo/odoo-bin \
    -c /etc/odoo/odoo.conf \
    -d odoo19 \
    --workers=0 --no-http \
    -i "$CORE_MODULES" \
    --stop-after-init \
    >/dev/null 2>&1 \
    || { echo "verify: required module bootstrap failed"; exit 1; }
  docker compose exec -T db psql -U odoo -d odoo19 -f - < testenv/seed-demo.sql >/dev/null 2>&1 \
    || { echo "verify: demo seed failed"; exit 1; }
  curl -sf --max-time 5 http://127.0.0.1:8070/web/login >/dev/null || true
fi

docker compose exec -T db psql -U odoo -d odoo19 -tAc \
  "SELECT COUNT(*) FROM ir_module_module WHERE name IN ('dojo_kiosk','dojo_theme','dojo_core','dojo_onboarding') AND state='installed';" \
  | grep -q "4" \
  || { echo "verify: required dojo kiosk modules not installed"; exit 1; }
docker compose exec -T db psql -U odoo -d odoo19 -tAc \
  "SELECT COUNT(*) FROM dojo_kiosk_config WHERE active IS TRUE AND kiosk_token IS NOT NULL;" \
  | grep -Eq '^[[:space:]]*[1-9][0-9]*[[:space:]]*$' \
  || { echo "verify: active kiosk token missing"; exit 1; }

# 5. Rescue verification harness present
for script in \
  testenv/scripts/devvm-kiosk-lib.sh \
  testenv/scripts/ver-devvm-kiosk-home.sh \
  testenv/scripts/ver-devvm-kiosk-student-flow.sh \
  testenv/scripts/ver-kiosk-home.sh \
  testenv/scripts/ver-kiosk-instructor-layout.sh \
  testenv/scripts/ver-kiosk-photo-flow.sh \
  testenv/scripts/ver-kiosk-profile-tabs.sh
do
  test -x "$script" || { echo "verify: missing or non-executable $script"; exit 1; }
done

echo "verify: healthy"
