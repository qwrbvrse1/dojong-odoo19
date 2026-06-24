# Release Scope — REL-002: REL-001 Remediation

## Summary

REL-002 is a remediation release. REL-001 passed its audit (APPROVED-PARTIAL) but its gates were insufficient: no increment exercised the running Odoo instance. As a result, multiple deliverables were marked PASS despite producing zero user-visible effect. This release does two things:

1. **Verify every REL-001 deliverable against the running system.** Each verification increment upgrades the relevant module(s) and asserts the deliverable against live output — live API responses, live rendered HTML, live DB state. Static file checks are permitted only as supplementary assertions; they cannot be the sole gate.

2. **Fix every confirmed failure.** Three failures are already confirmed from post-merge inspection. Additional failures will be identified during the verification phase. Every failing verification increment produces a corresponding fix increment before the release closes.

Gate contract (applies to all increments in this release):
- Any increment touching module code must include a `docker compose run ... -u <module> --stop-after-init` upgrade step in its gate.
- Any increment verifying UI must include a `curl` or `psql` assertion against the live running system, not just grep on source files.
- Static grep gates are permitted as additional specificity but cannot stand alone.

---

## Confirmed failures entering this release

| # | REL-001 Increment | Failure |
|---|---|---|
| F-1 | INC-01 (dojo_theme tokens) | Token values do not match client spec: `--gold` is `#eab308` (should be `#c9a84c`), `--red` is `#b41e16` (should be `#e8192c`), `--bg` is `#000000` (should be `#0a0a0c`), `--surface` is `#0c0c0c` (should be `#111116`), `--surface2` is `#141414` (should be `#18181f`), `--surface3` is `#1c1c1c` (should be `#1f1f2a`), `--border` is `#272727` (should be `#2a2a38`) |
| F-2 | INC-08 (three-panel layout) | `KioskInstructorLayout` is defined in `kiosk_instructor.js` and exported to `window` but is never instantiated or mounted in `kiosk_app.js`. The instructor view in the running kiosk is the old single-column layout. Dead code. |
| F-3 | INC-01/INC-08 (theme integration) | `dojo_kiosk` does not list `dojo_theme` in its manifest `depends`. `kiosk.css` uses a separate `--k-*` token system. The client-facing kiosk does not consume any `dojo_theme` design tokens. |

---

## In scope

### Phase 1 — Verification of all REL-001 deliverables against running system

One verification increment per REL-001 increment. Each must:
- Upgrade the relevant module(s) in the running Docker instance
- Assert the deliverable via live output (API response, rendered HTML, DB query)
- Exit 0 if delivered correctly; exit non-zero if not (triggering a fix increment)

