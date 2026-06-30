#!/usr/bin/env bash
# Gate: Development VM prototype-parity student roster visibility and filtering.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/devvm-kiosk-lib.sh"
devvm_cd_root

export DEMO_KIOSK_EXPECTED_INCREMENT="${DEMO_KIOSK_EXPECTED_INCREMENT:-INC-03}"
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

bootstrap="$(devvm_json_rpc "/kiosk/api/bootstrap" "{}")"
if ! student_roster="$(devvm_json_rpc "/kiosk/student_roster" "{}" 2>"$TMPDIR/student_roster.err")"; then
  cat "$TMPDIR/student_roster.err" >&2
  devvm_fail "devvm kiosk gate: /kiosk/student_roster is unavailable; deploy and upgrade dojo_kiosk for INC-03"
fi

DEVVM_SHELL_HTML_FILE="$TMPDIR/shell.html" \
DEVVM_APP_JS_FILE="$TMPDIR/kiosk_app.js" \
DEVVM_CSS_FILE="$TMPDIR/kiosk.css" \
DEVVM_BOOTSTRAP="$bootstrap" \
DEVVM_STUDENT_ROSTER="$student_roster" \
DEVVM_EXPECTED_BRANCH="$EXPECTED_BRANCH" \
DEVVM_EXPECTED_INCREMENT="$DEMO_KIOSK_EXPECTED_INCREMENT" \
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
with open(os.environ["DEVVM_CSS_FILE"], encoding="utf-8") as fh:
    kiosk_css = fh.read()

bootstrap_payload = json.loads(os.environ["DEVVM_BOOTSTRAP"])
roster_payload = json.loads(os.environ["DEVVM_STUDENT_ROSTER"])
bootstrap = bootstrap_payload.get("result") or {}
student_roster = roster_payload.get("result") or {}
members = student_roster.get("members") or []
session = student_roster.get("session") or {}

expected_branch = os.environ["DEVVM_EXPECTED_BRANCH"]
expected_increment = os.environ["DEVVM_EXPECTED_INCREMENT"]

assert '<div id="kiosk-root"></div>' in shell, "SPA root is missing from Development VM kiosk shell"
assert f'KIOSK_RELEASE_BRANCH = "{expected_branch}"' in app_js, (
    "served app asset does not match expected release branch %s" % expected_branch
)
assert f'KIOSK_RELEASE_INCREMENT = "{expected_increment}"' in app_js, (
    "served app asset does not expose expected increment %s" % expected_increment
)

for marker in (
    'jsonPost("/kiosk/student_roster"',
    "studentRosterCards",
    "studentRosterLoaded",
    "_applyStudentRosterPayload",
    "visibleStudentRoster()",
    "return roster.filter(member =>",
    "terms.every(term => haystack.includes(term))",
    "this.state.studentRosterLoaded || this.studentSelectedSessionId()",
    'data-student-card',
    'data-attendance-state',
    "k-member-tile__avatar-wrap",
    "k-member-tile__name-line",
    "k-member-tile__details",
    "k-member-tile__affordance",
    "ALREADY CHECKED IN",
):
    assert marker in app_js, "prototype roster marker missing from served app asset: %s" % marker

for marker in (
    ".k-prototype-home .k-results-grid",
    "minmax(180px, 220px)",
    "justify-content: center",
    ".k-prototype-home .k-member-tile__avatar-wrap",
    "border-radius: 50%",
    ".k-prototype-home .k-member-tile__state--checked-in",
    ".k-prototype-home .k-member-tile__affordance",
):
    assert marker in kiosk_css, "prototype roster CSS marker missing: %s" % marker

assert not bootstrap.get("error"), "bootstrap returned an error: %s" % bootstrap
assert bootstrap.get("config_id"), "bootstrap payload missing config_id"
assert isinstance(bootstrap.get("sessions") or [], list), "bootstrap sessions must be a list"

assert isinstance(student_roster, dict), "student_roster result is not an object"
assert student_roster.get("source") in {"session_roster", "member_roster"}, (
    "unexpected student_roster source: %s" % student_roster.get("source")
)
if session:
    assert session.get("id"), "student_roster session missing id"
    assert session.get("template_name") or session.get("name"), "student_roster session missing title"
assert isinstance(members, list), "student_roster members is not a list"
assert members, "Development VM student roster returned no first-load cards"

valid_attendance = {
    "pending",
    "present",
    "late",
    "absent",
    "excused",
    "checked_out",
    "sick",
    "injury",
    "vacation",
    "other",
}
private_keys = {
    "email",
    "phone",
    "household",
    "guardians",
    "date_of_birth",
    "plan_name",
    "issues",
    "workflow_status",
    "alert_count",
    "onboarding_pct",
    "open_task_count",
}
required_keys = {
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
}

for idx, card in enumerate(members):
    missing = required_keys - set(card)
    assert not missing, "student roster card %d missing keys: %s" % (idx, sorted(missing))
    assert card.get("member_id") or card.get("lead_id"), "student roster card %d has no member/lead id" % idx
    assert card.get("name"), "student roster card %d missing student identity" % idx
    assert card.get("attendance_state") in valid_attendance, (
        "student roster card %d has invalid attendance state: %s" % (idx, card.get("attendance_state"))
    )
    leaked = sorted(private_keys.intersection(card.keys()))
    assert not leaked, "student roster card leaked private profile keys: %s" % ", ".join(leaked)

def visible_for(query):
    terms = [part for part in query.strip().lower().split() if part]
    if not terms:
        return members
    filtered = []
    for member in members:
        haystack = " ".join(
            str(member.get(key) or "")
            for key in (
                "name",
                "member_number",
                "belt_rank",
                "program_name",
                "trial_program",
                "membership_label",
                "attendance_label",
            )
        ).lower()
        if all(term in haystack for term in terms):
            filtered.append(member)
    return filtered

target = next((card for card in members if card.get("name")), members[0])
target_term = str(target.get("name")).split()[0]
assert len(visible_for("")) == len(members), "empty query should preserve the visible first-load roster"
assert target in visible_for(target_term), "student name query did not keep the matching visible card"
assert not visible_for("__devvm_no_matching_student__"), "impossible query should filter the visible roster to empty"

checked_in_cards = [
    card for card in members
    if card.get("attendance_state") in {"present", "late"}
]
if checked_in_cards:
    assert "k-member-tile--checked-in" in app_js, "checked-in roster card class is missing"
    assert "ALREADY CHECKED IN" in app_js, "checked-in roster card label is missing"

print(
    "ver-devvm-kiosk-prototype-roster: PASS (source=%s cards=%d filter=%s checked_in=%d)"
    % (student_roster.get("source"), len(members), target_term, len(checked_in_cards))
)
PY
