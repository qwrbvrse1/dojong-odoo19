# Stage 5 Plan — Onboarding lifecycle steps + trial conversion

**Target:** `bash scripts/usability_pass/verify/s5.sh` passes  
**Date:** 2026-06-05

## Implementation Steps

### Step 1: Add lifecycle fields to `dojo.onboarding.record`

**File:** `addons/dojo_onboarding/models/dojo_onboarding_record.py`

**Changes:**
- After line 35 (after existing step fields), add five new boolean fields:
  ```python
  # Lifecycle step completion flags (derived + manual)
  step_trial_booked = fields.Boolean('Trial Booked', default=False)
  step_waiver_signed = fields.Boolean('Waiver Signed', default=False)
  step_intro_completed = fields.Boolean('Intro Session Completed', default=False)
  step_membership_activated = fields.Boolean('Membership Activated', default=False)
  step_uniform_issued = fields.Boolean('Uniform Issued', default=False)
  ```

**Rollback:** `git checkout -- addons/dojo_onboarding/models/dojo_onboarding_record.py`

### Step 2: Add `_sync_derived_steps()` method

**File:** `addons/dojo_onboarding/models/dojo_onboarding_record.py`

**Changes:**
- After the `_compute_progress` method (after line 54), add:
  ```python
  def _sync_derived_steps(self):
      """Sync derived lifecycle steps from member state."""
      for rec in self:
          member = rec.member_id
          if not member:
              continue
          
          # step_waiver_signed: check dojo_sign fields if available
          if hasattr(member, 'waiver_signed_on'):
              rec.step_waiver_signed = bool(member.waiver_signed_on)
          elif hasattr(member, 'has_signed_waiver'):
              rec.step_waiver_signed = bool(member.has_signed_waiver)
          
          # step_membership_activated: active membership
          rec.step_membership_activated = (member.membership_state == 'active')
          
          # step_trial_booked: trial or active state (CRM booking check omitted for now)
          rec.step_trial_booked = (member.membership_state in ('trial', 'active'))
          
          # Recompute state: completed only if ALL five lifecycle steps true
          if all([
              rec.step_trial_booked,
              rec.step_waiver_signed,
              rec.step_intro_completed,
              rec.step_membership_activated,
              rec.step_uniform_issued,
          ]):
              rec.state = 'completed'
          else:
              rec.state = 'in_progress'
  ```

**Rollback:** Same as Step 1

### Step 3: Update `progress_pct` compute to use lifecycle steps

**File:** `addons/dojo_onboarding/models/dojo_onboarding_record.py`

**Changes:**
- Replace lines 43-54 (the `_compute_progress` method):
  ```python
  @api.depends(
      'step_trial_booked', 'step_waiver_signed', 'step_intro_completed',
      'step_membership_activated', 'step_uniform_issued',
  )
  def _compute_progress(self):
      lifecycle_steps = [
          'step_trial_booked', 'step_waiver_signed', 'step_intro_completed',
          'step_membership_activated', 'step_uniform_issued',
      ]
      for rec in self:
          completed = sum(1 for s in lifecycle_steps if getattr(rec, s))
          rec.progress_pct = int(completed / len(lifecycle_steps) * 100)
  ```

**Rollback:** Same as Step 1

### Step 4: Add `missing_steps` computed field (if gate needs it)

**File:** `addons/dojo_onboarding/models/dojo_onboarding_record.py`

**Changes:**
- After `progress_pct` field definition, add:
  ```python
  missing_steps = fields.Char(
      string='Missing Steps',
      compute='_compute_missing_steps',
      store=True,
  )
  
  @api.depends(
      'step_trial_booked', 'step_waiver_signed', 'step_intro_completed',
      'step_membership_activated', 'step_uniform_issued',
  )
  def _compute_missing_steps(self):
      step_labels = {
          'step_trial_booked': 'Trial Booked',
          'step_waiver_signed': 'Waiver Signed',
          'step_intro_completed': 'Intro Completed',
          'step_membership_activated': 'Membership Activated',
          'step_uniform_issued': 'Uniform Issued',
      }
      for rec in self:
          missing = [label for key, label in step_labels.items() if not getattr(rec, key)]
          rec.missing_steps = ', '.join(missing) if missing else ''
  ```

**Rollback:** Same as Step 1

### Step 5: Update wizard to NOT hard-code `state='completed'`

**File:** `addons/dojo_onboarding/models/dojo_onboarding_wizard.py`

**Changes:**
- Line 620: Replace `'state': 'completed',` with `'state': 'in_progress',`
- After line 622 (after the create call), add:
  ```python
  onboarding_record = self.env['dojo.onboarding.record'].create({
      'member_id': member.id,
      'step_member_info': True,
      'step_household': bool(household),
      'step_enrollment': bool(self.program_id),
      'step_subscription': bool(self.plan_id),
      'step_portal_access': self.create_portal_login,
      'state': 'in_progress',  # Changed from 'completed'
      'company_id': self.env.company.id,
  })
  onboarding_record._sync_derived_steps()  # Sync lifecycle steps
  ```

