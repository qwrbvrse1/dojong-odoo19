#!/usr/bin/env bash
# Stage 2 gate — admin & instructor UI actually load in a real browser, menus exist
# (DEMO_RESCUE.md Phase 1: "modules don't load on admin" must be dead).
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; source "$HERE/common.sh"
stack_up || { echo "FAIL: web not up"; GATE_FAILED=1; finish; }

assert "browser smoke: admin UI loads, no JS errors" \
  node "$HERE/admin_smoke.mjs" "admin@demo.com" "admin123"
assert "browser smoke: instructor UI loads, no JS errors" \
  node "$HERE/admin_smoke.mjs" "instructor1@demo.com" "dojo@2026"

# Admin must see a real menu tree (the reported failure was missing apps/menus).
COOKIES=$(mktemp)
curl -s -c "$COOKIES" --max-time 15 -X POST "$BASE/web/session/authenticate" \
  -H 'Content-Type: application/json' \
  -d "{\"jsonrpc\":\"2.0\",\"params\":{\"db\":\"$DB\",\"login\":\"admin@demo.com\",\"password\":\"admin123\"}}" >/dev/null
MENUS=$(curl -s -b "$COOKIES" --max-time 15 -X POST "$BASE/web/dataset/call_kw" \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","params":{"model":"ir.ui.menu","method":"search_read","args":[[["parent_id","=",false]],["name"]],"kwargs":{}}}')
rm -f "$COOKIES"
ROOTS=$(echo "$MENUS" | grep -o '"name"' | wc -l | tr -d ' ')
if [ "${ROOTS:-0}" -ge 6 ]; then echo "PASS: admin sees $ROOTS root menus"; else
  echo "FAIL: admin sees only ${ROOTS:-0} root menus :: $(echo "$MENUS" | head -c 400)"; GATE_FAILED=1; fi
echo "$MENUS" | grep -qi 'kiosk' \
  && echo "PASS: Kiosk root menu present" \
  || { echo "FAIL: Kiosk root menu missing"; GATE_FAILED=1; }
finish
