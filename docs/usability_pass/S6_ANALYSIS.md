# Stage 6 Analysis — Parent portal checklist + FREEZE

**Gate script:** `scripts/usability_pass/verify/s6.sh`  
**Date:** 2026-06-05

## Gate Requirements (from s6.sh)

The gate mandates:

1. **Cold restart and prior gate re-runs** (lines 6-45):
   - `docker compose down && up` — clean slate test
   - Re-run gates S1 through S5 against the cold-started stack
   - All must pass

2. **Parent onboarding checklist endpoint** (lines 12-21):
   - Route: `GET /my/dojo/onboarding/summary`
   - Auth: `auth='user'` (http route)
   - Returns JSON with structure containing:
     - `"steps"` key (array of step objects)
     - `"progress_pct"` key (integer)
   - Parent sees ALL household children
   - Student sees ONLY their own record

3. **Student access returns 200 + valid JSON** (lines 24-29):
   - Student login (demo1@demo.com) calling the endpoint must return HTTP 200
   - Response must be valid JSON (test writes to `/tmp/upass_student_summary.json`)

4. **Checklist visible on portal home** (lines 32-38):
   - `GET /my/dojo` rendered HTML must contain "onboarding" text (case-insensitive)

5. **Runbook exists and documents key items** (lines 48-56):
   - File `USABILITY_PASS_RUNBOOK.md` exists in repo root
   - Contains text "instructor_key" (case-insensitive)
   - Contains text "rotate" (case-insensitive)

## Current State

### Portal controller structure (addons/dojo_members_portal/controllers/main.py)

- Lines 49-68: `_get_household_member_ids()` — returns member IDs scoped by role:
  - Students: only their own member ID
  - Guardians: all household member IDs
- Lines 85-106: `_resolve_view_member_ids(member_id=None)` — validates household scope for JSON requests
- Lines 151-213: `/my/dojo` route — renders the unified portal home with tabs
  - Returns template `dojo_members_portal.portal_dojo_home`
  - Already passes belt context, attendance counts, household members JSON
- Lines 231-280: Example JSON endpoint pattern (`/my/dojo/json/belt`)
  - Uses `_resolve_view_member_ids()` for scoping
  - Returns JSON via `request.make_response(json.dumps(...))`

### Onboarding record structure (from S5, addons/dojo_onboarding/models/dojo_onboarding_record.py)

- Lines 37-42: Five lifecycle step boolean fields exist:
  - `step_trial_booked`, `step_waiver_signed`, `step_intro_completed`, `step_membership_activated`, `step_uniform_issued`
- Lines 44-48: `progress_pct` computed field (0-100 integer)
- Lines 50-54: `missing_steps` computed field (comma-separated labels)
- Lines 56-67: `_compute_progress()` — calculates progress_pct from lifecycle steps
- Lines 69-83: `_compute_missing_steps()` — builds missing_steps string
- Line 11: `member_id` Many2one field links to `dojo.member`

### Step label mapping (from S5 analysis)

The S5 implementation uses these labels:
- `step_trial_booked` → "Trial Booked"
- `step_waiver_signed` → "Waiver Signed"
- `step_intro_completed` → "Intro Completed"
- `step_membership_activated` → "Membership Activated"
- `step_uniform_issued` → "Uniform Issued"

## Implementation Requirements

### 1. New JSON endpoint: `/my/dojo/onboarding/summary`

**Spec:**
- Route decorator: `@http.route('/my/dojo/onboarding/summary', type='http', auth='user')`
- Returns JSON (not HTML)
- Household scoping via `_get_household_member_ids()` (existing helper)
- Per-child structure:
  ```json
  {
    "children": [
      {
        "member_id": 123,
        "name": "Child Name",
        "progress_pct": 60,
        "steps": [
          {"key": "step_trial_booked", "label": "Trial Booked", "complete": true},
          {"key": "step_waiver_signed", "label": "Waiver Signed", "complete": true},
          {"key": "step_intro_completed", "label": "Intro Completed", "complete": true},
          {"key": "step_membership_activated", "label": "Membership Activated", "complete": false},
          {"key": "step_uniform_issued", "label": "Uniform Issued", "complete": false}
        ],
        "missing_steps": "Membership Activated, Uniform Issued"
      }
    ]
  }
  ```
- Students see only their own record → `children` array has one item

**Implementation pattern:**
- Use `_get_household_member_ids()` to get scoped member IDs
- Query `dojo.onboarding.record` with `member_id in household_member_ids` (sudo)
- Build step array from the five lifecycle step fields
- Use the existing step label mapping from `_compute_missing_steps()`
- Return `request.make_response(json.dumps(...), headers=[('Content-Type', 'application/json')])`

### 2. Portal home template update

