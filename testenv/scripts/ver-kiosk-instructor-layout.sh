#!/usr/bin/env bash
# Gate: live instructor kiosk layout/session/roster contract.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/kiosk-live-lib.sh"
kiosk_cd_root

kiosk_require_schema
kiosk_ensure_demo_member_searchable

TOKEN=$(kiosk_token)
SID=$(kiosk_active_session_id)

TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

kiosk_fetch "/kiosk/${TOKEN}" > "$TMPDIR/shell.html"
kiosk_fetch "/dojo_kiosk/static/src/js/kiosk_instructor.js" > "$TMPDIR/kiosk_instructor.js"
sessions=$(kiosk_json_rpc "/kiosk/sessions" "{\"token\":\"${TOKEN}\"}")
summary=$(kiosk_json_rpc "/kiosk/api/session_summary" "{\"token\":\"${TOKEN}\",\"session_id\":${SID}}")
roster=$(kiosk_json_rpc "/kiosk/roster" "{\"token\":\"${TOKEN}\",\"session_id\":${SID}}")

KIOSK_SHELL_HTML_FILE="$TMPDIR/shell.html" \
KIOSK_INSTRUCTOR_JS_FILE="$TMPDIR/kiosk_instructor.js" \
KIOSK_SESSIONS="$sessions" \
KIOSK_SUMMARY="$summary" \
KIOSK_ROSTER="$roster" \
python3 - <<'PY'
import json
import os
import sys

def _excepthook(exc_type, exc, _tb):
    print("%s: %s" % (exc_type.__name__, exc), file=sys.stderr)
sys.excepthook = _excepthook

with open(os.environ["KIOSK_SHELL_HTML_FILE"], encoding="utf-8") as fh:
    shell = fh.read()
with open(os.environ["KIOSK_INSTRUCTOR_JS_FILE"], encoding="utf-8") as fh:
    instructor_js = fh.read()
sessions_payload = json.loads(os.environ["KIOSK_SESSIONS"]).get("result") or {}
summary = json.loads(os.environ["KIOSK_SUMMARY"]).get("result") or {}
roster = json.loads(os.environ["KIOSK_ROSTER"]).get("result")

assert "kiosk_instructor.js" in shell, "live kiosk shell does not load the instructor layout script"

for marker in (
    "KioskInstructorLayout",
    "k-instructor-layout",
    "k-instructor-left",
    "k-instructor-main",
    "k-instructor-right",
    "k-roster-grid",
    "k-roster-card",
    "k-alert-section",
):
    assert marker in instructor_js, "instructor layout marker missing from served asset: %s" % marker

assert '"/kiosk/roster"' in instructor_js or "'/kiosk/roster'" in instructor_js, (
    "instructor layout must load roster data from the live /kiosk/roster endpoint"
)
assert "/kiosk/api/roster" not in instructor_js, (
    "instructor layout references /kiosk/api/roster, which is not the live roster endpoint"
)

sessions = sessions_payload.get("sessions") or []
context = sessions_payload.get("session_context") or {}
assert sessions, "sessions payload returned no sessions"
assert context.get("mode") in {"active", "upcoming_soon", "standby"}, "unexpected session context: %s" % context
assert context.get("selected_session_id"), "instructor session context did not select a session"

assert summary.get("success") is True, "session summary did not succeed: %s" % summary
for key in ("session_id", "session_name", "template_name", "start_datetime", "end_datetime", "present_count", "late_count", "absent_count"):
    assert key in summary, "session summary missing %s" % key

assert isinstance(roster, list), "roster payload is not a list"
assert roster, "active session roster is empty"
entry = roster[0]
for key in ("member_id", "name", "attendance_state", "membership_state", "workflow_status", "onboarding_pct", "open_task_count", "image_url"):
    assert key in entry, "roster tile payload missing %s" % key
workflow = entry.get("workflow_status") or {}
assert "onboarding" in workflow, "roster workflow payload missing onboarding status"
assert "tasks" in workflow, "roster workflow payload missing task status"

print("ver-kiosk-instructor-layout: PASS")
PY
