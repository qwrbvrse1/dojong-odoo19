#!/usr/bin/env bash
# Gate: Development VM instructor standby/session selection and roster tap safety.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/devvm-kiosk-lib.sh"
devvm_cd_root

devvm_require_env
[ -n "${DEMO_INSTRUCTOR_PIN:-}" ] || devvm_fail "devvm kiosk gate: DEMO_INSTRUCTOR_PIN is required"
EXPECTED_BRANCH="$(devvm_expected_branch)"
[ -n "$EXPECTED_BRANCH" ] || devvm_fail "devvm kiosk gate: could not determine expected branch; set DEMO_KIOSK_EXPECTED_BRANCH"

TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

devvm_fetch_url "$(devvm_kiosk_url)" > "$TMPDIR/shell.html"
devvm_fetch_served_app "$TMPDIR/shell.html" "$TMPDIR/kiosk_app.js"
devvm_fetch_path "/dojo_kiosk/static/src/js/kiosk_instructor.js" > "$TMPDIR/kiosk_instructor.js"
devvm_fetch_path "/dojo_kiosk/static/src/kiosk.css" > "$TMPDIR/kiosk.css"

DEVVM_APP_JS_FILE="$TMPDIR/kiosk_app.js" \
DEVVM_INSTRUCTOR_JS_FILE="$TMPDIR/kiosk_instructor.js" \
DEVVM_CSS_FILE="$TMPDIR/kiosk.css" \
DEVVM_BASE_URL="$(devvm_base_url)" \
DEVVM_TOKEN="$DEMO_KIOSK_TOKEN" \
DEVVM_PIN="$DEMO_INSTRUCTOR_PIN" \
DEVVM_EXPECTED_BRANCH="$EXPECTED_BRANCH" \
DEVVM_EXPECTED_INCREMENT="${DEMO_KIOSK_EXPECTED_INCREMENT:-INC-03}" \
DEVVM_STANDBY_DATE="${DEMO_KIOSK_STANDBY_DATE:-2099-01-01}" \
DEVVM_TARGET_SESSION_ID="${DEMO_KIOSK_SESSION_ID:-}" \
DEVVM_TARGET_MEMBER_ID="${DEMO_KIOSK_MEMBER_ID:-}" \
DEVVM_TIMEOUT="${DEMO_KIOSK_HTTP_TIMEOUT:-15}" \
python3 - <<'PY'
import json
import os
import sys
from urllib import error as urlerror
from urllib import request as urlrequest


def _excepthook(exc_type, exc, _tb):
    print("%s: %s" % (exc_type.__name__, exc), file=sys.stderr)


sys.excepthook = _excepthook

base_url = os.environ["DEVVM_BASE_URL"].rstrip("/")
token = os.environ["DEVVM_TOKEN"]
pin = os.environ["DEVVM_PIN"]
timeout = int(os.environ.get("DEVVM_TIMEOUT") or "15")


def rpc(path, params=None):
    merged = {"token": token}
    if params:
        merged.update(params)
    body = json.dumps({"jsonrpc": "2.0", "method": "call", "params": merged}).encode("utf-8")
    req = urlrequest.Request(
        base_url + path,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlrequest.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urlerror.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:240]
        raise AssertionError("HTTP %s from %s: %s" % (exc.code, path, detail))
    if payload.get("error"):
        raise AssertionError("JSON-RPC error from %s: %s" % (path, payload["error"]))
    return payload.get("result")


def sessions_and_context(payload):
    assert isinstance(payload, dict), "sessions payload must include session_context"
    sessions = payload.get("sessions") or []
    context = payload.get("session_context") or {}
    assert isinstance(sessions, list), "sessions payload sessions must be a list"
    assert isinstance(context, dict), "sessions payload session_context must be an object"
    return sessions, context


def roster_entry(session_id, member_id):
    roster = rpc("/kiosk/roster", {"session_id": session_id}) or []
    return next((entry for entry in roster if int(entry.get("member_id") or 0) == member_id), None)


with open(os.environ["DEVVM_APP_JS_FILE"], encoding="utf-8") as fh:
    app_js = fh.read()
with open(os.environ["DEVVM_INSTRUCTOR_JS_FILE"], encoding="utf-8") as fh:
    instructor_js = fh.read()
with open(os.environ["DEVVM_CSS_FILE"], encoding="utf-8") as fh:
    kiosk_css = fh.read()

expected_branch = os.environ["DEVVM_EXPECTED_BRANCH"]
expected_increment = os.environ["DEVVM_EXPECTED_INCREMENT"]
assert f'KIOSK_RELEASE_BRANCH = "{expected_branch}"' in app_js, (
    "served app asset does not match expected release branch %s" % expected_branch
)
assert f'KIOSK_RELEASE_INCREMENT = "{expected_increment}"' in app_js, (
    "served app asset does not expose expected increment %s" % expected_increment
)

for marker in (
    "class InstructorThreePanelLayout",
    "k-session-card--standby",
    'ctx.mode === "standby"',
    "isToggleableAttendance()",
    "attendanceToggleStatus()",
    "state.busy",
    "k-roster-tile--busy",
    "await handler(memberId, nextStatus)",
    'validStatuses.has(status)',
):
    assert marker in app_js, "instructor safety marker missing from served app asset: %s" % marker

