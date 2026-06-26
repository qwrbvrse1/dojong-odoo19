# Kiosk Profile and Onboarding

## Status

Canonical REL-20260626 domain specification. INC-01 establishes the live profile/auth/onboarding gate; later profile increments must make it pass against the running Odoo kiosk.

## Intended behavior

- Member profile data is served through the kiosk JSON-RPC controller, not a separate app.
- `MemberProfileCard` presents a coherent tab model:
  - Profile
  - Progress
  - Household
  - Manage
- Manage actions are instructor-only and are not exposed before instructor authorization.
- Public profile data before instructor authorization is deliberately scoped to safe kiosk check-in information:
  - member id
  - name
  - image URL
  - belt rank/color
  - attendance state
  - enrolled sessions for check-in
- Public profile data must not expose instructor/private fields:
  - email
  - phone
  - member number
  - membership state
  - household
  - guardians
  - issues
  - workflow status
  - program-management data
- Instructor-authorized profile data must expose operational context:
  - member number
  - membership state
  - issues
  - workflow status
  - attendance state
  - profile/manage action context
- Onboarding is a kiosk guidance model. The payload must include the lifecycle guidance keys:
  - `trial_booked`
  - `waiver_signed`
  - `intro_completed`
  - `membership_activated`
  - `uniform_issued`
- Onboarding payloads must include `available`, `complete`, `progress_pct`, `steps`, and `missing_steps`.

## Live gate

- Script: `testenv/scripts/ver-kiosk-profile-tabs.sh`
- Data source: `testenv/reset.sh` seeded demo environment.
- Credentials: kiosk token from `dojo_kiosk_config`; instructor PIN from the seeded kiosk config.
- The gate exercises:
  - served `kiosk_app.js` profile/tab markers
  - live `/kiosk/auth/pin`
  - live public `/kiosk/member/profile`
  - live instructor-authorized `/kiosk/member/profile`
- The gate intentionally rejects public profile payloads that leak workflow/private fields.

## Current INC-01 baseline

- The gate script exists and is executable.
- The current implementation may still fail this gate because the pre-PIN profile payload includes workflow/program information that belongs behind instructor authorization.

## Source of truth

- API/controller: `addons/dojo_kiosk/controllers/kiosk_controller.py`
- Service logic: `addons/dojo_kiosk/models/dojo_kiosk_service.py`
- UI: `addons/dojo_kiosk/static/src/kiosk_app.js`, `addons/dojo_kiosk/static/src/kiosk.css`