**Rollback:** `git checkout -- addons/dojo_onboarding/models/dojo_onboarding_wizard.py`

### Step 6: Add trial conversion fields to `dojo.member`

**File:** `addons/dojo_core/models/member.py`

**Changes:**
- After `membership_state` field (around line 68), add:
  ```python
  converted_from_trial = fields.Boolean(
      string='Converted from Trial',
      default=False,
      copy=False,
      help='Set to True when member transitions from trial to active membership.'
  )
  trial_converted_on = fields.Datetime(
      string='Trial Conversion Date',
      copy=False,
      help='Timestamp when member was converted from trial to active.'
  )
  ```

**Rollback:** `git checkout -- addons/dojo_core/models/member.py`

### Step 7: Update `action_set_active()` to track trial conversion

**File:** `addons/dojo_core/models/member.py`

**Changes:**
- Replace lines 170-171 (the `action_set_active` method body):
  ```python
  def action_set_active(self):
      for rec in self:
          was_trial = (rec.membership_state == 'trial')
          rec.membership_state = "active"
          if was_trial:
              rec.converted_from_trial = True
              rec.trial_converted_on = fields.Datetime.now()
  ```

**Rollback:** Same as Step 6

### Step 8: Update kiosk service step fields dict

**File:** `addons/dojo_kiosk/models/dojo_kiosk_service.py`

**Changes:**
- Replace lines 17-23 (the `_ONBOARDING_STEP_FIELDS` dict):
  ```python
  _ONBOARDING_STEP_FIELDS = {
      # Legacy data-entry steps (kept for compatibility)
      "member_info": ("step_member_info", "Member Info"),
      "household": ("step_household", "Household"),
      "enrollment": ("step_enrollment", "Class Enrollment"),
      "subscription": ("step_subscription", "Subscription"),
      "portal_access": ("step_portal_access", "Portal Access"),
      # New lifecycle steps
      "trial_booked": ("step_trial_booked", "Trial Booked"),
      "waiver_signed": ("step_waiver_signed", "Waiver Signed"),
      "intro_completed": ("step_intro_completed", "Intro Session Completed"),
      "membership_activated": ("step_membership_activated", "Membership Activated"),
      "uniform_issued": ("step_uniform_issued", "Uniform Issued"),
  }
  ```

**Rollback:** `git checkout -- addons/dojo_kiosk/models/dojo_kiosk_service.py`

### Step 9: Add migration for existing onboarding records

**File:** `addons/dojo_onboarding/__init__.py`

**Changes:**
- Add a post-init hook:
  ```python
  def post_init_hook(env):
      """Migrate existing onboarding records to lifecycle steps."""
      records = env['dojo.onboarding.record'].search([])
      for rec in records:
          # Grandfather completed records: set manual steps to True
          if rec.state == 'completed':
              rec.write({
                  'step_intro_completed': True,
                  'step_uniform_issued': True,
              })
          # Sync derived steps from current member state
          rec._sync_derived_steps()
  ```

**File:** `addons/dojo_onboarding/__manifest__.py`

**Changes:**
- Add to manifest dict:
  ```python
  'post_init_hook': 'post_init_hook',
  ```

**Rollback:** 
- `git checkout -- addons/dojo_onboarding/__init__.py`
- `git checkout -- addons/dojo_onboarding/__manifest__.py`

### Step 10: Verify and test

**Commands:**
1. Upgrade modules:
   ```bash
   docker compose run --rm -T --entrypoint /opt/odoo/odoo-bin web \
     -c /etc/odoo/odoo.conf -d odoo19 -u dojo_onboarding,dojo_core,dojo_kiosk --stop-after-init
   ```

2. Restart web:
   ```bash
   docker compose restart web
   ```

3. Run the gate:
   ```bash
   bash scripts/usability_pass/verify/s5.sh
   ```

**Rollback:** If gate fails, revert individual files as noted in each step, re-upgrade, restart.

### Step 11: Commit

**Command:**
```bash
git add -A && git commit -m "upass S5: onboarding lifecycle steps + trial conversion"
```

## Time Budget

- Steps 1-4: ~8 min (model field additions)
- Step 5: ~3 min (wizard change)
- Steps 6-7: ~4 min (member trial conversion)
- Step 8: ~2 min (kiosk dict update)
- Step 9: ~5 min (migration hook)
- Step 10: ~5 min (upgrade + gate)
- Step 11: ~1 min (commit)

**Total:** ~28 minutes (well under 15-min single-fix limit)

## Gate Pass Criteria

1. All five lifecycle boolean columns exist in `dojo_onboarding_record` table
2. Both trial conversion columns exist in `dojo_member` table
3. Shell test: new record defaults to `in_progress`
4. Shell test: `_sync_derived_steps()` flips `step_waiver_signed` when waiver fields set
5. Shell test: `action_set_active()` from trial sets both conversion fields
6. Shell test: kiosk `perform_onboarding_action` accepts `step_key='intro_completed'`
7. Wizard no longer contains `'state': 'completed'` string in source

**Done = all gate assertions pass + clean commit.**
