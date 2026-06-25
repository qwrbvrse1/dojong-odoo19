# VER-01: dojo_theme Token Verification

**Increment:** VER-01  
**Target:** `dojo_theme` module  
**Type:** Verification  
**Date:** 2026-06-25

---

## Objective

Verify that `dojo_theme` module:
1. Installs cleanly in the running Odoo instance
2. Contains exact hex token values from original client spec
3. Loads Google Fonts link in rendered admin HTML

---

## Verification Results

### 1. Module Installation
**Status:** ✅ PASS

Module upgrades cleanly:
```
docker compose run --rm --entrypoint /opt/odoo/odoo-bin web \
  -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http \
  -u dojo_theme --stop-after-init
```

Output confirms:
- `dojo_theme` loads without errors
- Registry updates successfully
- No Python exceptions

### 2. Token Value Verification
**Status:** ❌ FAIL

Current values in `addons/dojo_theme/static/src/css/tokens.css`:

| Token | Current Value | Expected Value | Status |
|-------|--------------|----------------|--------|
| `--bg` | `#000000` | `#0a0a0c` | ❌ FAIL |
| `--surface` | `#0c0c0c` | `#111116` | ❌ FAIL |
| `--surface2` | `#141414` | `#18181f` | ❌ FAIL |
| `--surface3` | `#1c1c1c` | `#1f1f2a` | ❌ FAIL |
| `--border` | `#272727` | `#2a2a38` | ❌ FAIL |
| `--red` | `#b41e16` | `#e8192c` | ❌ FAIL |
| `--gold` | `#eab308` | `#c9a84c` | ❌ FAIL |

**Failure Reason:** All seven brand/surface tokens use placeholder values instead of client specification values.

### 3. Google Fonts Integration
**Status:** ✅ PASS

`addons/dojo_theme/views/fonts.xml` contains:
- Preconnect to `fonts.googleapis.com`
- Font stylesheet link loading Bebas Neue, Barlow, Barlow Condensed
- Properly inherits `web.layout` template

Live admin HTML verification:
```bash
curl -sf -c /tmp/jar -b /tmp/jar \
  -X POST http://127.0.0.1:8070/web/session/authenticate \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"call","params":{"db":"odoo19","login":"admin@demo.com","password":"admin123"}}' && \
curl -sf -c /tmp/jar -b /tmp/jar http://127.0.0.1:8070/odoo/home | grep -q "fonts.googleapis"
```

Font link present in rendered admin HTML.

---

## Overall Status: ❌ FAIL

**Reason:** Token values do not match client specification (failure F-1).

**Next Increment:** FIX-01 must correct all seven token hex values before VER-01 can re-run and pass.

---

## Gate Command Summary

All gates executed:
1. ✅ Module upgrade: `docker compose run ... -u dojo_theme --stop-after-init`
2. ❌ Token grep assertions: 7/7 failed (values not yet corrected)
3. ✅ Font link assertion: `grep -q "fonts.googleapis"`
4. ✅ Live admin HTML verification: Font link present in running system

**Decision:** VER-01 correctly identifies failure F-1. Verification complete.
