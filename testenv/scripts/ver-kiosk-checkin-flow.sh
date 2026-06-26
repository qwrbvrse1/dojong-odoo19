#!/usr/bin/env bash
# Gate: live student search -> session selection -> self check-in contract.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/kiosk-live-lib.sh"
kiosk_cd_root

kiosk_require_schema
kiosk_ensure_demo_member_searchable

TOKEN=$(kiosk_token)
MEMBER_ID=$(kiosk_demo_member_id)
SESSION_ID=$(kiosk_active_session_id)

reset_demo_attendance() {
  kiosk_psql_exec "
    UPDATE dojo_member
       SET active = TRUE,
           membership_state = 'active',
           first_name = 'Demo',
           last_name = 'Member',
           search_name_normalized = 'demo member'
     WHERE id = ${MEMBER_ID};
    UPDATE dojo_class_session
       SET state = 'open',
           start_datetime = NOW() - INTERVAL '30 minutes',
           end_datetime = NOW() + INTERVAL '30 minutes',
           capacity = 20
     WHERE id = ${SESSION_ID};
    UPDATE dojo_class_enrollment
       SET status = 'registered',
           attendance_state = 'pending'
     WHERE member_id = ${MEMBER_ID}
       AND session_id = ${SESSION_ID};
    INSERT INTO dojo_class_enrollment (
      session_id, member_id, status, attendance_state,
      create_uid, write_uid, create_date, write_date
    )
    SELECT ${SESSION_ID}, ${MEMBER_ID}, 'registered', 'pending', 1, 1, NOW(), NOW()
     WHERE NOT EXISTS (
       SELECT 1
         FROM dojo_class_enrollment
        WHERE member_id = ${MEMBER_ID}
          AND session_id = ${SESSION_ID}
     );
    DELETE FROM dojo_attendance_log
     WHERE member_id = ${MEMBER_ID}
       AND session_id = ${SESSION_ID};
  "
}

reset_demo_attendance
trap reset_demo_attendance EXIT

TMPDIR=$(mktemp -d)
trap 'reset_demo_attendance; rm -rf "$TMPDIR"' EXIT

