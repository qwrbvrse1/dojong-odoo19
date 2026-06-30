#!/usr/bin/env bash
# Gate: Development VM prototype-parity student first-load home surface.
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
bootstrap="$(devvm_json_rpc "/kiosk/api/bootstrap" "{}")"

TARGET_SESSION_ID="$(
  DEVVM_BOOTSTRAP="$bootstrap" python3 - <<'PY'
import json
import os

payload = json.loads(os.environ["DEVVM_BOOTSTRAP"])
result = payload.get("result") or {}
sessions = result.get("sessions") or []
ctx = result.get("session_context") or {}
selected_id = ctx.get("selected_session_id")
if selected_id:
    print(selected_id)
    raise SystemExit
for state in ("active", "upcoming_soon", "upcoming"):
    for session in sessions:
        if session.get("time_state") == state:
            print(session.get("id") or "")
            raise SystemExit
print((sessions[0] or {}).get("id") if sessions else "")
PY
)"

if [ -n "$TARGET_SESSION_ID" ]; then
  ROSTER_PARAMS="$(DEVVM_SESSION_ID="$TARGET_SESSION_ID" python3 - <<'PY'
import json
import os
print(json.dumps({"session_id": int(os.environ["DEVVM_SESSION_ID"])}))
PY
)"
  roster="$(devvm_json_rpc "/kiosk/roster" "$ROSTER_PARAMS")"
else
  roster='{"jsonrpc":"2.0","result":[]}'
fi

DEVVM_SHELL_HTML_FILE="$TMPDIR/shell.html" \
DEVVM_APP_JS_FILE="$TMPDIR/kiosk_app.js" \
DEVVM_BOOTSTRAP="$bootstrap" \
DEVVM_ROSTER="$roster" \
DEVVM_EXPECTED_BRANCH="$EXPECTED_BRANCH" \
DEVVM_EXPECTED_INCREMENT="${DEMO_KIOSK_EXPECTED_INCREMENT:-INC-02}" \
DEVVM_TARGET_SESSION_ID="$TARGET_SESSION_ID" \
python3 - <<'PY'
import json
import os
import re
import sys

def _excepthook(exc_type, exc, _tb):
    print("%s: %s" % (exc_type.__name__, exc), file=sys.stderr)
sys.excepthook = _excepthook

with open(os.environ["DEVVM_SHELL_HTML_FILE"], encoding="utf-8") as fh:
    shell = fh.read()
with open(os.environ["DEVVM_APP_JS_FILE"], encoding="utf-8") as fh:
    app_js = fh.read()

bootstrap_payload = json.loads(os.environ["DEVVM_BOOTSTRAP"])
roster_payload = json.loads(os.environ["DEVVM_ROSTER"])
bootstrap = bootstrap_payload.get("result") or {}
roster = roster_payload.get("result") or []

expected_branch = os.environ["DEVVM_EXPECTED_BRANCH"]
expected_increment = os.environ["DEVVM_EXPECTED_INCREMENT"]
target_session_id = os.environ["DEVVM_TARGET_SESSION_ID"]

assert '<div id="kiosk-root"></div>' in shell, "SPA root is missing from Development VM kiosk shell"
assert "window.KIOSK_TOKEN" in shell, "kiosk token bootstrap is missing from Development VM shell"
assert "kiosk_app.js" in shell, "student kiosk app script is missing from Development VM shell"
assert "dojo-kiosk-body" in shell, "kiosk body class is missing from Development VM shell"

assert f'KIOSK_RELEASE_BRANCH = "{expected_branch}"' in app_js, (
    "served app asset does not match expected release branch %s" % expected_branch
)
assert f'KIOSK_RELEASE_INCREMENT = "{expected_increment}"' in app_js, (
    "served app asset does not expose expected increment %s" % expected_increment
)

for marker in (
    'data-prototype-contract="student-home"',
    "k-prototype-home",
    "k-prototype-home__topbar",
    "k-prototype-home__title",
    "k-prototype-home__exit",
    "k-prototype-home__search",
    "k-welcome-search",
    "k-search-results-flow",
    "visibleStudentRoster",
    "studentSelectedSession",
    "_loadStudentRoster",
    'jsonPost("/kiosk/roster"',
    "ALREADY CHECKED IN",
    "Tap to check in",
):
    assert marker in app_js, "prototype student-home marker missing from served app asset: %s" % marker

assert re.search(r'<t t-if="state\.instructorMode">\s*<div class="k-header k-header--instructor">', app_js), (
    "shared app header was not limited to instructor mode"
)
for removed in (
    'src="/dojo_kiosk/static/src/img/uft-logo-horizontal.png"',
    '<div class="k-kiosk-footer">',
    '!state.idle and state.aiEnabled',
    'title="Switch to Instructor Mode">🥋</button>',
):
    assert removed not in app_js, "non-prototype student chrome still present in served app asset: %s" % removed
assert "!state.idle and state.instructorMode and state.aiEnabled" in app_js, (
    "AI assistant must be gated away from the student surface"
)

assert not bootstrap.get("error"), "bootstrap returned an error: %s" % bootstrap
assert bootstrap.get("config_id"), "bootstrap payload missing config_id"
assert bootstrap.get("name"), "bootstrap payload missing kiosk name"
sessions = bootstrap.get("sessions") or []
assert sessions, "bootstrap payload returned no sessions for the Development VM demo"
context = bootstrap.get("session_context") or {}
assert context.get("mode") in {"active", "upcoming", "upcoming_soon", "standby"}, (
    "unexpected session context: %s" % context
)
assert target_session_id, "prototype home gate could not choose a roster session from bootstrap"
session = next((item for item in sessions if str(item.get("id")) == str(target_session_id)), None)
assert session, "chosen student roster session missing from bootstrap sessions"
assert session.get("template_name") or session.get("name"), "chosen session is missing display title"

assert isinstance(roster, list), "roster result is not a list"
assert roster, "Development VM selected roster returned no visible student cards"
card = next((item for item in roster if item.get("member_id") or item.get("lead_id")), None)
assert card, "selected roster contains no member or trial card"
for key in (
    "name",
    "image_url",
    "belt_rank",
    "belt_color",
    "program_name",
    "program_color",
    "attendance_state",
    "attendance_label",
    "membership_state",
    "membership_label",
):
    assert key in card, "roster card payload missing %s" % key
assert card.get("name"), "roster card missing student identity"
assert card.get("is_trial") in (True, False, None), "roster card is_trial must be boolean when present"
assert card.get("attendance_state") in {"pending", "present", "late", "absent", "excused", "checked_out"}, (
    "unexpected roster card attendance state: %s" % card.get("attendance_state")
)
for private_key in ("email", "phone", "household", "guardians", "date_of_birth", "plan_name"):
    assert private_key not in card, "student roster card leaked private profile key: %s" % private_key

print(
    "ver-devvm-kiosk-prototype-home: PASS (session=%s roster_cards=%d)"
    % (target_session_id, len(roster))
)
PY
