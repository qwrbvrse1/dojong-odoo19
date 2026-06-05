# Stage 3 Plan — Backend surname search view + dashboard stub removal

## Target: Gate script passes (scripts/usability_pass/verify/s3.sh)

## Numbered Steps

### 1. Add search view to member_views.xml
**File**: `addons/dojo_core/views/member_views.xml`  
**Action**: Insert a new `<record id="view_dojo_member_search">` BEFORE the actions section (before L178)

Search view requirements:
- `name` field with `filter_domain="['|', '|', ('name', 'ilike', self), ('last_name', 'ilike', self), ('search_name_normalized', 'ilike', self)]"`
- Dedicated `last_name` field
- Filters: active membership states (lead, trial, active, paused, cancelled)
- Group-by: Last Name (`context="{'group_by': 'last_name'}"`)
- Group-by: Membership State (`context="{'group_by': 'membership_state'}"`)

**Rollback**: `git checkout -- addons/dojo_core/views/member_views.xml`

### 2. Update list view to show first_name and last_name
**File**: `addons/dojo_core/views/member_views.xml`  
**Action**: 
- Modify `<list>` element (L7) to add `default_order="last_name, first_name"`
- Add `<field name="first_name"/>` after `<field name="name"/>` (after L8)
- Add `<field name="last_name"/>` after the new first_name field

**Rollback**: Same as step 1 (same file)

### 3. Wire search view to action
**File**: `addons/dojo_core/views/member_views.xml`  
**Action**: Add `<field name="search_view_id" ref="view_dojo_member_search"/>` to `action_dojo_members` record (after L181)

**Rollback**: Same as step 1 (same file)

### 4. Remove vestigial dojo_instructor_dashboard directory
**File**: `addons/dojo_instructor_dashboard/` (entire directory)  
**Action**: `rm -rf addons/dojo_instructor_dashboard`

**Risk**: LOW — no DB entry exists, no manifest, directory is orphaned  
**Rollback**: `git checkout -- addons/dojo_instructor_dashboard` (restores from git)

### 5. Upgrade dojo_core module
**Command**: `docker compose run --rm -T --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 -u dojo_core --stop-after-init`  
**Expected**: Clean upgrade, new search view registered in `ir_ui_view`

**Risk**: MEDIUM — stale registry if this fails  
**Rollback**: Fix XML syntax errors, re-run upgrade

### 6. Restart web container
**Command**: `docker compose restart web`  
**Expected**: Clean restart, no errors in logs

**Risk**: LOW  
**Rollback**: `docker compose restart web` (idempotent)

### 7. Run gate verification
**Command**: `bash scripts/usability_pass/verify/s3.sh` (from repo root)  
**Expected**: All assertions pass, "GATE: PASSED" printed

**Risk**: NONE (read-only check)  
**Iteration**: If gate fails, identify the failing assertion and fix the corresponding step

### 8. Commit
**Command**: `git add -A && git commit -m "upass S3: surname search view + list order + dashboard stub removal"`  
**Expected**: Clean commit on `usability-pass` branch

## Time Budget
- Steps 1-3: ~5 minutes (view XML edits)
- Step 4: ~30 seconds (directory removal)
- Steps 5-6: ~2 minutes (upgrade + restart)
- Step 7: ~1 minute (gate run)
- Step 8: ~30 seconds (commit)
- **Total**: ~9 minutes (well under 15-minute limit)

## Success Criteria
- `bash scripts/usability_pass/verify/s3.sh` prints "GATE: PASSED"
- Admin Playwright smoke passes (no view XML errors)
- Commit created with summary message
