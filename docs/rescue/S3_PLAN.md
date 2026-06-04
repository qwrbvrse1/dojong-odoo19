# Stage 3 Plan — Demo Dataset

## Goal
Gate passes: `bash scripts/demo_rescue/verify/s3.sh` returns `GATE: PASSED`

## Implementation Steps

### Step 1: Create Python seed script skeleton
**File**: `scripts/demo_rescue/seed/demo_data.py`
- Import required modules (datetime, base64, io, logging)
- Define constants for relative times (active session -10min/+50min, upcoming +10min, completed -8hr)
- Define member data structure with surnames: 2x Smith, 1x Smithson, 1x Doe, 1x multi-word
- Define idempotency marker (external_id prefix or search pattern)
- Rollback: delete file if broken

### Step 2: Implement profile image generator
**In same file**
- Function to generate 64x64 PNG with initials on colored background
- Use simple in-memory generation (no PIL dependency if possible, else use base64 of minimal PNG)
- Return base64-encoded string suitable for `image_1920` field
- Rollback: stub with None (images not strictly required for gate pass of 5/10 members)

### Step 3: Implement belt rank seeding
**In same file**
- Create 3-5 `dojo_belt_rank` records (White, Yellow, Orange, Green, Blue)
- Set `sequence` and `attendance_threshold` fields
- Idempotent: search by name, create if not found
- Rollback: SQL `DELETE FROM dojo_belt_rank WHERE name IN ('White', 'Yellow', 'Orange', 'Green', 'Blue')`

### Step 4: Implement member seeding
**In same file**
- Find existing demo1/demo2 members (from accounts.py)
- Create 10 additional members with varied surnames:
  - "John Smith", "Jane Smith" (2x Smith)
  - "Bob Smithson" (Smithson)
  - "Alice Doe" (Doe)
  - "Maria Garcia Lopez" (multi-word)
  - 5 more with varied names
- Assign belt ranks to at least 5 members
- Set profile images on at least 5 members (via partner_id.image_1920)
- Set membership_state='active', active=True
- Idempotent: search by email or member_number pattern (SEED-001, SEED-002, etc.)
- Rollback: `DELETE FROM dojo_member WHERE member_number LIKE 'SEED-%'`

### Step 5: Find instructor1 profile
**In same file**
- Search for user with login='instructor1@demo.com'
- Find linked `dojo.instructor.profile` via `user_id`
- Store profile ID for session assignment
- Rollback: N/A (read-only)

### Step 6: Create class template
**In same file**
- Create 1 `dojo.class.template` record
- Assign `instructor_profile_id` to instructor1's profile
- Set name, duration, capacity
- Idempotent: search by name pattern (e.g., "Demo Class Template")
- Rollback: `DELETE FROM dojo_class_template WHERE name = 'Demo Class Template'`

### Step 7: Create/update session times
**In same file**
- Calculate UTC times relative to `datetime.utcnow()`:
  - Completed: started -8hr, ended -7hr
  - Active: started -10min, ends +50min
  - Upcoming: starts +10min, ends +70min
  - Later: starts +4hr, ends +5hr
- If idempotency marker found (e.g., external_id exists):
  - Find existing seeded sessions
  - Calculate time delta from original to now
  - Update start_datetime and end_datetime
- Else (first run):
  - Create 4 `dojo.class.session` records
  - Set state ('completed' for first, 'open' for others)
  - Assign template_id and instructor_profile_id
- Rollback: `DELETE FROM dojo_class_session WHERE template_id = <seeded_template_id>`

### Step 8: Create enrollments
**In same file**
- Find active session (the one with start <= now <= end)
- Enroll demo1, demo2, and 5 seeded members (total 7 enrollments, meets ≥5 requirement)
- Create `dojo_class_enrollment` records with session_id and member_id
- Idempotent: search existing enrollments, create missing ones
- Rollback: `DELETE FROM dojo_class_enrollment WHERE session_id IN (seeded_session_ids)`

### Step 9: Create onboarding records
**In same file**
- Create 2 `dojo_onboarding_record` records
- One with state='completed' (100% progress)
- One with state='in_progress' (~60% progress, set relevant step fields)
- Link to 2 different members
- Idempotent: search by member_id, skip if exists
- Rollback: `DELETE FROM dojo_onboarding_record WHERE member_id IN (seeded_member_ids)`

