#!/usr/bin/env bash
# VER-05 gate: call /kiosk/api/sessions, assert every session has a valid time_state.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

# Load seed data (demo sessions for today)
# Note: dojo_kiosk must be installed first (previous gate command does this)
docker compose exec -T db psql -U odoo -d odoo19 -f - < testenv/seed-demo.sql >/dev/null 2>&1 || true

TOKEN=$(docker compose exec -T db psql -U odoo -d odoo19 -tAc "SELECT kiosk_token FROM dojo_kiosk_config LIMIT 1;" | xargs)

# Call the sessions endpoint
result=$(curl -sf -X POST http://127.0.0.1:8070/kiosk/sessions \
  -H "Content-Type: application/json" \
  -d "{\"jsonrpc\":\"2.0\",\"method\":\"call\",\"params\":{\"token\":\"${TOKEN}\"}}")

# Verify every session has a valid time_state
python3 <<EOF
import json
d = json.loads('''$result''')
sessions = d.get('result', {}).get('sessions', [])
valid = {'active', 'upcoming_soon', 'upcoming', 'done'}
assert len(sessions) > 0, 'no sessions found — seed data may have failed'
for s in sessions:
    ts = s.get('time_state')
    assert ts in valid, 'bad time_state: %s' % ts
    print('✓ %s: %s' % (s.get('name', 'unknown'), ts))
print('time_state OK — all %d sessions have valid time_state' % len(sessions))
EOF
