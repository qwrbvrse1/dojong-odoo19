#!/usr/bin/env bash
# Gate: live member profile tabs, onboarding payload, and auth scoping contract.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/kiosk-live-lib.sh"
kiosk_cd_root

kiosk_require_schema
kiosk_ensure_demo_member_searchable

TOKEN=$(kiosk_token)
MID=$(kiosk_demo_member_id)
SID=$(kiosk_active_session_id)
KEY=$(kiosk_instructor_key "$TOKEN")

TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

kiosk_fetch "/dojo_kiosk/static/src/kiosk_app.js" > "$TMPDIR/kiosk_app.js"
public_profile=$(kiosk_json_rpc "/kiosk/member/profile" "{\"token\":\"${TOKEN}\",\"member_id\":${MID},\"session_id\":${SID}}")
instructor_profile=$(kiosk_json_rpc "/kiosk/member/profile" "{\"token\":\"${TOKEN}\",\"member_id\":${MID},\"session_id\":${SID},\"instructor_key\":\"${KEY}\"}")

KIOSK_APP_JS_FILE="$TMPDIR/kiosk_app.js" \
KIOSK_PUBLIC_PROFILE="$public_profile" \
KIOSK_INSTRUCTOR_PROFILE="$instructor_profile" \
python3 - <<'PY'
import json
import os
import sys

def _excepthook(exc_type, exc, _tb):
    print("%s: %s" % (exc_type.__name__, exc), file=sys.stderr)
sys.excepthook = _excepthook

with open(os.environ["KIOSK_APP_JS_FILE"], encoding="utf-8") as fh:
    app_js = fh.read()
public_profile = json.loads(os.environ["KIOSK_PUBLIC_PROFILE"]).get("result") or {}
instructor_profile = json.loads(os.environ["KIOSK_INSTRUCTOR_PROFILE"]).get("result") or {}

for marker in (
    "MemberProfileCard",
    "k-profile-tabs",
    "k-profile-tab",
    "state.tab === 'profile'",
    "state.tab === 'progress'",
    "state.tab === 'household'",
    "state.tab === 'manage'",
    "props.instructorMode",
):
    assert marker in app_js, "profile tab marker missing from served app asset: %s" % marker

for key in ("member_id", "name", "image_url", "belt_rank", "attendance_state", "enrolled_sessions"):
    assert key in public_profile, "public profile missing safe key %s" % key
for private_key in ("email", "phone", "member_number", "membership_state", "household", "guardians", "issues", "workflow_status", "programs"):
    assert private_key not in public_profile, "public profile leaks instructor/private key %s" % private_key

for key in ("member_id", "name", "member_number", "membership_state", "workflow_status", "issues", "attendance_state"):
    assert key in instructor_profile, "instructor profile missing %s" % key
workflow = instructor_profile.get("workflow_status") or {}
onboarding = workflow.get("onboarding") or {}
assert onboarding.get("available") is True, "instructor profile onboarding payload is unavailable"
assert "progress_pct" in onboarding, "onboarding payload missing progress_pct"
assert "missing_steps" in onboarding, "onboarding payload missing missing_steps"
step_keys = {step.get("key") for step in onboarding.get("steps") or []}
for key in ("trial_booked", "waiver_signed", "intro_completed", "membership_activated", "uniform_issued"):
    assert key in step_keys, "onboarding guidance step missing: %s" % key

print("ver-kiosk-profile-tabs: PASS")
PY