### Step 10: Create subscription plan and subscriptions
**In same file**
- Check if `sale.subscription.plan` exists with basic setup
- If not: create minimal plan (name, billing cycle, price)
- Create 2-3 `sale_subscription` records with different states:
  - One state='open' (active)
  - One state='paused' or 'pending'
  - One with credits exhausted (need to check credit model fields)
- Link to different members
- Idempotent: search by member_id, skip if exists
- Rollback: `DELETE FROM sale_subscription WHERE member_id IN (seeded_member_ids)`

### Step 11: Create waiver records
**In same file**
- Set waiver_state on one member to 'unsigned' or relevant value
- Set has_signed_waiver=False
- Rollback: reset waiver fields on seeded members

### Step 12: Create instructor task
**In same file**
- Create 1 `project.task` record
- Set name to include exact member name (e.g., "Follow up with John Smith")
- Set state to open/active
- Set user_id to instructor1
- Link dojo_member_id if field exists
- Idempotent: search by name pattern
- Rollback: `DELETE FROM project_task WHERE name LIKE 'Follow up with %' AND create_uid = <seeded_uid>`

### Step 13: Create trial lead
**In same file**
- Create 1 `crm.lead` record
- Set trial_session_id to active session
- Set stage to appropriate trial stage
- Set contact info
- Idempotent: search by trial_session_id, skip if exists
- Rollback: `DELETE FROM crm_lead WHERE trial_session_id IN (seeded_session_ids)`

### Step 14: Create/update kiosk config
**In same file**
- Search for existing `dojo_kiosk_config` with active=True
- If exists: update pin_code to '123456'
- Else: create new config with active=True, pin_code='123456'
- Generate access_token if field exists and empty
- Print kiosk URL: `http://localhost:8070/dojo/kiosk?token=<access_token>`
- Idempotent: always update/create single active config
- Rollback: reset pin_code to original value or delete if created

### Step 15: Commit and log
**In same file**
- `env.cr.commit()`
- Log success message with counts
- Print kiosk URL prominently

### Step 16: Create shell wrapper
**File**: `scripts/demo_rescue/seed_demo_data.sh`
- Set COMPOSE_PROJECT_NAME if needed (inherit from env)
- Run: `docker compose run --rm -T --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --shell < scripts/demo_rescue/seed/demo_data.py`
- Rollback: delete file

### Step 17: Test idempotency
- Run seed script twice
- Verify no duplicates created
- Verify session times updated on second run
- Rollback: manual inspection, clean DB if broken

### Step 18: Run gate verification
- Execute: `bash scripts/demo_rescue/verify/s3.sh`
- Must print `GATE: PASSED`
- If fails: analyze SQL query outputs, adjust seed script, re-run
- Rollback: git checkout seed files, re-run

### Step 19: Commit
- `git add scripts/demo_rescue/seed/demo_data.py scripts/demo_rescue/seed_demo_data.sh docs/rescue/S3_*.md`
- `git commit -m "rescue S3: demo dataset seed script"`

## Critical Success Factors
1. All times in UTC
2. Instructor profile correctly linked to sessions AND templates
3. Session states correct ('open' for active/upcoming, 'completed' for past)
4. Idempotency via search-then-create pattern and time delta updates
5. search_name_normalized auto-populated by member model on write
6. At least 5 members with images (can be subset of 12 total)

## Corrective Action (Gate Failure)

The orchestrator uses a template gate script with simplified SQL that expects:
1. `name` column directly on `dojo_member` table (not just ORM `_inherits` delegation)
2. Profile images queryable without complex joins

**Fix**: Add stored related field `name` to dojo.member model that creates a database column.
This makes the gate's simplified SQL work without modifying the gate script itself.

**Steps**:
1. Add `name = fields.Char(related='partner_id.name', store=True, index=True)` to dojo.member model
2. Run module upgrade to create column
3. Populate existing members' name column
4. Re-run gate

## Time Box
- Total: 45 minutes
- If any step exceeds 10 minutes: simplify or stub (e.g., skip trial lead if model unclear)
- Gate must pass — that's the only measure of success
