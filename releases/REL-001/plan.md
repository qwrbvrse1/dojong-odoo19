# Release Plan — REL-001: UFTKD Platform Feature Delivery

> Prose sections are for humans. Fenced `yaml` blocks are parsed by `apev-run.sh`.
> Block 1 = release config. Each subsequent block = one increment, in execution order.
> Do not put status in this file — execution state lives in the run log.
>
> **Deviation from UnattendedBuild template:** This project uses a single `SPECIFICATION.md` at the repo root rather than the `specifications/<domain>.md` per-domain convention. All increment touchpoints and deliverables reference `SPECIFICATION.md`. When running the audit, treat `SPECIFICATION.md` as the equivalent of `specifications/`.
>
> **Resumption note:** INC-01, 02, 03, 04, 06, 08, 09, 10, 11, 12 passed on first run and are committed. This plan covers only the remaining increments. All `depends_on` references to already-committed increments have been cleared.

## Release configuration

```yaml
release: REL-001
branch: rel/REL-001
worker_model: claude
alternate_model: claude
max_shots: 3
halt_on_fail: downstream
workproducts: ~/workproducts/dojong-odoo19/REL-001
baseline_gate:
  - bash testenv/verify.sh
  - test -d addons/sms_twilio && test -f addons/sms_twilio/__manifest__.py
```

---

## INC-05 — session-time-tagging: time-state field on today's sessions

Add a `time_state` computed value to the `get_todays_sessions()` response in `dojo_kiosk_service.py`. State is one of: `active`, `upcoming_soon`, `upcoming`, `done`.

**Decision rules:**
- `active`: session `start_time` ≤ now < session `end_time`.
- `upcoming_soon`: session `start_time` > now AND session `start_time` ≤ now + 15 minutes.
- `upcoming`: session `start_time` > now + 15 minutes.
- `done`: session `end_time` ≤ now.
- Server-side computation only — use `fields.Datetime.now()` in service method. Do not rely on client clock.
- If a session has no `end_time`, treat `end_time` as `start_time + 60 minutes` for state computation.
- Write tests in `addons/dojo_kiosk/tests/test_session_time_state.py` covering all four states plus the no-end-time fallback. Use `freeze_time` or set `datetime.now` via monkeypatch in the test setup.
- If `freeze_time` is not available in the container, implement time injection via a keyword argument `_now=None` on the service method (defaults to `fields.Datetime.now()`). Tests pass a fixed datetime.
- **CRITICAL:** Do NOT modify `get_member_profile()`, `workflow_status`, or any method outside `get_todays_sessions()`. Existing tests `test_kiosk_workflow_visibility` and `test_kiosk_workflow_actions` test `workflow_status` in the member profile — do not touch that code path.

```yaml
id: INC-05
title: time_state field on kiosk session list
depends_on: []
touchpoints:
  - addons/dojo_kiosk/services/dojo_kiosk_service.py
  - addons/dojo_kiosk/tests/test_session_time_state.py
  - SPECIFICATION.md
deliverables:
  - get_todays_sessions() returns time_state on each session dict
  - Test file with ≥5 test methods covering all states
  - SPECIFICATION.md §5.1 (or §6) updated with time_state field description
test_data:
  seed: n/a
  migration_before_state: n/a
  external_stubs: n/a
  credentials: n/a
reset:
  - bash testenv/reset.sh
gate:
  - docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http -u dojo_kiosk --test-enable --test-file addons/dojo_kiosk/tests/test_session_time_state.py --stop-after-init
  - curl -sf http://127.0.0.1:8070/web/login -o /dev/null
regression_gate:
  - bash testenv/verify.sh
  - docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http -u dojo_core,dojo_kiosk --test-enable --stop-after-init
```

---

## INC-07 — dashboard: instructor dashboard module

Implement `dojo_instructor_dashboard` as a full Odoo module (manifest, OWL views, controllers). Provides a backend view with stat cards, belt distribution, upcoming birthdays, and expiring memberships.

