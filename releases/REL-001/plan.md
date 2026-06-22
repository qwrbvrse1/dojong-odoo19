# Release Plan — REL-001: UFTKD Platform Feature Delivery

> Prose sections are for humans. Fenced `yaml` blocks are parsed by `apev-run.sh`.
> Block 1 = release config. Each subsequent block = one increment, in execution order.
> Do not put status in this file — execution state lives in the run log.

## Release configuration

```yaml
release: REL-001
branch: rel/REL-001
worker_model: claude
alternate_model: codex
max_shots: 3
halt_on_fail: downstream
workproducts: ~/workproducts/dojong-odoo19/REL-001
baseline_gate:
  - bash testenv/verify.sh
  - test -d addons/sms_twilio && test -f addons/sms_twilio/__manifest__.py
```

## Milestone map

| Milestone | Increments | First depends on |
|---|---|---|
| M0 — Infrastructure | INC-01 – INC-02 | baseline_gate |
| M1 — Backend Logic | INC-03 – INC-06 | INC-01 (theme must exist before backend that references its assets) |
| M2 — Daily Operations UI | INC-07 – INC-12 | INC-06 (all M1 backend changes must be present) |
| M3 — Instructor Tools | INC-13 – INC-17 | INC-07 (dashboard module provides shared OWL patterns) |
| M4 — Communication & Automation | INC-18 – INC-21 | INC-16 (Inactive Report feeds follow-up email) |
| M5 — MuK Retirement | INC-22 – INC-23 | INC-21 (all UI work done before retiring MuK) |

## Dependency analysis

M0 increments (INC-01–02) have no inter-dependencies and run in file order. INC-01 (`dojo_theme`) is listed first because M1+ increments that reference theme assets need it installed first; for safety all M1 increments declare `depends_on: [INC-02]` (the last M0 increment), ensuring M0 fully passes before any backend work begins.

Within M1, INC-03–06 have no hard inter-dependencies and can fail independently (each is a self-contained backend change). M2 begins at INC-07 and all M2 increments declare `depends_on: [INC-06]` (the last M1 increment).

Within M2, the three-panel kiosk layout (INC-08) is a prerequisite for INC-09, INC-10, INC-11, INC-12 which all modify the same kiosk OWL component tree. INC-07 (dashboard) is independent of the kiosk changes and is declared first.

M3 increments declare `depends_on: [INC-07]`. Within M3, INC-17 (CSV export) depends on INC-15 and INC-16 (the data it exports must exist).

M4 increments declare `depends_on: [INC-16]`. INC-19 (inactive follow-up) depends on INC-18 (Email Center must exist). INC-20 and INC-21 depend on INC-18.

M5 starts at INC-22 (MuK audit) which depends on INC-21 (all M4 done). INC-23 (MuK retire) depends on INC-22.

---

## INC-01 — dojo_theme: CSS token module scaffold

Create the `dojo_theme` Odoo module. This is a CSS-only module with no Python models. It injects the brand design token system (CSS custom properties) and typography (Google Fonts) into all Odoo backend views via the asset bundle override mechanism.

