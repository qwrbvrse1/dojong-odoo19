# Kiosk Profile and Onboarding

## Status

Canonical REL-20260626 domain specification, carried forward for REL-20260628. REL-20260628 INC-04 adds Development VM proof that onboarding complete-step actions mutate visible onboarding state and that refreshed profiles reflect the mutation; INC-05 defines the final Development VM closure proof for that contract.

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
- Authenticated `complete_step` actions return success only when the selected step was incomplete before the action and the post-action workflow marks that step complete.
- Already-complete or non-persisting complete-step actions must return `success: false`; they must not show a successful kiosk outcome.
- The workflow returned by `complete_step` and a subsequent instructor-authorized `/kiosk/member/profile` refresh must agree on `progress_pct`, completed step state, and `missing_steps`.
- Source-derived facts may advance kiosk onboarding progress during refresh, but profile refresh must not silently clear a step completed through the kiosk action path.

## Live gate

- Scripts:
  - `testenv/scripts/ver04-member-profile.sh`
  - `testenv/scripts/ver-kiosk-profile-tabs.sh`
  - `testenv/scripts/ver-devvm-kiosk-onboarding-action.sh`
- Data source: `testenv/reset.sh` seeded demo environment.
- Credentials:
  - local gates: kiosk token from `dojo_kiosk_config`; instructor PIN from the seeded kiosk config
  - Development VM gate: `DEMO_KIOSK_URL`, `DEMO_KIOSK_TOKEN`, and `DEMO_INSTRUCTOR_PIN`
- The gate exercises:
  - served `kiosk_app.js` profile/tab markers
  - served `kiosk.css` profile/manage markers
  - live `/kiosk/auth/pin`
  - live public `/kiosk/member/profile`
  - live invalid-key `/kiosk/member/profile`
  - live instructor-authorized `/kiosk/member/profile`
  - live unauthenticated and authenticated `/kiosk/api/onboarding/complete_step`
  - Development VM authenticated complete-step mutation, returned workflow truthfulness, and refreshed profile truthfulness
- The gate intentionally rejects public profile payloads that leak workflow/private fields.
- The gate seeds a deterministic partial lifecycle onboarding state for `Demo Member`, verifies 40% progress, marks `intro_completed`, and verifies 60% progress.
- The Development VM gate selects an existing partially complete instructor-visible onboarding profile, prefers a manual lifecycle step when available, mutates one incomplete step, and verifies the refreshed profile no longer lists that step as missing.

## Current INC-04 state

- `/kiosk/member/profile` returns a public check-in payload unless an instructor key validates against the active kiosk token.
- Public and invalid-key profile payloads include only safe check-in fields and do not expose workflow, issues, membership state, household, guardians, contact details, member number, appointments, or program-management rows.
- Instructor-authorized profile payloads include workflow, onboarding, issues, membership state, household/guardian data, programs, and Manage-tab action context.
- `MemberProfileCard` hides Progress, Household, photo tools, and Manage unless the profile payload includes instructor workflow data.
- Manage-tab onboarding actions use token plus instructor key and render the lifecycle guidance steps.
- `complete_step` responses include `changed: true` only after the refreshed workflow shows the selected step complete.
- The kiosk displays complete-step success only after the action response and refreshed profile both reflect the completed step.

## REL-20260628 INC-05 Closure Proof

- The local reset/regression prerequisite remains `bash testenv/verify.sh`.
- The final Development VM onboarding proof is `bash testenv/scripts/ver-devvm-kiosk-onboarding-action.sh`.
- Development VM proof requires `DEMO_KIOSK_URL`, `DEMO_KIOSK_TOKEN`, and `DEMO_INSTRUCTOR_PIN`; the script uses `DEMO_KIOSK_EXPECTED_BRANCH` when set, otherwise the current git branch.
- The final suite expects the integrated REL-20260628 asset marker `KIOSK_RELEASE_INCREMENT = "INC-04"` by default. Operators may set `DEMO_KIOSK_EXPECTED_INCREMENT` only when proving a deliberately different deployed asset marker.
- If the script runs without Development VM credentials in a prepared local workspace, the local Odoo fallback is a smoke check only and does not count as Development VM release proof.
- A passing onboarding closure proves that the running Development VM kiosk rejects unauthenticated complete-step actions with `instructor_auth_required`, mutates an incomplete lifecycle onboarding step only with instructor authentication, returns a workflow that marks the selected step complete, and returns the same state after an instructor-authorized profile refresh.
- The Development VM onboarding gate is intentionally stateful: repeat runs require an available partially complete onboarding profile, and operators may steer selection with `DEMO_KIOSK_ONBOARDING_QUERY` or `DEMO_KIOSK_MEMBER_ID`.
- Pass/fail evidence is the gate exit status and stdout from the Development VM script; release `plan.md` and `scope.md` remain planning specifications, not run logs.

## Source of truth

- API/controller: `addons/dojo_kiosk/controllers/kiosk_controller.py`
- Service logic: `addons/dojo_kiosk/models/dojo_kiosk_service.py`
- UI: `addons/dojo_kiosk/static/src/kiosk_app.js`, `addons/dojo_kiosk/static/src/kiosk.css`
