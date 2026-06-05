# Stage 1 Plan — ACL Closure + Parent Tightening

## Execution Steps

### 1. Remove base.group_user W/C/U rows on dojo.* models

For each file below, remove the `base.group_user` rows that have write/create/unlink (1,1,1,1 or any W/C/U):

**Target files and rows to REMOVE (full RWX only):**

1. `addons/dojo_base/security/ir.model.access.csv` - Remove 3 rows:
   - `access_dojo_member_user`
   - `access_dojo_instructor_profile_user`
   - `access_dojo_martial_art_style_user`

2. `addons/dojo_classes/security/ir.model.access.csv` - Remove 5 rows:
   - `access_dojo_program_user`
   - `access_dojo_class_template_user`
   - `access_dojo_class_session_user`
   - `access_dojo_class_enrollment_user`
   - `access_dojo_course_auto_enroll_user`

3. `addons/dojo_attendance/security/ir.model.access.csv` - Remove 1 row:
   - `access_dojo_attendance_log_user`

4. `addons/dojo_belt_progression/security/ir.model.access.csv` - Remove 4 rows:
   - `access_dojo_belt_rank_user`
   - `access_dojo_belt_test_user`
   - `access_dojo_belt_test_registration_user`
   - `access_dojo_member_rank_user`

5. `addons/dojo_checkout/security/ir.model.access.csv` - Remove 3 rows:
   - `access_dojo_checkout_config`
   - `access_dojo_checkout_session`
   - `access_dojo_checkout_upsell`

6. `addons/dojo_communications/security/ir.model.access.csv` - Remove 1 row:
   - `access_dojo_send_message_wizard`

7. `addons/dojo_crm/security/ir.model.access.csv` - Remove 2 rows:
   - `access_dojo_book_trial_wizard`
   - `access_dojo_convert_lead_wizard`

8. `addons/dojo_management/security/ir.model.access.csv` - Remove 6 rows (keep read-only dashboard rows):
   - `access_dojo_session_user`
   - `access_dojo_student_user`
   - `access_dojo_attendance_user`
   - `access_dojo_payment_user`
   - `access_dojo_martial_arts_style_user`
   - `access_dojo_belt_rank_user`
   - Remove 2 wizard rows (they have 1,1,1,0):
   - `access_belt_promotion_wizard_user`
   - `access_attendance_wizard_user` (keep the line version, it has full RWX)
   - `access_attendance_wizard_line_user`

9. `addons/dojo_marketing/security/ir.model.access.csv` - Remove 1 row:
   - `access_dojo_marketing_card`

10. `addons/dojo_members/security/ir.model.access.csv` - Remove 1 row:
    - `access_dojo_emergency_contact_user`

11. `addons/dojo_migration/security/ir.model.access.csv` - Remove all 10 migration wizard rows (full RWX)

12. `addons/dojo_sign/security/ir.model.access.csv` - Remove 1 row:
    - `access_dojo_waiver_config`

13. `addons/dojo_social/security/ir.model.access.csv` - Remove 2 rows:
    - `access_dojo_social_post`
    - `access_dojo_social_account`

**Rows to KEEP (read-only, needed by widgets):**
- `addons/dojo_core/security/ir.model.access.csv`: `access_dojo_attendance_quick_wizard` and `access_dojo_attendance_quick_line` (widgets use these)
- `addons/dojo_kiosk/security/ir.model.access.csv`: 3 read-only kiosk rows
- `addons/dojo_management/security/ir.model.access.csv`: 3 dashboard read-only rows

**Rollback:** `git checkout -- addons/<module>/security/ir.model.access.csv`

### 2. Tighten parent group ACLs

Edit `addons/dojo_core/security/ir.model.access.csv`:

**Line 25** - Change `access_dojo_auto_enroll_parent`:
```
FROM: access_dojo_auto_enroll_parent,dojo.course.auto.enroll parent,model_dojo_course_auto_enroll,dojo_core.group_dojo_parent_student,1,1,1,1
TO:   access_dojo_auto_enroll_parent,dojo.course.auto.enroll parent,model_dojo_course_auto_enroll,dojo_core.group_dojo_parent_student,1,1,0,0
```
(Remove create/unlink: 1,1,1,1 → 1,1,0,0)

**Line 11** - Change `access_dojo_emergency_contact_parent`:
```
FROM: access_dojo_emergency_contact_parent,dojo.emergency.contact parent,model_dojo_emergency_contact,dojo_core.group_dojo_parent_student,1,1,1,1
TO:   access_dojo_emergency_contact_parent,dojo.emergency.contact parent,model_dojo_emergency_contact,dojo_core.group_dojo_parent_student,1,1,1,0
```
(Remove unlink: 1,1,1,1 → 1,1,1,0)

**Note:** Line 22 `access_dojo_class_enrollment_parent` is already (1,1,0,0) ✓

**Rollback:** `git checkout -- addons/dojo_core/security/ir.model.access.csv`

