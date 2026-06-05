#!/usr/bin/env bash
# Stage 5 gate — onboarding lifecycle steps + trial conversion (USABILITY_PASS.md change 8).
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; source "$HERE/common.sh"
stack_up || { echo "FAIL: web not up"; GATE_FAILED=1; finish; }

# 1. New columns exist.
for col in step_trial_booked step_waiver_signed step_intro_completed step_membership_activated step_uniform_issued; do
  assert_sql_gte "dojo_onboarding_record.$col exists" \
    "SELECT count(*) FROM information_schema.columns WHERE table_name='dojo_onboarding_record' AND column_name='$col'" 1
done
for col in converted_from_trial trial_converted_on; do
  assert_sql_gte "dojo_member.$col exists" \
    "SELECT count(*) FROM information_schema.columns WHERE table_name='dojo_member' AND column_name='$col'" 1
done

# 2. Behavior: defaults, derivation, conversion, kiosk step keys.
run_shell_test "new record defaults in_progress; waiver derivation works" "
import odoo.fields as f
m = env['dojo.member'].create({'name': 'UPass Gate Subject'})
rec = env['dojo.onboarding.record'].create({'member_id': m.id})
print('STATE0:', rec.state)
m.write({'waiver_signed_on': f.Datetime.now(), 'waiver_signed_by': 'QA Gate'})
rec._sync_derived_steps()
print('WAIVER:', rec.step_waiver_signed)
env.cr.rollback()
" "STATE0: in_progress"

run_shell_test "waiver derivation flips step_waiver_signed" "
import odoo.fields as f
m = env['dojo.member'].create({'name': 'UPass Gate Subject2'})
rec = env['dojo.onboarding.record'].create({'member_id': m.id})
m.write({'waiver_signed_on': f.Datetime.now(), 'waiver_signed_by': 'QA Gate'})
rec._sync_derived_steps()
print('WAIVER:', bool(rec.step_waiver_signed))
env.cr.rollback()
" "WAIVER: True"

run_shell_test "action_set_active from trial sets conversion fields" "
m = env['dojo.member'].create({'name': 'UPass Trial Subject'})
m.write({'membership_state': 'trial'})
m.action_set_active()
print('CONV:', bool(m.converted_from_trial), bool(m.trial_converted_on))
env.cr.rollback()
" "CONV: True True"

run_shell_test "kiosk complete_step accepts lifecycle key intro_completed" "
m = env['dojo.member'].create({'name': 'UPass Kiosk Subject'})
rec = env['dojo.onboarding.record'].create({'member_id': m.id})
svc = env['dojo.kiosk.service'].sudo()
res = svc.perform_onboarding_action(m.id, 'complete_step', step_key='intro_completed')
print('STEP:', bool(rec.step_intro_completed))
env.cr.rollback()
" "STEP: True"

# 3. The wizard no longer hard-codes completed.
if grep -n "'state': 'completed'" addons/dojo_onboarding/models/dojo_onboarding_wizard.py >/dev/null 2>&1; then
  echo "FAIL: onboarding wizard still writes state='completed' directly"; GATE_FAILED=1
else
  echo "PASS: onboarding wizard no longer hard-codes state='completed'"
fi
finish
