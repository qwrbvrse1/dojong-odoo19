# Stage 3 Analysis — Demo Dataset

## Gate Requirements (from verify/s3.sh)

The gate script specifies these exact checks:

1. **Members**: ≥10 active members
2. **Search names**: ≥2 members with surname "Smith" (case-insensitive)
3. **Profile images**: ≥5 members with `image_1920` on res.partner OR attachments
4. **Belt ranks**: ≥3 `dojo_belt_rank` records
5. **Members with ranks**: ≥5 members with `current_rank_id` populated
6. **Active session**: ≥1 session in `state='open'`, `instructor_profile_id` assigned, `start_datetime <= now() <= end_datetime`
7. **Upcoming session**: ≥1 session in `state='open'`, `instructor_profile_id` assigned, `start_datetime > now()` AND `< now() + 8 hours`
8. **Active session enrollments**: ≥5 enrollments linked to the active session
9. **Onboarding records**: ≥2 total
10. **Incomplete onboarding**: ≥1 record with `state != 'completed'`
11. **Subscriptions**: ≥2 `sale_subscription` records with `member_id` populated
12. **Kiosk config**: ≥1 active `dojo_kiosk_config` with `pin_code` set
13. **Search layer**: ≥10 members with `search_name_normalized` populated

## Additional Requirements from Stage Brief

Beyond the gate:

- **Relative times**: Active session ~10 min ago → +50 min; upcoming session ~+10 min (inside 15-min kiosk window); one completed session earlier today
- **Instructor assignment**: Every seeded session AND its template must reference `instructor1@demo.com`'s `dojo.instructor.profile`
- **Search demo surnames**: ≥2 distinct "X Smith", one "Smithson", one "Doe", one multi-word surname
- **Enrolled members**: demo1, demo2 enrolled in the active session
- **Workflow states** (spread across members):
  - One onboarding ~60% complete, one complete
  - One unsigned waiver
  - Subscriptions in different states (active / paused or pending / credits exhausted) — create minimal subscription plan if none exists
  - One open instructor task whose title CONTAINS the member's exact name (task matching is name-ilike)
  - Trial lead booked into active session IF `dojo_crm.crm_lead.trial_session_id` exists (confirmed: it does)
- **Profile images**: Tiny generated placeholder PNGs (initials on colored square), base64 into `image_1920`
- **Kiosk config**: Active, PIN `123456`, print kiosk URL at end
- **Idempotency**: Script must be re-runnable to re-center times (move existing seeded sessions rather than duplicating)

## Existing Assets

- **accounts.py**: Already seeds 5 demo accounts (admin, instructor1, demo1, demo2, DemoParent), grants portal access, creates instructor profile for instructor1
- **seed_accounts.sh**: Wrapper that runs accounts.py via odoo-bin shell pattern

## Database Schema Key Points

### dojo.member
- `partner_id` → `res.partner` (for `image_1920`)
- `current_rank_id` → `dojo_belt_rank`
- `membership_state` (varchar, not null)
- `active` (boolean)
- `first_name`, `last_name`, `search_name_normalized` (populated by model logic)
- `waiver_state`, `has_signed_waiver`, `waiver_signed_on`
- `active_subscription_id` → `sale_subscription`

### dojo.class.session
- `template_id` → `dojo.class.template` (not null)
- `instructor_profile_id` → `dojo.instructor.profile`
- `state` (varchar, not null) — valid values include 'draft', 'open', 'completed', 'cancelled'
- `start_datetime`, `end_datetime` (timestamp, not null)
- `attendance_complete` (boolean)

### dojo_class_enrollment
- `session_id` → `dojo.class.session` (CASCADE delete)
- `member_id` → `dojo.member`

### dojo_onboarding_record
- `member_id` → `dojo.member`
- `state` (varchar) — 'draft', 'in_progress', 'completed' (likely)
- Progress tracking fields (need to check model)

### sale_subscription
- `member_id` → `dojo.member`
- `state` (varchar) — 'draft', 'in_progress', 'open', 'close', etc.
- Subscription plan relationship

### dojo_kiosk_config
- `active` (boolean)
- `pin_code` (varchar)
- `access_token` (for URL generation)

### project.task
- `dojo_member_id` → `dojo.member` (possibly)
- `name` (for title matching)

### crm.lead (dojo_crm extension)
- `trial_session_id` → `dojo.class.session` (confirmed exists)

## Implementation Strategy

1. **One Python seed script** (`scripts/demo_rescue/seed/demo_data.py`) that:
   - Checks for existing seeded data (idempotency marker)
   - If re-running: updates session times (delta from original to now)
   - If first run: creates all data
   - Uses UTC times, calculates relative to `datetime.utcnow()`
   - Base64-encodes tiny PNG placeholders for profile images

2. **Shell wrapper** (`scripts/demo_rescue/seed_demo_data.sh`):
   - Runs via docker compose odoo-bin shell pattern
   - Prints kiosk URL at end

3. **Data structure**:
   - 12 members (demo1, demo2 already exist from accounts.py; add 10 more with varied surnames)
   - 3-5 belt ranks (White, Yellow, Orange, Green, Blue)
   - 1 class template (linked to instructor1 profile)
   - 4 sessions (completed earlier today, active now, upcoming +10min, later today) — all linked to instructor1
   - 7+ enrollments (demo1, demo2 + 5 others in active session)
   - 2 onboarding records (one incomplete ~60%, one complete)
   - 2-3 subscriptions (need to create minimal plan first)
   - 1 kiosk config (PIN 123456)
   - 1 project.task (open, name contains member name)
   - 1 crm.lead with trial_session_id pointing to active session

4. **Profile image generation**: Use Python PIL/Pillow to generate 64x64 PNGs with initials, convert to base64

5. **Idempotency approach**:
   - Mark seeded data with a unique external_id or a custom field flag
   - On re-run: find existing seeded sessions, calculate time delta, update start/end datetimes
   - Use `env.ref()` with try/except or search-then-create patterns

## Risk Assessment

- **Time zone handling**: Odoo stores UTC, gate checks use `now() AT TIME ZONE 'UTC'` — must use UTC everywhere
- **Instructor profile lookup**: Must find instructor1's profile by user login
- **Template requirements**: Session requires `template_id` (not null) — must create template first
- **Subscription plan**: May not exist — need to create minimal plan data
- **Module dependencies**: onboarding/subscription/crm modules must be installed and upgraded
- **Image format**: `image_1920` expects base64-encoded binary data
- **Search normalization**: Assuming model logic auto-populates `search_name_normalized` on member write

## Rollback Plan

If seed fails midway:
- Delete all seeded records by searching for marker (e.g., member_number starts with 'SEED-')
- Revert to clean state via SQL DELETE with WHERE clauses
- Keep demo accounts intact (from accounts.py)