kiosk_fetch "/dojo_kiosk/static/src/kiosk_app.js" > "$TMPDIR/kiosk_app.js"
search=$(kiosk_json_rpc "/kiosk/search" "{\"token\":\"${TOKEN}\",\"query\":\"Demo\"}")
sessions_before=$(kiosk_json_rpc "/kiosk/member/enrolled_sessions" "{\"token\":\"${TOKEN}\",\"member_id\":${MEMBER_ID}}")
checkin=$(kiosk_json_rpc "/kiosk/checkin" "{\"token\":\"${TOKEN}\",\"member_id\":${MEMBER_ID},\"session_id\":${SESSION_ID}}")
sessions_after=$(kiosk_json_rpc "/kiosk/member/enrolled_sessions" "{\"token\":\"${TOKEN}\",\"member_id\":${MEMBER_ID}}")
roster=$(kiosk_json_rpc "/kiosk/roster" "{\"token\":\"${TOKEN}\",\"session_id\":${SESSION_ID}}")
log_status=$(kiosk_psql_scalar "
  SELECT status
    FROM dojo_attendance_log
   WHERE member_id = ${MEMBER_ID}
     AND session_id = ${SESSION_ID}
   ORDER BY id DESC
   LIMIT 1;
")
log_count=$(kiosk_psql_scalar "
  SELECT COUNT(*)
    FROM dojo_attendance_log
   WHERE member_id = ${MEMBER_ID}
     AND session_id = ${SESSION_ID};
")
enrollment_state=$(kiosk_psql_scalar "
  SELECT attendance_state
    FROM dojo_class_enrollment
   WHERE member_id = ${MEMBER_ID}
     AND session_id = ${SESSION_ID}
   ORDER BY id DESC
   LIMIT 1;
")

KIOSK_APP_JS_FILE="$TMPDIR/kiosk_app.js" \
KIOSK_SEARCH="$search" \
KIOSK_SESSIONS_BEFORE="$sessions_before" \
KIOSK_CHECKIN="$checkin" \
KIOSK_SESSIONS_AFTER="$sessions_after" \
KIOSK_ROSTER="$roster" \
KIOSK_MEMBER_ID="$MEMBER_ID" \
KIOSK_SESSION_ID="$SESSION_ID" \
KIOSK_LOG_STATUS="$log_status" \
KIOSK_LOG_COUNT="$log_count" \
KIOSK_ENROLLMENT_STATE="$enrollment_state" \
python3 - <<'PY'
import json
import os
import sys

def _excepthook(exc_type, exc, _tb):
    print("%s: %s" % (exc_type.__name__, exc), file=sys.stderr)
sys.excepthook = _excepthook

member_id = int(os.environ["KIOSK_MEMBER_ID"])
session_id = int(os.environ["KIOSK_SESSION_ID"])

with open(os.environ["KIOSK_APP_JS_FILE"], encoding="utf-8") as fh:
    app_js = fh.read()

for marker in (
    "CHECKIN_SUCCESS_DISMISS_MS = 4000",
    "playCheckinChime();",
    "this.state.checkinResult = {",
    "k-checkin-success-overlay",
    "k-member-tile__affordance",
    "k-checkin-session-btn__cta",
):
    assert marker in app_js, "student check-in UI marker missing from served app asset: %s" % marker

search = json.loads(os.environ["KIOSK_SEARCH"]).get("result") or []
demo = next((item for item in search if item.get("member_id") == member_id), None)
assert demo, "Demo Member not returned by live kiosk search"
for key in (
    "member_id",
    "name",
    "image_url",
    "is_trial",
    "belt_rank",
    "belt_color",
    "membership_state",
    "membership_label",
    "program_name",
    "program_color",
):
    assert key in demo, "member search card payload missing %s" % key
assert demo["membership_state"] == "active", "Demo Member should be active before check-in"
assert demo["program_name"] == "Demo Program", "search card missing active class program context"

sessions_before = json.loads(os.environ["KIOSK_SESSIONS_BEFORE"]).get("result") or []
session_before = next((s for s in sessions_before if s.get("id") == session_id), None)
assert session_before, "enrolled session list is missing the active demo session"
assert session_before.get("attendance_state") == "pending", "demo session should start pending"
assert session_before.get("time_state") == "active", "demo session should be active"
assert session_before.get("program_name") == "Demo Program", "session selection payload missing program"

checkin = json.loads(os.environ["KIOSK_CHECKIN"]).get("result") or {}
assert checkin.get("success") is True, "check-in failed: %s" % checkin
assert checkin.get("log_id"), "check-in response missing log_id"
assert checkin.get("status") in {"present", "late"}, "unexpected attendance status: %s" % checkin
assert checkin.get("session_name"), "check-in response missing session_name"
assert checkin.get("program_name") == "Demo Program", "check-in response missing program_name"
member = checkin.get("member") or {}
assert member.get("member_id") == member_id, "check-in response member mismatch"
assert member.get("name") == "Demo Member", "check-in response member name mismatch"
assert member.get("attendance_state") == checkin.get("status"), "returned profile did not reflect check-in status"

sessions_after = json.loads(os.environ["KIOSK_SESSIONS_AFTER"]).get("result") or []
session_after = next((s for s in sessions_after if s.get("id") == session_id), None)
assert session_after, "post-check-in enrolled session missing"
assert session_after.get("attendance_state") == checkin.get("status"), "enrolled sessions did not reflect check-in status"

roster = json.loads(os.environ["KIOSK_ROSTER"]).get("result") or []
entry = next((item for item in roster if item.get("member_id") == member_id), None)
assert entry, "roster does not include checked-in member"
assert entry.get("attendance_state") == checkin.get("status"), "roster did not reflect check-in status"

assert os.environ["KIOSK_LOG_COUNT"].strip() == "1", "expected exactly one attendance log"
assert os.environ["KIOSK_LOG_STATUS"].strip() == checkin.get("status"), "database log status mismatch"
assert os.environ["KIOSK_ENROLLMENT_STATE"].strip() == "present", "enrollment state was not synced to present"

print("ver-kiosk-checkin-flow: PASS")
PY
