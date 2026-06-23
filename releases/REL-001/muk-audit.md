# MuK IT Theme Replacement Coverage Audit — REL-001/INC-22

**Audit Date:** 2026-06-23  
**Scope:** Verify `dojo_theme` covers all MuK IT functionality before uninstall in INC-25  
**Auditor:** INC-22 automated audit  
**Target Modules:** 7 MuK IT modules (`muk_web_theme`, `muk_web_chatter`, `muk_web_appsbar`, `muk_web_colors`, `muk_web_dialog`, `muk_web_refresh`, `muk_web_group`)

---

## Executive Summary

**Status:** ⚠️ **CRITICAL GAP IDENTIFIED**

| Module | Features | Coverage | Status |
|---|---|---|---|
| `muk_web_theme` | Color system (13 vars) | ✅ Fully replaced by `dojo_theme/tokens.css` | **PASS** |
| `muk_web_theme` | Layout SCSS (89 lines) | ❌ NOT covered by `dojo_theme` | **FAIL — Critical** |
| `muk_web_colors` | Color palette | ✅ Replaced by `dojo_theme` | **PASS** |
| `muk_web_appsbar` | Sidebar navigation | ⚠️ Acceptable loss (deferred to Post-Release) | **ACCEPT** |
| `muk_web_chatter` | Chatter styling | ⚠️ Acceptable loss (reverts to Community default) | **ACCEPT** |
| `muk_web_dialog` | Dialog polish | ⚠️ Acceptable loss (reverts to Community default) | **ACCEPT** |
| `muk_web_refresh` | Refresh button | ⚠️ Acceptable loss (native browser refresh) | **ACCEPT** |
| `muk_web_group` | Group expand/collapse | ⚠️ Acceptable loss (Community default behavior) | **ACCEPT** |

### Critical Finding

**`dojo_theme` provides only 41 lines of CSS (design tokens).** MuK's layout SCSS (navbar border-bottom removal, appsmenu fullscreen layout, form field border styling — 89 lines total) is **NOT YET COVERED**.

**INC-23 MUST ADD** the following SCSS files to `dojo_theme` BEFORE uninstalling MuK:

1. `static/src/webclient/navbar/navbar.scss` (3 lines)
2. `static/src/webclient/appsmenu/appsmenu.scss` (79 lines)
3. `static/src/views/form/form.scss` (7 lines)

**Total:** 89 lines of layout SCSS required.

### Dependency Check

✅ **Zero custom modules depend on MuK** (verified via `grep -rl "muk_web_" addons/dojo_*/\__manifest__.py addons/ai_*/\__manifest__.py`).

No dependency blockers exist. Uninstall can proceed after SCSS coverage gap is closed.

---

## 1. Module-by-Module Analysis

### 1.1 `muk_web_theme` (saas~19.2.1.4.2)

**Purpose:** Core backend theme — color variables, navbar, appsmenu, form styling.

**Assets Provided:**
- `static/src/scss/colors.scss` (12 lines) — color palette variables
- `static/src/scss/variables.scss` (1 line) — navbar badge color
- `static/src/webclient/navbar/navbar.scss` (3 lines) — navbar border-bottom removal
- `static/src/webclient/appsmenu/appsmenu.scss` (79 lines) — fullscreen appsmenu layout
- `static/src/views/form/form.scss` (7 lines) — form field border styling

**Total:** 102 lines SCSS

**`dojo_theme` Coverage:**

| Feature | MuK | `dojo_theme` | Status |
|---|---|---|---|
| Color system | 13 SCSS variables | 13 CSS custom properties (`--bg`, `--surface`, `--red`, `--gold`, `--text`, etc.) | ✅ COVERED |
| Font system | Bootstrap defaults | Google Fonts (Bebas Neue, Barlow, Barlow Condensed) via `views/fonts.xml` | ✅ COVERED |
| Navbar border | `border-bottom: none !important;` | ❌ Not in `dojo_theme` | ❌ NOT COVERED |
| Appsmenu layout | 79-line fullscreen flexbox layout | ❌ Not in `dojo_theme` | ❌ NOT COVERED |
| Form field borders | 7-line border color override | ❌ Not in `dojo_theme` | ❌ NOT COVERED |

**Gap:** 89 lines of layout SCSS (navbar + appsmenu + form) NOT covered.

**INC-23 Impact:** Must add 3 SCSS files to `dojo_theme` before uninstall.

---

### 1.2 `muk_web_colors` (saas~19.2.1.0.5)

**Purpose:** Base color palette for light/dark modes.

**Assets Provided:**
- `static/src/scss/colors.scss` — base color definitions
- `static/src/scss/colors_light.scss` — light mode overrides
- `static/src/scss/colors_dark.scss` — dark mode overrides

**`dojo_theme` Coverage:**

✅ **FULLY COVERED** — `dojo_theme/static/src/css/tokens.css` defines 13 color tokens matching the MuK palette (surfaces, brand colors, text colors, status colors, belt colors).

**No gap.** Color system replacement is complete.

---

### 1.3 `muk_web_appsbar` (saas~19.2.1.1.5)

