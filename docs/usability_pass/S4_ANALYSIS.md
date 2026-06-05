# Stage 4 Analysis — Session bulk-close + auto-close cron

## Gate Requirements (from `scripts/usability_pass/verify/s4.sh`)

1. **Cron record exists**: Active `ir.cron` with name ILIKE '%auto-close%'
2. **Cron behavior**: Method `_cron_auto_close_sessions()` on `dojo.class.session` that:
   - Finds sessions with `state='open'` and `end_datetime` > GRACE minutes in the past
   - GRACE from `ir.config_parameter` key `dojo_core.session_auto_close_grace_minutes` (default 60)
   - Resolves every `pending` enrollment's attendance to `absent`
   - Sets session to `done`
3. **Gate test**: Creates throwaway past session with minimal fields (`template_id`, `start_datetime`, `end_datetime`, `state='open'`), creates pending enrollment, runs cron, asserts session is `done` and enrollment is `absent`
4. **Kiosk endpoint**: `/kiosk/instructor/session/close` accepts new param `mark_remaining_absent` (boolean). When true, pending attendees are marked absent and close proceeds. Requires `instructor_key`.
5. **Config parameter**: `dojo_core.session_auto_close_grace_minutes` must exist in `ir_config_parameter`

## Current State

### Session Model (`addons/dojo_core/models/class_session.py`)
- Session `write()` already auto-creates absent logs for pending enrollments when state → done (lines 206-236)
- This logic creates `dojo.attendance.log` records and syncs `enrollment.attendance_state`
- The logic is already present and working — we can reuse it via `action_complete()` or direct write

### Enrollment Model (`addons/dojo_core/models/class_enrollment.py`)
- `attendance_state` field exists with values: pending, present, absent, excused
- Enrollments link to attendance logs via `dojo.attendance.log.enrollment_id`

### Kiosk Service (`addons/dojo_kiosk/models/dojo_kiosk_service.py`)
- `close_session()` at line 1416 currently blocks if pending enrollments exist (returns `"error": "pending_attendance"`)
- `mark_attendance()` at line 1264 creates/updates attendance logs and syncs enrollment state
- The attendance resolution pattern is: create log → sync enrollment.attendance_state

### Kiosk Controller (`addons/dojo_kiosk/controllers/kiosk_controller.py`)
- `/kiosk/instructor/session/close` at line 368 routes to `close_session()` with instructor auth

## Implementation Plan

### 1. Session cron method (`dojo.class.session._cron_auto_close_sessions()`)
- Location: `addons/dojo_core/models/class_session.py`
- Find sessions: `state='open'` AND `end_datetime < (now - GRACE minutes)`
- Get GRACE from `self.env['ir.config_parameter'].sudo().get_param('dojo_core.session_auto_close_grace_minutes', '60')`
- For each session:
  - Find pending enrollments: `enrollment_ids.filtered(lambda e: e.status == 'registered' and e.attendance_state == 'pending')`
  - For each: call existing `mark_attendance()` logic OR create log + sync enrollment directly
  - Set session state to `done` (triggers existing write() auto-resolution as backup)

**Key decision**: The session's `write()` method (lines 206-236) already handles this when state → done. We can:
- Option A: Just call `session.write({'state': 'done'})` and let the existing logic run
- Option B: Manually resolve pending → absent first, then set done
- **Choice**: Option A is simpler and reuses battle-tested code. The `write()` method already does exactly what we need.

### 2. Config parameter
- Location: `addons/dojo_core/data/` (new file: `dojo_config_parameters.xml`)
- Add `ir.config_parameter` record with key `dojo_core.session_auto_close_grace_minutes` and value `60`
- Add to `__manifest__.py` data list

### 3. Cron record
- Location: `addons/dojo_core/data/` (new file: `dojo_core_cron.xml`)
- Create `ir.cron` record:
  - `name`: "Dojo: Auto-close ended sessions"
  - `model_id`: ref to `dojo.class.session`
  - `state`: 'code'
  - `code`: `model._cron_auto_close_sessions()`
  - `interval_number`: 1
  - `interval_type`: 'hours'
  - `active`: True
