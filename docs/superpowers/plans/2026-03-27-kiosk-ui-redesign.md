# Kiosk UI/UX Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Modernise the visual design of `dojo_kiosk` — a branded admin panel (OWL client action) and a redesigned kiosk tablet welcome screen — without touching any business logic.

**Architecture:** Two independent surfaces. (1) A new `KioskAdminApp` OWL client action replaces the standard Odoo list view, rendering a red-accent branded layout with sidebar, top nav, kiosk table, and launch modal. (2) The existing `kiosk_app.js` SPA gets a restructured welcome screen: search moves from the header into the body as a centred large input beneath a bold WELCOME! hero, with a 4-card status bar drawn from the bootstrap session data.

**Tech Stack:** Odoo OWL (owl.js inline templates + `@odoo/owl` imports for backend), QWeb XML templates, CSS custom properties, Font Awesome (Odoo backend), Material Symbols (kiosk frontend via Google Fonts link).

**Spec:** `docs/superpowers/specs/2026-03-27-kiosk-ui-redesign.md`

---

## File Map

| Action | Path | Purpose |
|---|---|---|
| Create | `addons/dojo_kiosk/static/src/css/kiosk_admin.css` | Admin panel scoped styles (`.ka-*` prefix) |
| Create | `addons/dojo_kiosk/static/src/xml/kiosk_admin.xml` | OWL QWeb templates for admin panel |
| Create | `addons/dojo_kiosk/static/src/js/kiosk_admin.js` | `KioskAdminApp` OWL component |
| Modify | `addons/dojo_kiosk/__manifest__.py` | Register new backend assets |
| Modify | `addons/dojo_kiosk/views/dojo_kiosk_views.xml` | Add `ir.actions.client`, redirect menu |
| Modify | `addons/dojo_kiosk/static/src/kiosk.css` | Update accent tokens + add welcome/status classes |
| Modify | `addons/dojo_kiosk/controllers/kiosk_controller.py` | Add Material Symbols `<link>` to HTML shell |
| Modify | `addons/dojo_kiosk/static/src/kiosk_app.js` | Restructure KioskApp header + body templates |

---

## Task 1: Admin Panel CSS

**Files:**
- Create: `addons/dojo_kiosk/static/src/css/kiosk_admin.css`

- [ ] **Step 1: Create the CSS file**