### 3. Fix portal controllers to use sudo() after validation

Edit `addons/dojo_members_portal/controllers/main.py`:

**portal_enroll (line 772):**
- Lines 831, 833: Already use `sudo()` ✓ NO CHANGE NEEDED

**portal_unenroll (line 1168):**
- Line 1190: Already uses `sudo()` ✓ NO CHANGE NEEDED

**portal_post_auto_enroll (line 530):**
- Lines 569-605: Already use `sudo()` throughout ✓ NO CHANGE NEEDED

**FINDING:** All portal endpoints already use sudo() after their household validation. No changes needed.

### 4. Create probe user seed script

Create `scripts/usability_pass/seed/probe_user.py`:

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Seed the probe user for S1 gate verification."""
import odoo

def seed_probe_user(env):
    """Create or update the probe user (internal, no dojo groups)."""
    User = env['res.users']
    probe = User.search([('login', '=', 'probe@qa.local')], limit=1)
    
    vals = {
        'name': 'QA Probe User',
        'login': 'probe@qa.local',
        'password': 'Probe-2026!',
        'groups_id': [(6, 0, [env.ref('base.group_user').id])],  # Internal user only
        'active': True,
    }
    
    if probe:
        probe.write(vals)
        print(f"Updated probe user: {probe.login} (id={probe.id})")
    else:
        probe = User.create(vals)
        print(f"Created probe user: {probe.login} (id={probe.id})")
    
    return probe

if __name__ == '__main__':
    with odoo.api.Environment.manage():
        registry = odoo.registry(odoo.tools.config['db_name'])
        with registry.cursor() as cr:
            env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
            seed_probe_user(env)
            cr.commit()
```

Run via: `docker compose run --rm -T --entrypoint /opt/odoo/odoo-bin web shell -c /etc/odoo/odoo.conf -d odoo19 --no-http < scripts/usability_pass/seed/probe_user.py`

**Rollback:** `DELETE FROM res_users WHERE login='probe@qa.local';` via psql

### 5. Identify and grant group to integration accounts

Query for internal users without dojo groups:
```sql
SELECT u.id, u.login, u.partner_id, u.active
FROM res_users u
WHERE u.active = true
  AND EXISTS (SELECT 1 FROM res_groups_users_rel WHERE uid = u.id AND gid = (SELECT res_id FROM ir_model_data WHERE module='base' AND name='group_user'))
  AND u.id NOT IN (SELECT uid FROM res_groups_users_rel WHERE gid IN (
      SELECT res_id FROM ir_model_data WHERE module='dojo_core' AND name IN ('group_dojo_admin', 'group_dojo_instructor', 'group_dojo_parent_student')
  ))
  AND u.login NOT IN ('admin@demo.com', 'probe@qa.local');
```

For each found (e.g., n8n account):
- Create a data file `addons/dojo_core/data/integration_users.xml` to grant `group_dojo_admin` via XML
- OR document in plan if manual grant is acceptable

**Rollback:** Remove the XML file or manually remove the group grant via UI

### 6. Module upgrade sequence

After all CSV/controller edits:

1. Restart web: `docker compose restart web`
2. Upgrade all touched modules:
   ```bash
   docker compose run --rm -T --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 \
     -u dojo_base,dojo_classes,dojo_attendance,dojo_belt_progression,dojo_checkout,dojo_communications,dojo_crm,dojo_management,dojo_marketing,dojo_members,dojo_migration,dojo_sign,dojo_social,dojo_core \
     --stop-after-init
   ```
3. Restart web again: `docker compose restart web`
4. Run probe seed: `docker compose run --rm -T --entrypoint /opt/odoo/odoo-bin web shell -c /etc/odoo/odoo.conf -d odoo19 --no-http < scripts/usability_pass/seed/probe_user.py`

**Rollback:** Restore DB from backup, `git checkout -- <files>`

### 7. Verify manually before gate

Test parent portal endpoints:
- Login as DemoParent@demo.com / dojo@2026
- Navigate to http://localhost:8070/my/dojo
- Try enrolling a student
- Check emergency contact operations

Test admin/instructor UIs still load.

### 8. Run the gate

From repo root:
```bash
bash scripts/usability_pass/verify/s1.sh
```

Iterate until all assertions pass.

### 9. Commit

```bash
git add -A
git commit -m "upass S1: ACL closure + parent tightening"
```

## Risk Mitigation

- **Integration accounts losing access:** Query before upgrade, grant explicit group
- **Portal breaks:** Controllers already use sudo(), but test manually first
- **UI breaks for admin/instructor:** Gate runs browser smokes to catch this
- **Module upgrade fails:** Have backup ready, rollback individual files

## Time-Box

- CSV edits: ~10 minutes
- Integration account handling: ~5 minutes
- Module upgrade + probe seed: ~5 minutes
- Manual testing: ~10 minutes
- Gate debugging: ~15 minutes (if issues)
- **Total: ~45 minutes** (within stage budget)