selected_start = app_js.index("    selectedSession()")
selected_end = app_js.index("    selectedRoster()", selected_start)
selected_body = app_js[selected_start:selected_end]
assert "sessions[0]" not in selected_body, "selectedSession still falls back to sessions[0]"
assert 'ctx.mode === "standby"' in selected_body, "selectedSession does not treat standby as explicit no-selection"

for marker in (
    "KioskInstructorLayout",
    "/kiosk/roster",
):
    assert marker in instructor_js, "instructor contract asset marker missing: %s" % marker

for marker in (
    ".k-instructor-left .k-session-card--standby",
    ".k-roster-tile--busy",
):
    assert marker in kiosk_css, "instructor safety CSS marker missing: %s" % marker

current_sessions, current_context = sessions_and_context(rpc("/kiosk/sessions", {}))
assert current_context.get("mode") in {"active", "upcoming", "upcoming_soon", "standby"}, (
    "unexpected current session context: %s" % current_context
)
if current_context.get("mode") == "standby":
    assert not current_context.get("selected_session_id"), (
        "standby context must not select a session: %s" % current_context
    )
else:
    assert current_context.get("selected_session_id"), (
        "active/upcoming context must expose selected_session_id: %s" % current_context
    )

standby_date = os.environ["DEVVM_STANDBY_DATE"]
standby_sessions, standby_context = sessions_and_context(rpc("/kiosk/sessions", {"date": standby_date}))
assert standby_context.get("mode") == "standby", (
    "standby date %s did not return standby context: %s" % (standby_date, standby_context)
)
assert not standby_context.get("selected_session_id"), (
    "standby date %s selected a session: %s" % (standby_date, standby_context)
)
if standby_sessions:
    assert all(session.get("id") != standby_context.get("selected_session_id") for session in standby_sessions), (
        "standby sessions contradicted selected_session_id: %s" % standby_context
    )

auth = rpc("/kiosk/auth/pin", {"pin": pin}) or {}
assert auth.get("success") is True and auth.get("instructor_key"), (
    "instructor PIN authentication failed: %s" % auth
)
instructor_key = auth["instructor_key"]

target_session_id = os.environ.get("DEVVM_TARGET_SESSION_ID") or ""
target_member_id = os.environ.get("DEVVM_TARGET_MEMBER_ID") or ""
candidate_ids = []
if target_session_id:
    candidate_ids.append(int(target_session_id))
selected_id = current_context.get("selected_session_id")
if selected_id:
    candidate_ids.append(int(selected_id))
candidate_ids.extend(int(session["id"]) for session in current_sessions if session.get("id"))
candidate_ids = list(dict.fromkeys(candidate_ids))
assert candidate_ids, "no Development VM sessions available for roster safety validation"

selected = None
selection_errors = []
for session_id in candidate_ids:
    roster = rpc("/kiosk/roster", {"session_id": session_id}) or []
    candidates = []
    for entry in roster:
        if entry.get("is_trial") or not entry.get("member_id"):
            continue
        if target_member_id and str(entry.get("member_id")) != target_member_id:
            continue
        state = entry.get("attendance_state") or "pending"
        if state in {"pending", "present", "late"}:
            candidates.append(entry)
    if candidates:
        selected = (session_id, candidates[0])
        break
    selection_errors.append("session %s: no non-trial pending/present/late roster entry" % session_id)

assert selected, "could not select roster member for attendance toggle proof: %s" % "; ".join(selection_errors)
session_id, entry = selected
member_id = int(entry["member_id"])
original_state = entry.get("attendance_state") or "pending"


def mark_and_assert(status):
    result = rpc(
        "/kiosk/instructor/attendance",
        {
            "session_id": session_id,
            "member_id": member_id,
            "status": status,
            "instructor_key": instructor_key,
        },
    ) or {}
    assert result.get("success") is True, "attendance %s failed: %s" % (status, result)
    assert result.get("attendance_state") == status, (
        "attendance response did not echo %s: %s" % (status, result)
    )
    refreshed = roster_entry(session_id, member_id)
    assert refreshed, "roster entry disappeared after marking %s" % status
    assert refreshed.get("attendance_state") == status, (
        "roster state after %s was %s" % (status, refreshed.get("attendance_state"))
    )
    assert refreshed.get("attendance_label"), "roster entry missing attendance_label after %s" % status
    return refreshed


try:
    for status in ("present", "late", "pending"):
        mark_and_assert(status)
finally:
    if original_state in {"pending", "present", "late", "absent", "excused"}:
        rpc(
            "/kiosk/instructor/attendance",
            {
                "session_id": session_id,
                "member_id": member_id,
                "status": original_state,
                "instructor_key": instructor_key,
            },
        )

print(
    "ver-devvm-kiosk-instructor-safety: PASS "
    "(standby_date=%s roster_session=%s member=%s restored=%s)"
    % (standby_date, session_id, member_id, original_state)
)
PY
