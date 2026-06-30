# Release Plan — REL-20260629: Development VM Kiosk Prototype Parity

> Prose sections are for humans. Fenced `yaml` blocks are parsed by `apev-run.sh`.
> Block 1 = release config. Each subsequent block = one increment, in execution order.
>
> **Gate contract (mandatory for all increments):**
> - Every increment must prove behavior against the running Development VM demo URL referenced by `DEMO_KIOSK_URL`.
> - Any increment touching module code must include a module upgrade or deployment step appropriate to the Development VM.
> - Static grep gates alone are insufficient and will be rejected by the auditor.

## Release configuration

```yaml
release: REL-20260629
branch: rel/REL-20260629
worker_model: codex
alternate_model: codex
max_shots: 3
max_env_retries: 5
halt_on_fail: downstream
workproducts: ~/workproducts/dojong-odoo19/REL-20260629
baseline_gate:
  - bash testenv/verify.sh
  - bash -lc 'test -n "${DEMO_KIOSK_URL:-}"'
  - bash -lc 'test -n "${DEMO_KIOSK_TOKEN:-}"'
  - bash -lc 'curl -fsS "$DEMO_KIOSK_URL" | grep -q "/dojo_kiosk/static/src/kiosk_app.js"'
  - bash -lc 'source testenv/scripts/devvm-kiosk-lib.sh; tmp="$(mktemp -d)"; trap "rm -rf \"$tmp\"" EXIT; devvm_fetch_url "$(devvm_kiosk_url)" > "$tmp/shell.html"; devvm_fetch_served_app "$tmp/shell.html" "$tmp/kiosk_app.js"; grep -q "CHECK IN" "$tmp/kiosk_app.js"'
```

## Dependency analysis

`INC-01` establishes the unattended Development VM prototype-parity contract and is intentionally first. The remaining increments are linear because each later gate depends on the earlier UX contract being locked in:

- `INC-02` fixes the first-load student surface and removes non-prototype chrome first, because that is the first thing users see.
- `INC-03` then aligns roster/card behavior once the top-level surface is correct.
- `INC-04` converts the student action flow to prototype-style direct check-in and success behavior.
- `INC-05` updates the canonical student spec and closes the loop with final unattended Development VM proof.

---

## INC-01 — Re-baseline release artifacts for prototype-parity execution

Lock the release to a prototype-parity contract before any behavior-bearing work is done. This increment is planning-only and must leave a reviewable non-testenv workproduct diff that clarifies the unattended Development VM proof contract. It must not add `testenv/` scripts; INC-02 through INC-04 own those assets with the behavior they verify.

```yaml
id: INC-01
title: Re-baseline unattended VM prototype-parity scope and execution contract
depends_on: []
touchpoints:
  - releases/REL-20260629/scope.md
  - releases/REL-20260629/plan.md
deliverables:
  - Release scope explicitly names the HTML prototype as the student kiosk acceptance truth
  - Increment contracts are aligned to unattended Development VM proof expectations
  - Later increments own any new Development VM verification assets under testenv/
  - Operator-facing pass/fail proof is anchored to live gates against DEMO_KIOSK_URL
test_data:
  seed: current Development VM demo dataset
  migration_before_state: post-REL-20260628 kiosk deployment
  external_stubs: none
  credentials: DEMO_KIOSK_URL, DEMO_KIOSK_TOKEN
reset:
  - bash testenv/verify.sh
gate:
  - bash testenv/verify.sh
  - bash -lc 'test -n "${DEMO_KIOSK_URL:-}"'
  - bash -lc 'test -n "${DEMO_KIOSK_TOKEN:-}"'
  - bash -lc 'source testenv/scripts/devvm-kiosk-lib.sh; tmp="$(mktemp -d)"; trap "rm -rf \"$tmp\"" EXIT; devvm_fetch_url "$(devvm_kiosk_url)" > "$tmp/shell.html"; devvm_fetch_served_app "$tmp/shell.html" "$tmp/kiosk_app.js"; grep -q "CHECK IN" "$tmp/kiosk_app.js"'
regression_gate:
  - bash testenv/verify.sh
```

INC-01 establishes the execution boundary only: it is complete when the release artifacts state that prototype parity is judged from the HTML prototype and proven by unattended, SPA-aware live gates against the Development VM. The first new Development VM verification scripts are intentionally deferred to INC-02, INC-03, and INC-04, where each script is paired with the runtime behavior under test.

---

## INC-02 — Add unattended VM prototype-parity gates and fix the first-load student surface

Create the unattended VM verification assets that prove first-load parity and simplify the student surface so it matches the prototype's kiosk posture instead of the current app-shell posture.

