# Stage 2 Analysis — Kiosk Pre-PIN Gating, Instructor Key, Token Rotation, Action Log

**Goal**: Pass `scripts/usability_pass/verify/s2.sh`.

## Gate Requirements (from s2.sh)

### 1. Pre-PIN profile is minimal (lines 14-25)
- `/kiosk/member/profile` WITHOUT `instructor_key` param must:
  - **Exclude**: `date_of_birth`, `email`, `phone`, `household`, `guardians`, `credit_balance`, `billing_failure_count`, `workflow_status`
  - **Include**: `name`, `member_id`, `image_url`, `belt_rank`, `belt_color`, `attendance_state`, and enrolled sessions for today

### 2. PIN unlock returns instructor_key (lines 27-31)
- `/kiosk/auth/pin` with valid PIN (`123456`) must return `instructor_key` in response
- Key must be:
  - Random per unlock
  - Stored server-side (field or related model on `dojo.kiosk.config`)
  - Expire ≤ 8 hours

### 3. Full profile with instructor_key (lines 33-37)
- `/kiosk/member/profile` WITH `instructor_key` param must return full payload including `workflow_status`

### 4. Instructor routes require key (lines 39-43)
- `/kiosk/instructor/*` routes must reject missing/invalid `instructor_key`
- Error response must contain string `"instructor_auth_required"`

### 5. Self-check-in remains keyless (implicit)
- `/kiosk/checkin` must NOT require `instructor_key`

### 6. Token rotation (lines 45-52)
- `action_rotate_token()` on `dojo.kiosk.config` must:
  - Regenerate `kiosk_token`
  - Log to chatter
  - Be callable via shell test

### 7. Action log (lines 54-68)
- New model `dojo.kiosk.action.log` with fields:
  - `config_id`, `action`, `member_id`, `session_id`, `is_instructor_action`, `summary`, `create_date`
- Every kiosk mutation writes a row:
  - checkin, checkout, attendance mark, roster add/remove, onboarding action
- Gate calls `env['dojo.kiosk.service'].sudo().mark_attendance(session_id, member_id, 'present')` and expects a log row
- Admin-only menu/view

## Current Implementation Review

### Controller (`kiosk_controller.py`)
- Token validation: `_guard_token()` validates `kiosk_token` (line 43)
- No instructor_key validation yet
- All routes use `_guard_token()` pattern

### Service (`dojo_kiosk_service.py`)
- `get_member_profile()` (line 631): Returns full `_member_profile_dict()` unconditionally
- `_member_profile_dict()` (line 638): Includes ALL sensitive fields
- `mark_attendance()` (line 1203): No action logging

### Config (`dojo_kiosk_config.py`)
- `kiosk_token` field exists (line 38)
- No `instructor_key` field/mechanism yet
- `action_regenerate_token()` exists (line 88) but doesn't log to chatter

### JavaScript (`kiosk_app.js`)
- Lines 203-212: `/kiosk/member/profile` called without instructor_key
- No state for storing instructor_key after PIN unlock
- Pre-PIN profile modal renders from full payload (landmine 4)

## Implementation Plan

### Phase 1: Instructor Key Infrastructure
1. **Add instructor key storage to `dojo.kiosk.config`**:
   - `instructor_key` field (char, indexed)
   - `instructor_key_expires_at` field (datetime)
   - `_generate_instructor_key()` method
   - `_validate_instructor_key(key)` method (checks existence + expiry ≤ 8h)

2. **Update PIN verification**:
   - `verify_pin()` in service generates and returns `instructor_key` on success
   - Store key + expiry on config record

### Phase 2: Controller Gating
1. **Add `_guard_instructor()` helper** in controller:
   - Validates both `token` and `instructor_key`
   - Returns `{"success": False, "error": "instructor_auth_required"}` on failure

2. **Update privileged routes** to use `_guard_instructor()`:
   - `/kiosk/instructor/attendance`
   - `/kiosk/instructor/roster/*`
   - `/kiosk/instructor/session/*`
   - `/kiosk/instructor/update_photo`
   - `/kiosk/instructor/onboarding/action`
   - `/kiosk/instructor/belt_ranks`
   - `/kiosk/instructor/award_rank`
   - `/kiosk/instructor/send_message`
   - `/kiosk/instructor/next_rank`
   - `/kiosk/instructor/available_sessions`
   - `/kiosk/instructor/templates`

