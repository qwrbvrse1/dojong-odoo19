#!/usr/bin/env bash
# Gate: live instructor roster card density and operational semantics.
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

kiosk_fetch "/dojo_kiosk/static/src/kiosk_app.js" > "$TMPDIR/kiosk_app.js"
kiosk_fetch "/dojo_kiosk/static/src/kiosk.css" > "$TMPDIR/kiosk.css"
summary=$(kiosk_json_rpc "/kiosk/api/session_summary" "{\"token\":\"${TOKEN}\",\"session_id\":${SID}}")
roster=$(kiosk_json_rpc "/kiosk/roster" "{\"token\":\"${TOKEN}\",\"session_id\":${SID}}")

KIOSK_APP_JS_FILE="$TMPDIR/kiosk_app.js" \
KIOSK_CSS_FILE="$TMPDIR/kiosk.css" \
KIOSK_SUMMARY="$summary" \
KIOSK_ROSTER="$roster" \
python3 - <<'PY'
import json
import os
import sys

def _excepthook(exc_type, exc, _tb):
    print("%s: %s" % (exc_type.__name__, exc), file=sys.stderr)
sys.excepthook = _excepthook

with open(os.environ["KIOSK_APP_JS_FILE"], encoding="utf-8") as fh:
    app_js = fh.read()
with open(os.environ["KIOSK_CSS_FILE"], encoding="utf-8") as fh:
    kiosk_css = fh.read()
summary = json.loads(os.environ["KIOSK_SUMMARY"]).get("result") or {}
roster = json.loads(os.environ["KIOSK_ROSTER"]).get("result")

for marker in (
    "class InstructorRosterTile",
    "k-roster-tile__photo",
    "k-roster-tile__name",
    "k-roster-tile__attendance",
    "k-roster-tile__meta",
    "k-roster-card__progress-bar",
    "k-roster-card__progress-fill",
    "workflowBadges()",
    "onTileTap",
    "onPointerDown",
    "data-attendance-state",
    "data-onboarding-pct",
    "data-open-task-count",
    "data-membership-state",
):
    assert marker in app_js, "roster card UI marker missing from served app asset: %s" % marker

for marker in (
    "k-roster-grid--instructor",
    "minmax(112px",
    "min-height: 156px",
    ".k-roster-tile__attendance",
    ".k-roster-tile__meta",
):
    assert marker in kiosk_css, "roster density CSS marker missing: %s" % marker

assert summary.get("success") is True, "session summary failed: %s" % summary
assert summary.get("total_enrolled", 0) >= 1, "seeded instructor session has no enrolled roster"
assert isinstance(roster, list), "roster payload is not a list"
assert roster, "roster payload is empty"

valid_attendance = {"pending", "present", "late", "absent", "checked_out", "excused"}
required_keys = {
    "member_id",
    "name",
    "image_url",
    "attendance_state",
    "attendance_label",
    "membership_state",
    "membership_label",
    "workflow_status",
    "alert_count",
    "onboarding_pct",
    "open_task_count",
    "issues",
    "belt_rank",
    "program_name",
}

for idx, entry in enumerate(roster):
    missing = required_keys - set(entry)
    assert not missing, "roster entry %d missing keys: %s" % (idx, sorted(missing))
    assert entry["name"], "roster entry %d missing display name" % idx
    assert entry["attendance_state"] in valid_attendance, (
        "roster entry %d invalid attendance_state: %s" % (idx, entry["attendance_state"])
    )
    assert isinstance(entry["onboarding_pct"], int), "onboarding_pct must be an integer"
    assert 0 <= entry["onboarding_pct"] <= 100, "onboarding_pct out of range"
    assert isinstance(entry["open_task_count"], int), "open_task_count must be an integer"
    assert entry["open_task_count"] >= 0, "open_task_count cannot be negative"
    assert isinstance(entry["issues"], list), "issues must be a list"

    workflow = entry["workflow_status"] or {}
    assert isinstance(workflow, dict), "workflow_status must be an object"
    for key in ("alerts", "onboarding", "subscription", "tasks"):
        assert key in workflow, "workflow_status missing %s" % key
    assert isinstance(workflow.get("alerts"), list), "workflow alerts must be a list"
    assert isinstance(workflow.get("tasks") or {}, dict), "workflow tasks must be an object"

demo = next((entry for entry in roster if entry.get("name") == "Demo Member"), None)
assert demo, "Demo Member is not present in the active instructor roster"
assert demo.get("program_name") == "Demo Program", "Demo Member roster card missing program context"

print("ver-kiosk-roster-cards: PASS")
PY
