# Kiosk Photo Storage

## Status

Canonical REL-20260626 domain specification. INC-05 implements the storage-backed kiosk photo path and its live refresh gates.

## Intended behavior

- Instructor photo updates are initiated from the kiosk profile UI and posted to `/kiosk/instructor/update_photo`.
- The update route requires a valid kiosk token and valid instructor authorization.
- The storage path is Supabase-backed when Supabase credentials are configured:
  - `SUPABASE_URL` or `KIOSK_SUPABASE_URL`
  - `SUPABASE_SERVICE_ROLE_KEY`, `KIOSK_SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_ANON_KEY`, or `KIOSK_SUPABASE_ANON_KEY`
  - optional `KIOSK_PHOTO_BUCKET`
  - optional `KIOSK_SUPABASE_PUBLIC_BASE_URL` when public object URLs are served through a proxy/CDN
- The local VM uses the release-approved Supabase-compatible object endpoint by default:
  - local object root: `KIOSK_PHOTO_LOCAL_DIR` or Odoo data dir `kiosk-photo-storage`
  - public URL shape: `/kiosk/storage/v1/object/public/<bucket>/<object_path>?v=<cache_bust>`
- The photo update path must not be an Odoo-only `image_1920` write with a `/web/image/...` response URL.
- A successful upload returns:
  - `success: true`
  - an absolute storage-backed `image_url`
  - cache-safe URL or explicit cache-bust metadata
  - `storage_driver`
  - `bucket`
  - `object_path`
- Storage-backed image URLs must be suitable for direct browser display from the kiosk session.
- After upload, the refreshed image URL must appear in:
  - the instructor profile modal payload
  - the active roster tile payload
  - any member tile/view that should reflect the updated photo in-session
- Upload/capture failure must return an explicit safe error without leaving the UI in a false-success state.
- Invalid photo data must not mutate the currently stored member photo URL.

## Live gate

- Scripts:
  - `testenv/scripts/ver-kiosk-photo-flow.sh`
  - `testenv/scripts/ver-kiosk-photo-refresh.sh`
- Data source: `testenv/reset.sh` seeded demo environment.
- Credentials: kiosk token from `dojo_kiosk_config`; instructor PIN from the seeded kiosk config.
- The gates exercise:
  - served `kiosk_app.js` photo-control markers
  - live `/kiosk/auth/pin`
  - live `/kiosk/instructor/update_photo`
  - live instructor-authorized `/kiosk/member/profile`
  - live `/kiosk/roster`
  - live `/kiosk/search`
  - direct fetch of the returned object URL
- The gates reject `/web/image/...` response URLs and require storage-backed, cache-safe refresh semantics.
- The refresh gate performs two successive uploads and verifies that profile, roster, and search payloads converge on the latest URL.
- The failure branch posts invalid photo data and verifies an explicit error plus unchanged stored image URL.

## Current INC-05 state

- `dojo.kiosk.service.update_member_photo` decodes and validates PNG/JPEG/WEBP base64 payloads up to 10 MB.
- Configured Supabase storage uses the Supabase Storage REST API and returns the public object URL.
- The default local release environment writes to a Supabase-compatible object path and serves it through the kiosk storage route.
- Member search, roster, minimal profile, and instructor profile payloads all resolve member photos through the persisted storage URL when present.
- The kiosk UI applies a successful returned image URL immediately to the open profile, loaded rosters, active check-in modal, and loaded search results, then refreshes profile and roster payloads from the server.
- Failed uploads show an explicit error and do not leave a false-success preview state.

## Source of truth

- Route/controller: `addons/dojo_kiosk/controllers/kiosk_controller.py`
- Service logic: `addons/dojo_kiosk/models/dojo_kiosk_service.py`
- UI: `addons/dojo_kiosk/static/src/kiosk_app.js`, `addons/dojo_kiosk/static/src/kiosk.css`
