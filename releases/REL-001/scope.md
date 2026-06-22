# Release Scope — REL-001: UFTKD Platform Feature Delivery

## Summary

REL-001 delivers the full scope defined in the UFTKD gap analysis (`gap-analysis-2026-06-19.md`). It transforms the existing Odoo saas~19.2 platform from a functional but visually unbranded system into a fully styled, feature-complete dojo management platform matching the design reference (`scope/UFT_SUPABASE_STORAGE_PHOTOS.html`).

The release is structured across five Milestones executed as ordered Increments on a single release branch. Milestone 0 establishes infrastructure prerequisites (custom theme module, third-party modules added to version control). Milestones 1–4 deliver backend logic, daily operations UI, instructor tools, and communication automation respectively. Milestone 5 retires the MuK IT theme modules once OWL equivalents cover all functionality. All Increments merge together to main as a single production release.

## Prerequisites (manual steps before harness run)

The following must be completed by the operator before `apev-run.sh` is invoked. The `baseline_gate` verifies they are in place.

1. **`sms_twilio` source obtained** — copy the module from the production VM (`dojo-solution:/custom-addons/addons/sms_twilio/`) into `addons/sms_twilio/` in the repo. Required before INC-02.
2. **Docker image built** — run `docker compose build` to ensure the container image is current before the harness run.

## In scope

**Milestone 0 — Infrastructure**
- A new `dojo_theme` Odoo module exists in `addons/dojo_theme/` containing all brand design tokens (CSS custom properties) from the prototype: `--bg`, `--surface`, `--surface2`, `--surface3`, `--border`, `--red`, `--red-dim`, `--gold`, `--gold-light`, `--text`, `--text-muted`, `--text-dim`, `--green`, `--orange`, `--blue`. Fonts (Bebas Neue, Barlow, Barlow Condensed) loaded via Google Fonts asset override.
- `sms_twilio` module is present in `addons/` and tracked in version control.

**Milestone 1 — Backend Logic**
- `dojo.member` has a `name_search` override that parses the query, identifies the last token as a probable surname, and ranks surname-first matches above mid-name matches. Searching "Smith" returns members whose last name starts with Smith ranked above those with Smith elsewhere in the name.
- `get_member_profile()` in `dojo_kiosk_service.py` returns onboarding record data including: step statuses, `progress_pct`, and available actions (`complete_step`, `send_reminder`). New kiosk API endpoints `/kiosk/api/onboarding/complete_step` and `/kiosk/api/onboarding/send_reminder` exist and are authenticated.
- `get_todays_sessions()` in `dojo_kiosk_service.py` returns a `time_state` field on each session: one of `active`, `upcoming_soon` (within 15 minutes), `upcoming`, or `done`. Computed relative to server wall clock at request time.
- `dojo.member` has a stored computed field `expdate` (Date) derived from the linked subscription state. Field is indexed. Updates when subscription state changes via `_compute_expdate`. Accessible in filtered list views.

