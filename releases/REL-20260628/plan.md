# Release Plan — REL-20260628: Development VM Kiosk Demo Alignment

> Prose sections are for humans. Fenced `yaml` blocks are parsed by `apev-run.sh`.
> Block 1 = release config. Each subsequent block = one increment, in execution order.
>
> **Gate contract (mandatory for all increments):**
> - Every increment must prove behavior against the running Development VM demo URL referenced by `DEMO_KIOSK_URL`.
> - Any increment touching module code must include a module upgrade or deployment step appropriate to the Development VM.
> - Static grep gates alone are insufficient and will be rejected by the auditor.

## Release configuration

```yaml
release: REL-20260628
branch: rel/REL-20260628
worker_model: codex
alternate_model: codex
max_shots: 3
max_env_retries: 5
halt_on_fail: downstream
workproducts: ~/workproducts/dojong-odoo19/REL-20260628
baseline_gate:
  - bash testenv/verify.sh
  - bash -lc 'test -n "${DEMO_KIOSK_URL:-}"'
  - bash -lc 'test -n "${DEMO_KIOSK_TOKEN:-}"'
  - bash -lc 'test -n "${DEMO_INSTRUCTOR_PIN:-}"'
  - bash -lc 'curl -fsS "$DEMO_KIOSK_URL" | grep -q "Dojo Kiosk"'
  - bash -lc 'curl -fsS "$DEMO_KIOSK_URL" | grep -q "/dojo_kiosk/static/src/kiosk_app.js"'
```

## Dependency analysis

`INC-01` establishes the Development VM execution contract and is intentionally first. The remaining increments are linear because each builds on the same live kiosk surface and each later gate depends on the earlier defect class being resolved:

- `INC-02` corrects the student entry/search/check-in contract first, because that is the first thing demo users see.
- `INC-03` fixes instructor standby consistency and crash-prone roster interaction next, because those are blocking instructor demo defects.
- `INC-04` fixes onboarding mutation truthfulness after the instructor path is behaviorally safe.
- `INC-05` closes the loop with spec normalization and final Development VM proof.

---

## INC-01 — Re-baseline release artifacts for Development VM execution

Lock the remediation release to a harness-compatible baseline before any new verification assets are introduced. This increment is planning-only and must leave a reviewable non-testenv workproduct diff.

```yaml
id: INC-01
title: Re-baseline Development VM remediation scope and execution contract
depends_on: []
touchpoints:
  - releases/REL-20260628/scope.md
  - releases/REL-20260628/plan.md
deliverables:
  - Release scope is explicitly limited to Development VM kiosk remediation
  - Increment contracts are aligned to apev workproduct expectations
  - Later increments own any new Development VM verification assets under testenv/
test_data:
  seed: current Development VM demo dataset
  migration_before_state: post-REL-20260626 kiosk deployment
  external_stubs: none
  credentials: DEMO_KIOSK_URL, DEMO_KIOSK_TOKEN, DEMO_INSTRUCTOR_PIN
reset:
  - bash testenv/verify.sh
gate:
  - bash testenv/verify.sh
  - bash -lc 'test -n "${DEMO_KIOSK_URL:-}"'
  - bash -lc 'test -n "${DEMO_KIOSK_TOKEN:-}"'
  - bash -lc 'curl -fsS "$DEMO_KIOSK_URL" | grep -q "Dojo Kiosk"'
regression_gate:
  - bash testenv/verify.sh
```

---

## INC-02 — Establish Development VM gates and align student entry, search cards, and check-in flow


Bring the student-facing Development VM demo closer to the canonical kiosk UX and prove that result selection and check-in behavior work reliably in the live deployment.

```yaml
id: INC-02
title: Create Development VM gates and fix student landing, search card contract, and live check-in flow
depends_on:
  - INC-01
touchpoints:
  - addons/dojo_kiosk/static/src/kiosk_app.js
  - addons/dojo_kiosk/static/src/kiosk.css
  - addons/dojo_kiosk/controllers/kiosk_controller.py
  - addons/dojo_kiosk/models/dojo_kiosk_service.py
  - specifications/kiosk-student-experience.md
  - testenv/scripts/devvm-kiosk-lib.sh
  - testenv/scripts/ver-devvm-kiosk-home.sh
  - testenv/scripts/ver-devvm-kiosk-student-flow.sh
  - testenv/verify.sh
deliverables:
  - Development VM baseline verification assets exist under testenv/ and are accepted as part of a feature-bearing increment
  - Student landing screen remains kiosk-branded but better matches the reference walk-up check-in experience
  - Search-result cards expose the intended kiosk-safe identity and context fields
  - Tapping a search result reliably opens the expected session-selection or direct check-in path
  - Development VM live gates prove student selection and check-in behavior
test_data:
  seed: current Development VM demo dataset with searchable demo members
  migration_before_state: simplified landing/search result presentation and uncertain modal-open behavior
  external_stubs: none
  credentials: DEMO_KIOSK_URL, DEMO_KIOSK_TOKEN
reset:
  - bash testenv/verify.sh
gate:
  - docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http -u dojo_kiosk --stop-after-init
  - bash testenv/scripts/ver-devvm-kiosk-home.sh
  - bash testenv/scripts/ver-devvm-kiosk-student-flow.sh
regression_gate:
  - bash testenv/verify.sh
  - bash testenv/scripts/ver-kiosk-checkin-flow.sh
```