```css
/* ── Dojo Kiosk Admin Panel ─────────────────────────────────────
   All rules scoped to .ka-* prefix. No global Odoo styles touched.
─────────────────────────────────────────────────────────────── */

/* ── Tokens ── */
.ka-app {
    --ka-primary:      #b41e16;
    --ka-primary-btn:  #d7392c;
    --ka-bg:           #fcf8f8;
    --ka-surface:      #ffffff;
    --ka-surface-2:    #f6f3f2;
    --ka-surface-3:    #f1edec;
    --ka-border:       #e5e2e1;
    --ka-text:         #1c1b1b;
    --ka-text-2:       #5b403c;
    --ka-text-muted:   #8f706b;
    --ka-radius:       2px;
    --ka-font:         'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

/* ── App shell ── */
.ka-app {
    display: flex;
    flex-direction: column;
    height: 100vh;
    background: var(--ka-bg);
    font-family: var(--ka-font);
    color: var(--ka-text);
    font-size: 14px;
    overflow: hidden;
}

.ka-body {
    display: flex;
    flex: 1;
    overflow: hidden;
}

/* ── Top nav ── */
.ka-topnav {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 2rem;
    height: 52px;
    background: var(--ka-surface);
    border-bottom: 1px solid var(--ka-border);
    z-index: 100;
    flex-shrink: 0;
}

.ka-topnav__brand {
    display: flex;
    align-items: center;
    gap: 10px;
}

.ka-brand-icon {
    color: var(--ka-primary);
    font-size: 18px;
}

.ka-brand-title {
    font-weight: 800;
    font-size: 15px;
    letter-spacing: -0.02em;
    color: var(--ka-primary);
    text-transform: uppercase;
}

.ka-topnav__actions {
    display: flex;
    align-items: center;
    gap: 16px;
}

.ka-avatar {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background: var(--ka-surface-3);
    border: 1px solid var(--ka-border);
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--ka-text-2);
    font-size: 18px;
    cursor: pointer;
}

/* ── Sidebar ── */
.ka-sidebar {
    width: 240px;
    background: var(--ka-surface-2);
    border-right: 1px solid var(--ka-border);
    display: flex;
    flex-direction: column;
    flex-shrink: 0;
}

.ka-sidebar__header {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 1.25rem 1.25rem 1rem;
    border-bottom: 1px solid var(--ka-border);
}

.ka-sidebar__role-icon {
    width: 32px;
    height: 32px;
    background: var(--ka-primary);
    color: white;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: var(--ka-radius);
    font-size: 13px;
    flex-shrink: 0;
}

.ka-sidebar__role-title {
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--ka-text);
    line-height: 1.2;
}

.ka-sidebar__role-sub {
    font-size: 10px;
    color: var(--ka-text-muted);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    line-height: 1.2;
}

.ka-sidebar__nav {
    flex: 1;
    padding: 0.75rem 0.75rem 0;
}

.ka-nav-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 12px;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--ka-text-2);
    text-decoration: none;
    border-radius: var(--ka-radius);
    transition: background 100ms, color 100ms;
    cursor: pointer;
    border: none;
    background: none;
    width: 100%;
    text-align: left;
}

.ka-nav-item:hover {
    background: var(--ka-surface);
    color: var(--ka-text);
}

.ka-nav-item--active {
    background: var(--ka-surface);
    color: var(--ka-primary);
    border-right: 3px solid var(--ka-primary);
}

.ka-sidebar__footer {
    padding: 0.75rem;
    border-top: 1px solid var(--ka-border);
    display: flex;
    flex-direction: column;
    gap: 4px;
}

/* ── Main content ── */
.ka-main {
    flex: 1;
    overflow: auto;
    padding: 1.25rem;
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    min-width: 0;
}

/* ── Toolbar ── */
.ka-toolbar {
    display: flex;
    align-items: center;
    gap: 1rem;
    background: var(--ka-surface);
    border: 1px solid var(--ka-border);
    border-radius: var(--ka-radius);
    padding: 6px 12px;
    flex-shrink: 0;
}

.ka-toolbar__left {
    display: flex;
    align-items: center;
    gap: 12px;
}

.ka-toolbar__center {
    flex: 1;
    max-width: 380px;
}

.ka-toolbar__right {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-left: auto;
    flex-shrink: 0;
}

.ka-toolbar__title {
    font-size: 12px;
    font-weight: 700;
    color: var(--ka-text-2);
    display: flex;
    align-items: center;
    gap: 4px;
}

.ka-search-wrap {
    position: relative;
    width: 100%;
}

.ka-search-icon {
    position: absolute;
    left: 8px;
    top: 50%;
    transform: translateY(-50%);
    color: var(--ka-text-muted);
    font-size: 12px;
    pointer-events: none;
}

.ka-search-input {
    width: 100%;
    padding: 5px 8px 5px 28px;
    border: 1px solid var(--ka-border);
    border-radius: var(--ka-radius);
    font-size: 12px;
    color: var(--ka-text);
    background: var(--ka-bg);
    outline: none;
    transition: border-color 120ms, box-shadow 120ms;
    font-family: var(--ka-font);
}

.ka-search-input:focus {
    border-color: var(--ka-primary);
    box-shadow: 0 0 0 2px rgba(180, 30, 22, 0.12);
}

.ka-search-input::placeholder {
    color: var(--ka-text-muted);
}

.ka-pagination-label {
    font-size: 11px;
    font-weight: 700;
    color: var(--ka-text-2);
    white-space: nowrap;
    padding: 0 4px;
}

/* ── Table ── */
.ka-table-wrap {
    background: var(--ka-surface);
    border: 1px solid var(--ka-border);
    border-radius: var(--ka-radius);
    overflow: hidden;
    flex: 1;
}

.ka-table {
    width: 100%;
    border-collapse: collapse;
    table-layout: auto;
}

.ka-th {
    padding: 8px 12px;
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--ka-text-muted);
    background: var(--ka-surface-3);
    border-bottom: 1px solid var(--ka-border);
    text-align: left;
    white-space: nowrap;
}

.ka-th--check,
.ka-th--center { text-align: center; width: 48px; }

.ka-row {
    transition: background 80ms;
    cursor: pointer;
}

.ka-row:hover { background: var(--ka-surface-2); }

.ka-td {
    padding: 10px 12px;
    font-size: 12px;
    color: var(--ka-text);
    border-bottom: 1px solid var(--ka-border);
    vertical-align: middle;
}

.ka-td--check,
.ka-td--center { text-align: center; }

.ka-td--name { font-weight: 600; }

.ka-td--actions {
    text-align: right;
    white-space: nowrap;
}

.ka-td-empty {
    padding: 40px;
    text-align: center;
    color: var(--ka-text-muted);
    font-size: 13px;
}

.ka-link {
    color: #3b82f6;
    text-decoration: none;
    font-size: 12px;
    word-break: break-all;
}

.ka-link:hover { text-decoration: underline; }

.ka-active-check { color: var(--ka-primary); }
.ka-inactive-check { color: var(--ka-text-muted); }

/* ── Buttons ── */
.ka-btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 14px;
    border: none;
    border-radius: var(--ka-radius);
    font-family: var(--ka-font);
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    cursor: pointer;
    transition: opacity 120ms, transform 80ms;
    white-space: nowrap;
}

.ka-btn:active { transform: scale(0.98); }

.ka-btn--primary {
    background: var(--ka-primary-btn);
    color: white;
}

.ka-btn--primary:hover { opacity: 0.9; }

.ka-btn--dark {
    background: #334155;
    color: white;
}

.ka-btn--dark:hover { opacity: 0.88; }

.ka-btn--launch-sidebar {
    width: 100%;
    justify-content: center;
    background: var(--ka-primary);
    color: white;
    padding: 10px;
}

.ka-btn--launch-sidebar:hover { opacity: 0.9; }

.ka-btn--launch-row {
    background: #718096;
    color: white;
    padding: 4px 10px;
    font-size: 10px;
}

.ka-btn--launch-row:hover { background: #4a5568; }

.ka-icon-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 28px;
    height: 28px;
    background: transparent;
    border: none;
    border-radius: var(--ka-radius);
    color: var(--ka-text-muted);
    cursor: pointer;
    font-size: 13px;
    transition: background 100ms, color 100ms;
}

.ka-icon-btn:hover { background: var(--ka-surface-3); color: var(--ka-text); }
.ka-icon-btn:disabled { opacity: 0.35; cursor: default; }

/* ── Footer ── */
.ka-footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 2rem;
    background: var(--ka-surface);
    border-top: 1px solid var(--ka-border);
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--ka-text-muted);
    flex-shrink: 0;
}

.ka-footer__left { display: flex; align-items: center; gap: 16px; }
.ka-footer__right { display: flex; align-items: center; gap: 8px; }

.ka-footer__link {
    color: var(--ka-text-muted);
    text-decoration: none;
}

.ka-footer__link:hover { color: var(--ka-primary); }

.ka-sync-dot {
    display: inline-block;
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: #22c55e;
}

/* ── Launch Kiosk Modal ── */
.ka-modal-overlay {
    position: fixed;
    inset: 0;
    background: rgba(28, 27, 27, 0.55);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
}

.ka-modal {
    background: var(--ka-surface);
    border: 1px solid var(--ka-border);
    border-radius: 4px;
    width: 480px;
    max-width: 92vw;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
}

.ka-modal__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 14px 20px;
    border-bottom: 1px solid var(--ka-border);
}

.ka-modal__title {
    font-size: 13px;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    color: var(--ka-text);
    margin: 0;
}

.ka-modal__close {
    background: none;
    border: none;
    color: var(--ka-text-muted);
    cursor: pointer;
    font-size: 16px;
    padding: 4px;
    line-height: 1;
    transition: color 100ms;
}

.ka-modal__close:hover { color: var(--ka-text); }

.ka-modal__body {
    padding: 16px 20px;
    display: flex;
    flex-direction: column;
    gap: 8px;
    max-height: 60vh;
    overflow-y: auto;
}

.ka-modal__empty {
    color: var(--ka-text-muted);
    font-size: 13px;
    text-align: center;
    padding: 16px 0;
}

.ka-modal-kiosk-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 12px;
    background: var(--ka-surface-2);
    border-radius: var(--ka-radius);
    font-size: 13px;
    font-weight: 600;
    color: var(--ka-text);
    gap: 12px;
}

.ka-modal-kiosk-row span {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}
```

