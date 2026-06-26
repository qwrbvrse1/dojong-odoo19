#!/usr/bin/env bash
# Gate: INC-04 live member profile API, onboarding semantics, and auth boundary.
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

public_profile=$(kiosk_json_rpc "/kiosk/member/profile" "{\"token\":\"${TOKEN}\",\"member_id\":${MID},\"session_id\":${SID}}")
invalid_key_profile=$(kiosk_json_rpc "/kiosk/member/profile" "{\"token\":\"${TOKEN}\",\"member_id\":${MID},\"session_id\":${SID},\"instructor_key\":\"invalid-key\"}")
instructor_profile=$(kiosk_json_rpc "/kiosk/member/profile" "{\"token\":\"${TOKEN}\",\"member_id\":${MID},\"session_id\":${SID},\"instructor_key\":\"${KEY}\"}")
unauth_action=$(kiosk_json_rpc "/kiosk/api/onboarding/complete_step" "{\"token\":\"${TOKEN}\",\"member_id\":${MID},\"step_key\":\"intro_completed\"}")
complete_action=$(kiosk_json_rpc "/kiosk/api/onboarding/complete_step" "{\"token\":\"${TOKEN}\",\"member_id\":${MID},\"step_key\":\"intro_completed\",\"instructor_key\":\"${KEY}\"}")
refreshed_profile=$(kiosk_json_rpc "/kiosk/member/profile" "{\"token\":\"${TOKEN}\",\"member_id\":${MID},\"session_id\":${SID},\"instructor_key\":\"${KEY}\"}")

KIOSK_PUBLIC_PROFILE="$public_profile" \
KIOSK_INVALID_KEY_PROFILE="$invalid_key_profile" \
KIOSK_INSTRUCTOR_PROFILE="$instructor_profile" \
KIOSK_UNAUTH_ACTION="$unauth_action" \
KIOSK_COMPLETE_ACTION="$complete_action" \
KIOSK_REFRESHED_PROFILE="$refreshed_profile" \
python3 - <<'PY'
import json
import os
import sys

def fail(message):
    print(message, file=sys.stderr)
    sys.exit(1)

def result(name):
    payload = json.loads(os.environ[name])
    return payload.get("result")

public_profile = result("KIOSK_PUBLIC_PROFILE") or {}
invalid_key_profile = result("KIOSK_INVALID_KEY_PROFILE") or {}
instructor_profile = result("KIOSK_INSTRUCTOR_PROFILE") or {}
unauth_action = result("KIOSK_UNAUTH_ACTION") or {}
complete_action = result("KIOSK_COMPLETE_ACTION") or {}
refreshed_profile = result("KIOSK_REFRESHED_PROFILE") or {}

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

for key in ("member_id", "name", "member_number", "membership_state", "workflow_status", "issues", "attendance_state"):
    if key not in instructor_profile:
        fail("instructor profile missing %s" % key)

workflow = instructor_profile.get("workflow_status") or {}
onboarding = workflow.get("onboarding") or {}
expected_steps = {"trial_booked", "waiver_signed", "intro_completed", "membership_activated", "uniform_issued"}
legacy_steps = {"member_info", "household", "enrollment", "subscription", "portal_access"}
step_keys = {step.get("key") for step in onboarding.get("steps") or []}
if onboarding.get("available") is not True:
    fail("instructor onboarding payload unavailable: %s" % onboarding)
if step_keys != expected_steps:
    fail("onboarding steps should be lifecycle guidance keys only; got %s" % sorted(step_keys))
if step_keys.intersection(legacy_steps):
    fail("onboarding steps still expose legacy data-entry keys: %s" % sorted(step_keys.intersection(legacy_steps)))
if onboarding.get("progress_pct") != 40:
    fail("expected seeded lifecycle onboarding progress 40, got %s" % onboarding.get("progress_pct"))
if onboarding.get("complete") is not False:
    fail("partial lifecycle onboarding should not be complete")
if "Intro Session Completed" not in (onboarding.get("missing_steps") or []):
    fail("missing lifecycle step label not present before action")

if unauth_action.get("success") is not False or unauth_action.get("error") != "instructor_auth_required":
    fail("complete_step without instructor key must be rejected: %s" % unauth_action)
if complete_action.get("success") is not True:
    fail("complete_step with instructor key failed: %s" % complete_action)

refreshed_onboarding = ((refreshed_profile.get("workflow_status") or {}).get("onboarding") or {})
refreshed_steps = {step.get("key"): step for step in refreshed_onboarding.get("steps") or []}
if not refreshed_steps.get("intro_completed", {}).get("complete"):
    fail("intro_completed was not marked complete after authenticated action")
if refreshed_onboarding.get("progress_pct") != 60:
    fail("expected lifecycle onboarding progress 60 after action, got %s" % refreshed_onboarding.get("progress_pct"))

print("ver04-member-profile: PASS")
PY
