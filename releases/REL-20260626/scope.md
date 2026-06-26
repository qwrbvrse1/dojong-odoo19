# Release Scope — REL-20260626: Kiosk Full-Correctness Rescue

## Summary

REL-20260626 is the recovery release for the kiosk implementation. The target is **the existing Odoo `dojo_kiosk` app**, updated in place until it is behaviorally and visually aligned with the approved kiosk experience. We are **not** building a separate React/Vite kiosk, and we are **not** treating the HTML prototype as a literal source file to serve. The job is to make the Odoo kiosk behave like the intended kiosk product.

This release exists because REL-001 and REL-20260624 left the kiosk in a mixed state: some spec items were implemented, some were only partially integrated, and some were verified too narrowly to catch user-visible misses. REL-20260626 closes that gap with live gates against the running Odoo instance and a full-correctness bar before the release can close.

## Canonical truth for this release

When requirements conflict or feel ambiguous, resolve them in this order:

1. **This release scope**
2. **REL-001 kiosk-related scope items**
3. **`specifications/` verification and fix notes already in the repo**
4. **The approved kiosk prototype behavior and layout represented by the earlier `UFT_SUPABASE_STORAGE_PHOTOS.html` reference and the current demo build**

Interpretation rule:
- The HTML reference is a **design and interaction example**, not the deployable target.
- The deployable target is the **Odoo kiosk app** in `addons/dojo_kiosk/`.

## In scope

### Milestone 0 — Deterministic rescue baseline

- The rescue branch runs against a reproducible local Odoo environment using `testenv/reset.sh` and `testenv/verify.sh`.
- Missing or weak kiosk gates are replaced with live behavioral gates that exercise the running instance, not just static source grep.
- New verification scripts are added under `testenv/scripts/` for the kiosk flows delivered in this release.
- The rescue release documents exactly which kiosk behaviors are considered done, so the worker model is not allowed to “fill in” product intent.

### Milestone 1 — Student kiosk parity

- The student-facing home flow matches the intended kiosk UX:
  - welcome/search presentation is purpose-built for kiosk use, not a generic member list
  - search results render rich member cards with the expected identity cues
  - result cards clearly communicate trial/member state, belt/program context, and check-in affordance
- Student check-in is a tap-first kiosk interaction, not a staff-dashboard interaction disguised as kiosk UI.
- The check-in success state is visually prominent, fast, and deterministic:
  - full-screen confirmation treatment
  - member identity shown correctly
  - audio chime plays once on success
  - auto-dismiss timing is correct
- Session selection and self check-in behavior match the intended flow for a walk-up kiosk user.

### Milestone 2 — Instructor kiosk parity

- Instructor mode uses the intended three-panel kiosk layout in the running app, not dead code or a legacy single-column fallback.
- Session context auto-selection remains correct and visible in the live UI.
- The left, center, and right panels each surface the intended operational information:
  - current/next session state
  - roster tiles with actionable attendance state
  - alerts/onboarding/membership issues
- Instructor roster cards expose the intended visual density and quick-scan semantics, including onboarding/task indicators when present.

### Milestone 3 — Member profile, onboarding, and manage flow correctness

- `MemberProfileCard` behavior matches the intended kiosk workflow:
  - profile/manage organization is coherent
  - onboarding information is visible in the correct place
  - instructor actions are exposed only where appropriate
- Onboarding semantics are corrected where the current implementation still reflects the legacy five-step interpretation instead of the intended kiosk guidance model.
- Public versus instructor-authenticated profile data is deliberately scoped so the kiosk does not leak more information than intended before instructor authorization.

### Milestone 4 — Photo storage and refresh correctness

- Instructor photo capture and file upload from the kiosk use the intended **Supabase-backed storage flow** for kiosk photos, rather than writing only to the Odoo image blob field.
- The returned image URL and downstream roster/profile refresh behavior are cache-safe and deterministic.
- After a successful photo update, the changed image appears in:
  - the profile modal
  - the instructor roster tile
  - any member tile or view that is supposed to reflect the latest photo during the same kiosk session