- [ ] **Step 2: Verify file exists**

```bash
ls "addons/dojo_kiosk/static/src/css/kiosk_admin.css"
```
Expected: file listed.

---

## Task 2: Admin Panel XML Templates

**Files:**
- Create: `addons/dojo_kiosk/static/src/xml/kiosk_admin.xml`

- [ ] **Step 1: Create the template file**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<templates xml:space="preserve">

    <t t-name="dojo_kiosk.KioskAdminApp">
        <div class="ka-app">

            <!-- ── Top Nav ── -->
            <nav class="ka-topnav">
                <div class="ka-topnav__brand">
                    <i class="fa fa-th-large ka-brand-icon"/>
                    <span class="ka-brand-title">Dojo Kiosk Admin</span>
                </div>
                <div class="ka-topnav__actions">
                    <button class="ka-btn ka-btn--primary" t-on-click="openNew">
                        <i class="fa fa-plus"/> New Kiosk
                    </button>
                    <div class="ka-avatar" title="Admin">
                        <i class="fa fa-user-circle"/>
                    </div>
                </div>
            </nav>

            <!-- ── Body (sidebar + main) ── -->
            <div class="ka-body">

                <!-- Sidebar -->
                <aside class="ka-sidebar">
                    <div class="ka-sidebar__header">
                        <div class="ka-sidebar__role-icon">
                            <i class="fa fa-th-large"/>
                        </div>
                        <div>
                            <div class="ka-sidebar__role-title">Kiosk Admin</div>
                            <div class="ka-sidebar__role-sub">Management System</div>
                        </div>
                    </div>

                    <nav class="ka-sidebar__nav">
                        <div class="ka-nav-item ka-nav-item--active">
                            <i class="fa fa-th-large"/>
                            <span>Kiosks</span>
                        </div>
                    </nav>

                    <div class="ka-sidebar__footer">
                        <button class="ka-btn ka-btn--launch-sidebar" t-on-click="openLaunchModal">
                            <i class="fa fa-tablet"/> Launch Kiosk
                        </button>
                        <button class="ka-nav-item" t-on-click="logout">
                            <i class="fa fa-sign-out"/>
                            <span>Logout</span>
                        </button>
                    </div>
                </aside>

                <!-- Main content -->
                <main class="ka-main">

                    <!-- Toolbar -->
                    <div class="ka-toolbar">
                        <div class="ka-toolbar__left">
                            <button class="ka-btn ka-btn--dark" t-on-click="openNew">
                                <i class="fa fa-plus"/> New
                            </button>
                            <span class="ka-toolbar__title">
                                Kiosks <i class="fa fa-cog" style="font-size:10px;"/>
                            </span>
                        </div>
                        <div class="ka-toolbar__center">
                            <div class="ka-search-wrap">
                                <i class="fa fa-search ka-search-icon"/>
                                <input
                                    class="ka-search-input"
                                    type="text"
                                    placeholder="Search..."
                                    t-att-value="state.search"
                                    t-on-input="onSearchInput"/>
                            </div>
                        </div>
                        <div class="ka-toolbar__right">
                            <button class="ka-icon-btn" t-on-click="loadKiosks" title="Refresh">
                                <i class="fa fa-refresh"/>
                            </button>
                            <span class="ka-pagination-label" t-esc="paginationLabel"/>
                            <button class="ka-icon-btn"
                                t-on-click="prevPage"
                                t-att-disabled="state.page === 0 ? 'disabled' : undefined">
                                <i class="fa fa-chevron-left"/>
                            </button>
                            <button class="ka-icon-btn"
                                t-on-click="nextPage"
                                t-att-disabled="state.page >= totalPages - 1 ? 'disabled' : undefined">
                                <i class="fa fa-chevron-right"/>
                            </button>
                        </div>
                    </div>

                    <!-- Kiosk Table -->
                    <div class="ka-table-wrap">
                        <table class="ka-table">
                            <thead>
                                <tr>
                                    <th class="ka-th ka-th--check">
                                        <input type="checkbox"/>
                                    </th>
                                    <th class="ka-th">Kiosk Name</th>
                                    <th class="ka-th">Kiosk URL</th>
                                    <th class="ka-th">Theme</th>
                                    <th class="ka-th ka-th--center">Active</th>
                                    <th class="ka-th"/>
                                </tr>
                            </thead>
                            <tbody>
                                <t t-if="state.loading">
                                    <tr>
                                        <td colspan="6" class="ka-td-empty">
                                            <i class="fa fa-spinner fa-spin"/> Loading…
                                        </td>
                                    </tr>
                                </t>
                                <t t-elif="pagedKiosks.length === 0">
                                    <tr>
                                        <td colspan="6" class="ka-td-empty">No kiosks found.</td>
                                    </tr>
                                </t>
                                <t t-else="">
                                    <t t-foreach="pagedKiosks" t-as="kiosk" t-key="kiosk.id">
                                        <tr class="ka-row" t-on-click="() => this.openRecord(kiosk)">
                                            <td class="ka-td ka-td--check" t-on-click.stop="">
                                                <input type="checkbox"/>
                                            </td>
                                            <td class="ka-td ka-td--name" t-esc="kiosk.name"/>
                                            <td class="ka-td">
                                                <a class="ka-link"
                                                    t-att-href="kiosk.kiosk_url"
                                                    t-on-click.stop=""
                                                    target="_blank"
                                                    t-esc="kiosk.kiosk_url"/>
                                            </td>
                                            <td class="ka-td" t-esc="kiosk.theme_mode"/>
                                            <td class="ka-td ka-td--center">
                                                <t t-if="kiosk.active">
                                                    <i class="fa fa-check-square-o ka-active-check"/>
                                                </t>
                                                <t t-else="">
                                                    <i class="fa fa-square-o ka-inactive-check"/>
                                                </t>
                                            </td>
                                            <td class="ka-td ka-td--actions" t-on-click.stop="">
                                                <button class="ka-btn ka-btn--launch-row"
                                                    t-on-click="() => this.launchKiosk(kiosk)">
                                                    <i class="fa fa-external-link"/> Launch
                                                </button>
                                            </td>
                                        </tr>
                                    </t>
                                </t>
                            </tbody>
                        </table>
                    </div>
                </main>
            </div>

            <!-- ── Footer ── -->
            <footer class="ka-footer">
                <div class="ka-footer__left">
                    <span>© Dojang</span>
                    <a href="#" class="ka-footer__link">Privacy</a>
                    <a href="#" class="ka-footer__link">Terms</a>
                </div>
                <div class="ka-footer__right">
                    <span class="ka-sync-dot"/>
                    <span>Cloud Sync: Synchronized</span>
                </div>
            </footer>

            <!-- ── Launch Kiosk Modal ── -->
            <t t-if="state.showLaunchModal">
                <div class="ka-modal-overlay" t-on-click.self="closeLaunchModal">
                    <div class="ka-modal">
                        <div class="ka-modal__header">
                            <h2 class="ka-modal__title">
                                <i class="fa fa-tablet"/> Launch Kiosk
                            </h2>
                            <button class="ka-modal__close" t-on-click="closeLaunchModal">
                                <i class="fa fa-times"/>
                            </button>
                        </div>
                        <div class="ka-modal__body">
                            <t t-set="activeKiosks" t-value="state.kiosks.filter(k => k.active)"/>
                            <t t-if="activeKiosks.length === 0">
                                <p class="ka-modal__empty">No active kiosks configured.</p>
                            </t>
                            <t t-foreach="activeKiosks" t-as="kiosk" t-key="kiosk.id">
                                <div class="ka-modal-kiosk-row">
                                    <span t-esc="kiosk.name"/>
                                    <button class="ka-btn ka-btn--primary"
                                        t-on-click="() => this.launchKiosk(kiosk)">
                                        <i class="fa fa-external-link"/> Open
                                    </button>
                                </div>
                            </t>
                        </div>
                    </div>
                </div>
            </t>

        </div>
    </t>

