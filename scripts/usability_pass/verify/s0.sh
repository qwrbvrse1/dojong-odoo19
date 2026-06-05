#!/usr/bin/env bash
# Stage 0 gate — baseline boot, clean upgrade, demo accounts intact (USABILITY_PASS.md S0).
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; source "$HERE/common.sh"

compose up -d db >/dev/null 2>&1; sleep 5

if psql_admin "SELECT 1 FROM pg_database WHERE datname='$DB'" | grep -q 1; then
  echo "PASS: database $DB exists"
else
  echo "FAIL: database $DB does not exist"
  GATE_FAILED=1; finish
fi

psql_db "CREATE EXTENSION IF NOT EXISTS pg_trgm;" >/dev/null 2>&1
echo "INFO: pg_trgm ensured"

echo "INFO: running module upgrade across all modules this pass touches"
odoo_bin -d "$DB" --workers=0 --max-cron-threads=0 --no-http \
  -u dojo_base,dojo_core,dojo_classes,dojo_attendance,dojo_kiosk,dojo_onboarding,dojo_members_portal,dojo_subscriptions,dojo_sign,dojo_credits,dojo_crm \
  --stop-after-init --log-level=warn >/tmp/upass_upgrade.log 2>&1
UPG_RC=$?
ERRS=$(grep -cE "ERROR|CRITICAL|Traceback" /tmp/upass_upgrade.log || true)
if [ "$UPG_RC" -eq 0 ] && [ "${ERRS:-0}" -eq 0 ]; then
  echo "PASS: upgrade clean (rc=0, no ERROR/CRITICAL/Traceback)"
else
  echo "FAIL: upgrade rc=$UPG_RC, error lines=$ERRS — first errors:"
  grep -E "ERROR|CRITICAL|Traceback" -m 5 -A 3 /tmp/upass_upgrade.log
  GATE_FAILED=1
fi

stuck=$(psql_db "SELECT count(*) FROM ir_module_module WHERE state NOT IN ('installed','uninstalled','uninstallable')" | tr -d '[:space:]')
if [ "$stuck" = "0" ]; then echo "PASS: no stuck modules"; else
  echo "FAIL: $stuck stuck modules:"
  psql_db "SELECT name||' -> '||state FROM ir_module_module WHERE state NOT IN ('installed','uninstalled','uninstallable')"
  GATE_FAILED=1
fi

assert "web responds 200 on /web/login" stack_up 240

assert "admin@demo.com logs in"        authenticate "admin@demo.com" "admin123"
assert "instructor1@demo.com logs in"  authenticate "instructor1@demo.com" "dojo@2026"
assert "demo1@demo.com logs in"        authenticate "demo1@demo.com" "dojo@2026"
assert "demo2@demo.com logs in"        authenticate "demo2@demo.com" "dojo@2026"
assert "DemoParent@demo.com logs in"   authenticate "DemoParent@demo.com" "dojo@2026"
finish
