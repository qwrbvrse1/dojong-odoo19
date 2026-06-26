# Kiosk Photo Storage

## Status

Canonical REL-20260626 domain specification. INC-01 establishes the live photo-flow gate; the Supabase storage increment must make it pass against the running Odoo kiosk.

## Intended behavior

- Instructor photo updates are initiated from the kiosk profile UI and posted to `/kiosk/instructor/update_photo`.
- The update route requires a valid kiosk token and valid instructor authorization.
- The storage path is Supabase-backed or the release-approved local Supabase-compatible equivalent.
- The photo update path must not be an Odoo-only `image_1920` write with a `/web/image/...` response URL.
- A successful upload returns:
  - `success: true`
  - an absolute storage-backed `image_url`
  - cache-safe URL or explicit cache-bust metadata
- Storage-backed image URLs must be suitable for direct browser display from the kiosk session.
- After upload, the refreshed image URL must appear in:
  - the instructor profile modal payload
  - the active roster tile payload
  - any member tile/view that should reflect the updated photo in-session
- Upload/capture failure must return an explicit safe error without leaving the UI in a false-success state.

## Live gate

- Script: `testenv/scripts/ver-kiosk-photo-flow.sh`
- Data source: `testenv/reset.sh` seeded demo environment.
- Credentials: kiosk token from `dojo_kiosk_config`; instructor PIN from the seeded kiosk config.
- The gate exercises:
  - served `kiosk_app.js` photo-control markers
  - live `/kiosk/auth/pin`
  - live `/kiosk/instructor/update_photo`
  - live instructor-authorized `/kiosk/member/profile`
  - live `/kiosk/roster`
- The gate rejects `/web/image/...` response URLs and requires storage-backed, cache-safe refresh semantics.

## Current INC-01 baseline

- The gate script exists and is executable.
- The current implementation is expected to fail this gate until INC-05 replaces the Odoo image-field-only path with Supabase-backed storage and refresh behavior.

## Source of truth

- Route/controller: `addons/dojo_kiosk/controllers/kiosk_controller.py`
- Service logic: `addons/dojo_kiosk/models/dojo_kiosk_service.py`
- UI: `addons/dojo_kiosk/static/src/kiosk_app.js`, `addons/dojo_kiosk/static/src/kiosk.css`
