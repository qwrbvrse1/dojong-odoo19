# VER-08: Three-Panel Layout Verification

## Summary
Verification of REL-001 INC-08 deliverable: the three-panel instructor layout component in the kiosk interface.

## Verification Scope
- **Target module**: `dojo_kiosk`
- **Key files**:
  - `addons/dojo_kiosk/static/src/js/kiosk_instructor.js` — component definition
  - `addons/dojo_kiosk/static/src/kiosk_app.js` — main app entry point

## Expected Behavior (per REL-001 INC-08)
The `KioskInstructorLayout` component should:
1. Be defined in `kiosk_instructor.js`
2. Be instantiated and mounted in `kiosk_app.js`
3. Render with class `k-instructor-layout` in the live kiosk HTML when instructor mode is active

## Verification Gates

### Gate 1: Module Upgrade
```bash
docker compose run --rm --entrypoint /opt/odoo/odoo-bin web \
  -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http \
  -u dojo_kiosk --stop-after-init
```
**Expected**: Exit 0, module upgrades cleanly.

### Gate 2: Live HTML Contains k-instructor-layout Class
```bash
TOKEN=$(docker compose exec -T db psql -U odoo -d odoo19 -tAc \
  "SELECT token FROM dojo_kiosk_config LIMIT 1;")
curl -sf http://127.0.0.1:8070/kiosk/$TOKEN | grep -q "k-instructor-layout"
```
**Expected**: Exit 0 if layout is instantiated and mounted in live kiosk.
**Actual (confirmed failure F-2)**: Exit 1 — class not present in rendered HTML because component is never instantiated.

### Gate 3: Static Source Contains Component Reference
```bash
grep -q "KioskInstructorLayout" addons/dojo_kiosk/static/src/kiosk_app.js
```
**Expected**: Exit 0 if `kiosk_app.js` references the component.
**Actual (confirmed failure F-2)**: Exit 1 — component is defined and exported but never imported or used in `kiosk_app.js`.

## Findings

### Component Definition (kiosk_instructor.js:9-228)
- `KioskInstructorLayout` class is defined
- Exported to `window.KioskInstructorLayout` at line 228
- Template includes `k-instructor-layout` root class at line 11
- Component is architecturally sound: three-panel layout with session info, roster grid, and alerts

### Integration Gap (kiosk_app.js)
**Problem**: `KioskInstructorLayout` is never instantiated or mounted in the main kiosk app.

**Evidence**:
- No import or reference to `KioskInstructorLayout` in `kiosk_app.js`
- No mount logic for instructor view
- Component exists as **dead code** — defined but unused

**Impact**:
- Instructor mode in live kiosk shows old single-column layout
- Three-panel layout deliverable (REL-001 INC-08) is non-functional

## Verification Result
**FAIL** — confirmed failure F-2 is accurate.

The component is defined but not integrated. Gate 2 (live HTML check) will fail because the component is never instantiated. Gate 3 (static source check) will also fail because `kiosk_app.js` does not reference `KioskInstructorLayout`.

## Next Step
This verification confirms the failure. The next increment should be **FIX-03**, which will:
1. Import/reference `KioskInstructorLayout` in `kiosk_app.js`
2. Instantiate and mount the component in the instructor view render path
3. Ensure the live kiosk curl confirms `k-instructor-layout` is present in rendered HTML
