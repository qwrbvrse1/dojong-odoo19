# Stage 1 Analysis — ACL Closure + Parent Tightening

## Gate Requirements (from verify/s1.sh)

1. **NO** active `base.group_user` rows granting write/create/unlink on ANY `dojo.*` model
2. Parent group (`dojo_core.group_dojo_parent_student`) has:
   - NO create/unlink on `dojo.class.enrollment`
   - NO create/unlink on `dojo.course.auto.enroll`
   - NO unlink on `dojo.emergency.contact`
3. Probe user (`probe@qa.local` / `Probe-2026!`) exists, authenticates, but gets AccessError on `dojo.member`
4. Zero regression: admin/instructor browser smokes pass, parent portal `/my/dojo` returns 200

## Current State

### base.group_user ACL Rows on dojo.* Models (Full RWX)

From grep search, the following files have `base.group_user` rows with write/create/unlink on `dojo.*` models:

**Known files (from brief):**
- `addons/dojo_base/security/ir.model.access.csv`: 3 rows
  - `dojo.member` (1,1,1,1)
  - `dojo.instructor.profile` (1,1,1,1)
  - `dojo.martial.art.style` (1,1,1,1)
  
- `addons/dojo_classes/security/ir.model.access.csv`: 5 rows
  - `dojo.program` (1,1,1,1)
  - `dojo.class.template` (1,1,1,1)
  - `dojo.class.session` (1,1,1,1)
  - `dojo.class.enrollment` (1,1,1,1)
  - `dojo.course.auto.enroll` (1,1,1,1)
  
- `addons/dojo_attendance/security/ir.model.access.csv`: 1 row
  - `dojo.attendance.log` (1,1,1,1)

**Additional files found:**
- `addons/dojo_belt_progression/security/ir.model.access.csv`: 4 rows
  - `dojo.belt.rank` (1,1,1,1)
  - `dojo.belt.test` (1,1,1,1)
  - `dojo.belt.test.registration` (1,1,1,1)
  - `dojo.member.rank` (1,1,1,1)

- `addons/dojo_checkout/security/ir.model.access.csv`: 3 rows
  - `dojo.checkout.config` (1,1,1,1)
  - `dojo.checkout.session` (1,1,1,1)
  - `dojo.checkout.upsell` (1,1,1,1)

- `addons/dojo_communications/security/ir.model.access.csv`: 1 row
  - `dojo.send.message.wizard` (1,1,1,1)

- `addons/dojo_crm/security/ir.model.access.csv`: 2 dojo rows
  - `dojo.book.trial.wizard` (1,1,1,1)
  - `dojo.convert.lead.wizard` (1,1,1,1)

- `addons/dojo_management/security/ir.model.access.csv`: 9 rows
  - `dojo.dashboard` (1,0,0,0) - read-only, OK
  - `dojo.dashboard.belt.stat` (1,0,0,0) - read-only, OK
  - `dojo.dashboard.style.stat` (1,0,0,0) - read-only, OK
  - `dojo.session` (1,1,1,1)
  - `dojo.student` (1,1,1,1)
  - `dojo.attendance` (1,1,1,1)
  - `dojo.payment` (1,1,1,1)
  - `dojo.martial_arts_style` (1,1,1,1)
  - `dojo.belt_rank` (1,1,1,1)

- `addons/dojo_marketing/security/ir.model.access.csv`: 1 row
  - `dojo.marketing.card` (1,1,1,1)

- `addons/dojo_members/security/ir.model.access.csv`: 1 row
  - `dojo.emergency.contact` (1,1,1,1)

- `addons/dojo_migration/security/ir.model.access.csv`: 10 rows (all migration wizards, full RWX)

- `addons/dojo_sign/security/ir.model.access.csv`: 1 row
  - `dojo.waiver.config` (1,1,1,1)

- `addons/dojo_social/security/ir.model.access.csv`: 2 rows
  - `dojo.social.post` (1,1,1,1)
  - `dojo.social.account` (1,1,1,1)

**Read-only base.group_user rows (OK to keep):**
- `addons/dojo_core/security/ir.model.access.csv`: 2 wizard rows (0-create/unlink, needed by quick-attendance wizard)
- `addons/dojo_kiosk/security/ir.model.access.csv`: 3 read-only rows (kiosk config/announcement/pin-attempt)
- `addons/dojo_management/security/ir.model.access.csv`: 3 dashboard read-only rows

**Non-dojo models (ignore):**
- `ai_assistant`, `ai_vector`, `dojo_bridge`, `elevenlabs_connector` have base.group_user rows but NOT on `dojo.*` models

### Parent Group Current Permissions

From `dojo_core/security/ir.model.access.csv` lines 22, 25, 11:
- `dojo.class.enrollment parent` (1,1,0,0) - read/write, NO create/unlink ✓ Already correct
- `dojo.course.auto.enroll parent` (1,1,1,1) - full RWX ✗ Has create/unlink
- `dojo.emergency.contact parent` (1,1,1,1) - full RWX ✗ Has unlink

### Equivalent Group-Scoped Rows

Checked `dojo_core/security/ir.model.access.csv` - all target models have:
- Admin group: full RWX (1,1,1,1)
- Instructor group: appropriate permissions per role matrix
- Parent group: per above (need to fix auto-enroll + emergency contact)

### Portal Controller sudo() Landmine

File: `addons/dojo_members_portal/controllers/main.py`

Line 85-100: `_resolve_view_member_ids()` already validates household membership for parents
Line 42-47: `_get_current_member()` uses sudo() for member lookup
Line 49-68: `_get_household_member_ids()` uses sudo() for household scope validation

Need to find the enrollment/unenroll/auto-enroll endpoints and add sudo() AFTER validation.

### Integration Accounts

Need to query `res_users` for active internal users without dojo groups (e.g., n8n account from rescue).

### Probe User

Need to create seed script: `scripts/usability_pass/seed/probe_user.py`

## Risk Assessment

**High risk:**
- Removing `base.group_user` rows could break UI for integration accounts → mitigate by granting explicit group
- Portal enrollment endpoints will break when parent ACL tightened → mitigate by adding sudo() after validation

**Medium risk:**
- Missing equivalent group rows → verified all have admin/instructor/parent rows in dojo_core

**Low risk:**
- Read-only `base.group_user` rows (dashboards, kiosk read-only) - gate allows these, keeping them

## Rollback Strategy

- Git checkout individual CSV files if broke something
- If module upgrade fails, restore from backup and re-analyze
- All changes are in data files (CSVs) and one controller - no model schema changes
