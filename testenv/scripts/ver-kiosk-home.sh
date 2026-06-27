#!/usr/bin/env bash
# Gate: live student kiosk home/search contract.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/kiosk-live-lib.sh"
kiosk_cd_root

kiosk_require_schema
kiosk_ensure_demo_member_searchable

TOKEN=$(kiosk_token)

TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

kiosk_fetch "/kiosk/${TOKEN}" > "$TMPDIR/shell.html"
kiosk_fetch "/dojo_kiosk/static/src/kiosk_app.js" > "$TMPDIR/kiosk_app.js"
bootstrap=$(kiosk_json_rpc "/kiosk/api/bootstrap" "{\"token\":\"${TOKEN}\"}")
search=$(kiosk_json_rpc "/kiosk/search" "{\"token\":\"${TOKEN}\",\"query\":\"Demo\"}")

KIOSK_SHELL_HTML_FILE="$TMPDIR/shell.html" \
KIOSK_APP_JS_FILE="$TMPDIR/kiosk_app.js" \
KIOSK_BOOTSTRAP="$bootstrap" \
KIOSK_SEARCH="$search" \
python3 - <<'PY'
import json
import os
import sys

def _excepthook(exc_type, exc, _tb):
    print("%s: %s" % (exc_type.__name__, exc), file=sys.stderr)
sys.excepthook = _excepthook

with open(os.environ["KIOSK_SHELL_HTML_FILE"], encoding="utf-8") as fh:
    shell = fh.read()
with open(os.environ["KIOSK_APP_JS_FILE"], encoding="utf-8") as fh:
    app_js = fh.read()
bootstrap = json.loads(os.environ["KIOSK_BOOTSTRAP"]).get("result") or {}
search = json.loads(os.environ["KIOSK_SEARCH"]).get("result")

assert '<div id="kiosk-root"></div>' in shell, "SPA root is missing from live kiosk shell"
assert "window.KIOSK_TOKEN" in shell, "kiosk token bootstrap is missing from live shell"
assert "kiosk_app.js" in shell, "student kiosk app script is missing from live shell"
assert "kiosk_instructor.js" in shell, "instructor script is missing from live shell"
assert "dojo-kiosk-body" in shell, "kiosk body class is missing from live shell"

for marker in (
    "k-welcome-screen",
    "k-welcome-search",
    "k-search-results-flow",
    "k-member-tile",
    "k-member-tile__program",
    "k-member-tile__belt",
    "k-member-tile__state",
    "k-member-tile__affordance",
    "k-member-tile__trial-badge",
    "k-checkin-session-btn",
    "k-checkin-session-btn__cta",
    "k-checkin-success-overlay",
    "CHECKIN_SUCCESS_DISMISS_MS = 4000",
    "playCheckinChime();",
):
    assert marker in app_js, "student UI marker missing from served app asset: %s" % marker

sessions = bootstrap.get("sessions") or []
assert bootstrap.get("config_id"), "bootstrap payload missing config_id"
assert bootstrap.get("name"), "bootstrap payload missing kiosk name"
assert sessions, "bootstrap payload returned no sessions"
context = bootstrap.get("session_context") or {}
assert context.get("mode") in {"active", "upcoming_soon", "standby"}, "unexpected session context: %s" % context
assert context.get("selected_session_id") or context.get("mode") == "standby", "session context did not select an active/upcoming session"
for session in sessions:
    for key in ("id", "name", "template_name", "program_name", "start", "end", "time_state", "capacity", "seats_taken"):
        assert key in session, "session payload missing %s" % key
    assert session["time_state"] in {"active", "upcoming_soon", "upcoming", "done"}, "invalid time_state: %s" % session["time_state"]

assert isinstance(search, list), "search result is not a list"
demo = next((item for item in search if item.get("name") == "Demo Member"), None)
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
assert demo["is_trial"] is False, "Demo Member must render as a member card, not a trial card"
assert demo["membership_state"] == "active", "Demo Member search card should expose active state"
assert demo["program_name"] == "Demo Program", "Demo Member search card missing class program context"

print("ver-kiosk-home: PASS")
PY
