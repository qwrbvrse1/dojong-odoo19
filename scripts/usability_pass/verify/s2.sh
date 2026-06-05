#!/usr/bin/env bash
# Stage 2 gate — kiosk pre-PIN gating, instructor_key, token rotation, action log
# (USABILITY_PASS.md changes 3-4).
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; source "$HERE/common.sh"
stack_up || { echo "FAIL: web not up"; GATE_FAILED=1; finish; }

KTOKEN=$(psql_db "SELECT kiosk_token FROM dojo_kiosk_config WHERE active LIMIT 1" | tr -d '[:space:]')
[ -n "$KTOKEN" ] || { echo "FAIL: no active kiosk token in dojo_kiosk_config"; GATE_FAILED=1; finish; }
assert "kiosk page loads (HTTP 200)" wait_for_http "$BASE/kiosk/$KTOKEN" 30

MEMBER_ID=$(psql_db "SELECT id FROM dojo_member WHERE active ORDER BY id LIMIT 1" | tr -d '[:space:]')
[ -n "$MEMBER_ID" ] || { echo "FAIL: no active dojo_member found"; GATE_FAILED=1; finish; }

# 1. Pre-PIN profile is minimal — sensitive keys must be ABSENT.
PRE=$(kiosk_rpc "/kiosk/member/profile" "{\"token\":\"$KTOKEN\",\"member_id\":$MEMBER_ID}")
for key in date_of_birth email phone household guardians credit_balance billing_failure_count workflow_status; do
  if echo "$PRE" | grep -q "\"$key\""; then
    echo "FAIL: pre-PIN profile leaks \"$key\""; GATE_FAILED=1
  else
    echo "PASS: pre-PIN profile omits \"$key\""
  fi
done
echo "$PRE" | grep -q '"name"' \
  && echo "PASS: pre-PIN profile still returns the minimal card (name present)" \
  || { echo "FAIL: pre-PIN profile returned nothing usable :: $(echo "$PRE" | head -c 300)"; GATE_FAILED=1; }

# 2. PIN unlock returns an instructor_key.
PIN=$(kiosk_rpc "/kiosk/auth/pin" "{\"token\":\"$KTOKEN\",\"pin\":\"123456\"}")
IKEY=$(echo "$PIN" | grep -o '"instructor_key"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*:[[:space:]]*"//; s/"$//')
if [ -n "$IKEY" ]; then echo "PASS: /kiosk/auth/pin returns instructor_key"; else
  echo "FAIL: no instructor_key in PIN response :: $(echo "$PIN" | head -c 300)"; GATE_FAILED=1; finish; fi

# 3. With the key, the full profile is back.
POST=$(kiosk_rpc "/kiosk/member/profile" "{\"token\":\"$KTOKEN\",\"member_id\":$MEMBER_ID,\"instructor_key\":\"$IKEY\"}")
echo "$POST" | grep -q '"workflow_status"' \
  && echo "PASS: instructor profile includes workflow_status" \
  || { echo "FAIL: instructor profile missing workflow_status :: $(echo "$POST" | head -c 300)"; GATE_FAILED=1; }

# 4. Instructor routes reject a missing/invalid key with the mandated error string.
NOKEY=$(kiosk_rpc "/kiosk/instructor/attendance" "{\"token\":\"$KTOKEN\",\"member_id\":$MEMBER_ID,\"session_id\":1,\"status\":\"present\"}")
echo "$NOKEY" | grep -q 'instructor_auth_required' \
  && echo "PASS: instructor route without key returns instructor_auth_required" \
  || { echo "FAIL: instructor route without key did not refuse :: $(echo "$NOKEY" | head -c 300)"; GATE_FAILED=1; }

# 5. Token rotation works (shell-level; rolled back is fine if not committed — so commit).
run_shell_test "action_rotate_token() changes the kiosk token" "
cfg = env['dojo.kiosk.config'].search([('active','=',True)], limit=1)
old = cfg.kiosk_token
cfg.action_rotate_token()
print('ROTATED:', cfg.kiosk_token != old and bool(cfg.kiosk_token))
env.cr.rollback()
" "ROTATED: True"

# 6. Action log model exists and mutations write to it: checkin via service in a rolled-back txn.
run_shell_test "kiosk mutations write dojo.kiosk.action.log rows" "
Log = env['dojo.kiosk.action.log']
before = Log.search_count([])
svc = env['dojo.kiosk.service'].sudo()
m = env['dojo.member'].search([('active','=',True)], limit=1)
s = env['dojo.class.session'].search([], limit=1)
try:
    svc.mark_attendance(s.id, m.id, 'present')
except Exception as e:
    print('CALLERR:', e)
after = Log.search_count([])
print('LOGGED:', after > before)
env.cr.rollback()
" "LOGGED: True"
finish
