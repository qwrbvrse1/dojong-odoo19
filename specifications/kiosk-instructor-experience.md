# Kiosk Instructor Experience

## Status

Canonical REL-20260626 domain specification, carried forward for REL-20260628. INC-03 adds Development VM proof for explicit standby semantics, selected-session consistency, and roster-tap attendance safety in the running Odoo kiosk; INC-05 defines the final Development VM closure proof for that contract.

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
- When session context is standby, instructor mode must not fall back to `sessions[0]` as a selected session. The left panel renders a standby card, the roster panel renders no selected roster, and existing sessions remain available only as explicit instructor choices.
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
- Roster tile tap behavior is single-flight and deterministic for member entries:
  - pending taps mark present
  - present taps clear back to pending
  - late taps clear back to pending
  - trial tiles and non-member entries do not toggle attendance

## Live gate

- Script: `testenv/scripts/ver-kiosk-instructor-layout.sh`
- Script: `testenv/scripts/ver-kiosk-roster-cards.sh`
- Script: `testenv/scripts/ver-devvm-kiosk-instructor-safety.sh`
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
- The Development VM instructor-safety gate exercises:
  - served release branch and increment markers
  - served standby/no-fallback and roster-tap guard markers
  - live `/kiosk/sessions` standby context with no selected session
  - live instructor PIN authentication
  - live `/kiosk/instructor/attendance` transitions for present, late, and pending against a roster entry, with the original state restored
- The gates reject:
  - a layout that calls the dead `/kiosk/api/roster` route
  - a main app that depends on late-loaded `window.KioskInstructorLayout`
  - a hidden legacy single-column instructor fallback as the primary mounted view
  - roster payloads missing workflow, membership, attendance, onboarding, or task semantics
  - standby UI code that can select a fallback session without a selected session context
  - roster tap code that can fire invalid member/session/status attendance mutations

## REL-20260628 INC-05 Closure Proof

- The local reset/regression prerequisite remains `bash testenv/verify.sh`.
- The final Development VM instructor proof is `bash testenv/scripts/ver-devvm-kiosk-instructor-safety.sh`.
- Development VM proof requires `DEMO_KIOSK_URL`, `DEMO_KIOSK_TOKEN`, and `DEMO_INSTRUCTOR_PIN`; the script uses `DEMO_KIOSK_EXPECTED_BRANCH` when set, otherwise the current git branch.
- The final suite expects the integrated REL-20260628 asset marker `KIOSK_RELEASE_INCREMENT = "INC-04"` by default. Operators may set `DEMO_KIOSK_EXPECTED_INCREMENT` only when proving a deliberately different deployed asset marker.
- If the script runs without Development VM credentials in a prepared local workspace, the local Odoo fallback is a smoke check only and does not count as Development VM release proof.
- A passing instructor closure proves that the running Development VM kiosk serves the standby/no-fallback and roster-tap safety code, returns explicit standby context with no selected session for a standby day, authenticates the demo instructor PIN, and safely toggles present, late, and pending attendance states while restoring the original roster state.
- Pass/fail evidence is the gate exit status and stdout from the Development VM script; release `plan.md` and `scope.md` remain planning specifications, not run logs.

## Source of truth

- Runtime shell: `/kiosk/<token>`
- Runtime code: `addons/dojo_kiosk/static/src/kiosk_app.js`
- Served instructor contract asset: `addons/dojo_kiosk/static/src/js/kiosk_instructor.js`
- Styling: `addons/dojo_kiosk/static/src/kiosk.css`, with supplemental legacy selectors in `addons/dojo_kiosk/static/src/css/kiosk_instructor.css`
- Backing behavior: `addons/dojo_kiosk/controllers/kiosk_controller.py`, `addons/dojo_kiosk/models/dojo_kiosk_service.py`