**Decision rules:**
- Module depends on: `dojo_core`, `dojo_theme`, `web`. Do not depend on `dojo_subscriptions` directly — use `expdate` from `dojo.member` (already committed) for expiry filtering.
- Four stat cards: total active members (`dojo.member` where `active=True`), today's check-in count (`dojo.attendance.log` where `date=today`), birthdays in 7 days (members where birthday within next 7 calendar days), expiring in 30 days (members where `expdate` within next 30 days and `expdate` is set).
- Belt distribution: group `dojo.member` by current belt rank, return count per rank. Use existing `dojo.member.rank` or `member_rank_ids` relation — pick the most recent rank per member.
- Data served via a single JSON controller at `/instructor_dashboard/data` (GET, require login). OWL component fetches on mount and on a 60-second polling interval.
- Apply `dojo_theme` CSS tokens throughout — all colors from `var(--surface)`, `var(--red)`, `var(--gold)`, etc. No hardcoded hex values in component CSS.
- OWL component registered under `@dojo_instructor_dashboard/dashboard`. QWeb template in `views/dashboard.xml`.
- Write Python tests in `addons/dojo_instructor_dashboard/tests/test_dashboard_controller.py` covering: controller returns expected keys, stat counts are non-negative integers.
- **CRITICAL:** Do NOT include `OPL-1` in the manifest license field — use `LGPL-3` or omit the license key entirely. Do NOT add `# -*- coding: UTF-8 -*-` coding declarations to Python files.

```yaml
id: INC-07
title: dojo_instructor_dashboard OWL module
depends_on: []
touchpoints:
  - addons/dojo_instructor_dashboard/**
  - SPECIFICATION.md
deliverables:
  - addons/dojo_instructor_dashboard/__manifest__.py
  - addons/dojo_instructor_dashboard/controllers/dashboard.py (GET /instructor_dashboard/data)
  - addons/dojo_instructor_dashboard/static/src/js/dashboard.js (OWL component)
  - addons/dojo_instructor_dashboard/static/src/css/dashboard.css (dojo_theme tokens only)
  - addons/dojo_instructor_dashboard/views/dashboard.xml (QWeb template + ir.ui.menu entry)
  - addons/dojo_instructor_dashboard/views/assets.xml (asset bundle registration)
  - addons/dojo_instructor_dashboard/tests/test_dashboard_controller.py (≥2 test methods)
  - SPECIFICATION.md §3.1 and §5.1 updated (dojo_instructor_dashboard implemented)
test_data:
  seed: n/a
  migration_before_state: n/a
  external_stubs: n/a
  credentials: n/a
reset:
  - bash testenv/reset.sh
gate:
  - docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http -i dojo_instructor_dashboard --test-enable --test-file addons/dojo_instructor_dashboard/tests/test_dashboard_controller.py --stop-after-init
  - curl -sf http://127.0.0.1:8070/web/login -o /dev/null
regression_gate:
  - bash testenv/verify.sh
  - docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http -u dojo_core,dojo_kiosk,dojo_instructor_dashboard --test-enable --stop-after-init
```

---

## INC-13 — mass-promote: belt promotion with undo and history

Implement `dojo_belt_progression` module (currently a stub): OWL view for mass belt promotion, in-session undo, and a promotion history log per member.

**Decision rules:**
- Module manifest: `name: dojo_belt_progression, version: saas~19.2.1.0.0, depends: [dojo_core, dojo_theme, web]`.
- Mass promote view: a filterable grid of `dojo.member` records showing current belt rank. Instructor selects members (multi-checkbox), chooses target rank from a dropdown, clicks Promote All. Creates `dojo.member.rank` records for each selected member.
- Undo: client-side in-memory stack (JS array of promoted member IDs + previous rank). Undo button visible while stack is non-empty. Undo reverses the most recent promote action by deleting the created `dojo.member.rank` records and restoring previous rank.
- Undo is session-scoped only — no undo after page reload.
- Promotion history: read-only list view showing the member's `dojo.member.rank` records sorted by `date desc`. Columns: date, from_rank, to_rank, promoted_by (user name).
- Write tests in `addons/dojo_belt_progression/tests/test_mass_promote.py` covering: promote one member advances rank, promote multiple members, undo reverts last promotion.