```yaml
id: INC-02
title: Create prototype-parity VM gates and align first-load student layout and chrome
depends_on:
  - INC-01
touchpoints:
  - addons/dojo_kiosk/static/src/kiosk_app.js
  - addons/dojo_kiosk/static/src/kiosk.css
  - scope/UFT_SUPABASE_STORAGE_PHOTOS.html
  - testenv/scripts/devvm-kiosk-lib.sh
  - testenv/scripts/ver-devvm-kiosk-prototype-home.sh
  - testenv/verify.sh
deliverables:
  - Development VM baseline verification assets exist for first-load prototype parity
  - First-load student screen visually matches the prototype's kiosk hierarchy much more closely
  - Non-prototype student-mode chrome is removed or hidden from the default walk-up surface
  - Development VM live gate proves first-load title, search, and control-surface parity
test_data:
  seed: current Development VM demo dataset
  migration_before_state: branded landing screen with extra student-mode controls and widgets
  external_stubs: none
  credentials: DEMO_KIOSK_URL, DEMO_KIOSK_TOKEN
reset:
  - bash testenv/verify.sh
gate:
  - docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http -u dojo_kiosk --stop-after-init
  - bash testenv/scripts/ver-devvm-kiosk-prototype-home.sh
regression_gate:
  - bash testenv/verify.sh
  - bash testenv/scripts/ver-kiosk-home.sh
```

---

## INC-03 — Align roster-first behavior, search filtering, and card presentation

Bring the running Development VM student roster behavior into alignment with the prototype by rendering cards on first load, making search filter the visible roster, and matching card content/state expectations.

```yaml
id: INC-03
title: Make student roster visible on load and align card/filter behavior to the prototype
depends_on:
  - INC-02
touchpoints:
  - addons/dojo_kiosk/static/src/kiosk_app.js
  - addons/dojo_kiosk/static/src/kiosk.css
  - addons/dojo_kiosk/controllers/kiosk_controller.py
  - addons/dojo_kiosk/models/dojo_kiosk_service.py
  - testenv/scripts/ver-devvm-kiosk-prototype-roster.sh
deliverables:
  - Student roster grid is visible on first load on the Development VM
  - Search filters the visible roster rather than serving as the only reveal path
  - Student cards match prototype expectations for avatar, name, metadata, and checked-in badge treatment
  - Development VM live gate proves first-load roster visibility and filter behavior
test_data:
  seed: current Development VM demo dataset with seeded kiosk members and check-in history
  migration_before_state: results only appear after search and cards follow the current SPA layout contract
  external_stubs: none
  credentials: DEMO_KIOSK_URL, DEMO_KIOSK_TOKEN
reset:
  - bash testenv/verify.sh
gate:
  - docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http -u dojo_kiosk --stop-after-init
  - bash testenv/scripts/ver-devvm-kiosk-prototype-roster.sh
regression_gate:
  - bash testenv/verify.sh
  - bash testenv/scripts/ver-kiosk-roster-cards.sh
```

---

## INC-04 — Convert student action flow to prototype-style direct check-in and success state

Replace the current modal-first student flow with the prototype's direct card-tap behavior for the seeded Development VM demo members and align the checked-in and success states to the prototype contract.

```yaml
id: INC-04
title: Implement prototype-style direct check-in, checked-in state, and success overlay
depends_on:
  - INC-03
touchpoints:
  - addons/dojo_kiosk/static/src/kiosk_app.js
  - addons/dojo_kiosk/static/src/kiosk.css
  - addons/dojo_kiosk/controllers/kiosk_controller.py
  - addons/dojo_kiosk/models/dojo_kiosk_service.py
  - testenv/scripts/ver-devvm-kiosk-prototype-checkin.sh
deliverables:
  - Tapping a seeded demo student card follows the prototype's direct check-in path on the Development VM
  - Already-checked-in state is represented on the card surface in the prototype style
  - Success overlay copy, visual hierarchy, and dismiss timing match the prototype contract more closely
  - Development VM live gate proves direct check-in and success-state parity
test_data:
  seed: current Development VM demo dataset with deterministic seeded demo members and at least one check-in-eligible member
  migration_before_state: modal-first session-selection flow and richer SPA success state
  external_stubs: none
  credentials: DEMO_KIOSK_URL, DEMO_KIOSK_TOKEN
reset:
  - bash testenv/verify.sh
gate:
  - docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http -u dojo_kiosk --stop-after-init
  - bash testenv/scripts/ver-devvm-kiosk-prototype-checkin.sh
regression_gate:
  - bash testenv/verify.sh
  - bash testenv/scripts/ver-kiosk-checkin-flow.sh
```

---

## INC-05 — Normalize the student spec and close with unattended Development VM proof

Close the loop between code, runtime spec, and unattended Development VM proof so the release can be judged from artifacts and workproducts without relying on memory or subjective walkthroughs.

```yaml
id: INC-05
title: Align student specification to prototype-parity runtime and finalize unattended VM proof
depends_on:
  - INC-04
touchpoints:
  - specifications/kiosk-student-experience.md
  - releases/REL-20260629/scope.md
  - releases/REL-20260629/plan.md
deliverables:
  - Canonical student kiosk specification reflects the accepted prototype-parity runtime contract
  - Final unattended Development VM gate suite passes against the running demo
  - Release artifacts remain planning-only and operator-usable
test_data:
  seed: fully integrated Development VM demo deployment after INC-02 through INC-04
  migration_before_state: all in-scope prototype-parity deltas fixed in prior increments
  external_stubs: none
  credentials: DEMO_KIOSK_URL, DEMO_KIOSK_TOKEN
reset:
  - bash testenv/verify.sh
gate:
  - bash testenv/scripts/ver-devvm-kiosk-prototype-home.sh
  - bash testenv/scripts/ver-devvm-kiosk-prototype-roster.sh
  - bash testenv/scripts/ver-devvm-kiosk-prototype-checkin.sh
regression_gate:
  - bash testenv/verify.sh
```