- Add to `__manifest__.py` data list AFTER models are loaded

### 4. Kiosk `close_session()` modification
- Location: `addons/dojo_kiosk/models/dojo_kiosk_service.py` line 1416
- Accept new param `mark_remaining_absent=False`
- When true AND pending enrollments exist:
  - For each pending enrollment: call `self.mark_attendance(session_id, member_id, 'absent')`
  - OR: directly create logs and sync state (simpler, no service call overhead)
  - Then set session to done
- When false: keep existing behavior (return error if pending)

### 5. Kiosk controller modification
- Location: `addons/dojo_kiosk/controllers/kiosk_controller.py` line 371
- Extract `mark_remaining_absent` from `**kw`
- Pass to `svc.close_session(session_id, mark_remaining_absent=mark_remaining_absent)`

### 6. Gate test requirements
- Gate creates sessions with ONLY: `template_id`, `start_datetime`, `end_datetime`, `state='open'`
- Current `class_session.py` has NO `create()` override, so defaults should work
- BUT: check if any required fields are missing defaults:
  - `name`: computed field, OK
  - `template_id`: required=True, gate provides
  - `company_id`: has default, OK
  - `instructor_profile_id`: not required, OK
  - `capacity`: has default=20, OK
  - `state`: has default='draft', gate overrides to 'open', OK
- **Gate can create sessions directly** — no issues

### 7. Module upgrade order
- `dojo_core` contains sessions, enrollments, and will contain the cron/config
- Upgrade `dojo_core` first
- Then `dojo_kiosk` (depends on dojo_core already)
- Restart web after both upgrades

## Rollback Plan

If any step fails:
1. Cron/config XML: `git checkout -- addons/dojo_core/data/dojo_*`
2. Session method: `git checkout -- addons/dojo_core/models/class_session.py`
3. Kiosk service: `git checkout -- addons/dojo_kiosk/models/dojo_kiosk_service.py`
4. Kiosk controller: `git checkout -- addons/dojo_kiosk/controllers/kiosk_controller.py`
5. Manifest: `git checkout -- addons/dojo_core/__manifest__.py`
6. Re-upgrade modules and restart

## Files to Touch

1. `addons/dojo_core/models/class_session.py` — add `_cron_auto_close_sessions()` method
2. `addons/dojo_core/data/dojo_config_parameters.xml` — NEW, config parameter
3. `addons/dojo_core/data/dojo_core_cron.xml` — NEW, cron record
4. `addons/dojo_core/__manifest__.py` — add new data files
5. `addons/dojo_kiosk/models/dojo_kiosk_service.py` — modify `close_session()` signature and logic
6. `addons/dojo_kiosk/controllers/kiosk_controller.py` — extract and pass `mark_remaining_absent`

## Risks

1. **Data file ordering**: Cron XML must load AFTER models. Put it last in manifest data list.
2. **Module dependency**: `dojo_kiosk` already depends on `dojo_core`, so upgrade order is safe.
3. **Existing write() logic**: Session `write()` auto-creates absent logs. Cron should leverage this, not duplicate.
4. **Grace period edge case**: If GRACE=0, sessions close immediately at end_datetime. Acceptable per requirement (default 60 is reasonable).
5. **Kiosk SPA**: No changes needed to SPA — new param is optional, existing flow unchanged.

## Notes

- The gate script uses `env['dojo.class.session']._cron_auto_close_sessions()` — confirms it's a model method, not instance
- The gate expects both `CLOSED: True` and `ABSENT: True` assertions to pass
- Instructor auth is already enforced by `_guard_instructor()` in controller — just need to accept the param
- The existing `write()` logic at lines 206-236 is exactly what the cron needs — don't reinvent it