</templates>
```

- [ ] **Step 2: Verify file exists**

```bash
ls "addons/dojo_kiosk/static/src/xml/kiosk_admin.xml"
```
Expected: file listed.

---

## Task 3: Admin Panel JS Component

**Files:**
- Create: `addons/dojo_kiosk/static/src/js/kiosk_admin.js`

- [ ] **Step 1: Create the JS component file**

```javascript
/** @odoo-module **/
import { Component, useState, onMounted } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class KioskAdminApp extends Component {
    static template = "dojo_kiosk.KioskAdminApp";
    static components = {};

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            kiosks: [],
            search: "",
            page: 0,
            pageSize: 15,
            loading: true,
            showLaunchModal: false,
        });
        onMounted(() => this.loadKiosks());
    }

    async loadKiosks() {
        this.state.loading = true;
        try {
            this.state.kiosks = await this.orm.searchRead(
                "dojo.kiosk.config",
                [],
                ["id", "name", "kiosk_url", "theme_mode", "active"],
                { order: "name" }
            );
        } finally {
            this.state.loading = false;
        }
    }

    get filteredKiosks() {
        const q = this.state.search.toLowerCase().trim();
        if (!q) return this.state.kiosks;
        return this.state.kiosks.filter(k => k.name.toLowerCase().includes(q));
    }

    get pagedKiosks() {
        const { page, pageSize } = this.state;
        return this.filteredKiosks.slice(page * pageSize, (page + 1) * pageSize);
    }

    get totalPages() {
        return Math.max(1, Math.ceil(this.filteredKiosks.length / this.state.pageSize));
    }

    get paginationLabel() {
        const total = this.filteredKiosks.length;
        if (!total) return "0";
        const { page, pageSize } = this.state;
        const start = page * pageSize + 1;
        const end = Math.min((page + 1) * pageSize, total);
        return `${start}-${end} / ${total}`;
    }

    onSearchInput(ev) {
        this.state.search = ev.target.value;
        this.state.page = 0;
    }

    prevPage() {
        if (this.state.page > 0) this.state.page--;
    }

    nextPage() {
        if (this.state.page < this.totalPages - 1) this.state.page++;
    }

    openNew() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "dojo.kiosk.config",
            views: [[false, "form"]],
            target: "current",
        });
    }

    openRecord(kiosk) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "dojo.kiosk.config",
            res_id: kiosk.id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    launchKiosk(kiosk) {
        if (kiosk.kiosk_url) {
            window.open(kiosk.kiosk_url, "_blank");
        }
        this.state.showLaunchModal = false;
    }

    openLaunchModal() {
        this.state.showLaunchModal = true;
    }

    closeLaunchModal() {
        this.state.showLaunchModal = false;
    }

    logout() {
        window.location.href = "/web/session/logout";
    }
}

