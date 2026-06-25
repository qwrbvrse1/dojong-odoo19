# VER-02 Verification — sms_twilio module installed state and upgrade

## Verification target
REL-001 INC-02 delivered the `sms_twilio` module for Twilio SMS integration. This verification increment confirms:
1. The module manifest exists at the declared touchpoint `addons/sms_twilio/__manifest__.py`
2. The module upgrades cleanly against the running Odoo 19 instance (no Python errors, clean shutdown)
3. The module state is `installed` in the live `ir_module_module` table

## Contract with REL-001 INC-02
The original increment delivered:
- Module structure at `addons/sms_twilio/`
- Manifest declaring dependencies: `sms` base module
- Views: `res_config_settings_views.xml`, `sms_sms_views.xml`, `sms_twilio_account_manage_views.xml`
- Security: `security/ir.model.access.csv`
- Backend assets: `static/src/**/*`

This verification does NOT test Twilio API integration or SMS sending functionality. It verifies only that the module **structure** is valid and the Odoo module loader accepts it.

## Method
Three-gate live system verification:

### Gate 1: File existence
```bash
test -f addons/sms_twilio/__manifest__.py
```
Confirms the manifest file is present at the expected path.

### Gate 2: Module upgrade
```bash
docker compose run --rm --entrypoint /opt/odoo/odoo-bin web \
  -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http \
  -u sms_twilio --stop-after-init
```
Runs Odoo module upgrade in non-HTTP mode. The `-u sms_twilio` flag forces an upgrade of the module and all its dependencies. Exit code 0 means:
- Python code in the module is syntactically valid
- All declared dependencies are satisfied
- All declared data files (views, security) load without error
- No model/field/constraint conflicts

### Gate 3: Database state query
```bash
bash -c 'state=$(docker compose exec -T db psql -U odoo -d odoo19 -tAc \
  "SELECT state FROM ir_module_module WHERE name='"'"'sms_twilio'"'"';"); \
  echo "sms_twilio_state=$state"; test "$state" = "installed"'
```
Queries the live PostgreSQL database for the module's installation state. The `ir_module_module` table is Odoo's source of truth for module status. Possible states:
- `uninstalled` — module known but not loaded
- `to install` — queued for installation
- `installed` — fully loaded and active
- `to upgrade` — needs upgrade on next restart
- `to remove` — queued for uninstall

Expected: `installed`

## Verification outcome
**PASS** — All three gates executed successfully against the running system.

## Evidence (shot 4)
### Gate 1 output
```
manifest exists
```

### Gate 2 output (upgrade log excerpt)
```
2026-06-25 15:21:53,553 1 INFO odoo19 odoo.modules.loading: loading 1 modules...
2026-06-25 15:21:53,553 1 INFO odoo19 odoo.modules.loading: loading module sms_twilio
2026-06-25 15:21:53,724 1 INFO odoo19 odoo.modules.loading: Module dojo_communications loaded in 0.31s
2026-06-25 15:21:53,907 1 INFO odoo19 odoo.modules.loading: 100 modules loaded in 2.02s
2026-06-25 15:21:54,543 1 INFO odoo19 odoo.modules.loading: Modules loaded.
2026-06-25 15:21:54,553 1 INFO odoo19 odoo.service.server: Initiating shutdown
2026-06-25 15:21:54,553 1 INFO odoo19 odoo.sql_db: ConnectionPool: Closed 1 connections
```
Clean shutdown, no errors.

### Gate 3 output
```
sms_twilio_state=installed
```

## Regression verification
`testenv/verify.sh` passes:
```
verify: healthy
```
- Docker Compose services `web` and `db` are running
- Odoo web server responds on port 8070
- PostgreSQL database `odoo19` is accessible

## Conclusion
The `sms_twilio` module delivered in REL-001 INC-02 is structurally valid, upgrades without error, and is confirmed installed in the live database. This increment satisfies the verification contract for INC-02.

No code changes were required — this is a verification-only increment documenting that the previously delivered module meets its installation contract.
