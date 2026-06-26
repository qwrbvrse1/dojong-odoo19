# Kiosk Student Experience

## Status

Current-state baseline before REL-20260626 execution.

## Current behavior

- The kiosk student home flow is served by `addons/dojo_kiosk/static/src/kiosk_app.js` and `addons/dojo_kiosk/static/src/kiosk.css`.
- Search returns member and trial results, but the card presentation is still a reduced tile treatment rather than the full intended kiosk card density.
- Student selection opens a modal-driven check-in flow.
- The check-in success path includes a success overlay and audio chime implementation in source, but full parity with the intended kiosk UX must be proven by live gates during REL-20260626.
- Session recommendation logic exists and relies on `time_state` values from the kiosk sessions payload.

## Known gaps entering REL-20260626

- Home/search presentation is not yet certified as matching the intended walk-up kiosk UX.
- Result cards do not yet have a canonical current-state spec for expected identity, program, and check-in cues.
- The live student flow has not been validated end-to-end under the unattended harness with a dedicated kiosk verification script.

## Source of truth

- Runtime code: `addons/dojo_kiosk/static/src/kiosk_app.js`
- Styling: `addons/dojo_kiosk/static/src/kiosk.css`
- Backing behavior: `addons/dojo_kiosk/controllers/kiosk_controller.py`, `addons/dojo_kiosk/models/dojo_kiosk_service.py`