---

## INC-03 — Fix instructor standby consistency and roster interaction safety

Resolve the Development VM instructor-mode defects where standby messaging contradicts rendered session state and roster tile interaction can crash the live app.

```yaml
id: INC-03
title: Fix instructor standby/session selection consistency and roster tap safety
depends_on:
  - INC-02
touchpoints:
  - addons/dojo_kiosk/static/src/kiosk_app.js
  - addons/dojo_kiosk/static/src/kiosk.css
  - addons/dojo_kiosk/static/src/js/kiosk_instructor.js
  - addons/dojo_kiosk/models/dojo_kiosk_service.py
  - specifications/kiosk-instructor-experience.md
  - testenv/scripts/ver-devvm-kiosk-instructor-safety.sh
deliverables:
  - Standby state renders as explicit standby with no contradictory fallback-selected session
  - Instructor roster tile interactions no longer crash the live kiosk
  - Attendance toggle behavior is deterministic for present, late, and pending entries
  - Development VM live gate proves both standby semantics and roster interaction safety
test_data:
  seed: current Development VM demo dataset with instructor-accessible session roster
  migration_before_state: standby contradiction and roster-tap JS crash observed in the live demo
  external_stubs: none
  credentials: DEMO_KIOSK_URL, DEMO_KIOSK_TOKEN, DEMO_INSTRUCTOR_PIN
reset:
  - bash testenv/verify.sh
gate:
  - docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http -u dojo_kiosk --stop-after-init
  - bash testenv/scripts/ver-devvm-kiosk-instructor-safety.sh
regression_gate:
  - bash testenv/verify.sh
  - bash testenv/scripts/ver-kiosk-instructor-layout.sh
  - bash testenv/scripts/ver-kiosk-roster-cards.sh
```

---

## INC-04 — Fix onboarding action truthfulness and profile refresh

Ensure that instructor-authenticated onboarding actions on the Development VM only report success when they mutate real onboarding state, and that the refreshed profile reflects the change.

```yaml
id: INC-04
title: Fix onboarding complete-step mutation and refreshed profile truthfulness
depends_on:
  - INC-03
touchpoints:
  - addons/dojo_kiosk/static/src/kiosk_app.js
  - addons/dojo_kiosk/controllers/kiosk_controller.py
  - addons/dojo_kiosk/models/dojo_kiosk_service.py
  - specifications/kiosk-profile-onboarding.md
  - testenv/scripts/ver-devvm-kiosk-onboarding-action.sh
deliverables:
  - Unauthenticated onboarding actions still return instructor_auth_required
  - Authenticated complete-step actions mutate real onboarding state
  - Refreshed profile data reflects the updated onboarding progress and missing steps
  - Development VM live gate proves mutation correctness end to end
test_data:
  seed: current Development VM demo dataset with a partially complete onboarding record
  migration_before_state: authenticated complete-step returns success but leaves visible onboarding state unchanged
  external_stubs: none
  credentials: DEMO_KIOSK_URL, DEMO_KIOSK_TOKEN, DEMO_INSTRUCTOR_PIN
reset:
  - bash testenv/verify.sh
gate:
  - docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http -u dojo_kiosk,dojo_onboarding --stop-after-init
  - bash testenv/scripts/ver-devvm-kiosk-onboarding-action.sh
regression_gate:
  - bash testenv/verify.sh
  - bash testenv/scripts/ver-kiosk-profile-tabs.sh
```

---

## INC-05 — Final Development VM proof and release closure

Close the loop between code, canonical specs, and Development VM proof so the release can be judged from artifacts and workproducts without relying on memory or subjective walkthroughs.

```yaml
id: INC-05
title: Align kiosk specs and final Development VM proof for demo closure
depends_on:
  - INC-04
touchpoints:
  - specifications/kiosk-student-experience.md
  - specifications/kiosk-instructor-experience.md
  - specifications/kiosk-profile-onboarding.md
  - releases/REL-20260628/scope.md
  - releases/REL-20260628/plan.md
deliverables:
  - Canonical kiosk specifications reflect the intentionally shipped Development VM behavior after fixes
  - Final Development VM gate suite passes against the running demo
  - Release artifacts remain planning-only and operator-usable
test_data:
  seed: fully integrated Development VM demo deployment after INC-02 through INC-04
  migration_before_state: all in-scope defects fixed in prior increments
  external_stubs: none
  credentials: DEMO_KIOSK_URL, DEMO_KIOSK_TOKEN, DEMO_INSTRUCTOR_PIN
reset:
  - bash testenv/verify.sh
gate:
  - bash testenv/scripts/ver-devvm-kiosk-home.sh
  - bash testenv/scripts/ver-devvm-kiosk-student-flow.sh
  - bash testenv/scripts/ver-devvm-kiosk-instructor-safety.sh
  - bash testenv/scripts/ver-devvm-kiosk-onboarding-action.sh
regression_gate:
  - bash testenv/verify.sh
```
