# Release Scope — REL-20260629: Development VM Kiosk Prototype Parity

## Summary

REL-20260629 is a focused prototype-parity release for the unattended Development VM kiosk demo. Earlier remediation releases materially improved the Odoo `dojo_kiosk` SPA, but the running Development VM kiosk still does not match the accepted HTML prototype in the ways that matter most for walk-up check-in:

- the first-load student surface is still a branded landing page rather than the prototype's roster-first kiosk overlay
- student-mode chrome still exposes controls and widgets that are not present in the prototype
- result cards, checked-in state, and success behavior still follow the current SPA contract instead of the prototype contract
- the unattended verification suite does not yet prove parity against the accepted prototype

This release exists to close those gaps on the **running Development VM demo**. The deployable target remains the Odoo `dojo_kiosk` SPA served from `/kiosk/<token>`, but the **HTML prototype is the acceptance reference** for the student kiosk flow.

## Canonical truth for this release

When requirements conflict or feel ambiguous, resolve them in this order:

1. **This release scope**
2. **`scope/UFT_SUPABASE_STORAGE_PHOTOS.html`**
3. **`specifications/kiosk-student-experience.md`**
4. **The current Development VM demo behavior only where it does not contradict the prototype**

Interpretation rules:

- The HTML prototype is the visual and interaction acceptance truth for the student kiosk flow.
- The Development VM demo URL is the primary verification target for this release.
- Static source grep is supplementary evidence only; it is never sufficient proof for a pass.
- If the current `dojo_kiosk` behavior and the prototype disagree, the prototype wins unless this scope explicitly says otherwise.
- A release pass requires live unattended gates against `DEMO_KIOSK_URL`; local source checks are only support evidence.
- Because the kiosk is served as an Odoo SPA shell, live gates must inspect browser-rendered behavior or the served app asset referenced by that shell rather than treating raw shell HTML as the rendered student surface.

## Prerequisites (manual steps before harness run)

The following must be completed by the operator before `apev-run.sh` is invoked. The `baseline_gate` verifies they are in place.

1. **Demo URL exported** — set `DEMO_KIOSK_URL` to the current Development VM kiosk URL.
2. **Kiosk token exported** — set `DEMO_KIOSK_TOKEN` to the token used by the current Front Desk kiosk on the Development VM.
3. **Repo and deployment aligned** — the branch being executed from the repo must be the same branch deployed on the Development VM before live gates are run.

## In scope

### Milestone 0 — Prototype parity gate contract

- The release defines an unattended Development VM verification contract that proves parity against the accepted HTML prototype instead of only against the current SPA contract.
- `INC-01` is a planning-only baseline: it locks this contract in the release artifacts and does not create runtime or `testenv/` behavior.
- Later behavior-bearing increments add Development VM verification assets under `testenv/scripts/` for:
  - first-load student screen composition
  - default roster visibility and search/filter behavior
  - member-card content and checked-in state
  - direct student check-in and success overlay behavior
- The release plan defines a single operator-facing way to determine whether the running Development VM kiosk matches the accepted prototype.

### Milestone 1 — First-load student surface parity

- The first student screen on `/kiosk/<token>` matches the prototype's kiosk overlay posture rather than a branded landing-page posture.
- The student surface is simplified to the prototype contract:
  - kiosk title
  - search field
  - visible roster grid
  - single explicit exit action
- Student-mode chrome not present in the prototype is removed from the default walk-up screen:
  - sync
  - settings
  - instructor toggle
  - floating AI widget
  - footer chrome not present in the prototype

### Milestone 2 — Roster and card parity

- Student cards are visible on first load without requiring search input.
- Search acts as a filter over the visible roster rather than the sole way to reveal members.
- Card presentation aligns to the prototype:
  - circular avatar
  - stacked name treatment
  - belt and class metadata
  - clear card-tap affordance
  - `ALREADY CHECKED IN` card state rendered directly on the card
- Empty-state copy and treatment align to the prototype.

### Milestone 3 — Direct check-in and success parity

