# Stage 0 Plan — Baseline Verification Fix

**Issue:** Concurrent update error during module upgrade because web container is running.

## Root Cause (Second Attempt)

The gate script expects to control service lifecycle:
1. Start only `db` (`compose up -d db`)
2. Run upgrade command with `--workers=0 --max-cron-threads=0`
3. Start `web` via `stack_up` 
4. Test authentication

When web is already running from previous work, `compose up -d db` doesn't stop it. The running web container (with `workers = 2` from odoo.conf) has active cron threads that conflict with the upgrade command, causing:
```
ERROR: could not serialize access due to concurrent update
```

## Corrective Steps

1. **Stop web before stage completion** to ensure clean state for next gate run
2. **Add to S0 completion:** `docker compose stop web` before commit
3. This ensures the orchestrator's gate run starts with only db running (as designed)

## Rollback Plan

If this doesn't work: revert to no services running at stage end (`docker compose down`).
