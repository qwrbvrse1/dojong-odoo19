# Kiosk Student Experience

## Status

Canonical REL-20260626 domain specification. INC-01 establishes the live gate; later student-flow increments must make it pass against the running Odoo kiosk.

## Intended behavior

- The deployable target is the Odoo `dojo_kiosk` SPA served from `/kiosk/<token>`.
- The first student screen is a walk-up check-in surface, not a generic member list.
- The live kiosk shell must provide the kiosk root, token bootstrap, student app asset, instructor asset, theme body class, and kiosk CSS.
- The student home UI must expose the welcome/search treatment through the served kiosk asset:
  - `k-welcome-screen`
  - `k-welcome-search`
  - `k-search-results-flow`
  - `k-member-tile`
  - trial-state marker for trial cards
  - session selection button treatment
  - full-screen check-in success overlay treatment
- Bootstrap must return kiosk config, today's sessions, and session context in one JSON-RPC response.
- Session payloads must include `id`, `name`, `template_name`, `program_name`, `start`, `end`, `time_state`, `capacity`, and `seats_taken`.
- `time_state` values are limited to `active`, `upcoming_soon`, `upcoming`, and `done`.
- Student search results must carry enough data to render rich result cards:
  - member or trial identity
  - trial/member state
  - belt rank when applicable
  - membership state for members
  - program context for the card
  - check-in affordance through card selection
- Selecting a student opens a tap-first check-in flow with today's enrolled sessions.
- Successful check-in shows a prominent deterministic confirmation, identifies the member and session, plays one chime, and auto-dismisses.

## Live gate

- Script: `testenv/scripts/ver-kiosk-home.sh`
- Data source: `testenv/reset.sh` seeded demo environment.
- Credentials: kiosk token from `dojo_kiosk_config`.
- The gate exercises:
  - live `/kiosk/<token>` shell fetch
  - served `kiosk_app.js` UI markers
  - live `/kiosk/api/bootstrap`
  - live `/kiosk/search`
- The gate is intentionally stricter than the INC-01 baseline. It is expected to fail until the student kiosk card payload and rendering satisfy the rich-card requirements.

## Current INC-01 baseline

- The gate script exists and is executable.
- The script normalizes the seeded `Demo Member` fixture because the raw SQL seed does not populate `active`, split-name fields, or `search_name_normalized`.
- The current implementation may still fail this gate because public member search results do not yet expose the full card context required above.

## Source of truth

- Runtime shell: `/kiosk/<token>`
- Runtime code: `addons/dojo_kiosk/static/src/kiosk_app.js`
- Styling: `addons/dojo_kiosk/static/src/kiosk.css`
- Backing behavior: `addons/dojo_kiosk/controllers/kiosk_controller.py`, `addons/dojo_kiosk/models/dojo_kiosk_service.py`
