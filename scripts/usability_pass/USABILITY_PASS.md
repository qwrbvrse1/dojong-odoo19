# USABILITY PASS — Access & usability updates. Make the system SAFE and SMOOTH.

You are working in `dojong-odoo19` on the dedicated VM with Docker, Playwright, and full
unrestricted access. The demo rescue is complete and the system RUNS. This pass implements the
access-control and usability changes from the completed role-by-role review
(`dojang-spec-role-review.md`). Your job is NOT a redesign. It is: **close the access holes,
land the usability changes, keep every existing demo flow working, and PROVE both via the
gates before declaring done.**

## Non-negotiable rules

1. **Verify, don't assume.** Every change must be confirmed by a clean module upgrade + its
   stage gate. "The code looks right" does not count.
2. **Regression is failure.** The five demo accounts, the kiosk happy path (search → check-in),
   and the parent portal must keep working after every stage. Gates re-check them; the final
   stage cold-restarts and re-runs everything.
3. **Time-box.** If a fix takes >15 min, choose the smallest change that passes the gate.
   Reverting a piece and noting it in the runbook beats a half-landed redesign.
4. **Do NOT** rename modules, change demo account credentials, change the kiosk PIN (123456),
   or touch anything not on this list.
5. Commit after each working stage. Keep `main` untouched.
6. Run Odoo logs in a terminal you watch: `docker compose logs -f web` — every traceback gets
   triaged immediately.

## The change set (from the role review — these ARE the stages)

| # | Change | Stage |
|---|--------|-------|
| 1 | Close `base.group_user` full-RWX ACLs on all `dojo.*` models | S1 |
| 2 | Tighten parent ACLs (enrollment / auto-enroll / emergency contact) | S1 |
| 3 | Gate pre-PIN kiosk data exposure (search + profile minimal until PIN) | S2 |
| 4 | Kiosk token rotation action + kiosk mutation action log | S2 |
| 5 | Backend surname search view (filter / group-by / column on member list) | S3 |
| 6 | Remove the vestigial `dojo_instructor_dashboard` stub | S3 |
| 7 | Session bulk-close ("mark remaining absent") + auto-close cron | S4 |
| 8 | Onboarding lifecycle steps + trial-conversion tracking | S5 |
| 9 | Parent portal onboarding checklist | S6 |

## Known landmines (from the completed review — start here)

1. **Demoting `base.group_user` rows breaks UI for plain internal users.** This was rescue
   landmine #4 in the other direction: any view/widget loaded by a user who reads a dojo model
   without an ACL row now throws. Before removing a `base.group_user` row, confirm an
   equivalent row exists for `group_dojo_admin` (RWX) and the right instructor/parent rows.
   The S1 gate runs admin AND instructor Playwright smokes to catch misses.
2. **Integration/service accounts (e.g. the n8n account) are plain internal users.** After S1
   they lose dojo model access. Grant them an explicit group (admin or a new integration
   group) in a data file or post-init hook — and record it in the runbook.
3. **Portal controllers create records as the portal user.** Tightening parent ACL
   create/unlink on `dojo.class.enrollment` / `dojo.course.auto.enroll` will break
   `/my/dojo/enroll`, `/my/dojo/unenroll`, and `/my/dojo/auto-enroll` unless those controller
   paths switch to `sudo()` AFTER their existing household validation
   (`dojo_members_portal/controllers/main.py` already validates via
   `_resolve_view_member_ids` — keep that, sudo only the write).
4. **The kiosk SPA expects the full profile pre-PIN.** `dojo_kiosk/static/src/kiosk_app.js`
   renders profile modals from `/kiosk/member/profile`. When you gate that endpoint, update
   the SPA: minimal card pre-PIN, re-fetch full profile after PIN unlock. Otherwise the
   self-check-in flow renders empty fields and S2's smoke fails.
