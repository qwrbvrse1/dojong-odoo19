# Stage 2 Plan — Kiosk Pre-PIN Gating, Instructor Key, Token Rotation, Action Log

## Success Criteria
`bash scripts/usability_pass/verify/s2.sh` passes all assertions.

## Step-by-Step Implementation

### STEP 1: Create action log model + views
**Files**: `addons/dojo_kiosk/models/dojo_kiosk_action_log.py`, `addons/dojo_kiosk/security/ir.model.access.csv`, `addons/dojo_kiosk/views/dojo_kiosk_action_log_views.xml`

**What**:
1. Create `dojo.kiosk.action.log` model with fields:
   - `config_id` (Many2one to dojo.kiosk.config, required, indexed)
   - `action` (Char, required, indexed) — e.g. "checkin", "attendance_mark"
   - `member_id` (Many2one to dojo.member, indexed)
   - `session_id` (Many2one to dojo.class.session, indexed)
   - `is_instructor_action` (Boolean, default False, indexed)
   - `summary` (Text)
   - `create_date` (auto)

2. Add ACL row: `access_dojo_kiosk_action_log_admin,dojo.kiosk.action.log admin,model_dojo_kiosk_action_log,group_dojo_admin,1,1,1,1`

3. Create tree/form views + menu under Kiosk configuration

**Rollback**: Delete model file, ACL row, view file; revert manifest.

---

### STEP 2: Add instructor key infrastructure to config model
**File**: `addons/dojo_kiosk/models/dojo_kiosk_config.py`

**What**:
1. Add fields:
   ```python
   instructor_key = fields.Char(string="Instructor Session Key", readonly=True, index=True, copy=False)
   instructor_key_expires_at = fields.Datetime(string="Key Expires At", readonly=True)
   ```

2. Add methods:
   ```python
   def _generate_instructor_key(self):
       """Generate a new 8h instructor key and store it."""
       self.ensure_one()
       import secrets
       from datetime import datetime, timedelta
       self.sudo().write({
           'instructor_key': secrets.token_urlsafe(32),
           'instructor_key_expires_at': fields.Datetime.now() + timedelta(hours=8),
       })
       return self.instructor_key

   def _validate_instructor_key(self, key):
       """Return True if key matches and hasn't expired."""
       self.ensure_one()
       if not key or not self.instructor_key:
           return False
       if key != self.instructor_key:
           return False
       if not self.instructor_key_expires_at:
           return False
       return fields.Datetime.now() < self.instructor_key_expires_at
   ```

**Rollback**: Remove fields, methods; revert file to prior state.

---

### STEP 3: Update PIN verification to return instructor_key
**File**: `addons/dojo_kiosk/models/dojo_kiosk_service.py`

**What**:
1. Update `verify_pin()` method (line ~1517):
   - After successful PIN verification (`config_record._verify_pin_value(pin)` returns True),
   - Call `instructor_key = config_record._generate_instructor_key()`
   - Return `{"success": True, "instructor_key": instructor_key}`

**Rollback**: Revert `verify_pin()` to original — remove key generation and return value change.

---

### STEP 4: Add gated profile method to service
**File**: `addons/dojo_kiosk/models/dojo_kiosk_service.py`

**What**:
1. Rename existing `get_member_profile()` → `_get_member_profile_full()`

2. Add new public method:
   ```python
   @api.model
   def get_member_profile(self, member_id, session_id=None, instructor_key=None):
       """Return minimal profile pre-PIN; full profile with valid instructor_key."""
       member = self.env["dojo.member"].browse(member_id)
       if not member.exists():
           return None
       
       # Validate instructor_key if provided
       if instructor_key:
           config = self.env["dojo.kiosk.config"].search([("active", "=", True)], limit=1)
           if config and config._validate_instructor_key(instructor_key):
               return self._get_member_profile_full(member, session_id=session_id)
       
       # Pre-PIN: minimal payload
       return self._member_profile_minimal(member, session_id=session_id)
   ```