```yaml
id: INC-13
title: dojo_belt_progression mass promote and history
depends_on: [INC-07]
touchpoints:
  - addons/dojo_belt_progression/**
  - SPECIFICATION.md
deliverables:
  - addons/dojo_belt_progression/__manifest__.py
  - addons/dojo_belt_progression/controllers/promotion.py (promote and undo endpoints)
  - addons/dojo_belt_progression/static/src/js/mass_promote.js (OWL component)
  - addons/dojo_belt_progression/views/mass_promote.xml (QWeb + menu entry)
  - addons/dojo_belt_progression/views/assets.xml
  - Promotion history view (read-only list of dojo.member.rank)
  - addons/dojo_belt_progression/tests/test_mass_promote.py (≥3 test methods)
  - SPECIFICATION.md §3.5 removed from stubs, §5 updated
test_data:
  seed: n/a
  migration_before_state: n/a
  external_stubs: n/a
  credentials: n/a
reset:
  - bash testenv/reset.sh
gate:
  - docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http -i dojo_belt_progression --test-enable --test-file addons/dojo_belt_progression/tests/test_mass_promote.py --stop-after-init
  - curl -sf http://127.0.0.1:8070/web/login -o /dev/null
regression_gate:
  - bash testenv/verify.sh
  - docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http -u dojo_core,dojo_kiosk,dojo_instructor_dashboard,dojo_belt_progression --test-enable --stop-after-init
```

---

## INC-14 — belt-test-roster: test roster with print view and saved records

Add belt test roster functionality to `dojo_belt_progression`: filterable roster view, print-ready CSS, and roster persistence via `dojo.belt.test` records.

**Decision rules:**
- Roster view: filter members by class group (from `dojo.class.enrollment`) and/or minimum belt rank. Display: member name, current belt rank, last promotion date.
- Print view: `@media print` CSS that hides navigation and renders the roster as a clean table. Triggered by `window.print()` from a Print button.
- Save roster: populate a `dojo.belt.test` record with the filtered member set (as `dojo.belt.test.registration` records). Use existing `dojo.belt.test` model from `dojo_core`.
- Saved rosters are accessible via a list view of `dojo.belt.test` records, showing name, date, and registration count.
- Write tests in `addons/dojo_belt_progression/tests/test_belt_test_roster.py` covering: filtering by class group returns correct members, save roster creates dojo.belt.test record with correct registrations.

```yaml
id: INC-14
title: belt test roster with print view and saved records
depends_on: [INC-13]
touchpoints:
  - addons/dojo_belt_progression/controllers/roster.py
  - addons/dojo_belt_progression/static/src/js/belt_test_roster.js
  - addons/dojo_belt_progression/static/src/css/roster_print.css
  - addons/dojo_belt_progression/views/belt_test_roster.xml
  - addons/dojo_belt_progression/tests/test_belt_test_roster.py
  - SPECIFICATION.md
deliverables:
  - Belt test roster OWL view with class group and belt rank filters
  - Print-ready CSS (@media print)
  - Save roster → dojo.belt.test record
  - Saved roster list view
  - Test file with ≥2 test methods
  - SPECIFICATION.md §5 updated
test_data:
  seed: n/a
  migration_before_state: n/a
  external_stubs: n/a
  credentials: n/a
reset:
  - bash testenv/reset.sh
gate:
  - docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http -u dojo_belt_progression --test-enable --test-file addons/dojo_belt_progression/tests/test_belt_test_roster.py --stop-after-init
  - curl -sf http://127.0.0.1:8070/web/login -o /dev/null
regression_gate:
  - bash testenv/verify.sh
  - docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http -u dojo_core,dojo_kiosk,dojo_instructor_dashboard,dojo_belt_progression --test-enable --stop-after-init
```

---

## INC-15 — attendance-analytics: analytics views

Add attendance analytics to `dojo_instructor_dashboard`: busiest sessions, top attending members, inactive members.

**Decision rules:**
- Analytics data controller at `/instructor_dashboard/analytics` (GET, require login). Accepts query params: `days=30` (or `90`). Returns: top 10 sessions by check-in count, top 10 members by check-in count, members with zero attendance in the period.
- OWL component renders three sections: "Busiest Classes" (bar list), "Most Attendance" (member list), "Inactive Members" (member list with last-seen date).
- `Inactive Members` uses `dojo.member` left-joined to `dojo.attendance.log` where log date >= (today - days). Members with no matching log rows are inactive.
- Time period selector (30 days / 90 days) in the UI. Default 30.
- Write Python tests in `addons/dojo_instructor_dashboard/tests/test_analytics.py` covering: controller returns expected keys, inactive list excludes members with recent attendance.

