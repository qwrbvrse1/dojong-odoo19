#!/usr/bin/env bash
# Gate: live member profile tabs, onboarding payload, and auth scoping contract.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/kiosk-live-lib.sh"
kiosk_cd_root

kiosk_require_schema
kiosk_require_table "dojo_onboarding_record"
kiosk_ensure_demo_member_searchable

TOKEN=$(kiosk_token)
MID=$(kiosk_demo_member_id)
SID=$(kiosk_active_session_id)
KEY=$(kiosk_instructor_key "$TOKEN")

kiosk_psql_exec "UPDATE dojo_member SET membership_state = 'active' WHERE id = ${MID};"
record_count=$(kiosk_psql_scalar "SELECT COUNT(*) FROM dojo_onboarding_record WHERE member_id = ${MID};")
if [ "$record_count" = "0" ]; then
  kiosk_psql_exec "INSERT INTO dojo_onboarding_record (member_id, company_id, state, step_member_info, step_household, step_enrollment, step_subscription, step_portal_access, step_trial_booked, step_waiver_signed, step_intro_completed, step_membership_activated, step_uniform_issued, create_uid, write_uid, create_date, write_date) VALUES (${MID}, 1, 'in_progress', TRUE, TRUE, FALSE, FALSE, FALSE, TRUE, FALSE, FALSE, TRUE, FALSE, 1, 1, NOW(), NOW());"
fi
RID=$(kiosk_psql_scalar "SELECT id FROM dojo_onboarding_record WHERE member_id = ${MID} ORDER BY create_date DESC, id DESC LIMIT 1;")
kiosk_psql_exec "UPDATE dojo_onboarding_record SET state = 'in_progress', step_member_info = TRUE, step_household = TRUE, step_enrollment = FALSE, step_subscription = FALSE, step_portal_access = FALSE, step_trial_booked = TRUE, step_waiver_signed = FALSE, step_intro_completed = FALSE, step_membership_activated = TRUE, step_uniform_issued = FALSE WHERE id = ${RID};"

TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

kiosk_fetch "/dojo_kiosk/static/src/kiosk_app.js" > "$TMPDIR/kiosk_app.js"
kiosk_fetch "/dojo_kiosk/static/src/kiosk.css" > "$TMPDIR/kiosk.css"
public_profile=$(kiosk_json_rpc "/kiosk/member/profile" "{\"token\":\"${TOKEN}\",\"member_id\":${MID},\"session_id\":${SID}}")
invalid_key_profile=$(kiosk_json_rpc "/kiosk/member/profile" "{\"token\":\"${TOKEN}\",\"member_id\":${MID},\"session_id\":${SID},\"instructor_key\":\"invalid-key\"}")
instructor_profile=$(kiosk_json_rpc "/kiosk/member/profile" "{\"token\":\"${TOKEN}\",\"member_id\":${MID},\"session_id\":${SID},\"instructor_key\":\"${KEY}\"}")

KIOSK_APP_JS_FILE="$TMPDIR/kiosk_app.js" \
KIOSK_CSS_FILE="$TMPDIR/kiosk.css" \
KIOSK_PUBLIC_PROFILE="$public_profile" \
KIOSK_INVALID_KEY_PROFILE="$invalid_key_profile" \
KIOSK_INSTRUCTOR_PROFILE="$instructor_profile" \
python3 - <<'PY'
import json
import os
import sys

def fail(message):
    print(message, file=sys.stderr)
    sys.exit(1)

with open(os.environ["KIOSK_APP_JS_FILE"], encoding="utf-8") as fh:
    app_js = fh.read()
with open(os.environ["KIOSK_CSS_FILE"], encoding="utf-8") as fh:
    kiosk_css = fh.read()

public_profile = json.loads(os.environ["KIOSK_PUBLIC_PROFILE"]).get("result") or {}
invalid_key_profile = json.loads(os.environ["KIOSK_INVALID_KEY_PROFILE"]).get("result") or {}
instructor_profile = json.loads(os.environ["KIOSK_INSTRUCTOR_PROFILE"]).get("result") or {}

for marker in (
    "MemberProfileCard",
    "k-profile-tabs",
    "k-profile-tab",
    "state.tab === 'profile'",
    "state.tab === 'progress' and isInstructorProfile()",
    "state.tab === 'household' and isInstructorProfile()",
    "state.tab === 'manage' and props.instructorMode and isInstructorProfile()",
    "props.instructorMode and isInstructorProfile()",
    "k-profile-tab--manage",
    "k-profile-private-note",
    "instructorKey",
    "instructorParams({",
    "workflow().onboarding.steps",
):
    if marker not in app_js:
        fail("profile tab marker missing from served app asset: %s" % marker)

for marker in (
    ".k-profile-private-note",
    ".k-profile-tabs",
    ".k-profile-tab--manage",
    ".k-onboarding-step",
    ".k-onboarding-actions",
):
    if marker not in kiosk_css:
        fail("profile/manage CSS marker missing from served stylesheet: %s" % marker)

safe_keys = {"member_id", "name", "image_url", "belt_rank", "belt_color", "program_name", "program_color", "attendance_state", "enrolled_sessions"}
private_keys = {"email", "phone", "member_number", "membership_state", "household", "guardians", "issues", "workflow_status", "programs", "appointments", "plan_name"}

for key in ("member_id", "name", "image_url", "belt_rank", "attendance_state", "enrolled_sessions"):
    if key not in public_profile:
        fail("public profile missing safe key %s" % key)
for payload_name, payload in (("public", public_profile), ("invalid-key", invalid_key_profile)):
    leaked = sorted(private_keys.intersection(payload))
    if leaked:
        fail("%s profile leaks instructor/private keys: %s" % (payload_name, ", ".join(leaked)))
    unexpected = sorted(set(payload) - safe_keys)
    if unexpected:
        fail("%s profile returned keys outside public contract: %s" % (payload_name, ", ".join(unexpected)))

for key in ("member_id", "name", "member_number", "membership_state", "workflow_status", "issues", "attendance_state", "programs", "guardians"):
    if key not in instructor_profile:
        fail("instructor profile missing %s" % key)

workflow = instructor_profile.get("workflow_status") or {}
onboarding = workflow.get("onboarding") or {}
if onboarding.get("available") is not True:
    fail("instructor profile onboarding payload is unavailable")
for key in ("available", "complete", "progress_pct", "steps", "missing_steps"):
    if key not in onboarding:
        fail("onboarding payload missing %s" % key)

expected_steps = {"trial_booked", "waiver_signed", "intro_completed", "membership_activated", "uniform_issued"}
legacy_steps = {"member_info", "household", "enrollment", "subscription", "portal_access"}
step_keys = {step.get("key") for step in onboarding.get("steps") or []}
if step_keys != expected_steps:
    fail("onboarding guidance steps mismatch: %s" % sorted(step_keys))
if step_keys.intersection(legacy_steps):
    fail("legacy onboarding steps are still exposed: %s" % sorted(step_keys.intersection(legacy_steps)))
if onboarding.get("progress_pct") != 40:
    fail("expected partial lifecycle onboarding progress 40, got %s" % onboarding.get("progress_pct"))
if onboarding.get("complete") is not False:
    fail("partial onboarding should not be complete")

print("ver-kiosk-profile-tabs: PASS")
PY