3. **Update `/kiosk/member/profile`** endpoint:
   - Accept optional `instructor_key` param
   - Call new service method `get_member_profile_gated(member_id, session_id, instructor_key)`
   - Service returns minimal payload if no key; full if valid key

### Phase 3: Service — Minimal Profile
1. **Add `get_member_profile_gated()`**:
   - If `instructor_key` is None or invalid: return minimal dict
   - If valid: return full `_member_profile_dict()`

2. **Add `_member_profile_minimal()`**:
   - Return only: `member_id`, `name`, `image_url`, `belt_rank`, `belt_color`, `attendance_state`
   - Include today's enrolled sessions (call `get_enrolled_sessions_today()`)
   - Exclude: DOB, email, phone, household, guardians, credit_balance, billing_failure_count, workflow_status

### Phase 4: Token Rotation Enhancement
1. **Update `action_rotate_token()`** on `dojo.kiosk.config`:
   - Add chatter message: "Kiosk token rotated by [user]"
   - Already regenerates token (line 91)

2. **Add UI button** (if needed — gate only checks shell callable)

### Phase 5: Action Log Model
1. **Create `dojo.kiosk.action.log` model**:
   ```python
   config_id = Many2one('dojo.kiosk.config', required=True, index=True)
   action = Char(required=True, index=True)
   member_id = Many2one('dojo.member', index=True)
   session_id = Many2one('dojo.class.session', index=True)
   is_instructor_action = Boolean(default=False, index=True)
   summary = Text()
   create_date = auto
   ```

2. **Add logging calls** to service methods:
   - `checkin_member()`: log "checkin"
   - `checkout_member()`: log "checkout"
   - `mark_attendance()`: log "attendance_mark"
   - `roster_add()`: log "roster_add"
   - `roster_remove()`: log "roster_remove"
   - `bulk_roster_add()`: log per member
   - `perform_onboarding_action()`: log "onboarding_action"

3. **Add security + views**:
   - ACL: admin RWX, others none
   - Tree view with filters (action, date, member, session, is_instructor_action)
   - Menu under Kiosk

4. **Add `mark_attendance` alias** if needed:
   - Gate calls `svc.mark_attendance(session_id, member_id, 'present')`
   - Current service has this method (line 1203)
   - Ensure it writes to action log

### Phase 6: JavaScript Updates (Landmine 4)
1. **Add instructor key state** to KioskApp:
   - `state.instructorKey = null`
   - Set after PIN unlock

2. **Update profile fetch**:
   - Pre-PIN: call `/kiosk/member/profile` without key → render minimal card
   - Post-PIN: include `instructor_key` in params → re-fetch full profile

3. **Pass key to all instructor calls**:
   - Attendance, roster, session management, photo upload, etc.

4. **Bump static asset version** in controller (line 85, 100)

## Rollback Plan
- If instructor key logic breaks PIN flow: revert controller + service changes, keep action log
- If minimal profile breaks SPA: revert profile gating, keep key infrastructure
- If action log insert fails: wrap in try/except, log error but don't block operations

## Verification Steps
1. Upgrade `dojo_kiosk` module
2. Restart web container (SPA JS must reload)
3. Run gate: `bash scripts/usability_pass/verify/s2.sh`
4. Check:
   - Pre-PIN profile minimal (no email/phone/household)
   - PIN returns instructor_key
   - Full profile with key includes workflow_status
   - Instructor route without key returns `instructor_auth_required`
   - Token rotation callable and logs
   - Action log rows created on mutations

## File Manifest
- `addons/dojo_kiosk/models/dojo_kiosk_config.py` — instructor key fields/methods, token rotation logging
- `addons/dojo_kiosk/models/dojo_kiosk_service.py` — gated profile, minimal profile, action logging
- `addons/dojo_kiosk/models/dojo_kiosk_action_log.py` — NEW model
- `addons/dojo_kiosk/controllers/kiosk_controller.py` — instructor guard, profile gating
- `addons/dojo_kiosk/static/src/kiosk_app.js` — instructor key state, profile re-fetch
- `addons/dojo_kiosk/security/ir.model.access.csv` — action log ACL
- `addons/dojo_kiosk/views/dojo_kiosk_action_log_views.xml` — tree/form/menu
- `addons/dojo_kiosk/__manifest__.py` — add action log data file

**Analysis complete.** Ready to write S2_PLAN.md.