```yaml
id: INC-15
title: attendance analytics views
depends_on: [INC-07]
touchpoints:
  - addons/dojo_instructor_dashboard/controllers/analytics.py
  - addons/dojo_instructor_dashboard/static/src/js/analytics.js
  - addons/dojo_instructor_dashboard/views/analytics.xml
  - addons/dojo_instructor_dashboard/tests/test_analytics.py
  - SPECIFICATION.md
deliverables:
  - GET /instructor_dashboard/analytics controller
  - Analytics OWL component with three sections and time period selector
  - Test file with ≥2 test methods
  - SPECIFICATION.md §5.1 updated with analytics description
test_data:
  seed: n/a
  migration_before_state: n/a
  external_stubs: n/a
  credentials: n/a
reset:
  - bash testenv/reset.sh
gate:
  - docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http -u dojo_instructor_dashboard --test-enable --test-file addons/dojo_instructor_dashboard/tests/test_analytics.py --stop-after-init
  - curl -sf http://127.0.0.1:8070/web/login -o /dev/null
regression_gate:
  - bash testenv/verify.sh
  - docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http -u dojo_core,dojo_kiosk,dojo_instructor_dashboard,dojo_belt_progression --test-enable --stop-after-init
```

---

## INC-16 — reports: Inactive Student, Contact, and Family reports

Implement `dojo_members` module (currently a stub) with three report views: Inactive Student, Contact, Family.

**Decision rules:**
- Module manifest: `name: dojo_members, version: saas~19.2.1.0.0, depends: [dojo_core, dojo_theme, web]`.
- Inactive Student report: list of members with no `dojo.attendance.log` in the last N days (configurable via a UI input, default 30). Columns: name, belt rank, expdate, last check-in date.
- Contact report: list of members where `res.partner` linked to member has no email OR no phone. Columns: member name, parent/guardian name, email, phone. Missing values highlighted in `var(--orange)`.
- Family report: members grouped by household (shared `res.partner` parent). Show household name, member count, members list.
- Each report rendered as an OWL list view inside the `dojo_members` menu. Filter controls at top of each view.
- Write tests in `addons/dojo_members/tests/test_reports.py` covering: inactive report excludes member with recent attendance, contact report flags member with no email.

```yaml
id: INC-16
title: dojo_members Inactive, Contact, and Family reports
depends_on: [INC-07]
touchpoints:
  - addons/dojo_members/**
  - SPECIFICATION.md
deliverables:
  - addons/dojo_members/__manifest__.py
  - addons/dojo_members/controllers/reports.py (report data endpoints)
  - addons/dojo_members/static/src/js/reports.js (three OWL report components)
  - addons/dojo_members/views/reports.xml (QWeb templates + menu entries)
  - addons/dojo_members/views/assets.xml
  - addons/dojo_members/tests/test_reports.py (≥2 test methods)
  - SPECIFICATION.md §3.5 updated (dojo_members removed from stubs), §5 updated
test_data:
  seed: n/a
  migration_before_state: n/a
  external_stubs: n/a
  credentials: n/a
reset:
  - bash testenv/reset.sh
gate:
  - docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http -i dojo_members --test-enable --test-file addons/dojo_members/tests/test_reports.py --stop-after-init
  - curl -sf http://127.0.0.1:8070/web/login -o /dev/null
regression_gate:
  - bash testenv/verify.sh
  - docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http -u dojo_core,dojo_kiosk,dojo_instructor_dashboard,dojo_belt_progression,dojo_members --test-enable --stop-after-init
```

---

## INC-17 — csv-export: data export wizard

Add a CSV export transient wizard accessible from the dashboard and reports. Exports: students, attendance log, promotion history, belt test rosters.

