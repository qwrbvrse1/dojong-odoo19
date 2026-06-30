# Kiosk Student Experience

## Status

Canonical student kiosk domain specification for REL-20260629 prototype
parity. The accepted student walk-up experience is the roster-first HTML
prototype contract implemented in the Odoo `dojo_kiosk` SPA and proven against
the running Development VM demo.

This specification supersedes the earlier REL-20260628 search-first,
modal-first student contract for the default walk-up surface.

## Runtime Target

- The kiosk is served by the Odoo SPA shell at `/kiosk/<token>`.
- The shell must provide the kiosk root, token bootstrap, student app asset,
  instructor asset, theme body class, and kiosk CSS.
- `scope/UFT_SUPABASE_STORAGE_PHOTOS.html` is not deployed as the kiosk, but it
  defines the visual and interaction contract for the student walk-up flow.
- When this specification conflicts with `releases/REL-20260629/scope.md` or
  the accepted prototype, the release scope and prototype win.

## Student Home

- The first student screen is the prototype-style roster-first walk-up overlay,
  not a branded landing page, a search-only landing state, or an instructor
  roster surface.
- The default student surface contains only the prototype student chrome:
  - kiosk title
  - student search field
  - visible roster grid
  - one explicit exit action
- Student mode must not show non-prototype controls on the default walk-up
  screen, including sync, settings, instructor toggle, floating AI widget, or
  footer chrome.
- Shared app header controls and the AI assistant are allowed only outside the
  default student surface, such as instructor mode.

## Roster And Search

- Student cards are visible on first load without requiring search input.
- The first-load roster is loaded from `/kiosk/student_roster` for the active or
  recommended kiosk session when available.
- The roster payload may come from a session roster or a member roster fallback,
  but the rendered student surface must still show visible cards on first load
  for the seeded Development VM demo dataset.
- Search filters the visible roster in place. An empty query preserves the full
  visible roster, a matching query keeps matching cards visible, and an
  impossible query renders the prototype empty state.
- `/kiosk/search` remains a compatibility fallback for environments where no
  student roster or session context is available. It is not the normal reveal
  path for the prototype-parity student surface.

## Student Cards

- Student cards use the prototype card treatment:
  - circular avatar with initials fallback
  - stacked, prominent student name
  - belt metadata when available
  - class, session, or program metadata when available
  - clear card-tap affordance
  - `ALREADY CHECKED IN` state rendered directly on checked-in cards
- Card data must be kiosk-safe. Public student card payloads may expose student
  identity, `member_id` or `lead_id`, image URL, trial flag, belt and program
  display fields, attendance state and label, membership state and label, and
  the session context needed for check-in.
- Public student cards must not expose private profile, household, guardian,
  contact, date-of-birth, task, onboarding, billing, or plan detail.
- Checked-in cards are considered checked in when `attendance_state` is
  `present` or `late`; they render as already checked in and do not force a
  checkout-first modal path on the default student surface.

## Direct Student Check-In

- Tapping a visible student card follows the prototype direct check-in path for
  the seeded Development VM demo members.
- Direct student check-in posts to `/kiosk/student/checkin` with the active
  kiosk token, member or trial identity, session ID, and kiosk date context.
- Trial leads use their booked trial session when present.
- Members use the session carried by the student roster card, the loaded student
  roster session, or the current recommended kiosk session.
- Successful check-in creates or confirms one attendance record and refreshes
  the card state to `present` or `late`.
- Repeat check-in attempts for an already-present or late student may return an
  already-checked-in response, but the refreshed visible card must still render
  the prototype checked-in state.
- If a non-demo card has no resolvable session without a broader enrollment
  redesign, the runtime may fall back to the legacy session selection path or an
  explicit error. Seeded demo members used by unattended Development VM proof
  must not require that fallback.

## Success And Failure

- Successful direct check-in shows the prototype-style full-screen success state
  instead of a modal-first confirmation.
- The success state uses simple `CHECKED IN` messaging, shows the student name
  prominently, includes session or program context when available, and displays
  the returning-to-check-in message.