**Target template:** `addons/dojo_members_portal/templates/portal_dojo_home.xml`

**Requirement:** Render an onboarding checklist block visible on the home tab

**Approach:**
- Add a new section to the existing `/my/dojo` template
- Conditionally render for guardians (parents) or students
- Use the same household scoping logic as the JSON endpoint
- Display per-child checklist with progress indicator
- Link to the JSON endpoint for dynamic updates (optional) or render server-side
- Must contain the word "onboarding" (case-insensitive) — gate checks this

**Server-side vs client-side:**
- Server-side: Pass onboarding data via template context in `portal_dojo_home()` controller
- Client-side: OWL component fetching `/my/dojo/onboarding/summary`
- Gate only checks that HTML contains "onboarding" — server-side is simpler

### 3. USABILITY_PASS_RUNBOOK.md

**Location:** Repo root (`/opt/worktrees/dojong-odoo19/core-dojo-realignment/USABILITY_PASS_RUNBOOK.md`)

**Content requirements (from gate + pass context):**
- Summary: what changed per stage (S1-S6) — one line each
- New endpoint names + params:
  - `instructor_key` param (S2 kiosk changes)
  - `mark_remaining_absent` bulk action (S4)
  - `/my/dojo/onboarding/summary` endpoint (S6)
- How to rotate a kiosk token (S2)
- Integration accounts granted groups (S1)
- Probe account details (S1: `probe@qa.local` / `Probe-2026!`)
- Deliberately deferred items (if any)

**Structure suggestion:**
```markdown
# Usability Pass Runbook

## Summary

S1: ACL closure (removed base.group_user full access) + parent ACL tightening + probe account seeded
S2: Pre-PIN kiosk data gating + instructor_key validation + token rotation action + kiosk action log
S3: Backend surname search view + instructor dashboard stub removal
S4: Session bulk-close action (mark_remaining_absent) + auto-close cron
S5: Onboarding lifecycle steps + trial conversion tracking
S6: Parent portal onboarding checklist endpoint + runbook + cold-restart verification

## New Endpoints & Parameters

### /my/dojo/onboarding/summary (S6)
- Returns household-scoped onboarding progress as JSON
- Students see only their own record
- Parents see all children in household

### instructor_key parameter (S2)
- Added to kiosk mutation endpoints for instructor authorization
- Validates against `dojo.kiosk.config.instructor_key` field
- Required for: session actions, onboarding step completion

### mark_remaining_absent bulk action (S4)
- Closes open session + marks all un-checked-in enrollments as absent
- Available on dojo.class.session list view

## Kiosk Token Rotation (S2)

New button action on `dojo.kiosk.config` form view:
1. Navigate to Settings → Kiosk Configuration
2. Click "Rotate Auth Token"
3. Confirmation dialog appears
4. New token generated (uuid4)
5. Update kiosk app .env with new VITE_KIOSK_AUTH_TOKEN value
6. Rebuild + redeploy kiosk SPA

## Integration Accounts (S1)

Service accounts granted explicit dojo groups post-ACL closure:
- (List any integration accounts that were granted group_dojo_admin or other groups)

## Probe Account (S1)

QA account for ACL verification:
- Login: probe@qa.local
- Password: Probe-2026!
- Groups: Internal User only (NO dojo groups)
- Purpose: Verify ACL closure — must NOT have access to dojo.* models

## Deferred Items

(List any deliberately skipped or out-of-scope items)
```

## Files to Create or Modify

1. `addons/dojo_members_portal/controllers/main.py` — add `/my/dojo/onboarding/summary` route
2. `addons/dojo_members_portal/controllers/main.py` — update `portal_dojo_home()` to pass onboarding context (if server-side rendering)
3. `addons/dojo_members_portal/templates/portal_dojo_home.xml` — add onboarding checklist block
4. `USABILITY_PASS_RUNBOOK.md` — create in repo root

## Rollback Strategy

- Controller changes: `git checkout -- addons/dojo_members_portal/controllers/main.py`
- Template changes: `git checkout -- addons/dojo_members_portal/templates/portal_dojo_home.xml`
- Runbook: `rm USABILITY_PASS_RUNBOOK.md`

## Risk Assessment

- **Low risk:** New JSON endpoint (additive, read-only, uses existing helpers)
- **Low risk:** Template addition (additive, no existing functionality changed)
- **Low risk:** Runbook creation (documentation only)
- **Medium risk:** Cold restart + full gate re-run (exposes any warm-state dependencies)

The cold restart is the critical test — if any prior stage only passed due to:
- Uncommitted manual DB tweaks
- Stale module registry (module not upgraded)
- Transient container state

...it will fail here and must be fixed in the source (module upgrade scripts, data files, post-init hooks).

## Next: PLAN

Write the step-by-step implementation plan targeting the gate requirements.
