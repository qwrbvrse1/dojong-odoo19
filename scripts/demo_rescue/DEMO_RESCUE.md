# DEMO RESCUE — Client demo in ~90 minutes. Make the system RUN.

You are working in `dojang-odoo19` (branch `feature/core-dojo-realignment`) on a dedicated VM with
Docker, Playwright, and full unrestricted access. The previous agent (Codex) left a change set that
introduced UI errors and broke module loading. Your job is NOT a refactor. It is: **boot clean,
fix demo-blocking errors, seed believable demo data, and PROVE it works via Playwright before
declaring done.**

## Non-negotiable rules

1. **Verify, don't assume.** Every fix must be confirmed by a clean module upgrade + a Playwright
   check. "The code looks right" does not count.
2. **Time-box.** If a fix takes >15 min, revert that piece to the last-known-good behavior instead.
   `git stash` / `git checkout -- <file>` is a valid fix today.
3. **Do NOT** redesign kiosk endpoint auth, rename modules, or touch anything not on this list.
4. Commit after each working phase with a clear message. Keep `main` untouched.
5. Run Odoo logs in a terminal you watch: `docker compose logs -f web` — every traceback gets
   triaged immediately.

## Reported symptoms (from the client)

- Errors in the UI.
- **Most modules don't load for the admin user** (menus/apps missing).
- Demo logins don't match the agreed accounts (see "Required demo accounts" below).

## Known landmines (from a completed code review — start here)

These are confirmed defects in the current change set; they are the most likely cause of the
reported symptoms:

1. **Menu → action reference ordering.** Uncommitted changes repoint menus to
   `dojo_core.action_all_sessions_today`:
   - `addons/dojo_core/views/dojo_core_menus.xml` (Dashboard menu)
   - `addons/dojo_core/views/dojo_instructor_dashboard_views.xml`
   - `addons/dojo_kiosk/views/dojo_kiosk_views.xml` (root menu action)
   The action is defined in `dojo_instructor_dashboard_views.xml`. If `dojo_core_menus.xml` loads
   first in the manifest `data` list, the upgrade fails → modules stuck in `to upgrade` → **menus
   vanish for admin**. Check manifest ordering, fix or revert these menu changes.
2. **Duplicate group redefinition.** `dojo_core.group_dojo_instructor` has `implied_ids` written in
   BOTH `security/dojo_security.xml` and `data/instructor_todos_data.xml`, including
   `(3, ref('account.group_account_invoice'))` unlink ops. If `account`/`hr` groups aren't loaded
   (modules not installed), `ref()` raises and the upgrade dies. Verify both files load cleanly;
   consolidate to one definition if needed.
3. **`dojo_credits` was never upgraded.** `scripts/prep_kiosk_demo.sh` MODULES list omits
   `dojo_credits`, but the change set added `security/dojo_credits_security.xml` + rewrote its
   access CSV (removed `base.group_user` rows). Any user touching credit transactions without the
   upgrade applied → access errors in the UI. Add `dojo_credits` to the upgrade list.
4. **Access CSVs demoted `base.group_user` rows to admin/instructor-only** in `dojo_credits` and
   `dojo_onboarding`. Any view/widget loaded by a plain internal user that reads those models now
   throws. If admin UI errors trace to ACLs, this is why.
5. **New instructor record rules hide everything unassigned.** Sessions/members are only visible to
   an instructor if their instructor profile is on the session/template. The demo seed assigns NO
   instructor → an instructor login sees an empty system. Demo data must link
   `instructor1@demo.com`'s profile to every seeded session/template.
6. **`(3, ref(...))` implied-group removal is not retroactive.** Existing users keep
   accounting/HR groups. For the demo DB this only matters if you reuse an old DB — prefer a fresh
   seed.
7. **Trigram index needs `pg_trgm`.** Run
   `CREATE EXTENSION IF NOT EXISTS pg_trgm;` in the demo DB before upgrading `dojo_core`, or the
   `search_name_normalized` index is skipped/warns.
8. `scripts/prep_kiosk_demo.sh` is untracked and the menu changes are uncommitted — decide
   deliberately what's in the demo build, then commit it.

## Phase 0 — Reproduce & triage (≤15 min)

```
./scripts/start-docker.sh   # or: docker compose up -d
docker compose logs -f web  # watch for tracebacks
```
- Upgrade ALL touched modules (note: includes dojo_credits):
  `docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http -u dojo_core,dojo_credits,dojo_subscriptions,dojo_onboarding,dojo_sign,dojo_crm,dojo_kiosk --stop-after-init`
