# Kiosk Student Experience

## Status

Canonical REL-20260626 domain specification. INC-02 delivers the student home, search, selection, and self check-in behavior in the running Odoo `dojo_kiosk` app.

## Runtime Target

- The deployable target is the Odoo `dojo_kiosk` SPA served from `/kiosk/<token>`.
- The HTML prototype remains a design reference only; it is not served as the kiosk.
- The live kiosk shell must provide the kiosk root, token bootstrap, student app asset, instructor asset, theme body class, and kiosk CSS.

## Student Home And Search

- The first student screen is a walk-up check-in surface, not a staff member list.
- The home screen presents the kiosk logo, check-in title, and large name search input.
- Search runs through live JSON-RPC at `/kiosk/search` with the active kiosk token.
- Search results render as tap-first member cards through the served app asset.
- Result cards expose kiosk-safe identity and check-in context:
  - member or trial identity
  - photo URL with initials fallback
  - trial or membership state
  - belt rank when applicable
  - program context from an active subscription or today's registered class
  - explicit check-in affordance
- Public search does not expose full profile, household, guardian, contact, task, or onboarding detail.

## Session Selection

- Selecting a member opens a kiosk check-in modal immediately.
- Trial leads use their booked trial session directly.
- Members load today's registered open sessions from `/kiosk/member/enrolled_sessions`.
- Session options show class name, program, time, instructor when available, and a clear check-in CTA.
- If the member has already checked into a session today, the modal shows that state and offers checkout.
- The seeded active, registered demo member is considered check-in eligible even when the SQL seed has no subscription row; cancelled, paused, lead, and unregistered no-subscription members remain blocked.

## Check-In Success

- Self check-in posts to `/kiosk/checkin` for members and `/kiosk/trial/checkin` for trial leads.
- A successful member check-in creates exactly one attendance log, syncs enrollment attendance to present, and returns member, session, status, and program context.
- The enrolled-session and roster payloads reflect the attendance log status (`present` or `late`) during the same kiosk session.
- Successful student check-in closes the selection modal and shows the full-screen `CheckinSuccessView` overlay.
- The overlay identifies the member and session, shows the program when available, plays the Web Audio chime once on mount, and auto-dismisses after `CHECKIN_SUCCESS_DISMISS_MS` (`4000` ms).
- Failed check-in remains in the modal with an explicit error so the student can retry or ask the front desk.

## Live Gates

- `testenv/scripts/ver-kiosk-home.sh`
  - Fetches the live kiosk shell and served `kiosk_app.js`.
  - Verifies bootstrap sessions and session context.
  - Verifies rich search-card payload for the seeded Demo Member.
  - Verifies served UI markers for result cards, session buttons, success overlay, chime, and dismiss timing.
- `testenv/scripts/ver-kiosk-checkin-flow.sh`
  - Resets the seeded Demo Member attendance state.
  - Exercises live `/kiosk/search`, `/kiosk/member/enrolled_sessions`, `/kiosk/checkin`, and `/kiosk/roster`.
  - Verifies the database attendance log and enrollment state after check-in.
  - Verifies the served app contains the full-screen success overlay and chime path used by the successful live check-in.

## Source Of Truth

- Runtime shell: `/kiosk/<token>`
- Runtime code: `addons/dojo_kiosk/static/src/kiosk_app.js`
- Styling: `addons/dojo_kiosk/static/src/kiosk.css`
- Backing behavior: `addons/dojo_kiosk/controllers/kiosk_controller.py`, `addons/dojo_kiosk/models/dojo_kiosk_service.py`