**Decision rules:**
- Transient model `dojo.export.wizard` in `dojo_instructor_dashboard` (extend the existing module, do not create a new one). Fields: `export_type` (Selection: students, attendance, promotions, rosters), `date_from` (Date, optional), `date_to` (Date, optional).
- Controller at `/instructor_dashboard/export` (GET). Accepts params: `type`, `date_from`, `date_to`. Returns `Content-Type: text/csv` with `Content-Disposition: attachment; filename=<type>_<date>.csv`.
- Students export: all `dojo.member` fields: name, expdate, current_belt_rank, active, email, phone, parent_name, parent_email. One row per member.
- Attendance export: `dojo.attendance.log` records within date range. Columns: date, member_name, session_name, status.
- Promotions export: `dojo.member.rank` records within date range. Columns: date, member_name, from_rank, to_rank, promoted_by.
- Rosters export: `dojo.belt.test` records with `dojo.belt.test.registration` rows. Columns: test_name, test_date, member_name, belt_rank.
- Write tests in `addons/dojo_instructor_dashboard/tests/test_export.py` covering: students export returns CSV with header row, attendance export respects date range.

```yaml
id: INC-17
title: CSV export wizard
depends_on: [INC-16]
touchpoints:
  - addons/dojo_instructor_dashboard/models/export_wizard.py
  - addons/dojo_instructor_dashboard/controllers/export.py
  - addons/dojo_instructor_dashboard/views/export_wizard.xml
  - addons/dojo_instructor_dashboard/tests/test_export.py
  - SPECIFICATION.md
deliverables:
  - dojo.export.wizard transient model
  - GET /instructor_dashboard/export controller returning CSV
  - Export button accessible from dashboard and report views
  - Test file with ≥2 test methods
  - SPECIFICATION.md §5 updated with export description
test_data:
  seed: n/a
  migration_before_state: n/a
  external_stubs: n/a
  credentials: n/a
reset:
  - bash testenv/reset.sh
gate:
  - docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http -u dojo_instructor_dashboard --test-enable --test-file addons/dojo_instructor_dashboard/tests/test_export.py --stop-after-init
  - curl -sf http://127.0.0.1:8070/web/login -o /dev/null
regression_gate:
  - bash testenv/verify.sh
  - docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http -u dojo_core,dojo_kiosk,dojo_instructor_dashboard,dojo_belt_progression,dojo_members --test-enable --stop-after-init
```

---

## INC-18 — email-center: mass email and history in dojo_communications

Add an Email Center view to `dojo_communications`: audience segment selector, email composer, send action, and email history log.

**Decision rules:**
- Email Center is an OWL view inside `dojo_communications`. Menu entry: Communications → Email Center.
- Audience segment options: By class group (uses `dojo.class.enrollment`), by belt rank (uses `dojo.member.rank`), by expiring membership (`expdate` within N days), all active members.
- Compose area: Subject (text), Body (textarea, no rich text editor — plain text only to keep implementation simple).
- Send action: creates `mail.mail` records via `env['mail.mail'].create(...)` for each recipient, calls `.send()`. Outgoing mail server must be configured on the Odoo instance (not in scope to configure here — document as post-release step).
- Email history: a new model `dojo.email.history` (id, send_date, subject, sender_id m2o res.users, recipient_count int, audience_type char). One record per batch send. List view in Email Center.
- Write tests in `addons/dojo_communications/tests/test_email_center.py` covering: audience by class group returns correct member count, send creates dojo.email.history record with correct recipient_count. Use Odoo test mail mode (no real sends).

```yaml
id: INC-18
title: Email Center with audience segmentation and history
depends_on: [INC-16]
touchpoints:
  - addons/dojo_communications/models/email_history.py
  - addons/dojo_communications/controllers/email_center.py
  - addons/dojo_communications/static/src/js/email_center.js
  - addons/dojo_communications/views/email_center.xml
  - addons/dojo_communications/views/assets.xml
  - addons/dojo_communications/tests/test_email_center.py
  - SPECIFICATION.md
deliverables:
  - dojo.email.history model
  - Email Center OWL view with audience selector and composer
  - Send action creating mail.mail records and dojo.email.history record
  - Email history list view
  - Test file with ≥2 test methods
  - SPECIFICATION.md §5.6 updated
test_data:
  seed: n/a
  migration_before_state: n/a
  external_stubs: n/a — mail.mail.send() intercepted by Odoo test mode
  credentials: n/a
reset:
  - bash testenv/reset.sh
gate:
  - docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http -u dojo_communications --test-enable --test-file addons/dojo_communications/tests/test_email_center.py --stop-after-init
  - curl -sf http://127.0.0.1:8070/web/login -o /dev/null
regression_gate:
  - bash testenv/verify.sh
  - docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http -u dojo_core,dojo_kiosk,dojo_instructor_dashboard,dojo_belt_progression,dojo_members,dojo_communications --test-enable --stop-after-init
```

