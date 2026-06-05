# Stage 5 Analysis — Onboarding lifecycle steps + trial conversion

**Gate script:** `scripts/usability_pass/verify/s5.sh`  
**Date:** 2026-06-05

## Gate Requirements (from s5.sh)

The gate mandates:

1. **New boolean fields on `dojo.onboarding.record`:**
   - `step_trial_booked`, `step_waiver_signed`, `step_intro_completed`, 
     `step_membership_activated`, `step_uniform_issued`
   - Legacy data-entry step fields (`step_member_info`, `step_household`, etc.) preserved for compatibility

2. **Method `_sync_derived_steps()` on `dojo.onboarding.record`:**
   - Derives `step_waiver_signed` from member's `waiver_signed_on`/`has_signed_waiver` fields
   - Derives `step_membership_activated` from `membership_state == 'active'`
   - Derives `step_trial_booked` from membership_state in ('trial','active') or CRM trial booking
   - Manual steps `step_intro_completed` and `step_uniform_issued` stay manual-only
   - State transitions: `completed` only when ALL five lifecycle steps true; otherwise `in_progress`
   - New records default to `in_progress`

3. **`progress_pct` and `missing_steps` compute over the NEW lifecycle step set** (not the legacy five)

4. **Wizard change (`dojo_onboarding/models/dojo_onboarding_wizard.py`):**
   - STOP writing `'state': 'completed'` directly (line 620)
   - Instead: create record as `in_progress`, call `_sync_derived_steps()`

5. **Trial conversion tracking on `dojo.member`:**
   - New fields: `converted_from_trial` (Boolean), `trial_converted_on` (Datetime)
   - `action_set_active()` sets both when previous state was `'trial'`

6. **Kiosk `perform_onboarding_action` updates:**
   - Must accept new step keys: `intro_completed`, `uniform_issued`, etc.
   - The `_ONBOARDING_STEP_FIELDS` dict (line 17-23 of `dojo_kiosk_service.py`) needs the new lifecycle keys
   - Workflow_status in kiosk reflects the lifecycle step list

7. **Migration for existing records:**
   - Sync derived steps from current member state
   - Grandfather `intro_completed`/`uniform_issued` = True for previously `completed` records
   - Recompute state

8. **Gate no longer allows wizard to hard-code `state='completed'`** (line 56-60 check)

## Current State

### `dojo.onboarding.record` (addons/dojo_onboarding/models/dojo_onboarding_record.py)
- Lines 30-35: Five legacy step boolean fields exist (`step_member_info`, etc.)
- Lines 37-54: `progress_pct` computed from those five legacy fields
- No `_sync_derived_steps()` method exists
- No `missing_steps` computed field visible in this excerpt

### `dojo.onboarding.wizard` (addons/dojo_onboarding/models/dojo_onboarding_wizard.py)
- Line 620: `'state': 'completed'` hard-coded in the wizard's `_create_student_member()` method
- Lines 613-622: The wizard creates an onboarding record with all legacy steps set based on what data was provided

### `dojo.member` (addons/dojo_core/models/member.py)
- Lines 56-68: `membership_state` field exists with values: lead, trial, active, paused, cancelled
- Lines 167-171: `action_set_active()` exists (line 170) but only sets `membership_state = "active"`
- No trial conversion fields exist
- No waiver fields visible in this excerpt (they come from `dojo_sign` module per USABILITY_PASS.md)

### `dojo.kiosk.service` (addons/dojo_kiosk/models/dojo_kiosk_service.py)
- Lines 17-23: `_ONBOARDING_STEP_FIELDS` dict maps the legacy five steps
- Line 1892+: `perform_onboarding_action` method exists
- Line 1926-1945: `_kiosk_complete_onboarding_step` uses the `_ONBOARDING_STEP_FIELDS` dict for validation and lookup
- Line 1934: Completion check uses `all()` over the dict values

## Gaps to Close

1. **`dojo.onboarding.record` model:**
   - Add five new boolean fields for lifecycle steps
   - Add `_sync_derived_steps()` method
   - Update `progress_pct` compute to use lifecycle steps (not legacy)
   - Add `missing_steps` computed field if not present
   - Update depends decorators

2. **`dojo.onboarding.wizard._create_student_member()`:**
   - Remove line 620: `'state': 'completed'`
   - Change to create record with `'state': 'in_progress'`
   - Call `_sync_derived_steps()` on the newly created record

3. **`dojo.member` model:**
   - Add `converted_from_trial` boolean field
   - Add `trial_converted_on` datetime field
   - Update `action_set_active()` to detect when previous state was 'trial' and set both fields

4. **`dojo.kiosk.service`:**
   - Update `_ONBOARDING_STEP_FIELDS` dict to include new lifecycle keys
   - Keep legacy keys or remove them? Gate tests `intro_completed` specifically, so at minimum add that one

5. **Migration/post-init hook:**
   - For existing `dojo.onboarding.record` records: call `_sync_derived_steps()`
   - For records with `state='completed'`: set `step_intro_completed=True` and `step_uniform_issued=True` (grandfathering)
   - Recompute state after sync

6. **Module dependencies:**
   - `dojo_onboarding` needs to import/check for `dojo_sign` fields (waiver_signed_on, has_signed_waiver)
   - Safe access pattern: check if fields exist before reading

## Files to Modify

1. `addons/dojo_onboarding/models/dojo_onboarding_record.py` — add fields, add method, update computes
2. `addons/dojo_onboarding/models/dojo_onboarding_wizard.py` — remove hard-coded completion
3. `addons/dojo_core/models/member.py` — add conversion fields, update action
4. `addons/dojo_kiosk/models/dojo_kiosk_service.py` — update step fields dict
5. `addons/dojo_onboarding/__init__.py` or `__manifest__.py` — add post-init hook for migration
6. `addons/dojo_onboarding/migrations/` or inline hook — migration logic

## Rollback Strategy

Each piece is additive (new fields, new method) except:
- Wizard line 620 removal — can revert with `git checkout -- addons/dojo_onboarding/models/dojo_onboarding_wizard.py`
- If migration breaks, disable the post-init hook and re-upgrade

## Risk Assessment

- **Low risk:** New field additions (non-breaking)
- **Medium risk:** Wizard state change (affects new onboarding flows only)
- **Medium risk:** Member action update (only triggers on trial→active, existing active members unaffected)
- **High risk:** Migration of existing records (must handle missing `dojo_sign` gracefully)

## Next: PLAN

Write the step-by-step implementation plan targeting the gate requirements.
