# Stage 0 Plan — Boot Clean

**Target:** Gate passes (`bash scripts/demo_rescue/verify/s0.sh`)

**Strategy:** Fix the RST docstring error in dojo_sign manifest that causes the ERROR line in upgrade log.

## Steps

### 1. Fix dojo_sign/__manifest__.py RST docstring

**File:** `addons/dojo_sign/__manifest__.py`

**Change:** Remove indentation from the `description` field content, or simplify to plain string.

**Approach:** Change the docstring to have no leading indentation (RST requires consistent indentation, and the current mix is invalid).

**Before:**
```python
'description': """
    Replaces the Odoo Enterprise Sign dependency with an inline, blocking waiver
    step inside the member onboarding wizard.  Uses bi_all_digital_sign's
    ...
```

**After:**
```python
'description': """
Replaces the Odoo Enterprise Sign dependency with an inline, blocking waiver
step inside the member onboarding wizard.  Uses bi_all_digital_sign's
...
```

**Rollback:** `git checkout -- addons/dojo_sign/__manifest__.py`

**Time-box:** 2 minutes (simple text edit)

### 2. (Optional) Clean up __pycache__ warning

**File:** `addons/dojo_subscriptions/migrations/__pycache__/`

**Change:** Delete the directory

**Command:** `rm -rf addons/dojo_subscriptions/migrations/__pycache__`

**Rollback:** Not needed (auto-regenerated)

**Time-box:** 30 seconds

### 3. Verify gate passes

**Command:** `bash scripts/demo_rescue/verify/s0.sh`

**Expected:** All checks PASS, no ERROR/CRITICAL/Traceback in upgrade log

**If failed:** Check upgrade log at `/tmp/rescue_upgrade.log` for new errors and iterate.

### 4. Commit

```bash
git add -A
git commit -m "rescue S0: fix dojo_sign RST docstring error"
```

## Out of Scope

- Duplicate group definition in instructor_todos_data.xml (currently working, not causing failure)
- Menu ordering issues (not present in this worktree)
- Any other landmines from DEMO_RESCUE.md (addressed in later stages)

## Success Criteria

- Gate script exits 0
- Upgrade log contains ZERO lines matching "ERROR|CRITICAL|Traceback"
- No stuck modules
- Web responds 200 on /web/login

## Actual Execution

**Completed:** 2026-06-04 18:23

**Changes Made:**
1. Simplified `addons/dojo_sign/__manifest__.py` description field to plain text (removed RST formatting that was causing parse errors)
2. Removed `addons/dojo_subscriptions/migrations/__pycache__/` directory

**Gate Status:** ✅ PASSED

**Note on Commit:** Git permission issue prevents direct commit from this user (ainzellan) - the orchestrator script will handle the commit after stage completion per `run_rescue.sh:110-111`.
