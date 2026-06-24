# Process Lessons — REL-001 Postmortem
*Date: 2026-06-24 | Authored by: John Bentley / Claude (Sonnet 4.6)*

---

## What Happened

REL-001 was audited APPROVED-PARTIAL by a third-party model (GPT-5.3-Codex) and merged. When the release was deployed to the demo server, the client immediately identified that their provided HTML design was not reflected in the running kiosk. Manual inspection confirmed at least four scope requirements that passed audit had not actually been delivered:

1. `dojo_theme` CSS token values did not match the client's design file (`scope/UFT_SUPABASE_STORAGE_PHOTOS.html`).
2. `dojo_kiosk` never loaded `dojo_theme` — the kiosk uses an entirely separate `--k-*` token system.
3. The three-panel instructor layout (`KioskInstructorLayout`) was built as a standalone component, loaded by the controller, but never mounted by `kiosk_app.js`. It was dead code.
4. The auditor marked all three items as "present" based on file existence in the diff.

---

## Root Causes

### 1. Gates checked existence, not correctness

Every gate that failed in production was a file-existence or process-exit gate. No gate verified that a value, reference, or behavior was actually correct.

**Example — INC-01 (dojo_theme tokens):**
The gate confirmed `tokens.css` existed and Odoo loaded. It did not assert that `--gold` equaled `#c9a84c`. The worker used `#eab308` — a visually similar yellow — and the gate passed.

**Example — INC-08 (three-panel layout):**
The gate confirmed `kiosk_instructor.js` existed. It did not assert that `KioskInstructorLayout` was instantiated anywhere in `kiosk_app.js`. The component was never wired.

**Rule going forward:** Every gate for a UI component must include a grep or curl-based assertion on the *specific value or reference* the scope requires, not just the file that contains it. Existence gates are only valid for truly binary deliverables (file present or not).

---

### 2. "Built in isolation" is the same as not built

The worker built `KioskInstructorLayout` in `kiosk_instructor.js`, exported it to `window`, and stopped. The integration step — mounting it inside `kiosk_app.js`'s instructor view — was never done. The component existed but had zero user-visible effect.

This is not a partial delivery. It is zero delivery. A component that is never mounted is equivalent to a component that does not exist.

**Rule going forward:** For any UI component increment, the gate must verify integration at the mount point, not just file existence. Acceptable assertions:
- `grep -q "KioskInstructorLayout" addons/dojo_kiosk/static/src/kiosk_app.js` — confirms the component is referenced in the file that actually renders the page.
- For CSS: `grep -q "var(--gold)" addons/dojo_kiosk/static/src/kiosk.css` — confirms the theme token is consumed, not just defined.

---

### 3. The auditor's diff-review methodology cannot catch "built but not wired" bugs

The third-party auditor reviewed the release diff and confirmed that `kiosk_instructor.js` appeared in the diff, therefore marked three-panel as "present." This is the correct behavior for a diff reviewer — it cannot know whether the component is mounted.

The gap is that **diff review is necessary but not sufficient**. A diff reviewer can catch: wrong files changed, missing files, scope creep. It cannot catch: correct file changed but never integrated, correct value range but wrong specific value, component built but not invoked.

**Rule going forward:** The auditor's role must be explicitly scoped. Add an **Integration Verification** section to the audit template that requires the auditor to assert:
- Cross-file references exist (e.g., component A used in file B)
- CSS token consumers match token producers (same variable names)
- Module dependency chain is complete (manifest depends, controller loads, template renders)

The auditor cannot verify these from the diff alone — these must be in the gate so the worker verifies them before commit. The auditor's job is to confirm the gates actually test what they claim.

---

### 4. Spec values were approximated instead of copied

The scope said "exact client values from `scope/UFT_SUPABASE_STORAGE_PHOTOS.html`." The worker read the spec, found the design file, and typed in values from memory or approximation. `#c9a84c` (client gold) became `#eab308` (generic yellow). `#e8192c` (client red) became `#b41e16` (different red).

These differences are invisible in a diff review. They are immediately visible to the client who provided the design.

**Rule going forward:** When a scope item says "match values from file X," the gate must contain a grep for the exact value from that file. The worker must copy, not retype. Example:
```bash
grep -q "c9a84c" addons/dojo_theme/static/src/css/tokens.css
grep -q "e8192c" addons/dojo_theme/static/src/css/tokens.css
grep -q "0a0a0c" addons/dojo_theme/static/src/css/tokens.css
```

---

### 5. No behavioral / visual gate was ever run

Every gate in REL-001 was static analysis (file exists, grep, curl login check). No gate confirmed that the running application rendered the expected output. The kiosk page was never loaded and screenshotted. If it had been, the design mismatch would have been caught immediately.

**Rule going forward:** For any increment that changes visible UI, add at least one behavioral gate:
- `curl -sf https://<demo-host>/kiosk/<token>` — confirms the kiosk SPA loads (already done).
- A Playwright or puppeteer screenshot check comparing against a reference: or at minimum, a page source grep confirming the expected DOM element or CSS class is present in the rendered HTML.

This does not need to be pixel-perfect. A grep on rendered page source for the CSS class or token value is sufficient to catch "the component was never mounted."

---

### 6. The auditor's APPROVED-PARTIAL verdict was too lenient on "partial" items

The auditor correctly identified partial deliveries for: onboarding available_actions payload shape, automation mechanism (ir.cron vs OCA rule), MuK feature parity, and success overlay timing. These were noted and the release was approved anyway.

All four of these have user-visible consequences. "Partial" on a spec item is a gap, not an acceptable state for a client-facing release.

**Rule going forward:** APPROVED-PARTIAL is only valid when the partial items are explicitly documented as accepted deviations with operator sign-off in the scope document. If they are not pre-accepted, the verdict must be REJECTED with a required remediation increment before merge.

---

## Gate Template Additions

Add the following gate types to the UnattendedBuild template:

```yaml
# For design tokens — verify exact values from reference file
gate:
  - grep -q "<exact_hex_value>" addons/<module>/static/src/css/tokens.css

# For UI components — verify integration at mount point
gate:
  - grep -q "<ComponentName>" addons/<consuming_module>/static/src/<entry_point>.js

# For CSS token consumption — verify consumer references producer
gate:
  - grep -q "var(--<token_name>)" addons/<module>/static/src/<file>.css

# For module dependency chain — verify manifest wiring
gate:
  - grep -q "<dependency_module>" addons/<module>/__manifest__.py

# For behavioral verification — verify rendered output
gate:
  - bash -c 'body=$(curl -sf http://127.0.0.1:8070/kiosk/<token>); echo "$body" | grep -q "<expected_class_or_element>"'
```

---

## Summary of Rule Changes

| # | Rule | Applies To |
|---|---|---|
| 1 | Existence gates are invalid for value, reference, or behavioral requirements | Worker, Gate author |
| 2 | UI component increments must gate on integration at the mount point | Worker, Gate author |
| 3 | Audit template must include an Integration Verification section | Auditor |
| 4 | Spec values from a reference file must be grep-verified as exact copies | Worker, Gate author |
| 5 | Any UI-changing increment must include at least one behavioral gate | Worker, Gate author |
| 6 | APPROVED-PARTIAL requires operator-signed accepted deviations in scope | Auditor, Operator |
