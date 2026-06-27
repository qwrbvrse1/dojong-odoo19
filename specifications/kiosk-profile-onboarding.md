# Kiosk Profile and Onboarding

## Status

Canonical REL-20260626 domain specification. INC-04 delivered the live profile/auth/onboarding contract against the running Odoo kiosk. INC-06 final verification confirmed the shipped behavior against the local Odoo instance.

## Intended behavior

- Member profile data is served through the kiosk JSON-RPC controller, not a separate app.
- `MemberProfileCard` presents a coherent tab model:
  - Profile
  - Progress
  - Household
  - Manage
- Profile is the only pre-authorization tab. Progress, Household, photo tools, and Manage render only when the loaded profile payload is instructor-authorized.
- Manage actions are instructor-only and are not exposed before instructor authorization.
- Public profile data before instructor authorization is deliberately scoped to safe kiosk check-in information:
  - member id
  - name
  - image URL
  - belt rank/color
  - non-sensitive program name/color context
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
- Onboarding progress and completion are calculated from the lifecycle guidance keys only. Legacy data-entry keys (`member_info`, `household`, `enrollment`, `subscription`, `portal_access`) may remain on the underlying model for compatibility, but they are not returned as kiosk onboarding steps and do not count toward kiosk progress.
- Instructor onboarding actions must carry the active kiosk token and instructor key. Unauthenticated onboarding actions return `instructor_auth_required`.

## Live gate

- Scripts:
  - `testenv/scripts/ver04-member-profile.sh`
  - `testenv/scripts/ver-kiosk-profile-tabs.sh`
- Data source: `testenv/reset.sh` seeded demo environment.
- Credentials: kiosk token from `dojo_kiosk_config`; instructor PIN from the seeded kiosk config.
- The gate exercises:
  - served `kiosk_app.js` profile/tab markers
  - served `kiosk.css` profile/manage markers
  - live `/kiosk/auth/pin`
  - live public `/kiosk/member/profile`
  - live invalid-key `/kiosk/member/profile`
  - live instructor-authorized `/kiosk/member/profile`
  - live unauthenticated and authenticated `/kiosk/api/onboarding/complete_step`
- The gate intentionally rejects public profile payloads that leak workflow/private fields.
- The gate seeds a deterministic partial lifecycle onboarding state for `Demo Member`, verifies 40% progress, marks `intro_completed`, and verifies 60% progress.

## Current INC-04 state

- `/kiosk/member/profile` returns a public check-in payload unless an instructor key validates against the active kiosk token.
- Public and invalid-key profile payloads include only safe check-in fields and do not expose workflow, issues, membership state, household, guardians, contact details, member number, appointments, or program-management rows.
- Instructor-authorized profile payloads include workflow, onboarding, issues, membership state, household/guardian data, programs, and Manage-tab action context.
- `MemberProfileCard` hides Progress, Household, photo tools, and Manage unless the profile payload includes instructor workflow data.
- Manage-tab onboarding actions use token plus instructor key and render the lifecycle guidance steps.

## Final INC-06 Verification

- `bash testenv/scripts/ver-kiosk-profile-tabs.sh` passed.
- The final run verified public payload scoping, instructor-authorized profile tabs, lifecycle onboarding progress, and authenticated onboarding action handling.

## Source of truth

- API/controller: `addons/dojo_kiosk/controllers/kiosk_controller.py`
- Service logic: `addons/dojo_kiosk/models/dojo_kiosk_service.py`
- UI: `addons/dojo_kiosk/static/src/kiosk_app.js`, `addons/dojo_kiosk/static/src/kiosk.css`