registry.category("actions").add("dojo_kiosk.KioskAdminApp", KioskAdminApp);
```

- [ ] **Step 2: Verify file exists**

```bash
ls "addons/dojo_kiosk/static/src/js/kiosk_admin.js"
```
Expected: file listed.

---

## Task 4: Register Assets and Client Action

**Files:**
- Modify: `addons/dojo_kiosk/__manifest__.py`
- Modify: `addons/dojo_kiosk/views/dojo_kiosk_views.xml`

- [ ] **Step 1: Add backend assets to `__manifest__.py`**

Open `addons/dojo_kiosk/__manifest__.py`. It currently has no `assets` key. Add it after `"auto_install": False,`:

Replace:
```python
    "application": True,
    "installable": True,
    "auto_install": False,
```

With:
```python
    "assets": {
        "web.assets_backend": [
            "dojo_kiosk/static/src/css/kiosk_admin.css",
            "dojo_kiosk/static/src/xml/kiosk_admin.xml",
            "dojo_kiosk/static/src/js/kiosk_admin.js",
        ],
    },
    "application": True,
    "installable": True,
    "auto_install": False,
```

- [ ] **Step 2: Add client action and redirect menu in `dojo_kiosk_views.xml`**

Open `addons/dojo_kiosk/views/dojo_kiosk_views.xml`. Add the client action record before the closing `</odoo>` tag, and update the menu action to point to it.

Find the existing menu item:
```xml
    <!-- Kiosks list (launch URLs from here) -->
    <menuitem
        id="menu_dojo_kiosk_list"
        name="Kiosks"
        parent="menu_dojo_kiosk_root"
        action="action_dojo_kiosk_config"
        sequence="10"
        groups="dojo_base.group_dojo_admin"
    />
```

Replace with:
```xml
    <!-- Custom OWL client action for the admin panel -->
    <record id="action_dojo_kiosk_admin_client" model="ir.actions.client">
        <field name="name">Kiosk Admin</field>
        <field name="tag">dojo_kiosk.KioskAdminApp</field>
        <field name="target">main</field>
    </record>

    <!-- Kiosks list — now opens the branded OWL admin panel -->
    <menuitem
        id="menu_dojo_kiosk_list"
        name="Kiosks"
        parent="menu_dojo_kiosk_root"
        action="action_dojo_kiosk_admin_client"
        sequence="10"
        groups="dojo_base.group_dojo_admin"
    />
```

- [ ] **Step 3: Update the module (required for XML data changes)**

```bash
docker compose exec web odoo-bin -u dojo_kiosk -d odoo19 --stop-after-init
```
Expected: process exits cleanly (no Python tracebacks).

- [ ] **Step 4: Verify admin panel renders**

Open `http://localhost:8069/odoo/kiosk` (or navigate to Kiosk app in Odoo). Expect: custom branded admin layout with sidebar, top nav, and kiosk table instead of the default Odoo list view.

---

## Task 5: Update Kiosk Frontend CSS

**Files:**
- Modify: `addons/dojo_kiosk/static/src/kiosk.css`

- [ ] **Step 1: Update dark theme accent from blue to red-orange**

In `kiosk.css`, find the dark theme block:
```css
/* — Dark theme (True Black · Industrial Minimalism) — */
body.kiosk-theme-dark {
```

Inside that block, find and replace:
```css
    /* Accent — MD3 steel blue / cyan */
    --k-accent:      #29b6f6;
    --k-accent-dim:  #001f32;
    --k-accent-text: #000000;
```

With:
```css
    /* Accent — Iron & Ember red-orange */
    --k-accent:      #FA5241;
    --k-accent-dim:  #2a0a08;
    --k-accent-text: #ffffff;
```

- [ ] **Step 2: Update light theme accent from blue to deep red**

In `kiosk.css`, find the light theme block:
```css
:root,
body.kiosk-theme-light {
```

Inside that block, find and replace:
```css
    /* Accent — MD3 Google Blue */
    --k-accent:      #1a73e8;
    --k-accent-dim:  #e8f0fe;
    --k-accent-text: #ffffff;
```

With:
```css
    /* Accent — deep red */
    --k-accent:      #b41e16;
    --k-accent-dim:  #fce8e6;
    --k-accent-text: #ffffff;
```

- [ ] **Step 3: Update instructor header in dark theme (remove blue tint)**

In `kiosk.css` dark theme block, find and replace:
```css
    /* Instructor header — deep teal-dark */
    --k-instr-bg:    #00111e;
    --k-instr-bg-2:  #000b15;
    --k-instr-text:  #bee3f8;
```

With:
```css
    /* Instructor header — dark charcoal */
    --k-instr-bg:    #1a1a1a;
    --k-instr-bg-2:  #0f0f0f;
    --k-instr-text:  #e8eaed;
```

- [ ] **Step 4: Add welcome screen, status bar, and updated header styles**

At the end of `kiosk.css`, append:

```css
/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   WELCOME SCREEN & STATUS BAR (redesigned student mode layout)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */

/* ── Slim header (student mode) ── */
.k-header--slim {
    min-height: 52px;
    padding: 8px 16px;
}

.k-header__brand {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-shrink: 0;
}

.k-header__brand-icon {
    color: var(--k-accent);
    font-size: 20px;
}

/* ── Welcome screen wrapper ── */
.k-welcome-screen {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    flex: 1;
    padding: 2rem 1.5rem;
    gap: 1.5rem;
    min-height: 0;
}

/* ── Welcome hero (shown when no search query) ── */
.k-welcome-hero {
    text-align: center;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.5rem;
}

.k-welcome-title {
    font-size: clamp(3rem, 10vw, 6rem);
    font-weight: 900;
    font-style: italic;
    text-transform: uppercase;
    letter-spacing: -0.03em;
    line-height: 1;
    color: var(--k-text);
    margin: 0;
}

.k-welcome-subtitle {
    font-size: clamp(0.875rem, 2vw, 1rem);
    color: var(--k-text-2);
    font-weight: 400;
    margin: 0;
}

/* ── Centered search input ── */
.k-welcome-search-wrap {
    position: relative;
    width: 100%;
    max-width: 560px;
}

.k-welcome-search {
    width: 100%;
    padding: 18px 90px 18px 24px;
    border: 2px solid var(--k-accent);
    border-radius: var(--k-radius-lg);
    background: var(--k-surface);
    color: var(--k-text);
    font-size: clamp(1rem, 2.5vw, 1.25rem);
    font-family: inherit;
    outline: none;
    transition: box-shadow var(--k-transition), border-color var(--k-transition);
    box-sizing: border-box;
}

.k-welcome-search::placeholder {
    color: var(--k-text-3);
}

.k-welcome-search:focus {
    box-shadow: 0 0 0 3px rgba(250, 82, 65, 0.20);
}

body.kiosk-theme-light .k-welcome-search:focus {
    box-shadow: 0 0 0 3px rgba(180, 30, 22, 0.15);
}

.k-welcome-search-clear {
    position: absolute;
    right: 72px;
    top: 50%;
    transform: translateY(-50%);
    background: none;
    border: none;
    color: var(--k-text-3);
    font-size: 16px;
    cursor: pointer;
    padding: 4px 8px;
    line-height: 1;
    transition: color var(--k-transition);
}

.k-welcome-search-clear:hover { color: var(--k-text); }

.k-welcome-search-enter {
    position: absolute;
    right: 16px;
    top: 50%;
    transform: translateY(-50%);
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 5px 10px;
    background: var(--k-surface-3);
    border: 1px solid var(--k-border-2);
    border-radius: var(--k-radius-sm);
    color: var(--k-text-3);
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    font-family: inherit;
    pointer-events: none;
}

/* ── Status bar ── */
.k-status-bar {
    width: 100%;
    max-width: 860px;
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    border: 1px solid var(--k-border);
    border-radius: var(--k-radius-lg);
    overflow: hidden;
    flex-shrink: 0;
}

.k-status-card {
    padding: 16px 20px;
    background: var(--k-surface);
    text-align: left;
    transition: background var(--k-transition);
}

.k-status-card:not(:last-child) {
    border-right: 1px solid var(--k-border);
}

.k-status-card:hover {
    background: var(--k-surface-2);
}

.k-status-card__label {
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.10em;
    color: var(--k-accent);
    margin-bottom: 6px;
}

.k-status-card:not(:first-child) .k-status-card__label {
    color: var(--k-text-3);
}

.k-status-card__value {
    font-size: clamp(1rem, 2.5vw, 1.5rem);
    font-weight: 800;
    color: var(--k-text);
    line-height: 1.1;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

/* ── Kiosk footer ── */
.k-kiosk-footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 20px;
    border-top: 1px solid var(--k-border);
    background: var(--k-surface);
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--k-text-3);
    flex-shrink: 0;
}

.k-kiosk-footer__left {
    display: flex;
    align-items: center;
    gap: 12px;
}

.k-kiosk-footer__right {
    font-size: 10px;
    color: var(--k-text-3);
}

.k-kiosk-footer__sync-dot {
    display: inline-block;
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #22c55e;
    flex-shrink: 0;
}

/* ── Material Symbols in header buttons ── */
.k-header__action-btn .material-symbols-outlined,
.k-header__instructor-btn .material-symbols-outlined {
    font-size: 20px;
    vertical-align: middle;
}
```

- [ ] **Step 5: Verify CSS file is valid (no syntax errors visible)**

Open `addons/dojo_kiosk/static/src/kiosk.css` and confirm the appended section is at the end and the file closes without unclosed braces.

---

## Task 6: Add Material Symbols to Kiosk HTML Shell

**Files:**
- Modify: `addons/dojo_kiosk/controllers/kiosk_controller.py`

- [ ] **Step 1: Add Google Fonts link for Material Symbols**

Open `addons/dojo_kiosk/controllers/kiosk_controller.py`. Find the `kiosk_index` method. Inside the `html` f-string, find the existing `<link>` for `kiosk.css`:

```python
    <link rel="stylesheet" href="/dojo_kiosk/static/src/kiosk.css?v={_static_ver('static/src/kiosk.css')}"/>
```

Add the Material Symbols link directly after it:

```python
    <link rel="stylesheet" href="/dojo_kiosk/static/src/kiosk.css?v={_static_ver('static/src/kiosk.css')}"/>
    <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap"/>
```

- [ ] **Step 2: Verify no syntax errors in controller**

```bash
python -c "import ast; ast.parse(open('addons/dojo_kiosk/controllers/kiosk_controller.py').read()); print('OK')"
```
Expected: `OK`

---

## Task 7: Restructure KioskApp Templates

**Files:**
- Modify: `addons/dojo_kiosk/static/src/kiosk_app.js`

This task has three sub-changes to the `KioskApp` component's `static template` (starting at line 2371).

### Sub-change A: Slim down the header — remove student-mode search, add brand icons

- [ ] **Step 1: Replace the header section**