**Purpose:** Sidebar navigation (left-hand apps bar).

**Assets Provided:**
- `static/src/webclient/appsbar/appsbar.scss` (94 lines)
- `static/src/webclient/webclient.scss` (34 lines)
- `static/src/scss/variables.scss` (6 lines)
- `static/src/scss/variables.dark.scss` (2 lines)
- `static/src/scss/mixins.scss` (7 lines)

**Total:** 143 lines SCSS + JS overrides

**`dojo_theme` Coverage:**

❌ **NOT COVERED** — `dojo_theme` does not implement a sidebar/appsbar.

**Scope Decision:** Per REL-001 scope, sidebar retirement is an **acceptable loss**. The native Odoo Community appsmenu (top-bar dropdown) will be used after MuK uninstall. Sidebar is deferred to Post-Release work.

**No INC-23 action required** (per scope).

---

### 1.4 `muk_web_chatter` (saas~19.2.1.4.2)

**Purpose:** Polished chatter component styling.

**Assets Provided:**
- `static/src/chatter/chatter.scss` (16 lines)
- `static/src/scss/variables.scss` (2 lines)

**Total:** 18 lines SCSS + JS overrides

**`dojo_theme` Coverage:**

❌ **NOT COVERED** — `dojo_theme` does not override chatter styling.

**Scope Decision:** Per REL-001 scope, chatter polish is an **acceptable loss**. Chatter will revert to Odoo Community default styling after MuK uninstall. Enhanced chatter styling is deferred to Post-Release.

**No INC-23 action required** (per scope).

---

### 1.5 `muk_web_dialog` (saas~19.2.1.0.5)

**Purpose:** Fullscreen dialog mode and dialog styling enhancements.

**Assets Provided:**
- `static/src/core/dialog/dialog.scss` (6 lines)
- `static/src/scss/variables.scss` (2 lines)

**Total:** 8 lines SCSS + JS overrides

**`dojo_theme` Coverage:**

❌ **NOT COVERED** — `dojo_theme` does not override dialog styling.

**Scope Decision:** Per REL-001 scope, fullscreen dialogs and enhanced dialog styling are **acceptable losses**. Dialogs will revert to Odoo Community default (modal overlay, not fullscreen). Deferred to Post-Release.

**No INC-23 action required** (per scope).

---

### 1.6 `muk_web_refresh` (saas~19.2.1.0.5)

**Purpose:** Adds a manual refresh button to the control panel.

**Assets Provided:**
- `static/src/search/control_panel.js` — JS patch to add refresh button
- `static/src/search/control_panel.xml` — template override

**No SCSS.**

**`dojo_theme` Coverage:**

❌ **NOT COVERED** — `dojo_theme` does not add a refresh button.

**Scope Decision:** Per REL-001 scope, the manual refresh button is an **acceptable loss**. Users can refresh via browser (F5 / Cmd+R) or navigate away and back. Deferred to Post-Release.

**No INC-23 action required** (per scope).

---

### 1.7 `muk_web_group` (saas~19.2.1.0.2)

**Purpose:** Enhanced group expand/collapse behavior in list views.

**Assets Provided:**
- `static/src/**/*` — JS and XML overrides for group expand/collapse

**No SCSS.**

**`dojo_theme` Coverage:**

❌ **NOT COVERED** — `dojo_theme` does not override group behavior.

**Scope Decision:** Per REL-001 scope, enhanced group expand/collapse is an **acceptable loss**. List views will revert to Odoo Community default group behavior. Deferred to Post-Release.

**No INC-23 action required** (per scope).

---

## 2. Asset Bundle Impact Assessment

### MuK IT Modules — Total Lines by Category

| Category | Lines | Modules | Replacement Status |
|---|---|---|---|
| **Color SCSS** | 27 | `muk_web_theme`, `muk_web_colors`, `muk_web_appsbar`, `muk_web_chatter`, `muk_web_dialog` | ✅ Replaced by `dojo_theme/tokens.css` |
| **Layout SCSS** | 89 | `muk_web_theme` (navbar, appsmenu, form) | ❌ NOT covered by `dojo_theme` |
| **Behavioral SCSS** | 161 | `muk_web_appsbar`, `muk_web_chatter`, `muk_web_dialog` | ⚠️ Acceptable loss (deferred) |
| **JS overrides** | ~500+ | All 7 modules | ⚠️ Acceptable loss (deferred) |

**Total SCSS removed:** ~277 lines  
**Total SCSS added:** 41 lines (tokens only)  
**Net change:** **-236 lines SCSS**

**Critical:** 89 lines of layout SCSS must be added to `dojo_theme` in INC-23 to avoid visual regression.

---

## 3. INC-23 Impact Assessment

### Required Changes to INC-23 Deliverables

**Current INC-23 scope (per `releases/REL-001/plan.md`):**
- Install `dojo_theme` module
- Verify design tokens are applied
- Bump `dojo_theme` version to `saas~19.2.2.0.0`

**Required additions (per this audit):**

