#!/usr/bin/env bash
# VER-11 gate: call /kiosk/api/roster for today's session, assert onboarding_pct and open_task_count present.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

TOKEN=$(docker compose exec -T db psql -U odoo -d odoo19 -tAc "SELECT kiosk_token FROM dojo_kiosk_config LIMIT 1;" | xargs)
SID=$(docker compose exec -T db psql -U odoo -d odoo19 -tAc "SELECT id FROM dojo_class_session WHERE DATE(start_datetime) = CURRENT_DATE LIMIT 1;" | xargs)

result=$(curl -sf -X POST http://127.0.0.1:8070/kiosk/roster \
  -H "Content-Type: application/json" \
  -d "{\"jsonrpc\":\"2.0\",\"method\":\"call\",\"params\":{\"token\":\"${TOKEN}\",\"session_id\":${SID}}}")

python3 <<EOF
import json
d = json.loads('''$result''')
entries = d.get('result', [])
print('roster_entries=%d' % len(entries))
assert all('onboarding_pct' in e for e in entries), 'missing onboarding_pct'
assert all('open_task_count' in e for e in entries), 'missing open_task_count'
print('roster payload OK')
EOF