---

## INC-19 — inactive-followup: follow-up email from Inactive Report

Add a "Send Follow-up" action to the Inactive Student report (INC-16) that pre-populates and sends an email to selected members.

**Decision rules:**
- Follow-up action in `dojo_members` Inactive Report: a "Send Follow-up Email" button that activates when members are selected. Opens a simple confirmation dialog (member count, preview of template subject).
- On confirm: calls `dojo_communications` Email Center send logic for the selected member subset. Audience type recorded in `dojo.email.history` as `inactive_followup`.
- Default template subject: "We miss you at United Family Taekwondo!". Template body is a configurable `ir.config_parameter` key `dojo.inactive_followup_body`. If not set, use a default string.
- No new OWL component needed — reuse Email Center send logic via a new controller endpoint `POST /dojo_members/send_followup` that accepts a list of member IDs.
- Write tests in `addons/dojo_members/tests/test_followup_email.py` covering: send_followup endpoint creates dojo.email.history for given member IDs.

```yaml
id: INC-19
title: follow-up email action in Inactive Student report
depends_on: [INC-18]
touchpoints:
  - addons/dojo_members/controllers/followup.py
  - addons/dojo_members/static/src/js/reports.js
  - addons/dojo_members/views/reports.xml
  - addons/dojo_members/tests/test_followup_email.py
  - SPECIFICATION.md
deliverables:
  - POST /dojo_members/send_followup endpoint
  - Send Follow-up button and confirmation dialog in Inactive Report OWL component
  - Test file with ≥1 test method
  - SPECIFICATION.md §5.6 updated
test_data:
  seed: n/a
  migration_before_state: n/a
  external_stubs: n/a
  credentials: n/a
reset:
  - bash testenv/reset.sh
gate:
  - docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http -u dojo_members --test-enable --test-file addons/dojo_members/tests/test_followup_email.py --stop-after-init
  - curl -sf http://127.0.0.1:8070/web/login -o /dev/null
regression_gate:
  - bash testenv/verify.sh
  - docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http -u dojo_core,dojo_kiosk,dojo_instructor_dashboard,dojo_belt_progression,dojo_members,dojo_communications --test-enable --stop-after-init
```

---

## INC-20 — birthday-automation: automated birthday email via OCA automation

Add an OCA automation rule that fires daily, finds members with a birthday today (or within N configured days), and sends a templated birthday email.

**Decision rules:**
- Automation rule defined in `dojo_automation` module as a data XML record (`automation.rule` or `base.automation` depending on what `automation_oca` provides). Model: `dojo.member`, trigger: `on_time`, `trg_date_id` referencing a computed date field for birthday-this-year.
- If `automation_oca` does not support a birthday-year-aware trigger, implement as `ir.cron` in `dojo_automation` instead. Decision: check `automation_oca` model API at development time; if `base.automation` supports a `code` action, use it; otherwise use `ir.cron`.
- Email template as `mail.template` record in `dojo_automation` data XML: subject "Happy Birthday from United Family Taekwondo!", body configurable via the template.
- Configuration: `ir.config_parameter` key `dojo.birthday_email_days_ahead` (default 0 = on birthday only). If 0, match `birthday_day == today`. If N > 0, match within next N days.
- Write tests in `addons/dojo_automation/tests/test_birthday_automation.py` covering: birthday detection method returns correct members for today's date.

