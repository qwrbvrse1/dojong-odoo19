#!/usr/bin/env bash
# VER-05 gate: call /kiosk/api/sessions, assert every session has a valid time_state.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

TOKEN=$(docker compose exec -T db psql -U odoo -d odoo19 -tAc "SELECT token FROM dojo_kiosk_config LIMIT 1;" | xargs)

result=$(curl -sf -X POST http://127.0.0.1:8070/kiosk/api/sessions \
  -H "Content-Type: application/json" \
  -d "{\"jsonrpc\":\"2.0\",\"method\":\"call\",\"params\":{\"token\":\"${TOKEN}\"}}")

echo "$result" | python3 - <<'EOF'
import sys, json
d = json.load(sys.stdin)
sessions = d.get('result', {}).get('sessions', [])
valid = {'active', 'upcoming_soon', 'upcoming', 'done'}
for s in sessions:
    ts = s.get('time_state')
    assert ts in valid, 'bad time_state: %s' % ts
    print(ts)
print('time_state OK')
EOF