Find this block (lines ~2394–2455) in `kiosk_app.js`:
```javascript
            <!-- ── Header (single, conditional modifier class) ── -->
            <div t-attf-class="k-header #{state.instructorMode ? 'k-header--instructor' : ''}">
                <t t-if="state.showTitle">
                    <span class="k-header__logo">🥋 Dojang</span>
                </t>

                <!-- Student mode: search bar -->
                <t t-if="!state.instructorMode">
                    <div class="k-header__search-wrap">
                        <span class="k-header__search-icon">🔍</span>
                        <input class="k-header__search"
                            type="text"
                            placeholder="Type your name to check in…"
                            t-model="state.searchQuery"
                            t-on-input="onSearchInput"
                            autocomplete="off"
                            autocorrect="off"
                            spellcheck="false"/>
                        <t t-if="state.searchQuery">
                            <button class="k-header__search-clear" t-on-click="clearSearch">✕</button>
                        </t>
                    </div>
                </t>

                <!-- Instructor mode: pill + session filter + date -->
                <t t-if="state.instructorMode">
                    <span class="k-instructor-pill">🔓 Instructor Mode</span>
                    <div class="k-header__spacer"/>
                    <select class="k-svh-select" t-on-change="onSessionViewFilter">
                        <option value="">All Sessions</option>
                        <t t-foreach="state.sessions" t-as="s" t-key="s.id">
                            <option t-att-value="s.id"
                                t-att-selected="state.sessionViewId === s.id or undefined">
                                <t t-esc="s.template_name"/> (<t t-esc="formatTime(s.start)"/>)
                            </option>
                        </t>
                    </select>
                    <input class="k-svh-date"
                        type="date"
                        t-att-value="state.filterDate"
                        t-on-change="onDateChange"/>
                </t>

                <div class="k-header__actions">
                    <!-- Karate toggle — only in student mode -->
                    <t t-if="!state.instructorMode">
                        <button class="k-header__instructor-btn"
                            t-on-click="onInstructorToggle"
                            title="Switch to Instructor Mode">🥋</button>
                    </t>
                    <!-- Reload -->
                    <button class="k-header__action-btn" t-on-click="reloadSessions" title="Reload">
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 2v6h-6"/><path d="M3 12a9 9 0 0 1 15-6.7L21 8"/><path d="M3 22v-6h6"/><path d="M21 12a9 9 0 0 1-15 6.7L3 16"/></svg>
                    </button>
                    <!-- Settings -->
                    <button class="k-header__action-btn" t-on-click="openSettings" title="Settings">⚙</button>
                    <!-- Exit instructor mode -->
                    <t t-if="state.instructorMode">
                        <button class="k-header__action-btn" t-on-click="onInstructorToggle" title="Exit Instructor Mode" style="font-size:14px;font-weight:700;">✕ Exit</button>
                    </t>
                </div>
            </div>
```

Replace with:
```javascript
            <!-- ── Header ── -->
            <div t-attf-class="k-header k-header--slim #{state.instructorMode ? 'k-header--instructor' : ''}">

                <!-- Brand (student mode) / Instructor pill (instructor mode) -->
                <t t-if="!state.instructorMode">
                    <div class="k-header__brand">
                        <span class="k-header__brand-icon material-symbols-outlined">apparel</span>
                        <t t-if="state.showTitle">
                            <span class="k-header__logo">Dojo Kiosk</span>
                        </t>
                    </div>
                </t>
                <t t-if="state.instructorMode">
                    <span class="k-instructor-pill">🔓 Instructor Mode</span>
                    <div class="k-header__spacer"/>
                    <select class="k-svh-select" t-on-change="onSessionViewFilter">
                        <option value="">All Sessions</option>
                        <t t-foreach="state.sessions" t-as="s" t-key="s.id">
                            <option t-att-value="s.id"
                                t-att-selected="state.sessionViewId === s.id or undefined">
                                <t t-esc="s.template_name"/> (<t t-esc="formatTime(s.start)"/>)
                            </option>
                        </t>
                    </select>
                    <input class="k-svh-date"
                        type="date"
                        t-att-value="state.filterDate"
                        t-on-change="onDateChange"/>
                </t>

                <div class="k-header__actions">
                    <t t-if="!state.instructorMode">
                        <button class="k-header__instructor-btn"
                            t-on-click="onInstructorToggle"
                            title="Switch to Instructor Mode">
                            <span class="material-symbols-outlined">apparel</span>
                        </button>
                    </t>
                    <button class="k-header__action-btn" t-on-click="reloadSessions" title="Reload">
                        <span class="material-symbols-outlined">sync</span>
                    </button>
                    <button class="k-header__action-btn" t-on-click="openSettings" title="Settings">
                        <span class="material-symbols-outlined">settings</span>
                    </button>
                    <t t-if="state.instructorMode">
                        <button class="k-header__action-btn" t-on-click="onInstructorToggle"
                            title="Exit Instructor Mode" style="font-size:14px;font-weight:700;">✕ Exit</button>
                    </t>
                </div>
            </div>
```

### Sub-change B: Restructure student flow body — welcome hero + centered search + status bar

- [ ] **Step 2: Replace the student flow section in `.k-body`**

Find this block (lines ~2460–2467):
```javascript
                <!-- ════ STUDENT FLOW ════ -->
                <t t-if="!state.instructorMode">
                    <HomeContent
                        query="state.searchQuery"
                        results="state.searchResults"
                        loading="state.searchLoading"
                        onSelect="(member) => this.studentConfirm(member)"/>
                </t>
```