- The success state auto-dismisses after `CHECKIN_SUCCESS_DISMISS_MS`
  (`4000` ms).
- A failed direct check-in shows an explicit full-screen or inline error that
  tells the student to retry or see the front desk; it must not silently leave
  the card in an ambiguous state.

## Live Gates

- `testenv/scripts/ver-devvm-kiosk-prototype-home.sh`
  - Requires `DEMO_KIOSK_URL` and `DEMO_KIOSK_TOKEN` for release proof.
  - Fetches the Development VM kiosk shell and exact served `kiosk_app.js`.
  - Verifies served branch and increment markers, SPA bootstrap, prototype home
    markers, removal of non-prototype student chrome, and a live visible roster
    card payload.
- `testenv/scripts/ver-devvm-kiosk-prototype-roster.sh`
  - Requires `DEMO_KIOSK_URL` and `DEMO_KIOSK_TOKEN` for release proof.
  - Fetches the Development VM kiosk shell, served app asset, and kiosk CSS.
  - Exercises live `/kiosk/student_roster` and verifies first-load cards,
    search-filter semantics, card payload safety, circular-avatar card CSS, and
    checked-in state markers.
- `testenv/scripts/ver-devvm-kiosk-prototype-checkin.sh`
  - Requires `DEMO_KIOSK_URL` and `DEMO_KIOSK_TOKEN` for release proof.
  - Fetches the Development VM kiosk shell, served app asset, and kiosk CSS.
  - Exercises live `/kiosk/student_roster` and `/kiosk/student/checkin`.
  - Verifies direct card-tap markers, absence of modal-first card selection,
    success overlay copy and timing markers, direct check-in creation or
    already-checked-in acceptance, and refreshed roster state.
- `testenv/verify.sh`
  - Remains the local reset and regression prerequisite.
  - It proves the local Odoo environment and verification harness are healthy;
    it does not replace live Development VM proof.

## REL-20260629 INC-05 Closure Proof

- Final Development VM student proof is:
  - `DEMO_KIOSK_EXPECTED_INCREMENT=INC-04 bash testenv/scripts/ver-devvm-kiosk-prototype-home.sh`
  - `DEMO_KIOSK_EXPECTED_INCREMENT=INC-04 bash testenv/scripts/ver-devvm-kiosk-prototype-roster.sh`
  - `DEMO_KIOSK_EXPECTED_INCREMENT=INC-04 bash testenv/scripts/ver-devvm-kiosk-prototype-checkin.sh`
- Development VM proof requires `DEMO_KIOSK_URL` and `DEMO_KIOSK_TOKEN`.
- The scripts compare the served asset branch to
  `DEMO_KIOSK_EXPECTED_BRANCH` when set, otherwise to the current git branch.
- The integrated REL-20260629 student runtime is represented by
  `KIOSK_RELEASE_INCREMENT = "INC-04"`. INC-05 proof must set
  `DEMO_KIOSK_EXPECTED_INCREMENT=INC-04` so the earlier home and roster gates
  validate the integrated asset rather than their historical per-increment
  defaults.
- Static source checks and local fallback runs are supporting evidence only. A
  passing release requires the live gates to pass against the running
  Development VM kiosk referenced by `DEMO_KIOSK_URL`.
- Pass/fail evidence is the gate exit status and stdout from the Development VM
  scripts. Release `plan.md` and `scope.md` remain planning specifications, not
  execution logs.

## Source Of Truth

- Runtime shell: `/kiosk/<token>`
- Student runtime: `addons/dojo_kiosk/static/src/kiosk_app.js`
- Styling: `addons/dojo_kiosk/static/src/kiosk.css`
- Backing behavior:
  `addons/dojo_kiosk/controllers/kiosk_controller.py`,
  `addons/dojo_kiosk/models/dojo_kiosk_service.py`
- Release acceptance:
  `releases/REL-20260629/scope.md`,
  `scope/UFT_SUPABASE_STORAGE_PHOTOS.html`
