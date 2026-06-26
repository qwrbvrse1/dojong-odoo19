# Release Plan — REL-20260626: Kiosk Full-Correctness Rescue

> Prose sections are for humans. Fenced `yaml` blocks are parsed by `apev-run.sh`.
> Block 1 = release config. Each subsequent block = one increment, in execution order.

## Release configuration

```yaml
release: REL-20260626
branch: rel/REL-20260626
worker_model: codex
alternate_model: codex
max_shots: 3
max_env_retries: 5
halt_on_fail: downstream
workproducts: ~/workproducts/dojong-odoo19/REL-20260626
baseline_gate:
  - bash testenv/verify.sh
  - bash -c 'test -f addons/dojo_kiosk/static/src/kiosk_app.js'
  - bash -c 'test -f addons/dojo_kiosk/models/dojo_kiosk_service.py'
  - bash -c 'docker compose exec -T db psql -U odoo -d odoo19 -tAc "SELECT COUNT(*) FROM ir_module_module WHERE name IN ('"'"'dojo_kiosk'"'"','"'"'dojo_theme'"'"','"'"'dojo_core'"'"','"'"'dojo_onboarding'"'"') AND state='"'"'installed'"'"';" | grep -q "4"'
```

## Dependency analysis

`INC-01` is the M0 infrastructure increment and stands alone. It creates the missing live verification artifacts and establishes the rescue gate posture. Every subsequent increment depends on `INC-01`, so feature work cannot proceed until the verification surface exists.

`INC-02` through `INC-05` are intentionally linear because each step sharpens the same kiosk surface:
- `INC-02` fixes the student-facing flow first, which is the baseline kiosk journey.
- `INC-03` builds on that live kiosk surface to correct instructor mode and layout integration.
- `INC-04` then corrects profile and onboarding behavior inside the now-correct instructor/student shell.
- `INC-05` changes photo storage and refresh semantics, which depend on the profile/instructor flows already being stable.

`INC-06` depends on the whole stack because it closes specifications, changelog, and final rescue proof after the behavioral work is complete.

---

## INC-01 — Baseline the kiosk rescue with live gates

Replace the weak kiosk proof points with deterministic live verification scripts before feature correction work continues. This increment does not claim the kiosk is fixed; it establishes the rescue harness so later passes cannot “green” without proving behavior.

```yaml
id: INC-01
title: Establish deterministic kiosk rescue gates
depends_on: []
touchpoints:
  - testenv/scripts/
  - testenv/verify.sh
  - specifications/kiosk-student-experience.md
  - specifications/kiosk-instructor-experience.md
  - specifications/kiosk-profile-onboarding.md
  - specifications/kiosk-photo-storage.md
  - releases/REL-20260626/scope.md
  - releases/REL-20260626/plan.md
deliverables:
  - Dedicated live kiosk verification scripts exist for home flow, instructor layout, profile tabs, and photo flow
  - Baseline release documents are aligned with the unattended-build template requirements
  - Canonical kiosk domain specification files exist in specifications/
test_data:
  seed: testenv/reset.sh seeded demo environment
  migration_before_state: current dojo_kiosk implementation
  external_stubs: none
  credentials: admin@demo.com / admin123, kiosk token from dojo_kiosk_config
reset:
  - bash testenv/reset.sh
gate:
  - bash testenv/verify.sh
  - bash -c 'test -f testenv/scripts/ver-kiosk-home.sh'
  - bash -c 'test -f testenv/scripts/ver-kiosk-instructor-layout.sh'
  - bash -c 'test -f testenv/scripts/ver-kiosk-photo-flow.sh'
  - bash -c 'test -f testenv/scripts/ver-kiosk-profile-tabs.sh'
regression_gate:
  - bash testenv/verify.sh
```

---

## INC-02 — Student kiosk UX parity

Correct the student-facing kiosk flow so the live Odoo app matches the intended walk-up kiosk experience: welcome/search, result cards, self-check-in interaction, and success overlay behavior.