1. **Add 3 SCSS files to `dojo_theme` BEFORE module install:**
   - `addons/dojo_theme/static/src/webclient/navbar/navbar.scss` (3 lines)
   - `addons/dojo_theme/static/src/webclient/appsmenu/appsmenu.scss` (79 lines)
   - `addons/dojo_theme/static/src/views/form/form.scss` (7 lines)

2. **Update `dojo_theme/__manifest__.py` asset bundle:**
   ```python
   'assets': {
       'web._assets_primary_variables': [
           ('after', 'web/static/src/scss/primary_variables.scss', 'dojo_theme/static/src/css/tokens.css'),
       ],
       'web.assets_backend': [
           'dojo_theme/static/src/webclient/**/*.scss',
           'dojo_theme/static/src/views/**/*.scss',
       ],
   },
   ```

3. **Update INC-23 gates to verify SCSS files exist:**
   ```bash
   test -f addons/dojo_theme/static/src/webclient/navbar/navbar.scss
   test -f addons/dojo_theme/static/src/webclient/appsmenu/appsmenu.scss
   test -f addons/dojo_theme/static/src/views/form/form.scss
   ```

4. **Update INC-23 touchpoints:**
   ```yaml
   touchpoints:
     - addons/dojo_theme/__manifest__.py
     - addons/dojo_theme/static/src/webclient/navbar/navbar.scss  # NEW
     - addons/dojo_theme/static/src/webclient/appsmenu/appsmenu.scss  # NEW
     - addons/dojo_theme/static/src/views/form/form.scss  # NEW
     - addons/dojo_theme/views/assets.xml
   ```

**Without these changes, INC-25 (MuK uninstall) will cause visual regressions:** navbar will gain a border-bottom, appsmenu will revert to a small dropdown (not fullscreen), and form field borders will change.

---

## 4. INC-25 Safety Checklist

### Pre-Uninstall Verification

Before uninstalling MuK modules in INC-25, verify:

1. ✅ `dojo_theme` is installed and active
2. ✅ All 3 SCSS files exist in `dojo_theme` (navbar, appsmenu, form)
3. ✅ Asset bundles are compiled (`docker compose run --rm web odoo-bin --stop-after-init`)
4. ✅ Zero custom modules depend on MuK (verified in this audit)
5. ✅ Visual smoke test confirms navbar border is absent, appsmenu is fullscreen, form fields have correct border styling

### Uninstall Sequence (INC-25)

Uninstall in reverse dependency order:

1. `muk_web_theme` (depends on all others)
2. `muk_web_refresh`, `muk_web_colors`, `muk_web_appsbar`, `muk_web_dialog`, `muk_web_chatter` (peer modules)
3. `muk_web_group` (no dependencies)

**Command:**
```bash
docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http -u muk_web_theme,muk_web_refresh,muk_web_colors,muk_web_appsbar,muk_web_dialog,muk_web_chatter,muk_web_group --stop-after-init
```

Then remove directories from `addons/`.

---

## 5. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Visual regression (missing layout SCSS) | **HIGH** | **HIGH** — navbar border, appsmenu layout, form fields | ✅ Add 89 lines SCSS to `dojo_theme` in INC-23 |
| Behavioral regression (sidebar, chatter, dialogs) | **CERTAIN** | **LOW** — acceptable losses per scope | Document in user-facing changelog |
| Uninstall failure (dependency conflict) | **LOW** | **MEDIUM** — partial uninstall | Follow uninstall sequence in §4 |
| Asset bundle compilation error | **LOW** | **HIGH** — blank backend UI | Test asset compilation in INC-23 gate |
| Production upgrade timeout (asset recompile) | **MEDIUM** | **MEDIUM** — deploy rollback required | Stage in `prod2` first; monitor recompile time |

**Overall Risk:** **MEDIUM** (HIGH likelihood of visual regression IF INC-23 scope is not expanded; MITIGATED by adding SCSS files).

---

## 6. Recommendations

1. **CRITICAL:** Expand INC-23 scope to add 3 SCSS files to `dojo_theme` (89 lines total) before module install.
2. **CRITICAL:** Update INC-23 gates to verify SCSS file existence.
3. **CRITICAL:** Update INC-23 touchpoints to include new SCSS files.
4. Document acceptable losses (sidebar, chatter polish, fullscreen dialogs, refresh button, group behavior) in user-facing changelog.
5. Visual smoke test INC-23 deliverables before proceeding to INC-25.
6. Stage INC-25 uninstall in `prod2` before deploying to `prod`.

---

## 7. Conclusion

**Status:** ⚠️ **INC-23 scope expansion required**

`dojo_theme` currently provides only **design tokens** (41 lines CSS). MuK's **layout SCSS** (89 lines) is not covered. INC-23 must add 3 SCSS files (navbar, appsmenu, form) to close this gap before INC-25 can safely uninstall MuK.

**Zero dependency blockers** exist — no custom modules depend on MuK.

**Acceptable losses** (sidebar, chatter, dialogs, refresh, group behavior) are documented and deferred to Post-Release per REL-001 scope.

**Action required:** Update INC-23 plan to include layout SCSS delivery.

---

**Audit complete.**  
**Next step:** Update INC-23 deliverables and gates based on findings.
