# Kiosk Instructor Experience

## Status

Canonical REL-20260626 domain specification. INC-03 delivered the live three-panel instructor layout, roster-card density corrections, and session-context validation for the running Odoo kiosk. INC-06 final verification confirmed the shipped behavior against the local Odoo instance.

## Intended behavior

- Instructor mode is part of the same Odoo `dojo_kiosk` SPA served from `/kiosk/<token>`.
- Instructor mode mounts the intended three-panel layout directly from `kiosk_app.js`; it must not depend on a late-loaded global component registration to render the primary layout.
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
- The center panel shows dense roster tiles with actionable attendance state:
  - tap a member tile to mark pending members present or clear present/late attendance back to pending
  - long-press a member tile to open instructor manage actions
  - trial tiles are visible but do not toggle member attendance
- The right panel surfaces operational alerts:
  - onboarding incomplete
  - membership/subscription issues
  - instructor tasks
- Session context auto-selection must be visible and deterministic:
  - current active class wins
  - otherwise nearest class starting within the configured threshold wins
  - otherwise standby is explicit
- Session context uses today's sessions in the company local timezone; the release demo company must have an explicit timezone for deterministic local-day behavior around UTC midnight.
- Roster entries must include quick-scan fields:
  - identity
  - image URL
  - attendance state
  - attendance label
  - membership state
  - membership label
  - program context
  - workflow status
  - alert count
  - onboarding percentage
  - open task count
- Roster tiles must expose stable DOM semantics for live gates and visual scanning:
  - `data-attendance-state`
  - `data-onboarding-pct`
  - `data-open-task-count`
  - `data-membership-state`
  - visible attendance label
  - visible belt/program context when available
  - visible onboarding progress when incomplete
  - compact workflow badges for onboarding, waiver, membership, grading, and task states

## Live gate

- Script: `testenv/scripts/ver-kiosk-instructor-layout.sh`
- Script: `testenv/scripts/ver-kiosk-roster-cards.sh`
- Data source: `testenv/reset.sh` seeded demo environment.
- Credentials: kiosk token from `dojo_kiosk_config`.
- The layout gate exercises:
  - live `/kiosk/<token>` shell fetch
  - served `kiosk_app.js` mounted layout markers
  - served `kiosk_instructor.js` layout markers
  - served `kiosk.css` three-panel selectors
  - live `/kiosk/sessions`
  - live `/kiosk/api/session_summary`
  - live `/kiosk/roster`
- The roster-card gate exercises:
  - served app asset roster tile markers
  - served CSS density markers
  - live session summary counts
  - live roster payload shape for every returned card
- The gates reject:
  - a layout that calls the dead `/kiosk/api/roster` route
  - a main app that depends on late-loaded `window.KioskInstructorLayout`
  - a hidden legacy single-column instructor fallback as the primary mounted view
  - roster payloads missing workflow, membership, attendance, onboarding, or task semantics

## Final INC-06 Verification

- `bash testenv/scripts/ver-kiosk-instructor-layout.sh` passed.
- The final run used the local demo company timezone `America/New_York`, matching the service's company-local session-context behavior.

## Source of truth

- Runtime shell: `/kiosk/<token>`
- Runtime code: `addons/dojo_kiosk/static/src/kiosk_app.js`
- Served instructor contract asset: `addons/dojo_kiosk/static/src/js/kiosk_instructor.js`
- Styling: `addons/dojo_kiosk/static/src/kiosk.css`, with supplemental legacy selectors in `addons/dojo_kiosk/static/src/css/kiosk_instructor.css`
- Backing behavior: `addons/dojo_kiosk/controllers/kiosk_controller.py`, `addons/dojo_kiosk/models/dojo_kiosk_service.py`