```yaml
id: INC-02
title: Fix student kiosk search, selection, and check-in experience
depends_on:
  - INC-01
touchpoints:
  - addons/dojo_kiosk/static/src/kiosk_app.js
  - addons/dojo_kiosk/static/src/kiosk.css
  - addons/dojo_kiosk/controllers/kiosk_controller.py
  - addons/dojo_kiosk/models/dojo_kiosk_service.py
  - specifications/kiosk-student-experience.md
  - testenv/scripts/ver-kiosk-home.sh
  - testenv/scripts/ver-kiosk-checkin-flow.sh
deliverables:
  - Student home/search presentation matches the intended kiosk experience in the running Odoo app
  - Result selection and self check-in flow behave correctly for a walk-up user
  - Success overlay and chime are proven by live gates
  - specifications/kiosk-student-experience.md is updated to current state
test_data:
  seed: seeded member, trial lead, active session, check-in eligible member
  migration_before_state: current dojo_kiosk student flow
  external_stubs: none
  credentials: kiosk token from dojo_kiosk_config
reset:
  - bash testenv/reset.sh
gate:
  - docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http -u dojo_kiosk --stop-after-init
  - bash testenv/scripts/ver-kiosk-home.sh
  - bash testenv/scripts/ver-kiosk-checkin-flow.sh
regression_gate:
  - bash testenv/verify.sh
  - bash testenv/scripts/ver05-time-state.sh
```

---

## INC-03 — Instructor kiosk layout and session operations parity

Integrate the intended three-panel instructor layout into the running kiosk and prove that session context, roster presentation, and operational side panels behave correctly in live output.

```yaml
id: INC-03
title: Fix instructor kiosk layout, roster density, and session context behavior
depends_on:
  - INC-02
touchpoints:
  - addons/dojo_kiosk/static/src/kiosk_app.js
  - addons/dojo_kiosk/static/src/kiosk.css
  - addons/dojo_kiosk/static/src/js/kiosk_instructor.js
  - addons/dojo_kiosk/models/dojo_kiosk_service.py
  - specifications/kiosk-instructor-experience.md
  - testenv/scripts/ver-kiosk-instructor-layout.sh
  - testenv/scripts/ver-kiosk-roster-cards.sh
deliverables:
  - The intended three-panel instructor layout is mounted and visible in the running kiosk
  - Session context and roster presentation are validated in live output
  - Instructor roster card semantics are corrected and verified
  - specifications/kiosk-instructor-experience.md is updated to current state
test_data:
  seed: seeded instructor session with roster, onboarding flags, membership issues
  migration_before_state: current mixed instructor kiosk implementation
  external_stubs: none
  credentials: kiosk token and valid instructor PIN/key from demo seed
reset:
  - bash testenv/reset.sh
gate:
  - docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http -u dojo_kiosk --stop-after-init
  - bash testenv/scripts/ver-kiosk-instructor-layout.sh
  - bash testenv/scripts/ver-kiosk-roster-cards.sh
  - bash testenv/scripts/ver11-roster-check.sh
regression_gate:
  - bash testenv/verify.sh
  - bash testenv/scripts/ver05-time-state.sh
```

---

## INC-04 — Member profile and onboarding flow correctness

Make profile/manage behavior internally consistent, correct the onboarding presentation semantics, and ensure public versus instructor-authorized payloads are deliberate and safe.