| VER | REL-001 INC | What is verified live |
|---|---|---|
| VER-01 | INC-01 | `dojo_theme` installs cleanly; `tokens.css` contains exact hex values from `scope/UFT_SUPABASE_STORAGE_PHOTOS.html`; Google Fonts link present in rendered admin HTML |
| VER-02 | INC-02 | `sms_twilio` module upgrades without error; `state = installed` in DB |
| VER-03 | INC-03 | Live JSON-RPC call to `/web/dataset/call_kw` for `dojo.member._name_search` with query `"Smi"` returns results with surname-first matches ranked above mid-name matches |
| VER-04 | INC-04 | Live JSON-RPC call to `/kiosk/api/member_profile` returns payload with `onboarding` key containing `progress_pct`, `available`, `complete`, and `missing_steps` |
| VER-05 | INC-05 | Live JSON-RPC call to `/kiosk/api/sessions` returns session list where each entry contains a `time_state` field with value in `{active, upcoming_soon, upcoming, done}` |
| VER-06 | INC-06 | DB query confirms `expdate` column exists on `dojo_member` table and is populated for at least one member with an active subscription |
| VER-07 | INC-07 | Live curl to `/odoo/instructor-dashboard` (or equivalent URL) returns HTTP 200 and rendered HTML contains stat card markup (`k-stat-card` or equivalent class) |
| VER-08 | INC-08 | Live curl to `/kiosk/<token>` returns rendered HTML containing `k-instructor-layout` class indicating the three-panel component is mounted |
| VER-09 | INC-09 | Live curl to `/kiosk/<token>` returns rendered HTML (or kiosk_app.js source) containing `k-checkin-success-overlay` class and `playCheckinChime` function |
| VER-10 | INC-10 | Live JSON-RPC call to `/kiosk/api/sessions` with an `active` session returns that session first; kiosk source contains auto-select logic referencing `time_state` |
| VER-11 | INC-11 | Live JSON-RPC roster call returns entries with `onboarding_pct` and `open_task_count` fields; kiosk_app.js renders a progress bar element when `onboarding_pct > 0` |
| VER-12 | INC-12 | Live curl to `/kiosk/<token>` page source (or kiosk_app.js) contains onboarding step markup with Mark Complete / Send Reminder action buttons |
| VER-13 | INC-13 | Live curl to dojo_belt_progression mass promote URL returns HTTP 200 and page contains multi-select member grid markup |
| VER-14 | INC-14 | Live curl to belt test roster URL returns HTTP 200 and page source contains `@media print` CSS and roster table markup |
| VER-15 | INC-15 | Live curl to analytics URL returns HTTP 200 and page source contains attendance chart/stat markup |
| VER-16 | INC-16 | Live curl to dojo_members reports URL returns HTTP 200 and page source contains inactive/contact/family report list markup |
| VER-17 | INC-17 | Live POST to CSV export endpoint returns HTTP 200 with `Content-Type: text/csv` or `application/octet-stream` and non-empty body |
| VER-18 | INC-18 | Live curl to email center URL returns HTTP 200 and page source contains compose form markup with audience segment selector |
| VER-19 | INC-19 | Live curl to dojo_members reports page source contains follow-up email action button wired to the follow-up endpoint |
| VER-20 | INC-20 | DB query confirms an `ir.cron` record exists with `name` containing `birthday`, `active = true`, and `nextcall` is set |
| VER-21 | INC-21 | DB query confirms an `ir.cron` record exists with `name` containing `expir`, `active = true`, and `nextcall` is set |
| VER-22 | INC-22/23 | DB query returns 0 rows for `muk_web_*` modules with `state = installed`; `addons/muk_web_*` directories absent from filesystem |

### Phase 2 — Fix confirmed failures

| FIX | Addresses | Deliverable |
|---|---|---|
| FIX-01 | F-1 (token values) | `dojo_theme/static/src/css/tokens.css` updated with exact hex values from `scope/UFT_SUPABASE_STORAGE_PHOTOS.html`. Gates grep exact values. Module upgraded in running instance. |
| FIX-02 | F-3 (theme integration) | `dojo_kiosk/__manifest__.py` adds `dojo_theme` to `depends`. `kiosk_controller.py` loads `dojo_theme` token CSS before `kiosk.css`. `kiosk.css` dark-mode overrides updated to reference `var(--bg)`, `var(--gold)`, `var(--red)`, `var(--surface)` etc. from `dojo_theme` instead of hardcoded values. Module upgraded; live kiosk curl confirms tokens are active. |
| FIX-03 | F-2 (three-panel dead code) | `kiosk_app.js` updated to instantiate and mount `KioskInstructorLayout` in the instructor view render path. Gate: live kiosk curl confirms `k-instructor-layout` is present in rendered kiosk HTML. |
| FIX-XX | Any VER-01 to VER-22 failures | Worker adds FIX increments immediately after discovering failures in Phase 1. Each FIX increment must have a live gate that passes before its VER increment is re-run. |

### Phase 3 — Final regression

- All modules upgraded together in one final pass
- Full Odoo Python test suite run for all custom modules
- Live kiosk curl confirms client design tokens and three-panel layout are active
- Live admin curl confirms dojo_theme CSS is loaded in backend

---

## Out of scope

- New feature additions beyond what REL-001 scoped
- Production deployment (manual operator step after this release merges to main)
- Cloud SQL changes (deferred, per REL-001 out-of-scope)
- Any module not touched by REL-001

---

## Success criteria

- All 22 VER increments reach PASS (gate exits 0 against running system).
- All FIX increments reach PASS (live gate confirms fix is effective in running system).
- Final regression: all custom modules upgrade cleanly, Python test suite exits 0, live kiosk renders client design tokens.
- Auditor can confirm every gate in this release exercises the running instance, not just static files.