**Milestone 2 — OWL UI: Daily Operations**
- `dojo_instructor_dashboard` module exists (manifest, models, OWL views) and is installable. It provides a backend Odoo view with: four stat cards (total active students, today's check-ins, upcoming birthdays within 7 days, expiring memberships within 30 days), a belt distribution bar chart, a birthday list (next 7 days), and an expiring memberships list (next 30 days). All data sourced from `dojo.member` and `dojo.attendance.log`.
- Instructor kiosk view has a three-panel CSS grid layout: left panel (active session + countdown timer + attendance summary), main panel (member roster cards), right panel (instructor notes, onboarding alerts, membership issues). Layout defined in `dojo_kiosk` static CSS.
- Check-in success state shows a full-screen confirmation overlay with member name, belt rank color, and plays an audio chime (Web Audio API, single tone). Overlay auto-dismisses after 3 seconds.
- Instructor kiosk session list auto-selects the `active` or `upcoming_soon` session on page load. Session cards render with visual state classes: `k-session--active`, `k-session--soon`, `k-session--upcoming`, `k-session--done`.
- `InstructorRosterTile` OWL component renders an `onboarding_pct` progress bar and an `open_task_count` badge when values are non-zero. Data sourced from the updated roster API payload.
- `MemberProfileCard` has an Onboarding tab (or section within Manage tab) showing each onboarding step status and buttons: Mark Complete, Send Reminder, Add Note, Escalate.

**Milestone 3 — OWL UI: Instructor Tools**
- `dojo_belt_progression` module is fully implemented (not a stub): OWL view for mass belt promotion with multi-select member grid, single-click promote-all, and undo (within the same session via in-memory stack). Promotion history log accessible per member showing date, from-rank, to-rank, promoted-by.
- Belt test roster view in `dojo_belt_progression`: filterable by class group and belt rank, generates a print-ready roster (CSS `@media print`), and can be saved as a named `dojo.belt.test` record.
- Attendance analytics view (in `dojo_instructor_dashboard` or dedicated module): busiest class sessions by check-in count (last 30 / 90 days), top attending members, members with zero attendance in last 30 days.
- Reports views (in `dojo_members` module, fully implemented not a stub): Inactive Student report (no attendance in N days, configurable), Contact report (members missing parent/guardian email or phone), Family report (household groupings). Each report is an OWL list view with filter controls.
- CSV export: a backend wizard (transient model + controller) accessible from the dashboard or reports views, exporting: students (all fields), attendance log, promotion history, belt test rosters. Returns a `.csv` file download.

**Milestone 4 — Communication & Automation**
- Email Center in `dojo_communications`: OWL view for composing and sending mass email to audience segments (by class group, by belt rank, by expiring membership status). Individual email to a single member. Email history log showing sent date, subject, recipient count, sender.
- Follow-up email action accessible from the Inactive Student report: pre-populates an email to selected inactive students; sends via Odoo mail system; records in email history.
- Birthday email automation: OCA automation rule fires daily, finds members with birthday today (or within N days if configured), sends a templated birthday email via Odoo mail. Configurable: enabled/disabled, days-ahead, template.
- Membership expiry email automation: OCA automation rule fires daily, finds members with `expdate` within N days (configurable), sends a templated expiry warning email. Configurable: enabled/disabled, days-ahead threshold, template.

**Milestone 5 — MuK Retirement**
- All 7 `muk_web_*` modules (`muk_web_theme`, `muk_web_chatter`, `muk_web_colors`, `muk_web_dialog`, `muk_web_group`, `muk_web_refresh`, `muk_web_appsbar`) are uninstalled from the `odoo19` database and removed from `addons/`.
- `dojo_theme` provides all visual styling previously supplied by MuK: dark background, topbar, sidebar, chatter styling, dialog styling, color palette, refresh behavior, apps bar appearance.
- `docs/ui-ux-guide.md` is updated to document the new `dojo_theme` token system, replacing MuK token references.

## Out of scope

- **Cloud SQL changes** (backups, right-sizing, decommissioning idle instance) — deferred to Post-Release infrastructure work.
- **`api_doc` and `social_media` modules** — installed in production but sources are unknown and untracked. Not touched by this release.
- **n8n workflow changes** — no changes to n8n automation flows.
- **Stripe configuration changes** — `dojo_stripe`, `dojo_onboarding_stripe` are not modified.
- **`dojo_bridge` and `dojo_checkout`** — existing implementations are not modified.
- **AI caller / ElevenLabs changes** — `dojo_ai_caller`, `elevenlabs_connector`, `dojo_connect_ai` not modified.
- **Production deployment** — the release branch merges to main; actual production deploy to `dojo-solution` VM is a manual operator step after merge.
- **`prod2` instance changes** — this release targets `prod`. `prod2` deployment is a manual operator step.
- **Database migrations on production data** — the new `expdate` field is a stored computed field that populates on module upgrade; no separate migration script required. If data volume causes the upgrade to timeout, that is a production deployment concern, not a release concern.
- **`theme_liquid_glass` cleanup** — present in `addons/`, not installed. Removing it is a separate maintenance task outside this release.
- **`portalops_demo` cleanup** — same: present, not installed, deferred.
- **Stub module implementations** (`dojo_attendance`, `dojo_classes`, `dojo_base`, `dojo_members` beyond reports, `dojo_belt_progression` is implemented in this release) — `dojo_attendance`, `dojo_classes`, `dojo_base` remain stubs.

## Affected SPEC sections

- **Section 3.1** — Module Inventory: `dojo_theme` added; `dojo_instructor_dashboard`, `dojo_belt_progression`, `dojo_members` promoted from stub to implemented; `dojo_communications` updated.
- **Section 3.4** — MuK IT Theme: all 7 modules removed (Milestone 5).
- **Section 3.5** — Stub modules: `dojo_belt_progression` removed from stub list.
- **Section 4** — Data Model: `dojo.member.expdate` field added; kiosk API response shape updated.
- **Section 5** — Deployed Functionality: updated for all new features across M1–M4.
- **Section 10** — Design System: current state updated from MuK to `dojo_theme`; migration plan marked complete.
- **Section 12** — Technical Debt: MuK IT theme and `docs/ui-ux-guide.md` items resolved.

## Decisions

| Decision | Rationale | Alternatives rejected |
|---|---|---|
| OWL for all new UI, no React Bridge | saas~19.2 compatibility of React Bridge unconfirmed; existing kiosk is already full OWL SPA; OWL can produce identical visual output | React Bridge (Shachain) |
| Plain CSS custom properties, no SCSS or Tailwind | No build tooling required; matches Odoo's native asset pipeline; tokens map directly from prototype | SCSS (extra build step), Tailwind (PostCSS complexity) |
| `dojo_theme` as a new module (not patching `muk_web_theme`) | Clean separation; MuK modules can be uninstalled without affecting `dojo_theme`; audit trail for what we own vs third-party | Patching MuK directly |
| Stored computed `expdate` on `dojo.member` | Allows indexed filtering/sorting in ORM list views; avoiding re-computing from subscriptions on every query | Pure computed (non-stored), direct subscription query |
| OCA automation for birthday/expiry emails | Already installed; avoids custom cron boilerplate; configurable without code changes | Custom `ir.cron`, n8n workflows |
| `dojo_instructor_dashboard` as new implemented module | Stub exists in repo; implementing it in-place preserves the intended module name and cleans up the stub | New module name |
| MuK retired last (Milestone 5) | MuK and `dojo_theme` coexist safely; retiring last avoids visual regression during earlier increments | Retire MuK first (risk: visual gap before OWL coverage) |

## Risks and decision rules

| If… | Then… (never ask) |
|---|---|
| `sms_twilio` source cannot be copied from production VM before harness run | INC-02 fails baseline prerequisite check; operator must obtain source before running |
| Module upgrade fails with `ValueError` or `psycopg2` error during a gate | Classify `code_defect`; do not alter migration logic to suppress — fix the root cause |
| MuK module uninstall in INC-25 causes a `UserError` (dependency conflict) | Identify the blocking dependent module, uninstall it first; if it is a custom module, add its uninstall to INC-25's scope; never leave MuK partially uninstalled |
| OWL component causes a JS console error that does not fail the Python gate | Note in failure report; do not mark gate as passed; add a `curl` check for a `/web/dataset/call_kw` response that confirms the component renders, or classify `plan_defect` and add a JS gate |
| `expdate` stored compute triggers a long-running recompute during module upgrade | Expected behavior; wait for completion; if upgrade times out (>10 min), reduce recompute batch size in `_compute_expdate` using `write` with `limit` |
| A test touches files outside its declared `touchpoints` | Classify `plan_defect` on the increment; fix touchpoints in plan.md, rerun |
| Odoo test runner exits 0 but logs `ERROR` for a test | Treat as PASS only if the ERROR is in a third-party module outside this increment's touchpoints; otherwise classify `code_defect` |

## Success criteria (release level)

- All 23 increments reach PASS status (gate exits 0, no regression_gate failures).
- `bash testenv/verify.sh` exits 0 on the final commit of `rel/REL-001`.
- All 7 `muk_web_*` modules absent from `addons/` and not installed in `odoo19`.
- `dojo_theme` installs cleanly with no errors on a fresh `odoo19` database.
- `SPECIFICATION.md` updated to reflect post-release system state.
- `docs/ui-ux-guide.md` reflects `dojo_theme` token system.
- Auditor (not the worker model) can verify each in-scope item is present in the diff.
