# Stage 3 Analysis — Backend surname search view + dashboard stub removal

## Gate Requirements (from scripts/usability_pass/verify/s3.sh)

The gate script asserts:
1. A search view exists for `dojo.member` whose arch references `last_name` (field + filter and/or group-by)
2. The `dojo.member` list view arch references `last_name` (visible column)
3. A `group_by` on `last_name` is available in the search arch
4. `addons/dojo_instructor_dashboard` is either deleted or has a valid `__manifest__.py`
5. No broken `ir_module_module` row for `dojo_instructor_dashboard` (state must be 'uninstalled' or 'uninstallable' if present)
6. Admin Playwright smoke still passes (bad view XML surfaces here)

## Current State

### Member Views (addons/dojo_core/views/member_views.xml)
- **List view** (view_dojo_member_list, L3-23):
  - Fields: name, member_number, email, gender, total_sessions, attendance_rate, is_student, is_guardian, is_minor, membership_state, parent_id, has_portal_login
  - **No `first_name` or `last_name` fields present**
  - **No `default_order` attribute on the `<list>` element**
  
- **Search view**: **DOES NOT EXIST** — this is the primary task

- **Actions**:
  - `action_dojo_members` (L178-182): res_model=dojo.member, view_mode=list,form
  - **No search_view_id specified** — will need to wire the new search view

### Member Model (addons/dojo_core/models/member.py)
- `first_name` (L79-86): Char, computed from name, stored, indexed — **ready to use**
- `last_name` (L87-94): Char, computed from name, stored, indexed — **ready to use**
- `search_name_normalized` (L95-102): Char, computed, stored, trigram indexed — **ready to use**
- Model `_order` is NOT visible in the first 120 lines — need to check if it exists

### Vestigial dojo_instructor_dashboard
- Directory exists at `addons/dojo_instructor_dashboard`
- Contains: `security/` dir and `static/` dir
- **NO `__manifest__.py`** — confirms it's a stub (landmine 6)
- `ir_module_module` query returned 0 rows — **no database entry exists**
- Real instructor actions are in `addons/dojo_core/views/dojo_instructor_dashboard_views.xml` — **must NOT touch those**

### Verification Strategy
The gate runs:
1. SQL checks against `ir_ui_view` for search/list views with `last_name` in arch
2. Filesystem check for the dashboard directory
3. SQL check for broken module rows
4. Playwright admin smoke (detects view XML errors)

## Implementation Plan Summary

1. **Add search view** to `member_views.xml`:
   - Create `view_dojo_member_search` with:
     - `name` field with `filter_domain` matching `name`, `last_name`, `search_name_normalized`
     - Dedicated `last_name` field
     - Filters for active membership states
     - Group-by options for Last Name and Membership State
   - Wire to `action_dojo_members` via `search_view_id`

2. **Update list view**:
   - Add `first_name` and `last_name` fields after `name`
   - Add `default_order="last_name, first_name"` to the `<list>` element

3. **Remove vestigial directory**:
   - Delete `addons/dojo_instructor_dashboard` entirely (no DB cleanup needed)

4. **Upgrade and verify**:
   - Run `docker compose run --rm -T --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 -u dojo_core --stop-after-init`
   - Restart web: `docker compose restart web`
   - Run gate: `bash scripts/usability_pass/verify/s3.sh`

## Risk Assessment

**LOW RISK** — View-layer only work:
- No model changes, no ACL changes, no controller changes
- Fields already exist, stored, and indexed
- No migration needed
- List view `default_order` does not affect the model's `_order` (kiosk payload ordering unchanged)
- Dashboard removal is safe (no DB entry, no manifest, directory is orphaned)

**Rollback**: `git checkout -- addons/dojo_core/views/member_views.xml addons/dojo_instructor_dashboard`
