# Kiosk Instructor Experience

## Status

Canonical REL-20260626 domain specification. INC-01 establishes the live layout/session/roster gate; later instructor increments must make it pass against the running Odoo kiosk.

## Intended behavior

- Instructor mode is part of the same Odoo `dojo_kiosk` SPA served from `/kiosk/<token>`.
- Instructor mode mounts the intended three-panel layout in the running app.
- The live kiosk shell must load the instructor layout asset.
- The served instructor asset must expose:
  - `KioskInstructorLayout`
  - `k-instructor-layout`
  - `k-instructor-left`
  - `k-instructor-main`
  - `k-instructor-right`
  - roster grid/card classes
  - alert section classes
- The left panel shows the selected current/next session, time range, countdown, and attendance summary.
- The center panel shows roster tiles/cards with actionable attendance state.
- The right panel surfaces operational alerts:
  - onboarding incomplete
  - membership/subscription issues
  - instructor tasks
- Session context auto-selection must be visible and deterministic:
  - current active class wins
  - otherwise nearest class starting within the configured threshold wins
  - otherwise standby is explicit
- Roster entries must include quick-scan fields:
  - identity
  - image URL
  - attendance state
  - membership state
  - workflow status
  - onboarding percentage
  - open task count

## Live gate

- Script: `testenv/scripts/ver-kiosk-instructor-layout.sh`
- Data source: `testenv/reset.sh` seeded demo environment.
- Credentials: kiosk token from `dojo_kiosk_config`.
- The gate exercises:
  - live `/kiosk/<token>` shell fetch
  - served `kiosk_instructor.js` layout markers
  - live `/kiosk/sessions`
  - live `/kiosk/api/session_summary`
  - live `/kiosk/roster`
- The gate rejects a layout that calls a dead roster route. The instructor component must use the live `/kiosk/roster` endpoint.

## Current INC-01 baseline

- The gate script exists and is executable.
- The script is intentionally strict. It is expected to fail until the live instructor layout uses the correct roster endpoint and the running app proves all three panels against live session/roster payloads.

## Source of truth

- Runtime shell: `/kiosk/<token>`
- Runtime code: `addons/dojo_kiosk/static/src/kiosk_app.js`
- Instructor layout component: `addons/dojo_kiosk/static/src/js/kiosk_instructor.js`
- Styling: `addons/dojo_kiosk/static/src/kiosk.css`, `addons/dojo_kiosk/static/src/css/kiosk_instructor.css`
- Backing behavior: `addons/dojo_kiosk/controllers/kiosk_controller.py`, `addons/dojo_kiosk/models/dojo_kiosk_service.py`
