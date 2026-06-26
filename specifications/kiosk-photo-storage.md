# Kiosk Photo Storage

## Status

Current-state baseline before REL-20260626 execution.

## Current behavior

- Instructor photo updates are triggered from the kiosk UI and posted to `/kiosk/instructor/update_photo`.
- The current service implementation writes base64 image data directly to the Odoo member image field and returns an Odoo `/web/image/...` URL.
- The kiosk frontend performs cache-busting after upload so the profile modal and roster tile attempt to refresh immediately.

## Known gaps entering REL-20260626

- The current implementation is Odoo-image-field based, not Supabase-backed.
- No canonical current-state spec exists for expected storage, returned URL semantics, or failure handling.
- The unattended suite does not yet contain dedicated live verification for upload success plus in-session refresh behavior.

## Source of truth

- Route/controller: `addons/dojo_kiosk/controllers/kiosk_controller.py`
- Service logic: `addons/dojo_kiosk/models/dojo_kiosk_service.py`
- UI: `addons/dojo_kiosk/static/src/kiosk_app.js`, `addons/dojo_kiosk/static/src/kiosk.css`