```yaml
id: INC-20
title: birthday email automation rule
depends_on: [INC-18]
touchpoints:
  - addons/dojo_automation/data/birthday_automation.xml
  - addons/dojo_automation/data/birthday_template.xml
  - addons/dojo_automation/tests/test_birthday_automation.py
  - SPECIFICATION.md
deliverables:
  - automation.rule or ir.cron record for daily birthday email
  - mail.template for birthday email
  - ir.config_parameter for days-ahead setting
  - Test file with ≥1 test method
  - SPECIFICATION.md §5.7 updated
test_data:
  seed: n/a
  migration_before_state: n/a
  external_stubs: n/a
  credentials: n/a
reset:
  - bash testenv/reset.sh
gate:
  - docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http -u dojo_automation --test-enable --test-file addons/dojo_automation/tests/test_birthday_automation.py --stop-after-init
  - curl -sf http://127.0.0.1:8070/web/login -o /dev/null
regression_gate:
  - bash testenv/verify.sh
  - docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http -u dojo_core,dojo_kiosk,dojo_instructor_dashboard,dojo_belt_progression,dojo_members,dojo_communications,dojo_automation --test-enable --stop-after-init
```

---

## INC-21 — expiry-automation: automated membership expiry warning email

Add an OCA automation rule (or `ir.cron`) that fires daily, finds members with `expdate` within N days, and sends a templated expiry warning email.

**Decision rules:**
- Same implementation pattern as INC-20. Model: `dojo.member`, filter: `expdate` between today and today + N days.
- Configuration: `ir.config_parameter` key `dojo.expiry_warning_days` (default 14).
- Email template: subject "Your United Family Taekwondo membership is expiring soon". Body configurable via the template.
- Do not send to members whose `expdate` has already passed (only future-expiring).
- Write tests in `addons/dojo_automation/tests/test_expiry_automation.py` covering: expiry detection method returns members expiring within N days and excludes already-expired members.

```yaml
id: INC-21
title: membership expiry warning automation rule
depends_on: [INC-18]
touchpoints:
  - addons/dojo_automation/data/expiry_automation.xml
  - addons/dojo_automation/data/expiry_template.xml
  - addons/dojo_automation/tests/test_expiry_automation.py
  - SPECIFICATION.md
deliverables:
  - automation.rule or ir.cron record for daily expiry warning email
  - mail.template for expiry warning
  - ir.config_parameter for days-ahead threshold
  - Test file with ≥1 test method
  - SPECIFICATION.md §5.7 updated
test_data:
  seed: n/a
  migration_before_state: n/a
  external_stubs: n/a
  credentials: n/a
reset:
  - bash testenv/reset.sh
gate:
  - docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http -u dojo_automation --test-enable --test-file addons/dojo_automation/tests/test_expiry_automation.py --stop-after-init
  - curl -sf http://127.0.0.1:8070/web/login -o /dev/null
regression_gate:
  - bash testenv/verify.sh
  - docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http -u dojo_core,dojo_kiosk,dojo_instructor_dashboard,dojo_belt_progression,dojo_members,dojo_communications,dojo_automation --test-enable --stop-after-init
```

---

## INC-22 — muk-audit: document MuK replacement coverage

Audit which MuK modules have equivalent coverage in `dojo_theme` and the new OWL components. Produce the uninstall order for INC-23. This is a documentation-and-verification increment — no production code changes.

