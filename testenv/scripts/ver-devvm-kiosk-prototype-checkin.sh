#!/usr/bin/env bash
# Gate: Development VM prototype-parity direct card check-in and success state.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/devvm-kiosk-lib.sh"
devvm_cd_root

export DEMO_KIOSK_EXPECTED_INCREMENT="${DEMO_KIOSK_EXPECTED_INCREMENT:-INC-04}"
devvm_require_env
EXPECTED_BRANCH="$(devvm_expected_branch)"
[ -n "$EXPECTED_BRANCH" ] || devvm_fail "devvm kiosk gate: could not determine expected branch; set DEMO_KIOSK_EXPECTED_BRANCH"

TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

devvm_fetch_url "$(devvm_kiosk_url)" > "$TMPDIR/shell.html"
devvm_fetch_served_app "$TMPDIR/shell.html" "$TMPDIR/kiosk_app.js"

CSS_URL="$(
  DEVVM_SHELL_FILE="$TMPDIR/shell.html" DEVVM_BASE_URL="$(devvm_base_url)" python3 - <<'PY'
from urllib.parse import urljoin
import os
import re
import sys

with open(os.environ["DEVVM_SHELL_FILE"], encoding="utf-8") as fh:
    shell = fh.read()
match = re.search(r'<link[^>]+href="([^"]*dojo_kiosk/static/src/kiosk\.css[^"]*)"', shell)
if not match:
    print("devvm kiosk gate: served kiosk shell did not reference kiosk.css", file=sys.stderr)
    sys.exit(1)
print(urljoin(os.environ["DEVVM_BASE_URL"] + "/", match.group(1)))
PY
)"
devvm_fetch_url "$CSS_URL" > "$TMPDIR/kiosk.css"

DEVVM_APP_JS_FILE="$TMPDIR/kiosk_app.js" \
DEVVM_CSS_FILE="$TMPDIR/kiosk.css" \
DEVVM_BASE_URL="$(devvm_base_url)" \
DEVVM_TOKEN="$DEMO_KIOSK_TOKEN" \
DEVVM_EXPECTED_BRANCH="$EXPECTED_BRANCH" \
DEVVM_EXPECTED_INCREMENT="$DEMO_KIOSK_EXPECTED_INCREMENT" \
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
    'data-prototype-contract="checkin-success"',
    'data-direct-checkin',
    'data-session-id',
    'this.studentDirectCheckin(member)',
    'studentCheckinSessionForMember',
    'memberCardCheckedIn',
    'jsonPost("/kiosk/student/checkin"',
    'this.state.checkinModal = null;',
    'CHECKED IN',
    'Returning to check-in',
    'ALREADY CHECKED IN',
    'k-member-tile--checked-in',
    'CHECKIN_SUCCESS_DISMISS_MS = 4000',
):
    assert marker in app_js, "prototype direct check-in marker missing from served app asset: %s" % marker
assert 'onSelect="(member) => this.studentConfirm(member)"' not in app_js, (
    "student roster card tap still points at modal-first confirmation"
)

for marker in (
    ".k-success-kicker",
    ".k-success-meta",
    ".k-member-tile--checking-in",
    ".k-prototype-home .k-member-tile--checked-in:disabled",
):
    assert marker in kiosk_css, "prototype check-in CSS marker missing: %s" % marker

flow_date = os.environ.get("DEVVM_FLOW_DATE") or ""
roster_params = {"date": flow_date} if flow_date else {}
student_roster = rpc("/kiosk/student_roster", roster_params) or {}
session = student_roster.get("session") or {}
members = student_roster.get("members") or []
assert members, "Development VM student roster returned no cards for direct check-in proof"

target_member_id = os.environ.get("DEVVM_TARGET_MEMBER_ID") or ""
target_session_id = os.environ.get("DEVVM_TARGET_SESSION_ID") or ""

def card_id(card):
    if card.get("is_trial"):
        return "trial:%s" % card.get("lead_id")
    return "member:%s" % card.get("member_id")

def card_matches(card):
    if target_member_id and str(card.get("member_id") or "") != target_member_id:
        return False
    if target_session_id:
        sid = card.get("session_id") or session.get("id")
        if str(sid or "") != target_session_id:
            return False
    return bool(card.get("lead_id") or card.get("member_id"))

eligible = [card for card in members if card_matches(card)]
assert eligible, "no roster card matched the Development VM direct check-in target"

pending = [
    card for card in eligible
    if (card.get("attendance_state") or "pending") not in {"present", "late"}
]
already = [
    card for card in eligible
    if (card.get("attendance_state") or "") in {"present", "late"}
]
card = pending[0] if pending else already[0] if already else None
assert card, "no pending or already-checked-in card was available for direct check-in proof"

session_id = card.get("session_id") or session.get("id")
assert session_id, "selected student card has no session_id for direct check-in"
for key in (
    "name",
    "image_url",
    "belt_rank",
    "program_name",
    "attendance_state",
    "attendance_label",
    "membership_state",
    "membership_label",
    "session_id",
):
    assert key in card, "student direct check-in card missing %s" % key

checkin_params = {"session_id": int(session_id)}
if card.get("is_trial"):
    checkin_params["lead_id"] = int(card["lead_id"])
else:
    checkin_params["member_id"] = int(card["member_id"])
checkin = rpc("/kiosk/student/checkin", checkin_params) or {}

created = checkin.get("success") is True
already_checked_in = (
    not created
    and "already checked in" in (checkin.get("error") or "").lower()
)
assert created or already_checked_in, "direct student-card check-in failed unexpectedly: %s" % checkin
if created:
    assert checkin.get("status") in {"present", "late"}, "unexpected direct check-in status: %s" % checkin
    assert checkin.get("session_name"), "direct check-in response missing session_name"
    assert "program_name" in checkin, "direct check-in response missing program_name"

refreshed_roster = rpc("/kiosk/student_roster", roster_params) or {}
refreshed_members = refreshed_roster.get("members") or []
updated = next((item for item in refreshed_members if card_id(item) == card_id(card)), None)
assert updated, "refreshed student roster is missing the direct check-in card"
assert updated.get("attendance_state") in {"present", "late"}, (
    "refreshed student card did not render already-checked-in state: %s" % updated
)
assert updated.get("attendance_label"), "refreshed checked-in card is missing attendance_label"

print(
    "ver-devvm-kiosk-prototype-checkin: PASS (%s %s session=%s state=%s)"
    % (
        "created_checkin" if created else "already_checked_in",
        card_id(card),
        session_id,
        updated.get("attendance_state"),
    )
)
PY
