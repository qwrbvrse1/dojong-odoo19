# Stage 1 Plan — Demo Accounts Seed

## Goal
Create five demo accounts that pass `scripts/demo_rescue/verify/s1.sh` gate.

## Implementation Steps

### 1. Create seed script directory
```bash
mkdir -p scripts/demo_rescue/seed
```
**Rollback**: N/A (directory creation is safe)

### 2. Write `scripts/demo_rescue/seed/accounts.py`
Odoo shell script with the following structure:
- Import required modules (`env`, `Command`)
- Define account specs (login, password, groups, role)
- For each account:
  - Search for existing `res.users` by login
  - If exists: update password and groups
  - If not: create user with correct partner, groups
- Special handling per role:
  - **Admin**: ensure `group_dojo_admin` in groups
  - **Instructor**: create/update `dojo.instructor.profile` with `user_id` and `partner_id` linkage
  - **Students**: create `dojo.member` records (which auto-create partners), create household if needed, link to household
  - **Parent**: create guardian partner with `is_guardian=True`, link to household as `primary_guardian_id`, grant `group_dojo_parent_student`

**Rollback**: Delete `scripts/demo_rescue/seed/accounts.py`

### 3. Write wrapper shell script `scripts/demo_rescue/seed_accounts.sh`
```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
docker compose run --rm -T --entrypoint /opt/odoo/odoo-bin web \
  -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http \
  --shell < scripts/demo_rescue/seed/accounts.py
```
Make executable: `chmod +x scripts/demo_rescue/seed_accounts.sh`

**Rollback**: Delete `scripts/demo_rescue/seed_accounts.sh`

### 4. Ensure docker stack is running
```bash
docker compose up -d db web
```
Wait for web to be healthy (http://localhost:8070/web/login returns 200).

**Rollback**: N/A (starting containers is safe)

### 5. Run the seed script
```bash
bash scripts/demo_rescue/seed_accounts.sh
```
Expected output: "5 accounts seeded successfully" or similar confirmation.

**Rollback**: If errors occur, inspect output, fix `accounts.py`, re-run (idempotent)

### 6. Verify the gate
```bash
bash scripts/demo_rescue/verify/s1.sh
```
Expected output: `GATE: PASSED`

If any assertion fails:
- Check authentication errors → verify password setting logic
- Check instructor profile SQL → verify `dojo.instructor.profile` creation and `user_id` linkage
- Re-run seed script after fixes (idempotent design allows safe re-runs)

**Rollback**: N/A (verification is read-only)

### 7. Commit the changes
```bash
git add scripts/demo_rescue/seed/
git add docs/rescue/S1_*
git commit -m "rescue S1: demo account seed (5 accounts + instructor profile)"
```

**Rollback**: `git reset --soft HEAD~1` if commit needs revision

## Files to Create/Modify
- **New**: `scripts/demo_rescue/seed/accounts.py` (Python seed logic)
- **New**: `scripts/demo_rescue/seed_accounts.sh` (shell wrapper)
- **New**: `docs/rescue/S1_ANALYSIS.md` (already created)
- **New**: `docs/rescue/S1_PLAN.md` (this file)

## Success Criteria
- All 5 accounts authenticate via JSON-RPC
- `instructor1@demo.com` has `dojo.instructor.profile` with `user_id` populated
- Gate script exits 0 with "GATE: PASSED"
- Changes committed to git

## Time-box
If any single step exceeds 15 minutes, revert that piece and choose simpler approach. The gate is the requirement — code elegance is secondary.
