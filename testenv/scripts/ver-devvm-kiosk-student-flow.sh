#!/usr/bin/env bash
# Gate: Development VM student search -> session selection -> check-in contract.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/devvm-kiosk-lib.sh"
devvm_cd_root

devvm_require_env
EXPECTED_BRANCH="$(devvm_expected_branch)"
[ -n "$EXPECTED_BRANCH" ] || devvm_fail "devvm kiosk gate: could not determine expected branch; set DEMO_KIOSK_EXPECTED_BRANCH"

TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

devvm_fetch_url "$(devvm_kiosk_url)" > "$TMPDIR/shell.html"
devvm_fetch_served_app "$TMPDIR/shell.html" "$TMPDIR/kiosk_app.js"

DEVVM_APP_JS_FILE="$TMPDIR/kiosk_app.js" \
DEVVM_BASE_URL="$(devvm_base_url)" \
DEVVM_TOKEN="$DEMO_KIOSK_TOKEN" \
DEVVM_EXPECTED_BRANCH="$EXPECTED_BRANCH" \
DEVVM_EXPECTED_INCREMENT="${DEMO_KIOSK_EXPECTED_INCREMENT:-INC-04}" \
DEVVM_SEARCH_QUERY="${DEMO_KIOSK_SEARCH_QUERY:-Demo}" \
DEVVM_TARGET_NAME="${DEMO_KIOSK_MEMBER_NAME:-}" \
DEVVM_TARGET_MEMBER_ID="${DEMO_KIOSK_MEMBER_ID:-}" \
DEVVM_TARGET_SESSION_ID="${DEMO_KIOSK_SESSION_ID:-}" \
DEVVM_FLOW_DATE="${DEMO_KIOSK_FLOW_DATE:-}" \
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

with open(os.environ["DEVVM_APP_JS_FILE"], encoding="utf-8") as fh:
    app_js = fh.read()

expected_branch = os.environ["DEVVM_EXPECTED_BRANCH"]
expected_increment = os.environ["DEVVM_EXPECTED_INCREMENT"]
assert f'KIOSK_RELEASE_BRANCH = "{expected_branch}"' in app_js, (
    "served app asset does not match expected release branch %s" % expected_branch
)
assert f'KIOSK_RELEASE_INCREMENT = "{expected_increment}"' in app_js, (
    "served app asset does not expose expected increment %s" % expected_increment
)
for marker in (
    "this.state.checkinModal = { member, memberKey",
    "checkinMemberKey",
    "isCurrentCheckinMember",
    "_searchSeq",
    "/kiosk/member/enrolled_sessions",
    "/kiosk/checkin",
    "/kiosk/trial/checkin",
    "this.state.checkinResult = {",
    "k-checkin-success-overlay",
    "playCheckinChime();",
    "CHECKIN_SUCCESS_DISMISS_MS = 4000",
):
    assert marker in app_js, "student flow marker missing from served app asset: %s" % marker

query = os.environ.get("DEVVM_SEARCH_QUERY") or "Demo"
target_name = os.environ.get("DEVVM_TARGET_NAME") or ""
target_member_id = os.environ.get("DEVVM_TARGET_MEMBER_ID") or ""
target_session_id = os.environ.get("DEVVM_TARGET_SESSION_ID") or ""
flow_date = os.environ.get("DEVVM_FLOW_DATE") or ""

search = rpc("/kiosk/search", {"query": query})
assert isinstance(search, list), "search result is not a list"
assert search, "Development VM search query returned no results"

private_keys = {
    "email",
    "phone",
    "household",
    "guardians",
    "workflow_status",
    "issues",
    "appointments",
    "date_of_birth",
    "plan_name",
}

def card_matches(card):
    if card.get("is_trial") or not card.get("member_id"):
        return False
    if target_member_id and str(card.get("member_id")) != target_member_id:
        return False
    if target_name and card.get("name") != target_name:
        return False
    return True

cards = [card for card in search if card_matches(card)]
assert cards, "no member search result matched the Development VM student-flow target"

selected = None
selection_errors = []
for card in cards:
    for key in (
        "member_id",
        "lead_id",
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
        assert key in card, "member search card payload missing %s" % key
    leaked = sorted(private_keys.intersection(card.keys()))
    assert not leaked, "public search card leaked private profile keys: %s" % ", ".join(leaked)

    params = {"member_id": card["member_id"]}
    if flow_date:
        params["date"] = flow_date
    sessions = rpc("/kiosk/member/enrolled_sessions", params) or []
    session_candidates = [session for session in sessions if session.get("id")]
    if target_session_id:
        session_candidates = [session for session in session_candidates if str(session.get("id")) == target_session_id]
    if not session_candidates:
        selection_errors.append("%s: no enrolled sessions" % card.get("name"))
        continue

    pending = [
        session for session in session_candidates
        if (session.get("attendance_state") or "pending") == "pending"
        and session.get("time_state") != "done"
    ]
    already_present = [
        session for session in session_candidates
        if (session.get("attendance_state") or "") in {"present", "late"}
    ]
    if pending:
        selected = (card, pending[0], sessions, "pending")
        break
    if already_present and selected is None:
        selected = (card, already_present[0], sessions, "already_present")

assert selected, "no check-in eligible member/session found; details: %s" % "; ".join(selection_errors)

card, session, sessions_before, pre_mode = selected
member_id = int(card["member_id"])
session_id = int(session["id"])

for key in ("id", "name", "template_name", "program_name", "start", "end", "instructor", "attendance_state", "time_state"):
    assert key in session, "enrolled session payload missing %s" % key
assert session.get("time_state") in {"active", "upcoming_soon", "upcoming"}, (
    "selected session is not available for student check-in: %s" % session
)

checkin = rpc("/kiosk/checkin", {"member_id": member_id, "session_id": session_id}) or {}
checkin_created = checkin.get("success") is True
already_checked_in = (
    not checkin_created
    and "already checked in" in (checkin.get("error") or "").lower()
)
assert checkin_created or already_checked_in, "check-in failed unexpectedly: %s" % checkin

sessions_after = rpc("/kiosk/member/enrolled_sessions", {"member_id": member_id}) or []
session_after = next((item for item in sessions_after if int(item.get("id") or 0) == session_id), None)
assert session_after, "post-check-in enrolled sessions missing selected session"
after_state = session_after.get("attendance_state")
assert after_state in {"present", "late"}, "post-check-in session state was not present/late: %s" % session_after

roster = rpc("/kiosk/roster", {"session_id": session_id}) or []
entry = next((item for item in roster if int(item.get("member_id") or 0) == member_id), None)
assert entry, "roster does not include the selected checked-in member"
assert entry.get("attendance_state") == after_state, "roster did not reflect enrolled-session attendance state"

if checkin_created:
    assert checkin.get("log_id"), "check-in response missing log_id"
    assert checkin.get("status") == after_state, "check-in response status did not match refreshed session"
    assert checkin.get("session_name"), "check-in response missing session_name"
    assert "program_name" in checkin, "check-in response missing program_name"
    member = checkin.get("member") or {}
    assert member.get("member_id") == member_id, "check-in response member mismatch"
    assert member.get("name") == card.get("name"), "check-in response member name mismatch"
    assert member.get("attendance_state") == after_state, "returned profile did not reflect check-in status"
else:
    assert pre_mode == "already_present" or after_state in {"present", "late"}, (
        "already-checked-in response was not backed by a present/late refreshed state"
    )

print(
    "ver-devvm-kiosk-student-flow: PASS (%s member=%s session=%s state=%s)"
    % ("created_checkin" if checkin_created else "already_checked_in", member_id, session_id, after_state)
)
PY