**Decision rules:**
- Produce `releases/REL-001/muk-audit.md` documenting: for each of the 7 MuK modules, what functionality it provides and what in `dojo_theme` or new OWL components replaces it.
- Identify any MuK functionality not yet replaced. If gaps exist, add implementation to INC-23 scope (worker updates this plan entry's INC-23 deliverables).
- Verify that no installed non-MuK module lists a `muk_web_*` module in its `depends` list. Command: `grep -r "muk_web_" addons/*/\_\_manifest\_\_.py`.
- If any custom module depends on MuK, that dependency must be removed in INC-23 before uninstalling MuK. Document all such modules.
- Gate: audit document exists and the grep finds no MuK dependencies in custom modules (or documents them for INC-23 to resolve).

```yaml
id: INC-22
title: MuK audit — replacement coverage check
depends_on: [INC-21]
touchpoints:
  - releases/REL-001/muk-audit.md
  - SPECIFICATION.md
deliverables:
  - releases/REL-001/muk-audit.md documenting per-module replacement status
  - List of any custom modules depending on muk_web_* (empty is fine)
  - INC-23 deliverables updated if gaps found
  - SPECIFICATION.md §3.4 annotated with retirement status
test_data:
  seed: n/a
  migration_before_state: n/a
  external_stubs: n/a
  credentials: n/a
reset:
  - bash testenv/reset.sh
gate:
  - test -f releases/REL-001/muk-audit.md
  - bash -c "deps=$(grep -rl 'muk_web_' addons/dojo_*/\__manifest__.py addons/ai_*/\__manifest__.py 2>/dev/null | wc -l); echo \"MuK deps in custom modules: $deps\"; test \"$deps\" -eq 0"
  - curl -sf http://127.0.0.1:8070/web/login -o /dev/null
regression_gate:
  - bash testenv/verify.sh
```

---

## INC-23 — muk-retire: uninstall and remove all MuK modules

Uninstall all 7 `muk_web_*` modules from the `odoo19` database and remove their directories from `addons/`. Update `docs/ui-ux-guide.md` to document the `dojo_theme` token system.

**Decision rules:**
- Uninstall order (reverse dependency order): `muk_web_appsbar`, `muk_web_colors`, `muk_web_dialog`, `muk_web_group`, `muk_web_refresh`, `muk_web_chatter`, `muk_web_theme`. Uninstall one at a time via Odoo shell or `-u` with `--uninstall-module` if available; otherwise use RPC: `env['ir.module.module'].search([('name','=','muk_web_appsbar')]).button_uninstall()` per module.
- After uninstalling all 7, verify none appear in `ir.module.module` with `state = 'installed'`.
- Remove all 7 directories from `addons/`.
- Replace `docs/ui-ux-guide.md` content with `dojo_theme` token documentation: list all 15 CSS custom properties with their values and intended use. Document typography (Bebas Neue, Barlow, Barlow Condensed). Remove all MuK references.
- If uninstall of any module raises `UserError` (blocked by dependency): check `ir.module.module.downstream_dependencies()`, uninstall the blocker first. If the blocker is a custom module, remove its MuK dependency and re-upgrade it before retrying.
- Gate must confirm: no `muk_web_*` in installed modules, no `muk_web_*` dirs in `addons/`, Odoo backend loads cleanly.

```yaml
id: INC-23
title: MuK theme modules uninstalled and removed
depends_on: [INC-22]
touchpoints:
  - addons/muk_web_theme/**
  - addons/muk_web_chatter/**
  - addons/muk_web_appsbar/**
  - addons/muk_web_colors/**
  - addons/muk_web_dialog/**
  - addons/muk_web_group/**
  - addons/muk_web_refresh/**
  - docs/ui-ux-guide.md
  - SPECIFICATION.md
deliverables:
  - All 7 muk_web_* modules uninstalled from odoo19 database
  - All 7 muk_web_* directories removed from addons/
  - docs/ui-ux-guide.md rewritten with dojo_theme token documentation
  - SPECIFICATION.md §3.4 updated (MuK removed), §10.1 updated (current state = dojo_theme), §12 tech debt items resolved
test_data:
  seed: n/a
  migration_before_state: n/a
  external_stubs: n/a
  credentials: n/a
reset:
  - bash testenv/reset.sh
gate:
  - bash -c "count=$(docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http --stop-after-init -e \"print(env['ir.module.module'].search([('name','like','muk_web_'),('state','=','installed')]).mapped('name'))\" 2>/dev/null | grep -c 'muk_web_' || echo 0); test \"$count\" -eq 0"
  - bash -c "for mod in muk_web_theme muk_web_chatter muk_web_appsbar muk_web_colors muk_web_dialog muk_web_group muk_web_refresh; do test ! -d \"addons/$mod\" && echo \"$mod removed\" || (echo \"$mod still present\" && exit 1); done"
  - curl -sf http://127.0.0.1:8070/web/login -o /dev/null
  - test -f docs/ui-ux-guide.md
  - grep -q "dojo_theme" docs/ui-ux-guide.md
  - grep -vq "muk_web_" docs/ui-ux-guide.md
regression_gate:
  - bash testenv/verify.sh
  - docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http -u dojo_core,dojo_kiosk,dojo_theme,dojo_instructor_dashboard,dojo_belt_progression,dojo_members,dojo_communications,dojo_automation --test-enable --stop-after-init
```
