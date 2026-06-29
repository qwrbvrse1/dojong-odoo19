#!/usr/bin/env bash
# Gate: Development VM student kiosk home/search contract.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/devvm-kiosk-lib.sh"
devvm_cd_root

devvm_require_env
EXPECTED_BRANCH="$(devvm_expected_branch)"
[ -n "$EXPECTED_BRANCH" ] || devvm_fail "devvm kiosk gate: could not determine expected branch; set DEMO_KIOSK_EXPECTED_BRANCH"

QUERY="${DEMO_KIOSK_SEARCH_QUERY:-Demo}"
SEARCH_PARAMS=$(
  DEVVM_QUERY="$QUERY" python3 - <<'PY'
import json
import os
print(json.dumps({"query": os.environ["DEVVM_QUERY"]}))
PY
)

TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

devvm_fetch_url "$(devvm_kiosk_url)" > "$TMPDIR/shell.html"
devvm_fetch_served_app "$TMPDIR/shell.html" "$TMPDIR/kiosk_app.js"
bootstrap="$(devvm_json_rpc "/kiosk/api/bootstrap" "{}")"
search="$(devvm_json_rpc "/kiosk/search" "$SEARCH_PARAMS")"

DEVVM_SHELL_HTML_FILE="$TMPDIR/shell.html" \
DEVVM_APP_JS_FILE="$TMPDIR/kiosk_app.js" \
DEVVM_BOOTSTRAP="$bootstrap" \
DEVVM_SEARCH="$search" \
DEVVM_EXPECTED_BRANCH="$EXPECTED_BRANCH" \
DEVVM_EXPECTED_INCREMENT="${DEMO_KIOSK_EXPECTED_INCREMENT:-INC-02}" \
DEVVM_TARGET_NAME="${DEMO_KIOSK_MEMBER_NAME:-}" \
python3 - <<'PY'
import json
import os
import sys

def _excepthook(exc_type, exc, _tb):
    print("%s: %s" % (exc_type.__name__, exc), file=sys.stderr)
sys.excepthook = _excepthook

with open(os.environ["DEVVM_SHELL_HTML_FILE"], encoding="utf-8") as fh:
    shell = fh.read()
with open(os.environ["DEVVM_APP_JS_FILE"], encoding="utf-8") as fh:
    app_js = fh.read()

bootstrap_payload = json.loads(os.environ["DEVVM_BOOTSTRAP"])
search_payload = json.loads(os.environ["DEVVM_SEARCH"])
bootstrap = bootstrap_payload.get("result") or {}
search = search_payload.get("result")

expected_branch = os.environ["DEVVM_EXPECTED_BRANCH"]
expected_increment = os.environ["DEVVM_EXPECTED_INCREMENT"]

assert '<div id="kiosk-root"></div>' in shell, "SPA root is missing from Development VM kiosk shell"
assert "window.KIOSK_TOKEN" in shell, "kiosk token bootstrap is missing from Development VM shell"
assert "kiosk_app.js" in shell, "student kiosk app script is missing from Development VM shell"
assert "kiosk_instructor.js" in shell, "instructor script is missing from Development VM shell"
assert "dojo-kiosk-body" in shell, "kiosk body class is missing from Development VM shell"

assert f'KIOSK_RELEASE_BRANCH = "{expected_branch}"' in app_js, (
    "served app asset does not match expected release branch %s" % expected_branch
)
assert f'KIOSK_RELEASE_INCREMENT = "{expected_increment}"' in app_js, (
    "served app asset does not expose expected increment %s" % expected_increment
)

for marker in (
    "k-welcome-screen",
    "k-welcome-logo",
    "k-welcome-title",
    "k-welcome-search",
    "k-welcome-search-icon",
    "k-search-results-flow",
    "k-member-tile",
    "k-member-tile__program",
    "k-member-tile__belt",
    "k-member-tile__state",
    "k-member-tile__affordance",
    "check_circle",
    "StudentCheckinModal",
    "checkinMemberKey",
    "isCurrentCheckinMember",
    "_searchSeq",
    "k-checkin-session-btn",
    "k-checkin-session-btn__cta",
    "k-checkin-success-overlay",
    "CHECKIN_SUCCESS_DISMISS_MS = 4000",
    "playCheckinChime();",
):
    assert marker in app_js, "student UI marker missing from served app asset: %s" % marker

assert not bootstrap.get("error"), "bootstrap returned an error: %s" % bootstrap
assert bootstrap.get("config_id"), "bootstrap payload missing config_id"
assert bootstrap.get("name"), "bootstrap payload missing kiosk name"
assert "sessions" in bootstrap, "bootstrap payload missing sessions"
sessions = bootstrap.get("sessions") or []
assert sessions, "bootstrap payload returned no sessions for the Development VM demo"
context = bootstrap.get("session_context") or {}
assert context.get("mode") in {"active", "upcoming", "upcoming_soon", "standby"}, (
    "unexpected session context: %s" % context
)
assert context.get("selected_session_id") or context.get("mode") == "standby", (
    "session context did not select an active/upcoming session"
)
for session in sessions:
    for key in ("id", "name", "template_name", "program_name", "start", "end", "time_state", "capacity", "seats_taken"):
        assert key in session, "session payload missing %s" % key
    assert session["time_state"] in {"active", "upcoming_soon", "upcoming", "done"}, (
        "invalid time_state: %s" % session["time_state"]
    )

assert isinstance(search, list), "search result is not a list"
assert search, "Development VM search query returned no results"
target_name = os.environ.get("DEVVM_TARGET_NAME") or ""
if target_name:
    card = next((item for item in search if item.get("name") == target_name), None)
else:
    card = next((item for item in search if not item.get("is_trial")), None) or search[0]
assert card, "could not choose a search-card result to validate"

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
    assert key in card, "search card payload missing %s" % key
assert card.get("name"), "search card missing identity"
assert card.get("is_trial") in (True, False), "search card is_trial must be boolean"
if card.get("is_trial"):
    assert card.get("lead_id"), "trial search card missing lead_id"
    assert card.get("trial_session") is not None, "trial search card missing trial_session"
    assert card.get("membership_state") == "trial", "trial search card must expose trial state"
else:
    assert card.get("member_id"), "member search card missing member_id"
    assert card.get("membership_state") is not None, "member search card missing membership state"

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
leaked = sorted(private_keys.intersection(card.keys()))
assert not leaked, "public search card leaked private profile keys: %s" % ", ".join(leaked)

print("ver-devvm-kiosk-home: PASS")
PY
