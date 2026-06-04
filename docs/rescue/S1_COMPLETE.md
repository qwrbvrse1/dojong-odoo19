# Stage 1 Complete — Demo Accounts

## Status
✓ **GATE PASSED** at 2026-06-04 18:30

## Gate Results
```
PASS: admin@demo.com logs in
PASS: instructor1@demo.com logs in
PASS: demo1@demo.com logs in
PASS: demo2@demo.com logs in
PASS: DemoParent@demo.com logs in
PASS: instructor1 has an instructor profile linked to their user (1 >= 1)
GATE: PASSED
```

## Implementation Summary

### Files Created
1. `scripts/demo_rescue/seed/accounts.py` — Idempotent Python seed script
2. `scripts/demo_rescue/seed_accounts.sh` — Shell wrapper for seed execution
3. `docs/rescue/S1_ANALYSIS.md` — Analysis document
4. `docs/rescue/S1_PLAN.md` — Implementation plan
5. `docs/rescue/S1_COMPLETE.md` — This file

### Accounts Created
All 5 demo accounts now exist and authenticate:

| Login | Role | User ID | Additional Data |
|---|---|---|---|
| admin@demo.com | Admin | 24 | group_dojo_admin |
| instructor1@demo.com | Instructor | 25 | instructor profile ID 32 |
| demo1@demo.com | Student | 26 | member ID 153 |
| demo2@demo.com | Student | 27 | member ID 154 |
| DemoParent@demo.com | Parent | 28 | household ID 184, linked to both students |

### Key Implementation Details
- Used Odoo shell mode (`odoo-bin shell -c /etc/odoo/odoo.conf -d odoo19`)
- Idempotent upsert pattern (search by login first)
- Instructor profile auto-creates `hr.employee` via model hook
- Students created as `dojo.member` records (auto-creates partner)
- Household pattern: `res.partner` with `is_household=True`, students linked via `parent_id`
- Parent linked as `primary_guardian_id` on household
- Portal access granted via `_grant_portal_access_credentials()` method

### Verification Method
- JSON-RPC authentication via `/web/session/authenticate`
- SQL check for instructor profile: `SELECT count(*) FROM dojo_instructor_profile p JOIN res_users u ON p.user_id=u.id WHERE u.login='instructor1@demo.com'`

## Git Commit Note
Due to permission issues with the shared worktree refs directory (`/opt/repos/dojong-odoo19/.git/refs/heads/feature/` owned by `johnbentleyii:johnbentleyii`, not group-writable), the commit must be completed by the orchestrator or with elevated permissions. All code changes are staged and ready:

```bash
# To commit (run as user with write access to refs):
cd /opt/worktrees/dojong-odoo19/core-dojo-realignment
git add -A
git commit -m "rescue S1: demo account seed (5 accounts + instructor profile)"
```

Staged files:
- scripts/demo_rescue/seed/accounts.py
- scripts/demo_rescue/seed_accounts.sh
- docs/rescue/S1_ANALYSIS.md
- docs/rescue/S1_PLAN.md
- docs/rescue/S1_COMPLETE.md
