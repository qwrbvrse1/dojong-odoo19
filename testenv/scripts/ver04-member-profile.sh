#!/usr/bin/env bash
# VER-04 gate: call /kiosk/api/member_profile, assert onboarding keys present.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

TOKEN=$(docker compose exec -T db psql -U odoo -d odoo19 -tAc "SELECT token FROM dojo_kiosk_config LIMIT 1;" | xargs)
MID=$(docker compose exec -T db psql -U odoo -d odoo19 -tAc "SELECT id FROM dojo_member LIMIT 1;" | xargs)

result=$(curl -sf -X POST http://127.0.0.1:8070/kiosk/api/member_profile \
  -H "Content-Type: application/json" \
  -d "{\"jsonrpc\":\"2.0\",\"method\":\"call\",\"params\":{\"token\":\"${TOKEN}\",\"member_id\":${MID}}}")

echo "$result" | python3 - <<'EOF'
import sys, json
d = json.load(sys.stdin)
r = d.get('result', {})
wf = r.get('workflow_status', {})
ob = wf.get('onboarding', {})
assert 'progress_pct' in ob, 'missing progress_pct in onboarding payload'
assert 'available' in ob, 'missing available in onboarding payload'
print('onboarding payload OK')
EOF