- Tapping a student card follows the prototype's direct check-in contract rather than the current modal-first flow.
- If runtime enrollment/session rules make direct check-in impossible for a specific member, the kiosk must still preserve prototype behavior for the seeded demo members used by unattended VM proof.
- Successful student check-in matches the prototype contract:
  - full-screen confirmation
  - simple `CHECKED IN` messaging
  - student identity shown prominently
  - short dismiss timing aligned to the prototype
- Already-checked-in members show prototype-style state without forcing a modal-first checkout path on the default student surface.

### Milestone 4 — Specification normalization and unattended VM closure

- `specifications/kiosk-student-experience.md` is updated so the runtime spec reflects the accepted prototype-parity contract for the student kiosk flow.
- The release artifacts remain planning-only: no execution history or post-run notes in `plan.md`.
- The final unattended Development VM proof leaves a clear pass/fail trail for an operator reviewing workproducts.

## Out of scope

- Rebuilding the kiosk as a separate non-Odoo frontend
- Admin dashboard, instructor workflow, onboarding workflow, or broader member-management changes unrelated to student prototype parity
- Authentication redesign for kiosk endpoints
- Parent portal, CRM, billing, communications, and automation work
- Photo-storage redesign unless a regression is discovered while closing prototype-parity gaps
- Visual redesign of instructor mode
- New feature work beyond what is required to make the running Development VM kiosk match the accepted prototype

## Affected specifications

- `specifications/kiosk-student-experience.md`

## Decisions

| Decision | Rationale | Alternatives rejected |
|---|---|---|
| Treat `scope/UFT_SUPABASE_STORAGE_PHOTOS.html` as the acceptance truth for student kiosk UX | The current disagreement is about prototype parity, not generic kiosk correctness | Continuing to let the current SPA contract define acceptance |
| Make the Development VM demo the primary verification target | The requirement is parity on the unattended VM deployment, not just local correctness | Accepting local-only parity proof |
| Prototype wins on first-load layout and chrome | The remaining gap is mostly UX contract, not backend capability | Preserving current app-shell controls in student mode |
| Direct card-tap check-in is the target behavior | This is the clearest behavioral difference between the runtime and the prototype | Keeping modal-first selection as the default student interaction |
| Seeded demo members must satisfy direct-check-in proof even if broader runtime edge cases remain | The unattended VM release must have deterministic proof on the deployed demo dataset | Blocking the release on a full enrollment/session architecture redesign |

## Risks and decision rules

| If… | Then… (never ask) |
|---|---|
| The current runtime spec conflicts with the HTML prototype | Update the runtime spec in this release so it reflects prototype-parity truth |
| A prototype-parity fix changes student payload shape | Update both the unattended VM gate and the runtime UI gate in the same increment |
| Direct check-in cannot be made universal without major backend redesign | Preserve prototype behavior for the seeded demo members and document any remaining non-demo exceptions explicitly in the spec |
| A student-mode control is not visible in the prototype | Remove or hide it from the default walk-up screen |
| A live demo behavior can fail without a corresponding unattended VM gate | Add a Development VM gate for that behavior in the same increment |
| Static grep says parity is present but the live Development VM still differs visually | Treat as a code or deployment defect; static evidence never overrides live proof |

## Success criteria

- The Development VM kiosk first-load student screen visually matches the accepted prototype closely enough that header, hierarchy, and chrome differences are no longer user-visible blockers.
- The running Development VM kiosk shows a visible roster grid on first load.
- Search filters the visible roster rather than serving as the only reveal path.
- Student cards render the expected prototype-style metadata and checked-in state.
- Tapping a seeded demo member follows the prototype check-in path on the Development VM.
- Successful student check-in shows the prototype-style success state and dismiss timing.
- An operator can run the release plan on the unattended Development VM and determine pass/fail from the recorded live gates without subjective interpretation.
- `INC-01` leaves a reviewable release-artifact diff while deferring all new `testenv/` scripts to the increments that implement the corresponding runtime behavior.
