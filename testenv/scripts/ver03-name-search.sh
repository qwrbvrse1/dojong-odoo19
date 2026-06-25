#!/usr/bin/env bash
# VER-03 gate: authenticate, call name_search("Smi"), assert at least one result.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

# Authenticate (cookie jar maintains session)
curl -sf -c /tmp/jar -b /tmp/jar -X POST \
  http://127.0.0.1:8070/web/session/authenticate \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"call","params":{"db":"odoo19","login":"admin@demo.com","password":"admin123"}}' \
  >/dev/null

# Call name_search
result=$(curl -sf -c /tmp/jar -b /tmp/jar -X POST \
  http://127.0.0.1:8070/web/dataset/call_kw \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"call","params":{"model":"dojo.member","method":"name_search","args":["Smi"],"kwargs":{"limit":10}}}')

echo "$result" | python3 - <<'EOF'
import sys, json
d = json.load(sys.stdin)
names = d.get('result', [])
assert isinstance(names, list) and len(names) > 0, 'No results returned'
print('name_search OK, %d results' % len(names))
EOF
