# Kiosk UI/UX Redesign — Design Spec
**Date:** 2026-03-27
**Module:** `dojo_kiosk`
**Scope:** Visual modernisation of (1) the Kiosk Admin backend panel and (2) the Kiosk tablet frontend. No functional/business-logic changes. No new sections or features added — only existing functionality is restyled.

---

## 1. Context

The `dojo_kiosk` module currently uses standard Odoo list/form views for administration and a standalone OWL SPA (`kiosk_app.js` + `kiosk.css`) for the tablet check-in terminal. Both need a visual uplift inspired by a bold, branded aesthetic — tight typography, red primary accent, industrial minimalism — while remaining scoped to the custom module only (no global Odoo UI changes). The redesign keeps all existing buttons, sections, and functionality identical; only presentation changes.

---

## 2. Constraints

1. Do not edit any functional/business-logic code (models, controllers, service methods).
2. All UI work must use OWL templates, CSS, and existing Odoo view XML.
3. Do not modify default or global Odoo UI.
4. All icons must be present — use best-fit Font Awesome (backend) or Material Symbols (kiosk) icons.
5. JS edits are allowed only for UI/UX concerns (animations, layout state, transitions).
6. Do not add new sections, views, or nav items that do not exist in the current module.

---

## 3. Admin Panel Redesign

### 3.1 Goal
Replace the standard Odoo list view for `dojo.kiosk.config` with a full custom OWL client action that renders a branded admin layout. The existing Odoo form view for editing individual kiosk records is reused unchanged. Only the existing "Kiosks" section (the list) is wrapped in the new layout — no new nav sections are invented.

### 3.2 Layout
```
┌──────────────────────────────────────────────────────────────┐
│  [▣] Dojo Kiosk Admin                       [+ New Kiosk]   │  ← AdminTopNav
├──────────────────┬───────────────────────────────────────────┤
│ KIOSK ADMIN      │  [+ NEW]  Kiosks ⚙  [Search…] ↺  1-1/1  │
│ ──────────────   │  ─────────────────────────────────────── │
│ ▣ Kiosks      ◀  │  □  KIOSK NAME   KIOSK URL    THEME  ACT │
│                  │  □  Front Desk   http://…      Dark   ✓   │
│                  │                                    [▶ Launch]│
│ [▶ LAUNCH        │                                           │
│    KIOSK]        │                                           │
│                  │                                           │
│ → Logout         │                                           │
├──────────────────┴───────────────────────────────────────────┤
│ © Dojang                                    ● Sync: Active   │
└──────────────────────────────────────────────────────────────┘
```

### 3.3 Component Tree

| Component | Responsibility |
|---|---|
| `KioskAdminApp` | Root client action. Loads kiosk records via ORM service on mount. |
| `AdminTopNav` | Branded top bar: logo/title left, "New Kiosk" button right, user avatar. |
| `AdminSidebar` | Left panel: "Kiosk Admin" role header, "Kiosks" nav item (the only real section), "Launch Kiosk" button (opens modal), Logout link. |
| `KioskManagementView` | Toolbar (New, search input, refresh, pagination counter) + kiosk table. Row click → Odoo form view. Launch button per row → `action_open_kiosk_url`. |
| `LaunchKioskModal` | Overlay listing active kiosks; clicking one opens its URL in a new tab. |

No stub views for Analytics, System Health, or Check-in Mode — these do not exist and are not added.

### 3.4 Data Flow
- On mount: `orm.searchRead("dojo.kiosk.config", [], fields, {order:"name"})` — populates kiosk list.
- Refresh button: re-runs the same query.
- Search input: client-side filter on `name` field (no extra RPC).
- Pagination: client-side slice.
- New / row click: `actionService.doAction` with the existing form view action ID — reuses the existing Odoo form view.
- Launch (row button): `actionService.doAction({type:"ir.actions.act_url", url, target:"new"})`.
- Launch Kiosk (sidebar button): opens `LaunchKioskModal` listing all active kiosk URLs.

### 3.5 Brand Tokens (Admin)
| Token | Value |
|---|---|
| Primary red | `#b41e16` |
| Primary container | `#d7392c` |
| Background | `#fcf8f8` |
| Surface | `#ffffff` |
| Surface container | `#f1edec` |
| Border | `#e5e2e1` |
| Text | `#1c1b1b` |
| Text secondary | `#5b403c` |
| Font | Inter (system stack fallback) |
| Border radius | 2–4px (tight) |
| Label tracking | `0.08em` uppercase |

### 3.6 Icons (Font Awesome — already in Odoo backend)
| Element | Icon |
|---|---|
| Kiosks nav item | `fa-th-large` |
| Launch Kiosk button | `fa-tablet` |
| Logout | `fa-sign-out` |
| New button | `fa-plus` |
| Launch row button | `fa-external-link` |
| Refresh | `fa-refresh` |

### 3.7 New Files
- `addons/dojo_kiosk/static/src/xml/kiosk_admin.xml`
- `addons/dojo_kiosk/static/src/js/kiosk_admin.js`
- `addons/dojo_kiosk/static/src/css/kiosk_admin.css`

### 3.8 Modified Files
- `addons/dojo_kiosk/views/dojo_kiosk_views.xml` — add `ir.actions.client` record; redirect menu action to client action.
- `addons/dojo_kiosk/__manifest__.py` — register new assets in `web.assets_backend`.

