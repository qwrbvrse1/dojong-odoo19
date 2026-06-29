# Release Scope — REL-20260628: Development VM Kiosk Demo Alignment

## Summary

REL-20260628 is a focused follow-on release for the Development VM demo deployment. REL-20260626 established a much stronger kiosk baseline, but the live review of the Development VM demo on June 28, 2026 still showed a set of user-visible deltas and behavioral defects:

- the student landing/search experience is materially thinner than the reference kiosk UX
- instructor standby messaging contradicts the rendered session/roster state
- tapping a roster tile in instructor mode can crash the live kiosk
- instructor-authenticated onboarding completion appears to return success without changing visible onboarding state

This release exists to close those gaps on the **running Development VM demo**, not to reopen the entire kiosk rescue scope. The deployable target remains the Odoo `dojo_kiosk` SPA served by the Development VM.

## Canonical truth for this release

When requirements conflict or feel ambiguous, resolve them in this order:

1. **This release scope**
2. **`specifications/kiosk-student-experience.md`**
3. **`specifications/kiosk-instructor-experience.md`**
4. **`specifications/kiosk-profile-onboarding.md`**
5. **The current Development VM demo behavior only where it does not contradict the canonical specs**

Interpretation rules:

- The Development VM demo URL is the primary verification target for this release.
- Static source grep is supplementary evidence only; it is never sufficient proof for a pass.
- This release is about **alignment and behavioral correctness** of the live demo, not broad feature expansion.

## Prerequisites (manual steps before harness run)

The following must be completed by the operator before `apev-run.sh` is invoked. The `baseline_gate` verifies they are in place.

1. **Demo URL exported** — set `DEMO_KIOSK_URL` to the current Development VM kiosk URL.
2. **Kiosk token exported** — set `DEMO_KIOSK_TOKEN` to the token used by the current Front Desk kiosk on the Development VM.
3. **Instructor PIN exported** — set `DEMO_INSTRUCTOR_PIN` to the current seeded instructor PIN for the demo kiosk.
4. **Repo and deployment aligned** — the branch being executed from the repo must be the same branch deployed on the Development VM before live gates are run.

## In scope

### Milestone 0 — Development VM live-gate baseline

- The release verifies the **running Development VM demo**, not only the local Docker instance.
- New Development VM verification scripts are added under `testenv/scripts/` for:
  - student landing/search contract
  - student selection/check-in flow
  - instructor standby/session safety
  - onboarding action correctness
- The release plan defines a single operator-facing way to prove the deployed demo matches the branch under test.

### Milestone 1 — Student entry experience alignment

- The student landing screen keeps the current kiosk route and branding shell but is brought closer to the intended walk-up kiosk UX.
- Search-result cards expose the expected kiosk-safe context:
  - identity
  - membership or trial state
  - belt/program context when available
  - clear check-in affordance
- Tapping a result reliably opens the expected session-selection or direct check-in path.
- The Development VM gate proves the student flow end to end against the live demo deployment.

### Milestone 2 — Instructor standby and roster interaction correctness

- `standby` is explicit and internally consistent:
  - no misleading selected-session fallback when the session context is standby
  - no contradictory rendering of a live roster as if a session is active
- Instructor roster tile interaction does not crash the app.
- Attendance toggle behavior for present/late/pending members is safe and deterministic in the live demo.
- The Development VM gate proves both standby rendering and roster interaction safety.

### Milestone 3 — Onboarding action truthfulness and refresh correctness

- Instructor-authenticated onboarding actions must only report success when the underlying onboarding state actually changes.
- Completing an onboarding step updates the workflow status returned by the API and the visible profile state after refresh.
- The Development VM gate proves:
  - unauthenticated action returns `instructor_auth_required`
  - authenticated action mutates state
  - refreshed profile reflects the mutation

### Milestone 4 — Release integrity for the Development VM demo

- The canonical kiosk specifications are updated only where the shipped live demo behavior is intentionally changed.
- The new release artifacts remain planning-only: no execution history or post-run notes in `plan.md`.
- The final Development VM proof leaves a clear pass/fail trail for an operator reviewing workproducts.

## Out of scope

- Rebuilding the kiosk as a separate non-Odoo frontend
- Kiosk endpoint authentication redesign
- Parent portal, admin dashboard, or broader member-management changes unrelated to the listed demo defects
- Photo storage changes unless a regression is discovered while fixing in-scope behavior
- New feature work beyond what is required to align the existing demo to the reference kiosk UX

## Affected specifications

- `specifications/kiosk-student-experience.md`
- `specifications/kiosk-instructor-experience.md`
- `specifications/kiosk-profile-onboarding.md`

## Decisions

| Decision | Rationale | Alternatives rejected |
|---|---|---|
| Verify against the Development VM demo as the primary target | The reported issues are live-demo issues; a local-only pass is insufficient | Treating local Docker-only gates as release proof |
| Narrow the release to the observed deltas | The kiosk rescue release already covered broader domains; reopening everything would slow the demo fix path | Another full-correctness rescue cycle |
| Fix behavior before visual polish | Crashes, standby contradictions, and false-success onboarding actions are more damaging than style drift | Starting with surface-only design tweaks |
| Keep the Odoo `dojo_kiosk` SPA as the only deployable target | It matches the current system architecture and release history | Separate prototype or sidecar app |

## Risks and decision rules

| If… | Then… (never ask) |
|---|---|
| The Development VM live demo and local branch behavior diverge | Treat the live demo as the release truth target and add the missing deployment or verification step to the increment |
| A live demo action can fail without a corresponding failing gate | Add a Development VM gate for that action in the same increment |
| A fix changes kiosk payload shape | Update both the live API gate and the runtime UI gate in the same increment |
| Standby state has no selected session | Do not fall back to `sessions[0]`; render explicit standby UI only |
| An onboarding action reports success but the refreshed profile does not change | Treat as a code defect, not an acceptable no-op |

## Success criteria

- The Development VM student landing and search-card flow visibly align with the kiosk reference UX.
- Student selection/check-in works reliably in the running Development VM demo.
- Instructor standby state is explicit and non-contradictory.
- Instructor roster interaction no longer crashes the live app.
- Authenticated onboarding step completion changes the member’s visible workflow state after refresh.
- An operator can run the release plan on the Development VM and determine pass/fail from the recorded live gates without subjective interpretation.
