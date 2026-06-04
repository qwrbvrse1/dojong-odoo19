#!/usr/bin/env bash
# Stage 4 gate — full Playwright demo-flow suite (authored by Claude in stage 4) passes,
# plus script-owned kiosk API checks (DEMO_RESCUE.md Phase 4).
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; source "$HERE/common.sh"
stack_up || { echo "FAIL: web not up"; GATE_FAILED=1; finish; }

# Claude must have produced this exact entrypoint.
if [ ! -f "verify/smoke/run.sh" ]; then
  echo "FAIL: verify/smoke/run.sh does not exist (Claude must author the suite there)"; GATE_FAILED=1; finish
fi
assert "Playwright demo-flow suite (verify/smoke/run.sh) exits 0" bash verify/smoke/run.sh

# Script-owned kiosk checks (independent of the authored suite).
KTOKEN=$(psql_db "SELECT kiosk_token FROM dojo_kiosk_config WHERE active LIMIT 1" | tr -d '[:space:]')
if [ -n "$KTOKEN" ]; then
  assert "kiosk page loads (HTTP 200)" wait_for_http "$BASE/kiosk/$KTOKEN" 30
  SEARCH=$(curl -s --max-time 15 -X POST "$BASE/kiosk/search" -H 'Content-Type: application/json' \
    -d "{\"jsonrpc\":\"2.0\",\"params\":{\"query\":\"Smi\",\"token\":\"$KTOKEN\"}}")
  echo "$SEARCH" | grep -qi 'smith' \
    && echo "PASS: kiosk surname search 'Smi' returns Smiths" \
    || { echo "FAIL: kiosk search 'Smi' returned no Smith :: $(echo "$SEARCH" | head -c 300)"; GATE_FAILED=1; }
else
  echo "FAIL: could not read kiosk token from dojo_kiosk_config"; GATE_FAILED=1
fi
finish
