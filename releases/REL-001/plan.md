# Release Plan — REL-001: UFTKD Platform Feature Delivery

> Prose sections are for humans. Fenced `yaml` blocks are parsed by `apev-run.sh`.
> Block 1 = release config. Each subsequent block = one increment, in execution order.
> Do not put status in this file — execution state lives in the run log.
>
> **Deviation from UnattendedBuild template:** This project uses a single `SPECIFICATION.md` at the repo root rather than the `specifications/<domain>.md` per-domain convention. All increment touchpoints and deliverables reference `SPECIFICATION.md`. When running the audit, treat `SPECIFICATION.md` as the equivalent of `specifications/`.
>
> **Resumption note:** INC-01 through INC-21 passed and are committed. This plan covers only INC-22 and INC-23. All `depends_on` references to already-committed increments have been cleared.

## Release configuration

```yaml
release: REL-001
branch: rel/REL-001
worker_model: claude
alternate_model: claude
max_shots: 3
halt_on_fail: downstream
workproducts: ~/workproducts/dojong-odoo19/REL-001
baseline_gate:
  - bash testenv/verify.sh
  - test -d addons/sms_twilio && test -f addons/sms_twilio/__manifest__.py
```

---

## INC-22 — muk-audit: document MuK replacement coverage

Audit which MuK modules have equivalent coverage in `dojo_theme` and the new OWL components. Produce the uninstall order for INC-23. This is a documentation-and-verification increment — no production code changes.

**Decision rules:**
- Produce `releases/REL-001/muk-audit.md` documenting: for each of the 7 MuK modules, what functionality it provides and what in `dojo_theme` or new OWL components replaces it.
- Identify any MuK functionality not yet replaced. If gaps exist, add implementation to INC-23 scope (worker updates this plan entry's INC-23 deliverables).
- Verify that no installed non-MuK module lists a `muk_web_*` module in its `depends` list. Command: `grep -r "muk_web_" addons/*/\_\_manifest\_\_.py`.
- If any custom module depends on MuK, that dependency must be removed in INC-23 before uninstalling MuK. Document all such modules.
- Gate: audit document exists and the grep finds no MuK dependencies in custom modules (or documents them for INC-23 to resolve).

```yaml
id: INC-22
title: MuK audit — replacement coverage check
depends_on: []
touchpoints:
  - releases/REL-001/muk-audit.md
  - SPECIFICATION.md
deliverables:
  - releases/REL-001/muk-audit.md documenting per-module replacement status
  - List of any custom modules depending on muk_web_* (empty is fine)
  - INC-23 deliverables updated if gaps found
  - SPECIFICATION.md §3.4 annotated with retirement status
test_data:
  seed: n/a
  migration_before_state: n/a
  external_stubs: n/a
  credentials: n/a
reset:
  - bash testenv/reset.sh
gate:
  - test -f releases/REL-001/muk-audit.md
  - bash -c 'n=$(grep -rl muk_web_ addons/dojo_*/\__manifest__.py addons/ai_*/\__manifest__.py 2>/dev/null | wc -l); echo muk_dep_count=$n; test $n -eq 0'
  - curl -sf http://127.0.0.1:8070/web/login -o /dev/null
regression_gate:
  - bash testenv/verify.sh
```

---

## INC-23 — muk-retire: uninstall and remove all MuK modules

Uninstall all 7 `muk_web_*` modules from the `odoo19` database and remove their directories from `addons/`. Update `docs/ui-ux-guide.md` to document the `dojo_theme` token system.

**Decision rules:**
- Uninstall order (reverse dependency order): `muk_web_appsbar`, `muk_web_colors`, `muk_web_dialog`, `muk_web_group`, `muk_web_refresh`, `muk_web_chatter`, `muk_web_theme`. Uninstall one at a time via Odoo shell or `-u` with `--uninstall-module` if available; otherwise use RPC: `env['ir.module.module'].search([('name','=','muk_web_appsbar')]).button_uninstall()` per module.
- After uninstalling all 7, verify none appear in `ir.module.module` with `state = 'installed'`.
- Remove all 7 directories from `addons/`.
- Replace `docs/ui-ux-guide.md` content with `dojo_theme` token documentation: list all 15 CSS custom properties with their values and intended use. Document typography (Bebas Neue, Barlow, Barlow Condensed). Remove all MuK references.
- If uninstall of any module raises `UserError` (blocked by dependency): check `ir.module.module.downstream_dependencies()`, uninstall the blocker first. If the blocker is a custom module, remove its MuK dependency and re-upgrade it before retrying.
- Gate must confirm: no `muk_web_*` in installed modules, no `muk_web_*` dirs in `addons/`, Odoo backend loads cleanly.

```yaml
id: INC-23
title: MuK theme modules uninstalled and removed
depends_on: [INC-22]
touchpoints:
  - addons/muk_web_theme/**
  - addons/muk_web_chatter/**
  - addons/muk_web_appsbar/**
  - addons/muk_web_colors/**
  - addons/muk_web_dialog/**
  - addons/muk_web_group/**
  - addons/muk_web_refresh/**
  - docs/ui-ux-guide.md
  - SPECIFICATION.md
deliverables:
  - All 7 muk_web_* modules uninstalled from odoo19 database
  - All 7 muk_web_* directories removed from addons/
  - docs/ui-ux-guide.md rewritten with dojo_theme token documentation
  - SPECIFICATION.md §3.4 updated (MuK removed), §10.1 updated (current state = dojo_theme), §12 tech debt items resolved
test_data:
  seed: n/a
  migration_before_state: n/a
  external_stubs: n/a
  credentials: n/a
reset:
  - bash testenv/reset.sh
gate:
  - bash -c 'count=$(docker compose exec -T db psql -U odoo -d odoo19 -tAc "SELECT COUNT(*) FROM ir_module_module WHERE name LIKE '"'"'muk_web_%'"'"' AND state='"'"'installed'"'"';" 2>/dev/null || echo 0); echo muk_installed=$count; test $count -eq 0'
  - bash -c 'for mod in muk_web_theme muk_web_chatter muk_web_appsbar muk_web_colors muk_web_dialog muk_web_group muk_web_refresh; do test ! -d "addons/$mod" && echo "$mod removed" || (echo "$mod still present" && exit 1); done'
  - curl -sf http://127.0.0.1:8070/web/login -o /dev/null
  - test -f docs/ui-ux-guide.md
  - grep -q "dojo_theme" docs/ui-ux-guide.md
  - grep -vq "muk_web_" docs/ui-ux-guide.md
regression_gate:
  - bash testenv/verify.sh
  - docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http -u dojo_core,dojo_kiosk,dojo_theme,dojo_instructor_dashboard,dojo_belt_progression,dojo_members,dojo_communications,dojo_automation --test-enable --stop-after-init
```
