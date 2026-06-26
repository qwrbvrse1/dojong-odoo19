# Kiosk Profile and Onboarding

## Status

Current-state baseline before REL-20260626 execution.

## Current behavior

- Member profile data is served from `dojo_kiosk_service.py` through kiosk controller endpoints.
- Instructor-authorized profile views expose workflow and onboarding information.
- The current onboarding payload includes `available`, `complete`, `progress_pct`, and `missing_steps`.
- The implementation still reflects legacy onboarding-step semantics in parts of the service logic.

## Known gaps entering REL-20260626

- Profile and manage-tab organization is not yet defined in a canonical current-state spec.
- Public versus instructor-authorized data boundaries need explicit verification during the rescue release.
- The intended onboarding guidance model and the currently implemented legacy progress model are not yet reconciled.

## Source of truth

- API/controller: `addons/dojo_kiosk/controllers/kiosk_controller.py`
- Service logic: `addons/dojo_kiosk/models/dojo_kiosk_service.py`
- UI: `addons/dojo_kiosk/static/src/kiosk_app.js`, `addons/dojo_kiosk/static/src/kiosk.css`
