# Stage 0 Analysis — Boot Clean

**Date:** 2026-06-04
**Gate:** `bash scripts/demo_rescue/verify/s0.sh`
**Current Status:** FAILED (upgrade rc=0, error lines=1)

## Gate Output

```
PASS: database odoo19 exists
INFO: pg_trgm ensured
INFO: running module upgrade (this IS the gate, not a convenience)
FAIL: upgrade rc=0, error lines=1 — first errors:
dojo_sign:9: (ERROR/3) Unexpected indentation.
dojo_sign:10: (WARNING/2) Block quote ends without a blank line; unexpected unindent.
2026-06-04 18:18:53,335 1 WARNING odoo19 odoo.modules.migration: Invalid version for upgrade script '/mnt/extra-addons/dojo_subscriptions/migrations/__pycache__' 
PASS: no stuck modules
PASS: web responds 200 on /web/login
GATE: FAILED
```

## Root Causes Identified

### 1. RST Docstring Error in dojo_sign/__manifest__.py (ERROR/3)

**Location:** `addons/dojo_sign/__manifest__.py:9-10`

The `description` field contains a reStructuredText docstring with improper indentation:

```python
'description': """
    Replaces the Odoo Enterprise Sign dependency with an inline, blocking waiver
    step inside the member onboarding wizard.  Uses bi_all_digital_sign's
    Binary-image approach to store the drawn signature and embeds it in a
    QWeb PDF that is attached to the newly created member record.

    Features:
    - ``waiver`` step injected into the onboarding wizard after subscription
```

The RST parser (used by Odoo for manifest parsing) is erroring on line 9 due to unexpected indentation after the blank line. This is treated as an ERROR by the upgrade log checker.

**Impact:** Gate fails because grep finds "ERROR" in upgrade log.

### 2. Duplicate Group Definition (Landmine #2 - NOT CURRENTLY FAILING)

Both files define `dojo_core.group_dojo_instructor` with identical `implied_ids`:

- `addons/dojo_core/security/dojo_security.xml:14-20` — includes `(3, ref('account.group_account_invoice'))` and `(3, ref('hr.group_hr_user'))`
- `addons/dojo_core/data/instructor_todos_data.xml:5-13` — identical implied_ids list

**Current Status:** Both files process cleanly because:
- The `account` and `hr` modules ARE installed (declared in dojo_core depends)
- The `(3, ...)` unlink operations succeed
- Odoo merges the definitions without error

**Potential Risk:** If account/hr were missing, the `ref()` would fail. However, this is NOT causing the current gate failure.

### 3. Migration __pycache__ Warning (Non-blocking)

```
WARNING odoo19 odoo.modules.migration: Invalid version for upgrade script '/mnt/extra-addons/dojo_subscriptions/migrations/__pycache__'
```

Odoo is scanning the migrations directory and finds a `__pycache__` folder (Python bytecode cache). This is a harmless warning and does NOT contain "ERROR" or "CRITICAL" keywords.

**Impact:** None (warning only, not counted as error).

### 4. Landmine #1 (Menu Ordering) - NOT PRESENT

Checked `git diff HEAD` for uncommitted changes to menu files — none found. The menu repointing mentioned in DEMO_RESCUE.md is not in this worktree.

**Status:** Not applicable to this stage.

## Summary

**Only fix needed:** Remove or fix the RST docstring formatting error in `dojo_sign/__manifest__.py`.

**Duplicate group definition:** Currently harmless; consolidation is optional and not required to pass the gate.

**Migration warning:** Can be ignored (or __pycache__ deleted for cleanliness).