**Decision rules:**
- Use `assets_backend` bundle for all CSS injections — never `assets_common` or `assets_frontend` (those affect the portal/website, out of scope).
- Load fonts from Google Fonts CDN via `<link>` tag in a QWeb template override, not via `@import` in CSS (Odoo's asset pipeline does not resolve external `@import` reliably).
- CSS file must define all 15 design tokens as `:root` custom properties. Do not use Odoo's SCSS variable system — plain CSS only.
- If the module installs but the tokens are not visible (gate step 3 fails), the cause is the asset bundle name — check `ir.asset` records and correct the bundle key.
- Do not modify `muk_web_theme` — `dojo_theme` coexists with MuK until Milestone 5.

```yaml
id: INC-01
title: dojo_theme CSS token module
depends_on: []
touchpoints:
  - addons/dojo_theme/**
  - SPECIFICATION.md
deliverables:
  - addons/dojo_theme/__manifest__.py (name dojo_theme, version saas~19.2.1.0.0, depends web)
  - addons/dojo_theme/__init__.py (empty)
  - addons/dojo_theme/static/src/css/tokens.css (all 15 CSS custom properties on :root, all belt rank color variables)
  - addons/dojo_theme/views/assets.xml (ir.asset records injecting tokens.css into assets_backend bundle)
  - addons/dojo_theme/views/fonts.xml (QWeb template override loading Bebas Neue + Barlow + Barlow Condensed from Google Fonts CDN)
  - SPECIFICATION.md §3.1 updated to list dojo_theme
test_data:
  seed: n/a
  migration_before_state: n/a
  external_stubs: n/a
  credentials: n/a
reset:
  - bash testenv/reset.sh
gate:
  - docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http -i dojo_theme --stop-after-init
  - curl -sf http://127.0.0.1:8070/web/login -o /dev/null
  - docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http --stop-after-init -e "print(env['ir.module.module'].search([('name','=','dojo_theme'),('state','=','installed')]).name)"
regression_gate:
  - bash testenv/verify.sh
```

---

## INC-02 — sms_twilio: add to version control

Add the `sms_twilio` module (copied from production VM) to `addons/` and verify it installs cleanly in the dev environment. This brings a production-critical module under version tracking for the first time.

**Decision rules:**
- Do not modify `sms_twilio` source. Add as-is from production.
- If the module manifest declares a version incompatible with saas~19.2, do not change the manifest. Record the version as-is and let the install gate reveal any issues.
- If install fails with a dependency error, check that all declared dependencies are present in the database. If a dependency is a missing third-party module, classify `plan_defect` — the dependency must be added to prerequisites.
- Do not install `sms_twilio` if it is already installed (check state first; upgrade only if installed).

```yaml
id: INC-02
title: sms_twilio added to version control
depends_on: []
touchpoints:
  - addons/sms_twilio/**
  - SPECIFICATION.md
deliverables:
  - addons/sms_twilio/ present with all source files from production
  - Module installs without error in odoo19 database
  - SPECIFICATION.md §3.3 updated to note sms_twilio is now version-tracked
test_data:
  seed: n/a
  migration_before_state: n/a
  external_stubs: n/a
  credentials: n/a
reset:
  - bash testenv/reset.sh
gate:
  - test -f addons/sms_twilio/__manifest__.py
  - docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http -i sms_twilio --stop-after-init
  - curl -sf http://127.0.0.1:8070/web/login -o /dev/null
regression_gate:
  - bash testenv/verify.sh
  - docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http -u dojo_theme --stop-after-init
```

---

## INC-03 — lastname-search: surname-first name lookup

Override `_name_search` on `dojo.member` to parse the search query, identify the last whitespace-delimited token as a probable surname, and rank surname-first matches above mid-name matches using SQL `ORDER BY CASE`.

**Decision rules:**
- Override `_name_search` on `dojo.member`, not on `res.partner`. The kiosk calls `dojo.member` search methods directly.
- Add a stored computed field `last_name` (Char, compute `_compute_last_name`, store=True, index=True) that extracts the last space-delimited token from `name`. This field is used only for the index; it does not replace `name` anywhere in views.
- The `_name_search` override must fall back to the standard `ilike` search for single-token queries (no space) to avoid breaking existing behavior.
- Write Python unit tests in `addons/dojo_core/tests/test_member_search.py` covering: single-name search, surname-first ("Smith"), full-name search ("John Smith"), partial surname ("Smi"), no results.
- If `res.partner` has a conflicting `_name_search`, the `dojo.member` override takes precedence — do not modify `res.partner`.

```yaml
id: INC-03
title: dojo.member surname-first name search
depends_on: [INC-02]
touchpoints:
  - addons/dojo_core/models/member.py
  - addons/dojo_core/tests/test_member_search.py
  - SPECIFICATION.md
deliverables:
  - dojo.member._name_search override with surname-first ranking logic
  - dojo.member.last_name stored computed field with pg index
  - Test file addons/dojo_core/tests/test_member_search.py with ≥5 test methods
  - SPECIFICATION.md §5.1 updated to describe surname-first search
test_data:
  seed: n/a (testenv/reset.sh installs dojo_core with demo data)
  migration_before_state: n/a
  external_stubs: n/a
  credentials: n/a
reset:
  - bash testenv/reset.sh
gate:
  - docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http -u dojo_core --test-enable --test-file addons/dojo_core/tests/test_member_search.py --stop-after-init
  - curl -sf http://127.0.0.1:8070/web/login -o /dev/null
regression_gate:
  - bash testenv/verify.sh
  - docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http -u dojo_core --test-enable --stop-after-init
```

---

## INC-04 — onboarding-kiosk-api: expose onboarding in member profile

Extend `get_member_profile()` in `dojo_kiosk/services/dojo_kiosk_service.py` to include onboarding record data. Add two new kiosk API endpoints for onboarding step actions.

**Decision rules:**
- If a member has no `dojo.onboarding.record`, return `onboarding: null` in the profile dict — do not raise.
- New endpoints must be authenticated with the same kiosk token mechanism as existing kiosk endpoints. Reject unauthenticated calls with HTTP 403.
- `complete_step` accepts `{"step": "<step_name>"}`. Valid step names are: `member_info`, `household`, `class_enrollment`, `subscription`, `portal_access`. Invalid step name → HTTP 400, do not raise.
- `send_reminder` sends a mail to the member's primary contact email using `env['mail.mail'].create(...).send()`. If no email on record, return `{"error": "no_email"}` — do not raise.
- Write tests in `addons/dojo_kiosk/tests/test_kiosk_onboarding_api.py` covering: profile includes onboarding dict, complete_step marks step done, send_reminder with email, send_reminder without email returns error.

```yaml
id: INC-04
title: onboarding data in kiosk member profile API
depends_on: [INC-02]
touchpoints:
  - addons/dojo_kiosk/services/dojo_kiosk_service.py
  - addons/dojo_kiosk/controllers/kiosk_controller.py
  - addons/dojo_kiosk/tests/test_kiosk_onboarding_api.py
  - SPECIFICATION.md
deliverables:
  - get_member_profile() returns onboarding dict with step statuses and progress_pct
  - POST /kiosk/api/onboarding/complete_step endpoint
  - POST /kiosk/api/onboarding/send_reminder endpoint
  - Test file with ≥4 test methods
  - SPECIFICATION.md §6 (Kiosk) updated with onboarding API shape
test_data:
  seed: n/a
  migration_before_state: n/a
  external_stubs: n/a — mail.mail.send() is intercepted by Odoo test mode; no real email sent
  credentials: n/a
reset:
  - bash testenv/reset.sh
gate:
  - docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http -u dojo_kiosk --test-enable --test-file addons/dojo_kiosk/tests/test_kiosk_onboarding_api.py --stop-after-init
  - curl -sf http://127.0.0.1:8070/web/login -o /dev/null
regression_gate:
  - bash testenv/verify.sh
  - docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http -u dojo_core,dojo_kiosk --test-enable --stop-after-init
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

```yaml
id: INC-05
title: time_state field on kiosk session list
depends_on: [INC-02]
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

## INC-06 — member-expdate: stored computed expiration date field

Add a stored computed `expdate` (Date) field to `dojo.member`. Field derives from the linked subscription plan's next invoice / expiry date. Indexed for list view filtering.

**Decision rules:**
- Field name: `expdate` (matches prototype schema and scope.md). Type: `fields.Date`, compute=`_compute_expdate`, store=True, index=True.
- Compute logic: find the active `dojo.program.enrollment` linked to the member that has a subscription expiry or next billing date; use whichever is latest. If no active enrollment, set `expdate = False`.
- Trigger: `@api.depends('program_enrollment_ids.state', 'program_enrollment_ids.date_end')` — recomputes when enrollment state changes.
- If `dojo.program.enrollment` does not have a `date_end` field, use `subscription_id.next_invoice_date` from the linked OCA subscription. If that is also absent, set `expdate = False`.
- Write tests in `addons/dojo_core/tests/test_member_expdate.py` covering: member with active enrollment has expdate set, member without enrollment has expdate False, expdate updates when enrollment state changes.

```yaml
id: INC-06
title: dojo.member.expdate stored computed field
depends_on: [INC-02]
touchpoints:
  - addons/dojo_core/models/member.py
  - addons/dojo_core/tests/test_member_expdate.py
  - SPECIFICATION.md
deliverables:
  - dojo.member.expdate (Date, stored, indexed)
  - _compute_expdate method on dojo.member
  - Test file with ≥3 test methods
  - SPECIFICATION.md §4.1 updated to add expdate field description
test_data:
  seed: n/a
  migration_before_state: n/a
  external_stubs: n/a
  credentials: n/a
reset:
  - bash testenv/reset.sh
gate:
  - docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http -u dojo_core --test-enable --test-file addons/dojo_core/tests/test_member_expdate.py --stop-after-init
  - curl -sf http://127.0.0.1:8070/web/login -o /dev/null
regression_gate:
  - bash testenv/verify.sh
  - docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http -u dojo_core,dojo_kiosk --test-enable --stop-after-init
```

---

## INC-07 — dashboard: instructor dashboard module

Implement `dojo_instructor_dashboard` as a full Odoo module (manifest, OWL views, controllers). Provides a backend view with stat cards, belt distribution, upcoming birthdays, and expiring memberships.

**Decision rules:**
- Module depends on: `dojo_core`, `dojo_theme`, `web`. Do not depend on `dojo_subscriptions` directly — use `expdate` from `dojo.member` (INC-06) for expiry filtering.
- Four stat cards: total active members (`dojo.member` where `active=True`), today's check-in count (`dojo.attendance.log` where `date=today`), birthdays in 7 days (members where birthday within next 7 calendar days), expiring in 30 days (members where `expdate` within next 30 days and `expdate` is set).
- Belt distribution: group `dojo.member` by current belt rank, return count per rank. Use existing `dojo.member.rank` or `member_rank_ids` relation — pick the most recent rank per member.
- Data served via a single JSON controller at `/instructor_dashboard/data` (GET, require login). OWL component fetches on mount and on a 60-second polling interval.
- Apply `dojo_theme` CSS tokens throughout — all colors from `var(--surface)`, `var(--red)`, `var(--gold)`, etc. No hardcoded hex values in component CSS.
- OWL component registered under `@dojo_instructor_dashboard/dashboard`. QWeb template in `views/dashboard.xml`.
- Write Python tests in `addons/dojo_instructor_dashboard/tests/test_dashboard_controller.py` covering: controller returns expected keys, stat counts are non-negative integers.

```yaml
id: INC-07
title: dojo_instructor_dashboard OWL module
depends_on: [INC-06]
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
  - curl -sf --cookie "$(docker compose exec -T web cat /var/lib/odoo/sessions/*.json 2>/dev/null | head -1 || echo '')" http://127.0.0.1:8070/instructor_dashboard/data -o /dev/null || true
regression_gate:
  - bash testenv/verify.sh
  - docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http -u dojo_core,dojo_kiosk,dojo_instructor_dashboard --test-enable --stop-after-init
```

---

## INC-08 — kiosk-three-panel: instructor three-panel layout

Restructure the instructor kiosk view in `dojo_kiosk` to a three-panel CSS grid layout: left panel (active session info + countdown timer), main panel (member roster), right panel (instructor notes + alerts).

**Decision rules:**
- CSS grid defined in `dojo_kiosk/static/src/css/kiosk_instructor.css` (new file; existing `kiosk.css` is not removed — only extend it).
- Grid layout: `grid-template-columns: 280px 1fr 300px`. Left and right panels scroll independently; main panel is the primary scroll area.
- Left panel sources data from the currently selected session (`time_state === 'active'` or first `upcoming_soon`). Countdown timer: client-side JS `setInterval` updating every second. Show MM:SS until session starts (if `upcoming_soon`) or time elapsed (if `active`).
- Right panel data comes from the existing `get_member_profile()` member issue flags (`_compute_issue_flags`). At session level (not member level), aggregate: count of members with active issues, count with onboarding incomplete. Requires a new `get_session_summary()` service method returning these aggregates.
- Do not change the student/self-serve kiosk mode — only instructor view.
- Write tests in `addons/dojo_kiosk/tests/test_session_summary.py` covering: `get_session_summary()` returns issue_count and onboarding_incomplete_count as integers.

```yaml
id: INC-08
title: kiosk instructor three-panel layout
depends_on: [INC-06]
touchpoints:
  - addons/dojo_kiosk/static/src/css/kiosk_instructor.css
  - addons/dojo_kiosk/static/src/js/kiosk_instructor.js
  - addons/dojo_kiosk/services/dojo_kiosk_service.py
  - addons/dojo_kiosk/views/kiosk_templates.xml
  - addons/dojo_kiosk/tests/test_session_summary.py
  - SPECIFICATION.md
deliverables:
  - kiosk_instructor.css with three-column grid layout
  - KioskInstructorLayout OWL component refactored to three panels
  - get_session_summary() service method
  - Countdown timer (client-side setInterval)
  - Test file with ≥2 test methods
  - SPECIFICATION.md §6 updated with three-panel layout description
test_data:
  seed: n/a
  migration_before_state: n/a
  external_stubs: n/a
  credentials: n/a
reset:
  - bash testenv/reset.sh
gate:
  - docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http -u dojo_kiosk --test-enable --test-file addons/dojo_kiosk/tests/test_session_summary.py --stop-after-init
  - curl -sf http://127.0.0.1:8070/web/login -o /dev/null
regression_gate:
  - bash testenv/verify.sh
  - docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http -u dojo_core,dojo_kiosk,dojo_instructor_dashboard --test-enable --stop-after-init
```

---

## INC-09 — checkin-overlay: check-in success overlay and chime

Add a full-screen success overlay to the student self-serve check-in flow and a Web Audio API chime on successful check-in.

**Decision rules:**
- Overlay is a `<div class="k-checkin-success-overlay">` injected into the kiosk root component after a successful `create_attendance_log` API call. Displays: member name, belt rank color swatch, "Check-in Successful" text.
- Overlay auto-dismisses after 3000ms via `setTimeout`. OWL state variable `showSuccessOverlay` controls visibility.
- Chime: single Web Audio API `OscillatorNode` (type: 'sine', frequency: 880Hz, duration: 400ms). No external audio file dependency.
- If Web Audio API is unavailable (e.g. browser policy blocks autoplay), fail silently — do not throw. Wrap in try/catch.
- Overlay does not block background kiosk functionality — it is `position: fixed` overlay, not a modal that prevents interaction.
- No Python test needed for this increment. Gate is module upgrade + health check.

```yaml
id: INC-09
title: check-in success overlay and chime
depends_on: [INC-08]
touchpoints:
  - addons/dojo_kiosk/static/src/js/kiosk_app.js
  - addons/dojo_kiosk/static/src/css/kiosk.css
  - addons/dojo_kiosk/views/kiosk_templates.xml
  - SPECIFICATION.md
deliverables:
  - k-checkin-success-overlay CSS class and animation in kiosk.css
  - showSuccessOverlay OWL state variable and auto-dismiss logic in kiosk_app.js
  - Web Audio chime function (try/catch wrapped)
  - SPECIFICATION.md §6 updated to note overlay and chime
test_data:
  seed: n/a
  migration_before_state: n/a
  external_stubs: n/a
  credentials: n/a
reset:
  - bash testenv/reset.sh
gate:
  - docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http -u dojo_kiosk --stop-after-init
  - curl -sf http://127.0.0.1:8070/web/login -o /dev/null
regression_gate:
  - bash testenv/verify.sh
  - docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http -u dojo_core,dojo_kiosk,dojo_instructor_dashboard --test-enable --stop-after-init
```

---

## INC-10 — session-auto-select: time-aware session selection and visual states

Wire the `time_state` field (INC-05) into the kiosk instructor UI: auto-select on load and apply CSS state classes to session cards.

**Decision rules:**
- On `KioskApp` mount, call `get_todays_sessions()`. If exactly one session has `time_state === 'active'`, auto-select it. If none active, auto-select the first `upcoming_soon`. If neither, do not auto-select.
- Apply CSS class to each session card: `k-session--active`, `k-session--soon`, `k-session--upcoming`, `k-session--done`. Colors: active = `var(--green)` border, soon = `var(--gold)` border, done = `var(--text-muted)` opacity.
- Auto-select is non-destructive: if the instructor has already manually selected a session, do not override on re-poll.
- Session list re-polls every 60 seconds (use existing `setInterval` or add one). `time_state` is re-computed server-side on each poll — no client-side time logic.
- No Python tests needed. Gate is upgrade + health check.

```yaml
id: INC-10
title: time-aware session auto-select and visual states
depends_on: [INC-08]
touchpoints:
  - addons/dojo_kiosk/static/src/js/kiosk_instructor.js
  - addons/dojo_kiosk/static/src/css/kiosk_instructor.css
  - addons/dojo_kiosk/views/kiosk_templates.xml
  - SPECIFICATION.md
deliverables:
  - Auto-select logic on KioskApp mount
  - CSS state classes (k-session--active, k-session--soon, k-session--upcoming, k-session--done)
  - 60-second re-poll for session list
  - SPECIFICATION.md §5.1 updated
test_data:
  seed: n/a
  migration_before_state: n/a
  external_stubs: n/a
  credentials: n/a
reset:
  - bash testenv/reset.sh
gate:
  - docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http -u dojo_kiosk --stop-after-init
  - curl -sf http://127.0.0.1:8070/web/login -o /dev/null
regression_gate:
  - bash testenv/verify.sh
  - docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http -u dojo_core,dojo_kiosk,dojo_instructor_dashboard --test-enable --stop-after-init
```

---

## INC-11 — roster-badges: onboarding and task badges on roster tiles

Add `onboarding_pct` and `open_task_count` to the `_roster_entry_dict()` payload. Render as a progress bar and count badge on `InstructorRosterTile`.

**Decision rules:**
- `_roster_entry_dict()` in `dojo_kiosk_service.py` already returns member data per tile. Add two keys: `onboarding_pct` (int 0–100, from `dojo.onboarding.record.progress_pct`, or 100 if no record), `open_task_count` (int, count of open `mail.activity` records on the member, or 0).
- In `InstructorRosterTile` OWL template: render a thin progress bar (`<div class="k-tile-onboarding">`) under the member name only when `onboarding_pct < 100`. Render a red badge (`<span class="k-tile-task-badge">`) with count only when `open_task_count > 0`.
- Do not query `mail.activity` inline per tile — aggregate in one query in `get_session_roster()` using `read_group`.
- Write tests in `addons/dojo_kiosk/tests/test_roster_badges.py` covering: member with onboarding record < 100% has onboarding_pct < 100, member with open activity has open_task_count > 0.

```yaml
id: INC-11
title: onboarding and task badges on roster tiles
depends_on: [INC-08]
touchpoints:
  - addons/dojo_kiosk/services/dojo_kiosk_service.py
  - addons/dojo_kiosk/static/src/js/kiosk_instructor.js
  - addons/dojo_kiosk/static/src/css/kiosk_instructor.css
  - addons/dojo_kiosk/views/kiosk_templates.xml
  - addons/dojo_kiosk/tests/test_roster_badges.py
  - SPECIFICATION.md
deliverables:
  - _roster_entry_dict() updated with onboarding_pct and open_task_count
  - InstructorRosterTile OWL template with progress bar and task badge
  - Test file with ≥2 test methods
  - SPECIFICATION.md §5.2 updated
test_data:
  seed: n/a
  migration_before_state: n/a
  external_stubs: n/a
  credentials: n/a
reset:
  - bash testenv/reset.sh
gate:
  - docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http -u dojo_kiosk --test-enable --test-file addons/dojo_kiosk/tests/test_roster_badges.py --stop-after-init
  - curl -sf http://127.0.0.1:8070/web/login -o /dev/null
regression_gate:
  - bash testenv/verify.sh
  - docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http -u dojo_core,dojo_kiosk,dojo_instructor_dashboard --test-enable --stop-after-init
```

---

## INC-12 — onboarding-profile-modal: onboarding section in MemberProfileCard

Add an Onboarding tab (or Manage tab sub-section) to `MemberProfileCard` in the kiosk, showing step statuses and action buttons wired to the INC-04 endpoints.

**Decision rules:**
- Add a new "Onboarding" tab to `MemberProfileCard` if the member profile already has tabs (Profile, Progress, Household, Manage). If the component uses a different pattern, add a collapsible section inside the Manage tab.
- Show each of the 5 onboarding steps with: step name, status icon (✓ or ○), and action buttons (Mark Complete, Send Reminder). Buttons call the INC-04 endpoints.
- If `profile.onboarding === null`, render "No onboarding record" — do not show buttons.
- Progress bar at top of onboarding section showing `progress_pct` percentage.
- On button click: disable button during request, re-fetch profile on success, show inline error text on failure — do not alert().
- No new Python tests needed. Gate is module upgrade + health check.

```yaml
id: INC-12
title: onboarding tab in kiosk MemberProfileCard
depends_on: [INC-08]
touchpoints:
  - addons/dojo_kiosk/static/src/js/kiosk_member_profile.js
  - addons/dojo_kiosk/views/kiosk_templates.xml
  - addons/dojo_kiosk/static/src/css/kiosk.css
  - SPECIFICATION.md
deliverables:
  - MemberProfileCard Onboarding tab/section with step list and action buttons
  - API call wiring to /kiosk/api/onboarding/complete_step and /kiosk/api/onboarding/send_reminder
  - Loading and error states on action buttons
  - SPECIFICATION.md §6 updated
test_data:
  seed: n/a
  migration_before_state: n/a
  external_stubs: n/a
  credentials: n/a
reset:
  - bash testenv/reset.sh
gate:
  - docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http -u dojo_kiosk --stop-after-init
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