5. **Manifest `data` ordering.** New XML (search views, cron, log model views) must load after
   the actions/models it references — this exact class of bug broke the demo last time
   (`dojo_core_menus.xml` vs `dojo_instructor_dashboard_views.xml`).
6. **`dojo_instructor_dashboard` has NO `__manifest__.py`.** It is not an installable module —
   just an orphan ACL csv + two logo PNGs. The real instructor actions live in
   `dojo_core/views/dojo_instructor_dashboard_views.xml`. Check `ir_module_module` state
   before assuming anything; if it somehow shows as installed, clean that up first.
7. **Onboarding records are created post-hoc as `completed`** by
   `dojo_onboarding/models/dojo_onboarding_wizard.py` (`_create_student_member`). Changing
   step semantics (S5) requires a migration for existing records and keeps the kiosk's
   `perform_onboarding_action` step keys working
   (`dojo_kiosk/models/dojo_kiosk_service.py:1790`).
8. **`pg_trgm`** must exist in the DB before upgrading `dojo_core`
   (`CREATE EXTENSION IF NOT EXISTS pg_trgm;`) or the `search_name_normalized` index is
   skipped.
9. **Record rules vs ACLs.** Instructor scoping lives in record RULES
   (`dojo_core/security/dojo_security.xml`); the holes are in ACL CSVs
   (`dojo_base`, `dojo_classes`, `dojo_attendance`). Fix the CSVs; do not loosen the rules.

## Required accounts (unchanged from the rescue — gates depend on them)

| Role | Login | Password |
|---|---|---|
| Admin | admin@demo.com | admin123 |
| Instructor | instructor1@demo.com | dojo@2026 |
| Student 1 | demo1@demo.com | dojo@2026 |
| Student 2 | demo2@demo.com | dojo@2026 |
| Parent | DemoParent@demo.com | dojo@2026 |

S1 additionally seeds a **probe** account (`probe@qa.local` / `Probe-2026!`) — an internal user
with NO dojo groups, used by gates to prove the ACL closure. Kiosk PIN stays **123456**.

## Key file map (verified against the current tree)

- ACL holes: `addons/dojo_base/security/ir.model.access.csv`,
  `addons/dojo_classes/security/ir.model.access.csv`,
  `addons/dojo_attendance/security/ir.model.access.csv`
- Role matrix to mirror: `addons/dojo_core/security/ir.model.access.csv` +
  `addons/dojo_core/security/dojo_security.xml`
- Kiosk: `addons/dojo_kiosk/controllers/kiosk_controller.py`,
  `addons/dojo_kiosk/models/dojo_kiosk_service.py` (15-min window const at top;
  `perform_onboarding_action` ~line 1790), `addons/dojo_kiosk/models/dojo_kiosk_config.py`,
  `addons/dojo_kiosk/static/src/kiosk_app.js`
- Member search fields (already exist, indexed): `addons/dojo_core/models/member.py`
  (`first_name` L79, `last_name` L87, `search_name_normalized` L95, trigram)
- Member backend views (NO search view today): `addons/dojo_core/views/member_views.xml`
- Onboarding: `addons/dojo_onboarding/models/dojo_onboarding_record.py`,
  `addons/dojo_onboarding/models/dojo_onboarding_wizard.py`
- Portal: `addons/dojo_members_portal/controllers/main.py`
- Waiver state source: `addons/dojo_sign/models/dojo_member_waiver.py`

## Stage map

- **S0** — Baseline: clean boot + module upgrade, no stuck modules, five accounts authenticate.
- **S1** — ACL closure + parent tightening + probe seed + portal sudo-after-validation.
- **S2** — Kiosk: pre-PIN minimal data, instructor_key gating, token rotation, action log.
- **S3** — Backend surname search view + instructor_dashboard stub removal.
- **S4** — Session bulk-close + auto-close cron.
- **S5** — Onboarding lifecycle steps + trial conversion fields + migration.
- **S6** — Parent portal onboarding checklist + FREEZE (cold restart, re-run all gates, runbook).
