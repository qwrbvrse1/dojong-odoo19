#!/usr/bin/env bash
# Gate: verify surname-first ranking in name_search
# Query "Smi" should return members with last_name starting with "Smi" before
# members with "Smi" elsewhere in their name.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

# Authenticate (cookie jar maintains session)
curl -sf -c /tmp/jar -b /tmp/jar -X POST \
  http://127.0.0.1:8070/web/session/authenticate \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"call","params":{"db":"odoo19","login":"admin","password":"admin"}}' \
  >/dev/null

# Create test members for surname ranking verification
# Member 1: Jane Smith (surname match)
curl -sf -c /tmp/jar -b /tmp/jar -X POST \
  http://127.0.0.1:8070/web/dataset/call_kw \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"call","params":{"model":"dojo.member","method":"create","args":[[{"name":"Jane Smith","email":"jane.smith@test.local","membership_state":"active"}]],"kwargs":{}}}' \
  >/dev/null

# Member 2: Jordan Smith (surname match)
curl -sf -c /tmp/jar -b /tmp/jar -X POST \
  http://127.0.0.1:8070/web/dataset/call_kw \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"call","params":{"model":"dojo.member","method":"create","args":[[{"name":"Jordan Smith","email":"jordan.smith@test.local","membership_state":"active"}]],"kwargs":{}}}' \
  >/dev/null

# Member 3: Smith Jones (non-surname match - "Smith" is first name)
curl -sf -c /tmp/jar -b /tmp/jar -X POST \
  http://127.0.0.1:8070/web/dataset/call_kw \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"call","params":{"model":"dojo.member","method":"create","args":[[{"name":"Smith Jones","email":"smith.jones@test.local","membership_state":"active"}]],"kwargs":{}}}' \
  >/dev/null

# Member 4: John Smithson (partial surname match)
curl -sf -c /tmp/jar -b /tmp/jar -X POST \
  http://127.0.0.1:8070/web/dataset/call_kw \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"call","params":{"model":"dojo.member","method":"create","args":[[{"name":"John Smithson","email":"john.smithson@test.local","membership_state":"active"}]],"kwargs":{}}}' \
  >/dev/null

# Call name_search with query "Smi"
result=$(curl -sf -c /tmp/jar -b /tmp/jar -X POST \
  http://127.0.0.1:8070/web/dataset/call_kw \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"call","params":{"model":"dojo.member","method":"name_search","args":["Smi"],"kwargs":{"limit":10}}}')

# Verify surname-first ranking
python3 <<EOF
import json

result_json = '''$result'''
d = json.loads(result_json)
results = d.get('result', [])

assert isinstance(results, list) and len(results) > 0, 'No results returned'

# Extract display names in order
names = [r[1] for r in results]
print(f"name_search returned {len(names)} results in order:")
for i, name in enumerate(names, 1):
    print(f"  {i}. {name}")

# Verify surname matches come before non-surname matches
# We expect: Jane Smith, Jordan Smith (surname matches)
# BEFORE: Smith Jones, John Smithson (non-surname matches)

surname_match_names = {'Jane Smith', 'Jordan Smith'}
non_surname_match_names = {'Smith Jones', 'John Smithson'}

# Find positions
surname_positions = [i for i, name in enumerate(names) if name in surname_match_names]
non_surname_positions = [i for i, name in enumerate(names) if name in non_surname_match_names]

if surname_positions and non_surname_positions:
    max_surname_pos = max(surname_positions)
    min_non_surname_pos = min(non_surname_positions)
    assert max_surname_pos < min_non_surname_pos, \
        f"Surname ranking failed: last surname match at position {max_surname_pos}, " \
        f"but non-surname match found at position {min_non_surname_pos}"
    print("✓ Surname-first ranking verified: surname matches ranked above non-surname matches")
elif not surname_positions:
    raise AssertionError("No surname matches found in results (expected Jane Smith or Jordan Smith)")
else:
    print("✓ Surname-first ranking verified: only surname matches found, no non-surname matches")

print("✓ name_search surname-first ranking: PASS")
EOF