---

## 4. Kiosk Tablet Frontend Redesign

### 4.1 Goal
Restructure the welcome/search screen layout in `kiosk_app.js` and update `kiosk.css` design tokens to match the bold dark aesthetic. All other views (member card, PIN modal, instructor mode, success/error) inherit the updated CSS tokens with no template changes — they keep their existing structure.

### 4.2 Layout — Welcome Screen
```
┌──────────────────────────────────────────────────┐
│ [apparel icon] DOJO KIOSK   [sync] [settings]    │  ← thin header (48px)
│                                                  │
│                                                  │
│              WELCOME!                            │  ← huge bold italic uppercase
│      Type your name to check in                  │
│                                                  │
│   ┌──────────────────────────────────────────┐   │  ← red-bordered search input
│   │  Student Name…                   [ENTER] │   │
│   └──────────────────────────────────────────┘   │
│                                                  │
│  ┌──────────┐┌──────────┐┌──────────┐┌────────┐  │  ← status cards (from bootstrap)
│  │ACTIVE NOW││SESSION   ││TIME      ││INSTRUC.│  │
│  │    12    ││Poomsae   ││5:45 PM   ││Choi    │  │
│  └──────────┘└──────────┘└──────────┘└────────┘  │
│                                                  │
│ ● Connected   © Dojang          [kiosk name]     │  ← footer
└──────────────────────────────────────────────────┘
```

### 4.3 Template Changes (`kiosk_app.js`)
Only the `KioskApp` root template and the `SearchView` component template are restructured:

- **`KioskApp` template**: Remove search input from `.k-header`. Header becomes a minimal branded bar (logo icon + name left, sync + settings icon buttons right).
- **`SearchView` template**: Add `.k-welcome-screen` wrapper. Inside: `.k-welcome-title` ("WELCOME!"), `.k-welcome-subtitle`, the existing search input (restyled, full-width, centred), and `.k-status-bar`.
- **`.k-status-bar`**: 4 cards reading from `this.state.sessions[0]` (gracefully shows `—` if no session today):
  - **Active Now** — `sessions[0].attendance_count`
  - **Session** — `sessions[0].name`
  - **Time** — `formatTime(sessions[0].start_datetime)`
  - **Instructor** — `sessions[0].instructor_name`
- **Footer template**: connection status dot + "© Dojang" + `config.name` (kiosk identifier).
- Header icon buttons use Material Symbols (`apparel`, `sync`, `settings`) — font loaded via controller HTML shell.

All other component templates (member card, PIN modal, success/error, instructor mode, idle screen) are **not changed** — they continue to work as-is and inherit the updated CSS tokens automatically.

### 4.4 CSS Changes (`kiosk.css`)
- **Dark theme accent**: `#29b6f6` → `#FA5241` (red-orange)
- **Light theme accent**: `#1a73e8` → `#b41e16` (deep red)
- Add `.k-welcome-screen` — `display:flex; flex-direction:column; align-items:center; justify-content:center; flex:1; gap:2rem; padding: 2rem`
- Add `.k-welcome-title` — `font-size: clamp(3rem, 10vw, 6rem); font-weight:900; font-style:italic; text-transform:uppercase; letter-spacing:-0.03em`
- Add `.k-welcome-subtitle` — muted `var(--k-text-2)` secondary text
- Add `.k-status-bar` — 4-column grid pinned to bottom of body area, dark bordered cards
- Add `.k-status-card` — tiny uppercase label + large bold value
- Update `.k-header__search` focus ring to red glow: `box-shadow: 0 0 0 3px rgba(250,82,65,.25)`
- Restyle `.k-header` to minimal height (no search padding), align icon buttons right

### 4.5 Controller Change (`kiosk_controller.py`)
Add Material Symbols font `<link>` to the HTML shell served at `/kiosk/<token>`:
```html
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap"/>
```

### 4.6 Modified Files
- `addons/dojo_kiosk/static/src/kiosk_app.js`
- `addons/dojo_kiosk/static/src/kiosk.css`
- `addons/dojo_kiosk/controllers/kiosk_controller.py`

---

## 5. Out of Scope
- No changes to models, service logic, or API controllers.
- No changes to `muk_web_*` theme modules.
- No changes to other `dojo_*` modules.
- The Odoo form view for editing a single kiosk config record is not restyled.
- No new nav sections, stub views, or placeholder pages are added.
- Instructor mode, member card, success/error, PIN modal templates are not restructured.

---

## 6. Verification
1. Odoo backend → Kiosk app → renders branded admin layout (top nav + sidebar + kiosk table).
2. Sidebar shows only "Kiosks" nav item — no phantom Analytics/System Health sections.
3. Click a kiosk row → opens standard Odoo form view for editing.
4. Click "+ New" → opens standard Odoo form view in create mode.
5. Click "Launch" row button → opens kiosk URL in new tab.
6. Sidebar "Launch Kiosk" button → opens modal listing active kiosk URLs.
7. Open `/kiosk/<token>` → shows WELCOME! centred layout, red-bordered search, status cards.
8. Status cards populate from today's session (show `—` if no sessions).
9. Existing flows (search, check-in, PIN, instructor mode, idle screen) work end-to-end.
10. Dark and light theme both render correctly with updated red accent.
