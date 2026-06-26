# Kiosk Instructor Experience

## Status

Current-state baseline before REL-20260626 execution.

## Current behavior

- Instructor mode is implemented within `dojo_kiosk`.
- Session auto-selection logic for `active` and `upcoming_soon` exists in the kiosk app.
- Roster payloads expose onboarding and open-task indicators used by instructor-facing UI.
- A three-panel instructor layout implementation exists in the codebase, but prior release evidence showed a risk of partial or dead integration and requires fresh live verification.

## Known gaps entering REL-20260626

- The live instructor view is not yet certified as matching the intended three-panel kiosk layout in the running app.
- Roster tile density and quick-scan semantics are not yet described in a canonical current-state spec.
- The unattended suite does not yet contain a dedicated live verification script for instructor layout integration.

## Source of truth

- Runtime code: `addons/dojo_kiosk/static/src/kiosk_app.js`
- Instructor layout component: `addons/dojo_kiosk/static/src/js/kiosk_instructor.js`
- Styling: `addons/dojo_kiosk/static/src/kiosk.css`
- Backing behavior: `addons/dojo_kiosk/models/dojo_kiosk_service.py`
