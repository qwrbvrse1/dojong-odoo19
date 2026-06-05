# Stage 0 Analysis — Baseline Verification

**Date:** 2026-06-05  
**Gate script:** `scripts/usability_pass/verify/s0.sh`  
**Goal:** Prove the post-rescue baseline is intact before hardening begins.

## Initial State

Ran the S0 gate on first attempt. Results:

- ❌ **Database exists:** PASS
- ❌ **pg_trgm extension:** Ensured (already present or created successfully)
- ❌ **Module upgrade:** FAILED (rc=1)
- ❌ **Web service:** TIMEOUT (could not reach http://localhost:8070/web/login)
- ❌ **All 5 demo accounts authenticate:** FAILED (web not responding)

## Root Cause

The `config/odoo.conf` path was mounted as an empty **directory** instead of a **file**. This caused:

1. Odoo to fall back to default config (socket-based postgres connection)
2. Connection failure: tried `/var/run/postgresql/.s.PGSQL.5432` instead of TCP to `db:5432`
3. Upgrade command failed to connect to database
4. Web container entered restart loop with connection errors

## Fix Applied

1. **Removed** the `config/odoo.conf` directory: `rm -rf config/odoo.conf`
2. **Created** proper config file: `cp config/odoo.conf.example config/odoo.conf`
3. **Restarted** containers: `docker compose down && docker compose up -d`

The `odoo.conf.example` already contained correct settings:
- `db_host = db` (TCP connection to docker service)
- `db_port = 5432`
- `db_user = odoo`
- `db_password = odoo`
- `db_name = odoo19`

## Second Gate Run

After fix, all assertions passed:

- ✅ Database `odoo19` exists
- ✅ `pg_trgm` extension ensured
- ✅ Module upgrade clean (rc=0, no ERROR/CRITICAL/Traceback)
- ✅ No stuck modules
- ✅ Web responds 200 on `/web/login`
- ✅ All 5 demo accounts authenticate:
  - `admin@demo.com` / `admin123`
  - `instructor1@demo.com` / `dojo@2026`
  - `demo1@demo.com` / `dojo@2026`
  - `demo2@demo.com` / `dojo@2026`
  - `DemoParent@demo.com` / `dojo@2026`

**GATE: PASSED**

## Landmines Checked

- **Landmine #5 (manifest ordering):** Not applicable at baseline — no new XML added
- **Landmine #8 (pg_trgm):** Gate script ensures `CREATE EXTENSION IF NOT EXISTS pg_trgm;` before upgrade — extension is present

## Orchestrator Gate Failure (Second Attempt)

The gate failed when run by the orchestrator with the following error:
```
ERROR: could not serialize access due to concurrent update
```

**Cause:** Web container was still running with workers/crons enabled when the gate tried to run the upgrade. The gate script expects:
1. Only `db` running initially
2. Upgrade runs in isolation (`--workers=0 --max-cron-threads=0`)
3. Then `web` starts via `stack_up`

**Resolution:** Stop web before stage completion (`docker compose stop web`). This ensures the gate runs with the expected service state.

## Baseline Confirmed

The post-rescue system is **intact** in this worktree:
- All modules in scope upgrade cleanly
- No module state corruption
- All demo accounts seeded and functional
- Web client operational

**Stage completion protocol:** Stop web before commit to ensure clean state for gate runs.

**Ready for Stage 1 (ACL closure).**