Replace with:
```javascript
                <!-- ════ STUDENT FLOW ════ -->
                <t t-if="!state.instructorMode">
                    <div class="k-welcome-screen">

                        <!-- Welcome hero — shown only when no search query -->
                        <t t-if="!state.searchQuery and !state.searchLoading">
                            <div class="k-welcome-hero">
                                <h1 class="k-welcome-title">WELCOME!</h1>
                                <p class="k-welcome-subtitle">Type your name to check in</p>
                            </div>
                        </t>

                        <!-- Centred search input -->
                        <div class="k-welcome-search-wrap">
                            <input class="k-welcome-search"
                                type="text"
                                placeholder="Student Name…"
                                t-att-value="state.searchQuery"
                                t-on-input="onSearchInput"
                                autocomplete="off"
                                autocorrect="off"
                                spellcheck="false"
                                autofocus="autofocus"/>
                            <t t-if="state.searchQuery">
                                <button class="k-welcome-search-clear" t-on-click="clearSearch">✕</button>
                            </t>
                            <kbd class="k-welcome-search-enter">ENTER</kbd>
                        </div>

                        <!-- Search results -->
                        <t t-if="state.searchQuery or state.searchLoading">
                            <HomeContent
                                query="state.searchQuery"
                                results="state.searchResults"
                                loading="state.searchLoading"
                                onSelect="(member) => this.studentConfirm(member)"/>
                        </t>

                    </div>

                    <!-- Status bar — always visible in student mode -->
                    <div class="k-status-bar">
                        <div class="k-status-card">
                            <div class="k-status-card__label">Sessions Today</div>
                            <div class="k-status-card__value">
                                <t t-esc="state.sessions.length || '—'"/>
                            </div>
                        </div>
                        <div class="k-status-card">
                            <div class="k-status-card__label">Session</div>
                            <div class="k-status-card__value">
                                <t t-if="state.sessions.length">
                                    <t t-esc="state.sessions[0].template_name || '—'"/>
                                </t>
                                <t t-else="">—</t>
                            </div>
                        </div>
                        <div class="k-status-card">
                            <div class="k-status-card__label">Time</div>
                            <div class="k-status-card__value">
                                <t t-if="state.sessions.length and state.sessions[0].start">
                                    <t t-esc="formatTime(state.sessions[0].start)"/>
                                </t>
                                <t t-else="">—</t>
                            </div>
                        </div>
                        <div class="k-status-card">
                            <div class="k-status-card__label">Instructor</div>
                            <div class="k-status-card__value">
                                <t t-if="state.sessions.length and state.sessions[0].instructor">
                                    <t t-esc="state.sessions[0].instructor"/>
                                </t>
                                <t t-else="">—</t>
                            </div>
                        </div>
                    </div>
                </t>
```

### Sub-change C: Remove the old HomeContent empty-state prompt

- [ ] **Step 3: Update `HomeContent` empty-state to remove the now-redundant "Welcome!" prompt**

Find in `HomeContent.static template` (lines ~1000–1006):
```javascript
            <t t-if="!props.query and !props.loading">
                <div class="k-home__prompt">
                    <div class="k-home__prompt-icon">🥋</div>
                    <div class="k-home__prompt-title">Welcome!</div>
                    <div class="k-home__prompt-sub">Type your name in the search bar above to check in</div>
                </div>
            </t>
```

Replace with (empty state renders nothing since the welcome screen above handles it):
```javascript
            <t t-if="!props.query and !props.loading">
                <!-- Welcome hero is rendered by KioskApp above HomeContent -->
            </t>
```

### Sub-change D: Store kiosk name in state and add footer

- [ ] **Step 4: Add `kioskName` to `KioskApp` initial state**

In `kiosk_app.js`, find the `KioskApp` class `setup()` method and its `useState({...})` call. Add `kioskName: ""` to the state object. It will be in the area that initialises `idle`, `sessions`, `searchQuery`, etc. Example — find the `useState` block and add the field:

```javascript
        this.state = useState({
            // … existing fields …
            kioskName: "",
            // … existing fields …
        });
```

- [ ] **Step 5: Populate `kioskName` from bootstrap data**

In `kiosk_app.js`, find the `_bootstrap` method's success block (line ~2722). Find:
```javascript
                this.state.sessions = data.sessions || [];
                this.state.showTitle = data.show_title !== false;
```

Add one line after `showTitle`:
```javascript
                this.state.sessions = data.sessions || [];
                this.state.showTitle = data.show_title !== false;
                this.state.kioskName = data.name || "";
```

- [ ] **Step 6: Add the kiosk footer to the KioskApp template**

In `KioskApp.static template`, find the closing `</div>` of `.k-app` (very last line of the template, just before the closing backtick). It will look like:

```javascript
        </div>
    `;
```

Replace with:
```javascript
            <!-- ── Kiosk footer ── -->
            <t t-if="!state.idle">
                <footer class="k-kiosk-footer">
                    <div class="k-kiosk-footer__left">
                        <span class="k-kiosk-footer__sync-dot"/>
                        <span>Connected</span>
                        <span>© Dojang</span>
                    </div>
                    <div class="k-kiosk-footer__right">
                        <t t-if="state.kioskName">
                            <t t-esc="state.kioskName"/>
                        </t>
                    </div>
                </footer>
            </t>
        </div>
    `;
```

- [ ] **Step 6: Verify page in browser**

Open `/kiosk/<any-valid-token>` in the browser. Expected:
- Thin header with "Dojo Kiosk" text and Material Symbol icon buttons
- WELCOME! hero centred in the body
- Large red-bordered search input below the hero
- 4 status cards at the bottom (Sessions Today / Session / Time / Instructor)
- Footer with "Connected · © Dojang · [kiosk name]"

---

## Task 8: End-to-End Verification

- [ ] **Step 1: Admin panel smoke test**
  - Navigate to Kiosk app in Odoo → custom branded layout renders (no standard list view)
  - Sidebar shows "Kiosks" item active; no phantom Analytics/System Health entries
  - Click a kiosk row → Odoo standard form view opens for editing
  - Click "+ New" → form view opens in create mode
  - Click "Launch" button on a row → kiosk URL opens in new tab
  - Click "Launch Kiosk" in sidebar → modal appears listing active kiosks

- [ ] **Step 2: Kiosk frontend smoke test**
  - Open `/kiosk/<token>` → WELCOME! layout renders
  - Type a name → hero disappears, results appear
  - Clear search → hero reappears
  - Status bar always visible with session data (or `—` dashes if no sessions today)
  - Click the karate/apparel icon → PIN modal appears
  - Enter correct PIN → instructor mode activates (header changes to instructor pill)
  - Reload sessions button (sync icon) works

- [ ] **Step 3: Dark/light theme check**
  - In a kiosk config set theme to Light → `/kiosk/<token>` shows light theme with deep red accent
  - Dark theme shows red-orange accent (not blue)

- [ ] **Step 4: Module restart not needed for CSS/JS**

Static file changes take effect on browser hard-refresh (Ctrl+Shift+R). Only the XML data change in Task 4 requires a module update, which was already done.