```yaml
id: INC-04
title: Fix kiosk member profile, manage tabs, and onboarding semantics
depends_on:
  - INC-03
touchpoints:
  - addons/dojo_kiosk/static/src/kiosk_app.js
  - addons/dojo_kiosk/static/src/kiosk.css
  - addons/dojo_kiosk/controllers/kiosk_controller.py
  - addons/dojo_kiosk/models/dojo_kiosk_service.py
  - specifications/kiosk-profile-onboarding.md
  - testenv/scripts/ver04-member-profile.sh
  - testenv/scripts/ver-kiosk-profile-tabs.sh
deliverables:
  - Member profile and manage flow are internally consistent in the kiosk UI
  - Onboarding semantics are corrected and proven via live API plus UI verification
  - Public versus instructor-authorized data boundaries are verified
  - specifications/kiosk-profile-onboarding.md is updated to current state
test_data:
  seed: seeded member with partial onboarding and instructor-accessible actions
  migration_before_state: current legacy-leaning onboarding semantics
  external_stubs: none
  credentials: kiosk token and valid instructor PIN/key from demo seed
reset:
  - bash testenv/reset.sh
gate:
  - docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http -u dojo_kiosk,dojo_onboarding --stop-after-init
  - bash testenv/scripts/ver04-member-profile.sh
  - bash testenv/scripts/ver-kiosk-profile-tabs.sh
regression_gate:
  - bash testenv/verify.sh
  - bash testenv/scripts/ver-kiosk-instructor-layout.sh
```

---

## INC-05 — Supabase photo storage correction

Replace the current Odoo-only image write path with the intended Supabase-backed kiosk photo flow, and prove in-session refresh correctness after upload or capture.

```yaml
id: INC-05
title: Implement Supabase-backed kiosk photo upload and refresh behavior
depends_on:
  - INC-04
touchpoints:
  - addons/dojo_kiosk/static/src/kiosk_app.js
  - addons/dojo_kiosk/static/src/kiosk.css
  - addons/dojo_kiosk/controllers/kiosk_controller.py
  - addons/dojo_kiosk/models/dojo_kiosk_service.py
  - specifications/kiosk-photo-storage.md
  - testenv/scripts/ver-kiosk-photo-flow.sh
  - testenv/scripts/ver-kiosk-photo-refresh.sh
  - docker-compose.yml
deliverables:
  - Kiosk photo capture/upload uses the intended Supabase-backed storage path
  - Returned image URLs and in-session refresh behavior are deterministic
  - Upload failure handling is explicit and verified
  - specifications/kiosk-photo-storage.md is updated to current state
test_data:
  seed: seeded member with existing image and instructor access
  migration_before_state: current Odoo image_1920 write path
  external_stubs: local Supabase dev stack or equivalent release-approved local storage endpoint
  credentials: kiosk token and valid instructor PIN/key from demo seed
reset:
  - bash testenv/reset.sh
gate:
  - bash testenv/verify.sh
  - bash testenv/scripts/ver-kiosk-photo-flow.sh
  - bash testenv/scripts/ver-kiosk-photo-refresh.sh
regression_gate:
  - bash testenv/verify.sh
  - bash testenv/scripts/ver-kiosk-profile-tabs.sh
```

---

## INC-06 — Final release integrity and audit closure

Close the loop between code, specifications, and release proof so there is one coherent story of what the kiosk now does and how it was verified.

```yaml
id: INC-06
title: Align specifications, changelog, and final rescue proof
depends_on:
  - INC-05
touchpoints:
  - specifications/
  - CHANGELOG.md
  - releases/REL-20260626/scope.md
  - releases/REL-20260626/plan.md
deliverables:
  - Final kiosk rescue verification suite runs green against the local Odoo instance
  - Canonical kiosk specification files reflect shipped behavior
  - CHANGELOG.md has the release-ready material needed after audit
test_data:
  seed: final integrated local environment
  migration_before_state: kiosk behavior fixed in prior increments
  external_stubs: none beyond approved local photo storage stack
  credentials: admin@demo.com / admin123, kiosk token, instructor PIN/key
reset:
  - bash testenv/reset.sh
gate:
  - bash testenv/verify.sh
  - bash testenv/scripts/ver-kiosk-home.sh
  - bash testenv/scripts/ver-kiosk-checkin-flow.sh
  - bash testenv/scripts/ver-kiosk-instructor-layout.sh
  - bash testenv/scripts/ver-kiosk-profile-tabs.sh
  - bash testenv/scripts/ver-kiosk-photo-flow.sh
  - bash testenv/scripts/ver-kiosk-photo-refresh.sh
regression_gate:
  - bash testenv/verify.sh
```