- Error handling for capture/upload failure is explicit and user-safe.

### Milestone 5 — Release integrity

- `specifications/` is updated so the repo no longer claims kiosk completeness where the running app disagrees.
- `CHANGELOG.md` and release artifacts describe the rescue accurately.
- The final release gate proves the kiosk end-to-end on the local VM without relying on manual interpretation alone.

## Out of scope

- Building a separate non-Odoo kiosk frontend
- Reworking unrelated admin modules unless a kiosk dependency forces the change
- Production deployment to a remote environment
- Broader CRM/website/member-management redesign outside the kiosk rescue path
- “Close enough” substitutions for Supabase photo storage in the kiosk flow

## Affected specifications

- `specifications/kiosk-student-experience.md` — current student kiosk home, search, check-in, and success-state behavior
- `specifications/kiosk-instructor-experience.md` — current instructor layout, session context, and roster-card behavior
- `specifications/kiosk-profile-onboarding.md` — current member profile, manage flow, and onboarding payload/visibility rules
- `specifications/kiosk-photo-storage.md` — current photo capture/upload/storage/refresh behavior
- `CHANGELOG.md` — release history entry after audit

## Decisions

| Decision | Rationale | Alternatives rejected |
|---|---|---|
| Update `dojo_kiosk` in place | Preserves the existing deployment surface, routes, auth model, and Odoo integration already in use | Separate kiosk app or sidecar frontend |
| Full-correctness release instead of patching isolated defects | The current failures are interaction-level and cross file boundaries; piecemeal fixes are likely to regress | Single hotfix without integrated verification |
| Live behavioral gates required for all kiosk increments | Prior work passed narrow gates while missing user-visible behavior | Static source checks as sole proof |
| Supabase photo flow is a required correction item | Current Odoo-only image write path does not satisfy the intended kiosk photo-storage design | Leaving Odoo image blob storage in place and calling it done |

## Risks and decision rules

| If… | Then… (never ask) |
|---|---|
| A kiosk behavior can be shown in the running app but not proven by source grep alone | Add a live HTTP/JSON-RPC/browser gate; do not accept grep-only proof |
| Existing specs disagree with live intended kiosk UX | Treat the spec note as stale and correct it in this release before closeout |
| Supabase plumbing is missing or incomplete in repo | Add the missing adapter/configuration as part of this release; do not silently fall back to Odoo-only storage |
| The three-panel instructor layout exists in code but not in the live kiosk | Treat as not delivered until the live gate proves it renders |
| A fix changes payload shape used by kiosk UI | Add or update a live API gate and a UI-render gate in the same increment |

## Accepted deviations (operator sign-off required)

| Scope item | What is deferred / partial | Reason | Operator sign-off |
|---|---|---|---|
| Release baseline gate coverage | Baseline gate is limited to environment health and currently-shipped verification scripts; the broader kiosk rescue verification suite is created in INC-01 rather than existing before the release | The repo does not yet contain a single authoritative kiosk regression suite broad enough to represent the full rescue target pre-INC-01 | Required before run |
| Legacy `specifications/` normalization | Existing `specifications/` contents are mostly verification notes from prior releases, not clean domain-state specs; REL-20260626 establishes canonical kiosk domain specs and then keeps them current | Repo state predates the stricter artifact standard | Required before run |

## Success criteria

- Every in-scope kiosk increment passes its live gate against the running local Odoo instance.
- The existing Odoo kiosk app, not a prototype file, delivers the intended student and instructor kiosk UX.
- Photo upload/capture uses the intended storage path and refreshes correctly in-session.
- Release documentation, verification notes, and changelog no longer overstate kiosk completeness.
- An operator can run the rescue plan on the unattended development VM and decide pass/fail from the recorded gates without subjective guesswork.
