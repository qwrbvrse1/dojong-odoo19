#!/usr/bin/env bash
# gate: call /kiosk/api/member_profile, assert onboarding keys present.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

TOKEN=$(docker compose exec -T db psql -U odoo -d odoo19 -tAc "SELECT kiosk_token FROM dojo_kiosk_config LIMIT 1;" | xargs)
MID=$(docker compose exec -T db psql -U odoo -d odoo19 -tAc "SELECT id FROM dojo_member LIMIT 1;" | xargs)

result=$(curl -sf -X POST http://127.0.0.1:8070/kiosk/member/profile \
  -H "Content-Type: application/json" \
  -d "{\"jsonrpc\":\"2.0\",\"method\":\"call\",\"params\":{\"token\":\"${TOKEN}\",\"member_id\":${MID}}}")

python3 <<EOF
import json
d = json.loads('''$result''')
r = d.get('result', {})
wf = r.get('workflow_status', {})
ob = wf.get('onboarding', {})
assert 'progress_pct' in ob, 'missing progress_pct in onboarding payload'
assert 'available' in ob, 'missing available in onboarding payload'
print('onboarding payload OK')
EOF
