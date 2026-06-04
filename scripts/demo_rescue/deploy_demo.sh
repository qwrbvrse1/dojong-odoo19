#!/usr/bin/env bash
# One-shot demo deploy for the VM: pulled code -> running, seeded, VERIFIED demo.
# Run from anywhere inside the repo after `git pull`. Rerun safely any time;
# rerun right before the demo to re-center seeded session times to "now".
#
# Usage: ./scripts/demo_rescue/deploy_demo.sh [--build]
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
cd "$ROOT"
export RESCUE_BASE_URL="${RESCUE_BASE_URL:-http://localhost:8070}"
export RESCUE_DB="${RESCUE_DB:-odoo19}"
MODULES="dojo_core,dojo_credits,dojo_subscriptions,dojo_onboarding,dojo_sign,dojo_crm,dojo_kiosk"
FAIL=0
step() { echo; echo "════ $* ════"; }

step "1/6 Stack up"
[ "${1:-}" = "--build" ] && docker compose build
docker compose up -d db web
for _ in $(seq 1 60); do
  curl -fsS -o /dev/null "$RESCUE_BASE_URL/web/login" && break; sleep 3
done
curl -fsS -o /dev/null "$RESCUE_BASE_URL/web/login" || { echo "FATAL: web never came up at $RESCUE_BASE_URL"; docker compose logs --tail=80 web; exit 1; }

step "2/6 pg_trgm + module upgrade ($MODULES)"
docker compose exec -T db psql -U odoo -d "$RESCUE_DB" -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;" >/dev/null
docker compose stop web >/dev/null
docker compose run --rm -T --entrypoint /opt/odoo/odoo-bin web \
  -c /etc/odoo/odoo.conf -d "$RESCUE_DB" --workers=0 --max-cron-threads=0 --no-http \
  -u "$MODULES" --stop-after-init --log-level=warn || { echo "FATAL: module upgrade failed"; exit 1; }
docker compose up -d web >/dev/null
for _ in $(seq 1 40); do curl -fsS -o /dev/null "$RESCUE_BASE_URL/web/login" && break; sleep 3; done

step "3/6 Seed demo accounts (idempotent)"
bash "$HERE/seed_accounts.sh" || { echo "FATAL: account seed failed"; exit 1; }

step "4/6 Seed demo data + re-center session times to NOW (idempotent)"
bash "$HERE/seed_demo_data.sh" || { echo "FATAL: demo data seed failed"; exit 1; }

step "5/6 Verify (gates)"
bash "$HERE/verify/s1.sh" || { echo "GATE s1 (logins) FAILED"; FAIL=1; }
if node -e "import('playwright')" >/dev/null 2>&1 || node -e "require.resolve('playwright')" >/dev/null 2>&1; then
  bash "$HERE/verify/s2.sh" || { echo "GATE s2 (browser UI) FAILED"; FAIL=1; }
else
  echo "WARN: playwright not installed here — skipping browser gate (npm i playwright && npx playwright install chromium)"
fi
bash "$HERE/verify/s3.sh" || { echo "GATE s3 (demo data) FAILED"; FAIL=1; }
[ -f "verify/smoke/run.sh" ] && { bash verify/smoke/run.sh || { echo "GATE s4 (demo flow suite) FAILED"; FAIL=1; }; }

step "6/6 Demo sheet"
KTOKEN=$(docker compose exec -T db psql -U odoo -d "$RESCUE_DB" -tA \
  -c "SELECT kiosk_token FROM dojo_kiosk_config WHERE active LIMIT 1" | tr -d '[:space:]')
cat <<EOF
  Web:        $RESCUE_BASE_URL/web/login
  Kiosk:      $RESCUE_BASE_URL/kiosk/${KTOKEN:-<NO ACTIVE KIOSK CONFIG>}   (instructor PIN: 123456)
  Admin:      admin@demo.com / admin123
  Instructor: instructor1@demo.com / dojo@2026
  Students:   demo1@demo.com, demo2@demo.com / dojo@2026
  Parent:     DemoParent@demo.com / dojo@2026

  Re-center class times right before the demo:
    bash scripts/demo_rescue/seed_demo_data.sh
EOF

if [ "$FAIL" -ne 0 ]; then echo "RESULT: DEPLOYED WITH FAILED GATES — read the FAIL lines above"; exit 1; fi
echo "RESULT: DEPLOYED AND VERIFIED"