- If the upgrade errors: fix per landmines #1/#2 first. If still failing at T+15 min, revert the
  uncommitted view changes and any file the traceback names, and re-run until the upgrade is CLEAN.
- Confirm no stuck modules:
  `SELECT name, state FROM ir_module_module WHERE state NOT IN ('installed','uninstalled','uninstallable');`
  Must return 0 rows.

## Phase 1 — Admin UI loads (gate: Playwright-verified)

- Log in as admin via Playwright. Assert: apps/menus render (Dashboard, Members, Classes, Kiosk,
  Onboarding at minimum), no error dialog, no 500s in network log, no tracebacks in
  `docker compose logs`.
- Click through: Members list, a member form, Classes/Sessions, Kiosk config. Zero errors.

## Phase 2 — Required demo accounts (exactly these, per the client doc)

| Role | Login | Password |
|---|---|---|
| Admin | `admin@demo.com` | `admin123` |
| Instructor | `instructor1@demo.com` | `dojo@2026` |
| Student 1 | `demo1@demo.com` | `dojo@2026` |
| Student 2 | `demo2@demo.com` | `dojo@2026` |
| Parent (of both students) | `DemoParent@demo.com` | `dojo@2026` |

- Admin → `group_dojo_admin`. Instructor → `group_dojo_instructor` + an
  `dojo.instructor.profile` linked to their user. Students → members (+ portal). Parent →
  parent/student group with household links to both students.
- Replace/extend `scripts/prep_kiosk_demo.sh` accordingly (delete the invented
  `demo.admin/demo123` account or leave it as a backup — but the table above MUST work).

## Phase 3 — Demo data that shows the features (idempotent seed script)

Seed relative to **runtime now**, not fixed clock times:

1. **Members (10–12)** with real surname variety for the search demo: at least two `Smith`s, a
   `Smithson`, a `Doe`, a multi-word surname. Give each: belt rank, profile image (any bundled
   placeholder), email/phone.
2. **Belt ladder** with attendance thresholds so grading status shows `n/m Classes` and at least
   one member is "Ready for Grading".
3. **Sessions**: one ACTIVE now (started 10 min ago, ends +50 min), one starting in +10 min
   (inside the 15-min upcoming window), one later today, one completed earlier. ALL assigned to
   instructor1's profile (template + session). Enroll demo1, demo2, and most seeded members.
4. **Workflow states across members** (this is the wow factor): one with onboarding ~60% done, one
   complete; one unsigned waiver; one active subscription, one paused, one with credits exhausted;
   one open instructor task (use the exact member name in the task title — matching is
   name-ilike); one trial lead booked into the active session if `dojo_crm` trial fields exist.
5. Kiosk config active with PIN `123456`; print the kiosk URL at the end of the seed.
6. `CREATE EXTENSION IF NOT EXISTS pg_trgm;` before module upgrade (landmine #7).

## Phase 4 — Playwright verification suite (the actual deliverable)

Write and run a smoke script. ALL must pass; rerun after every fix:

1. Login succeeds for ALL FIVE accounts (correct landing, no error toast).
2. Admin: menus listed in Phase 1 render; member form opens.
3. Instructor backend: sees their sessions and enrolled members; does NOT see Credits or
   Onboarding-admin menus; no AccessError anywhere in the UI flows above.
4. Kiosk page (token URL) loads; search `Smi` → returns the Smiths; search `Doe` → returns Doe.
5. Kiosk instructor mode (PIN 123456): session auto-selected with "Active:" pill; roster tiles
   show photos + workflow badges; open a profile → workflow cards (Onboarding/Waiver/Membership/
   Grading) render; Manage tab → mark one onboarding step done → succeeds and progress updates.
6. Mark one member present from the roster; state persists after reload.
7. Console: no uncaught JS errors on any screen above. Server log: no tracebacks during the run.

## Phase 5 — Freeze (last 15 min)

- Commit everything (including the seed script). Tag `demo-YYYYMMDD`.
- Restart the stack from scratch (`docker compose down && up -d`) and re-run the Phase 4 suite
  once against the cold-started system. This is the "actually runs" proof.
- Write `DEMO_RUNBOOK.md`: start command, the five logins, kiosk URL + PIN, and the 3-line demo
  flow (admin view → kiosk search → instructor mode workflow actions).

## Explicitly OUT of scope today

Kiosk endpoint authentication redesign, res.partner search, audit trail, 3-panel kiosk layout,
periodic session-context refresh, name-splitting edge cases. Do not touch them.