3. Add `_member_profile_minimal()`:
   ```python
   def _member_profile_minimal(self, member, session_id=None):
       """Minimal member profile safe for pre-PIN kiosk search/display."""
       attendance_state = "pending"
       if session_id:
           enr = self.env["dojo.class.enrollment"].search([
               ("session_id", "=", session_id),
               ("member_id", "=", member.id),
               ("status", "=", "registered"),
           ], limit=1)
           if enr:
               log = self.env["dojo.attendance.log"].search([
                   ("session_id", "=", session_id),
                   ("member_id", "=", member.id),
               ], limit=1)
               attendance_state = log.status if log else enr.attendance_state

       enrolled_sessions = self.get_enrolled_sessions_today(member.id)
       
       return {
           "member_id": member.id,
           "name": member.name,
           "image_url": "/web/image/dojo.member/%d/image_128" % member.id,
           "belt_rank": member.current_rank_id.name if member.current_rank_id else "",
           "belt_color": member.current_rank_id.color if member.current_rank_id else "",
           "attendance_state": attendance_state,
           "enrolled_sessions": enrolled_sessions,
       }
   ```

4. Rename internal calls from `get_member_profile()` → `_get_member_profile_full()`

**Rollback**: Revert service file — remove minimal method, restore original `get_member_profile()` signature.

---

### STEP 5: Add instructor guard to controller
**File**: `addons/dojo_kiosk/controllers/kiosk_controller.py`

**What**:
1. Add helper after `_guard_token()` (line ~58):
   ```python
   def _guard_instructor(self, token, instructor_key, fail_return):
       """Validate token + instructor_key. Returns None on success; fail_return on failure."""
       guard = self._guard_token(token, fail_return)
       if guard is not None:
           return guard
       if not instructor_key:
           return {"success": False, "error": "instructor_auth_required"}
       try:
           svc = request.env["dojo.kiosk.service"].sudo()
           config = svc.validate_token(token)
           if not config._validate_instructor_key(instructor_key):
               return {"success": False, "error": "instructor_auth_required"}
           return None
       except AccessError:
           return {"success": False, "error": "instructor_auth_required"}
   ```

2. Update `/kiosk/member/profile` route (line ~203):
   - Add `instructor_key=None` to params
   - Pass `instructor_key` to `svc.get_member_profile()`

3. Update all `/kiosk/instructor/*` routes to use `_guard_instructor()`:
   - `/kiosk/instructor/attendance` (line ~266)
   - `/kiosk/instructor/roster/add` (line ~283)
   - `/kiosk/instructor/roster/bulk_add` (line ~304)
   - `/kiosk/instructor/roster/remove` (line ~338)
   - `/kiosk/instructor/session/close` (line ~355)
   - `/kiosk/instructor/session/reopen` (line ~368)
   - `/kiosk/instructor/session/delete` (line ~381)
   - `/kiosk/instructor/session/update` (line ~394)
   - `/kiosk/instructor/templates` (line ~407)
   - `/kiosk/instructor/session/create` (line ~419)
   - `/kiosk/instructor/update_photo` (line ~442)
   - `/kiosk/instructor/onboarding/action` (line ~459)
   - `/kiosk/instructor/belt_ranks` (line ~485)
   - `/kiosk/instructor/award_rank` (line ~498)
   - `/kiosk/instructor/send_message` (line ~515)
   - `/kiosk/instructor/next_rank` (line ~542)
   - `/kiosk/instructor/available_sessions` (line ~555)
   - Replace `_guard_token()` with `_guard_instructor()`, add `instructor_key=None` param

**Rollback**: Revert controller file — remove `_guard_instructor()`, restore `_guard_token()` in all routes.

---

### STEP 6: Add action logging to service mutations
**File**: `addons/dojo_kiosk/models/dojo_kiosk_service.py`

**What**:
1. Add helper method at top of service class:
   ```python
   def _log_action(self, action, member_id=None, session_id=None, is_instructor=False, summary=None):
       """Write a kiosk action log entry."""
       try:
           config = self.env["dojo.kiosk.config"].search([("active", "=", True)], limit=1)
           if config:
               self.env["dojo.kiosk.action.log"].sudo().create({
                   "config_id": config.id,
                   "action": action,
                   "member_id": member_id or False,
                   "session_id": session_id or False,
                   "is_instructor_action": is_instructor,
                   "summary": summary or "",
               })
       except Exception as e:
           import logging
           logging.getLogger(__name__).warning("Kiosk action log failed: %s", e)
   ```

2. Add logging calls to:
   - `checkin_member()` (line ~1070): after log creation, call `self._log_action("checkin", member_id, session_id, summary=f"Self check-in {status}")`
   - `checkout_member()` (line ~1569): after update, call `self._log_action("checkout", member_id, session_id)`
   - `mark_attendance()` (line ~1203): after log create/update, call `self._log_action("attendance_mark", member_id, session_id, is_instructor=True, summary=f"Marked {attendance_status}")`
   - `roster_add()` (line ~1262): after enrollment create, call `self._log_action("roster_add", member_id, session_id, is_instructor=True)`
   - `roster_remove()` (line ~1335): after enrollment cancel, call `self._log_action("roster_remove", member_id, session_id, is_instructor=True)`
   - `bulk_roster_add()` (line ~135): inside loop after each successful add, call `self._log_action("roster_add", member_id, session_id, is_instructor=True)`
   - `perform_onboarding_action()` (line ~1790): at end of each action branch, call `self._log_action("onboarding_action", member_id, is_instructor=True, summary=action)`

**Rollback**: Remove `_log_action()` method and all calls to it; revert service file.

---

### STEP 7: Enhance token rotation with chatter logging
**File**: `addons/dojo_kiosk/models/dojo_kiosk_config.py`

**What**:
1. Update `action_regenerate_token()` (line ~88) → rename to `action_rotate_token()`:
   ```python
   def action_rotate_token(self):
       """Rotate the kiosk token (invalidates open tablet sessions) and log to chatter."""
       for cfg in self:
           old_token = cfg.kiosk_token
           cfg.kiosk_token = secrets.token_urlsafe(32)
           cfg.message_post(
               body=f"Kiosk token rotated by {self.env.user.name}. Old token: {old_token[:8]}..."
           )
   ```

2. Keep existing `action_regenerate_token()` as alias:
   ```python
   def action_regenerate_token(self):
       """Legacy alias for action_rotate_token()."""
       return self.action_rotate_token()
   ```

**Rollback**: Revert method to original `action_regenerate_token()` without chatter.

---

### STEP 8: Update JavaScript SPA to handle instructor key
**File**: `addons/dojo_kiosk/static/src/kiosk_app.js`

**What**:
1. Add `instructorKey: null` to KioskApp state (search for `useState` calls)

2. Update `PinModal.props.onSuccess` callback:
   - Store the `instructor_key` returned by `/kiosk/auth/pin` in `state.instructorKey`

3. Update profile fetch calls to pass `instructor_key`:
   - Find all `jsonPost("/kiosk/member/profile", ...)` calls
   - Add `instructor_key: state.instructorKey` to params if in instructor mode

4. Update all instructor action calls to pass key:
   - Attendance, roster, session, photo, onboarding, belt rank, message routes
   - Add `instructor_key: state.instructorKey` to params

5. Pre-PIN profile modal: render minimal card (name, belt, photo only) until instructor key is set

**Rollback**: Revert JS file to original; restart web to clear cache.

---

### STEP 9: Update manifest and bump asset version
**Files**: `addons/dojo_kiosk/__manifest__.py`, `addons/dojo_kiosk/controllers/kiosk_controller.py`

**What**:
1. Manifest: Add `'data': ['security/ir.model.access.csv', 'views/dojo_kiosk_action_log_views.xml', ...]` (if not already in list)
2. Controller: Increment asset version query param (line 85, 100) — change `?v=...` to trigger browser reload

**Rollback**: Revert manifest data list; revert asset version bump.

---

### STEP 10: Module upgrade + restart + gate
**Commands**:
```bash
docker compose run --rm -T --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 -u dojo_kiosk --stop-after-init
docker compose restart web
bash scripts/usability_pass/verify/s2.sh
```

**What**: Upgrade module, restart web (clears JS cache), run gate.

**Rollback**: If gate fails, revert all changes in reverse order (step 9 → step 1), re-upgrade, restart.

---

### STEP 11: Commit
**Command**: `git add -A && git commit -m "upass S2: kiosk pre-PIN gating + instructor key + token rotation + action log"`

**What**: Commit only if gate passes.

---

## Notes
- Step 1 (action log model) can be done first — it's independent
- Steps 2-5 must be sequential (config → service → controller)
- Step 6 (logging) depends on step 1
- Step 8 (JS) can be done after step 5
- Gate line 62 calls `svc.mark_attendance(s.id, m.id, 'present')` — ensure service method signature matches

**Plan complete.** Ready to execute.
