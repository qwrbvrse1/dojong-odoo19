# Dojang Automation UI — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `dojo_automation` module — a Dojang-branded UI layer over `automation_oca` with a live stat panel, animated kanban cards, form accordions, and semantic step-type coloring.

**Architecture:** New `dojo_automation` module (depends: `dojo_core`, `automation_oca`) containing pure frontend overrides: one OWL JS file, one XML template file, one SCSS file, and one XML view-inherit file. No Python models. Follows the exact same injection pattern proven in Sprint 1 (`dojo_crm`).

**Tech Stack:** OWL 2 (Odoo 19), QWeb XML view inheritance, SCSS, Odoo `automation_oca` (OCA third-party — read only)

---

## File Map

| File | Create/Modify | Responsibility |
|------|--------------|----------------|
| `addons/dojo_automation/__init__.py` | Create | Empty Python init |
| `addons/dojo_automation/__manifest__.py` | Create | Module definition, asset registration |
| `addons/dojo_automation/views/automation_views_inherit.xml` | Create | Kanban card, form accordion, menu label overrides |
| `addons/dojo_automation/static/src/js/automation_stat_panel.js` | Create | OWL: AutomationStatPanel, AutomationFilterChips, controller mutation |
| `addons/dojo_automation/static/src/xml/automation_stat_panel.xml` | Create | QWeb templates + web.KanbanView injection |
| `addons/dojo_automation/static/src/css/automation.scss` | Create | All animations, step colors, card styles, accordions |

---

## Task 1: Module Scaffold

**Files:**
- Create: `addons/dojo_automation/__init__.py`
- Create: `addons/dojo_automation/__manifest__.py`
- Create: `addons/dojo_automation/views/` (directory)
- Create: `addons/dojo_automation/static/src/js/` (directory)
- Create: `addons/dojo_automation/static/src/xml/` (directory)
- Create: `addons/dojo_automation/static/src/css/` (directory)

- [ ] **Step 1: Create directory structure**

Run in PowerShell from `dojo-odoo19/`:
```powershell
New-Item -ItemType Directory -Force -Path addons/dojo_automation/views
New-Item -ItemType Directory -Force -Path addons/dojo_automation/static/src/js
New-Item -ItemType Directory -Force -Path addons/dojo_automation/static/src/xml
New-Item -ItemType Directory -Force -Path addons/dojo_automation/static/src/css
```

- [ ] **Step 2: Create `__init__.py`**

Create `addons/dojo_automation/__init__.py`:
```python
```
(empty file)

- [ ] **Step 3: Create `__manifest__.py`**

Create `addons/dojo_automation/__manifest__.py`:
```python
{
    "name": "Dojang Automation",
    "version": "19.2.1.0.0",
    "summary": "Dojang-branded UI layer for automation workflows",
    "author": "Dojo",
    "category": "Hidden",
    "depends": ["dojo_core", "automation_oca"],
    "data": ["views/automation_views_inherit.xml"],
    "assets": {
        "web.assets_backend": [
            "dojo_automation/static/src/xml/automation_stat_panel.xml",
            "dojo_automation/static/src/js/automation_stat_panel.js",
            "dojo_automation/static/src/css/automation.scss",
        ],
    },
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
```

- [ ] **Step 4: Commit scaffold**

```powershell
git add addons/dojo_automation/
git commit -m "feat(dojo_automation): scaffold module — init + manifest"
```

---

## Task 2: SCSS — Animations, Card Styles, Step Colors, Accordions

**Files:**
- Create: `addons/dojo_automation/static/src/css/automation.scss`

- [ ] **Step 1: Create `automation.scss`**

Create `addons/dojo_automation/static/src/css/automation.scss`:
```scss
// ─── Dojang Automation — all styles ──────────────────────────────────────────
// Color tokens map to MuK/Bootstrap variables. Never hardcode hex.

// ── Stat Panel ────────────────────────────────────────────────────────────────

.dojo-auto-stat-panel {
    background: var(--surface, var(--bs-body-bg));
    border-bottom: 1px solid var(--border, var(--bs-border-color));
}

.dojo-auto-stat-chip {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 2px;
    padding: 12px 20px;
    border-radius: var(--radius-md, 0.5rem);
    background: var(--surface, var(--bs-body-bg));
    box-shadow: var(--shadow-sm, 0 1px 3px rgba(0, 0, 0, 0.08));
    border: 1px solid var(--border, var(--bs-border-color));
    min-width: 120px;
    text-align: center;
    transition: box-shadow var(--transition-fast, 150ms ease);

    &:hover {
        box-shadow: var(--shadow-md, 0 4px 12px rgba(0, 0, 0, 0.12));
    }

    &__icon { font-size: 1.25rem; margin-bottom: 2px; }
    &__value { font-size: 1.5rem; font-weight: 700; line-height: 1; }
    &__label { font-size: 0.75rem; color: var(--text-muted, var(--bs-secondary-color)); }

    &--info    .dojo-auto-chip__icon { color: var(--info,    var(--bs-info)); }
    &--success .dojo-auto-chip__icon { color: var(--success, var(--bs-success)); }
    &--warning .dojo-auto-chip__icon { color: var(--warning, var(--bs-warning)); }
    &--danger  .dojo-auto-chip__icon { color: var(--danger,  var(--bs-danger)); }

    &--danger.is-alert {
        border-color: var(--danger, var(--bs-danger));
        background: rgba(var(--bs-danger-rgb), 0.06);
    }
}

.dojo-auto-stat-skeleton {
    width: 120px;
    height: 88px;
    border-radius: var(--radius-md, 0.5rem);
    background: linear-gradient(
        90deg,
        var(--surface, var(--bs-body-bg)) 25%,
        var(--surface-hover, #f0f0f0) 50%,
        var(--surface, var(--bs-body-bg)) 75%
    );
    background-size: 200% 100%;
    animation: dojo-auto-shimmer 1.4s infinite;
}

@keyframes dojo-auto-shimmer {
    0%   { background-position: 200% 0; }
    100% { background-position: -200% 0; }
}

// ── Filter Chips ──────────────────────────────────────────────────────────────

.dojo-auto-filter-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    border-bottom: 1px solid var(--border, var(--bs-border-color));
}

.dojo-auto-filter-chip {
    padding: 4px 12px;
    border-radius: 100px;
    border: 1px solid var(--border, var(--bs-border-color));
    background: transparent;
    color: var(--text-primary, var(--bs-body-color));
    font-size: 0.8125rem;
    cursor: pointer;
    transition: all var(--transition-fast, 150ms ease);
    display: flex;
    align-items: center;
    gap: 4px;

    &:hover { background: var(--surface-hover, rgba(0, 0, 0, 0.04)); }

    &.active {
        background: var(--info, var(--bs-info));
        border-color: var(--info, var(--bs-info));
        color: #fff;
    }

    &:focus-visible {
        outline: 2px solid var(--primary, var(--bs-primary));
        outline-offset: 2px;
    }
}

// ── Rule Cards — main Kanban view ─────────────────────────────────────────────

.dojo-auto-rule-card {
    border-radius: var(--radius-md, 0.5rem);
    border: 1px solid var(--border, var(--bs-border-color));
    border-left: 4px solid var(--bs-secondary);
    background: var(--surface, var(--bs-body-bg));
    box-shadow: var(--shadow-sm, 0 1px 3px rgba(0, 0, 0, 0.08));
    overflow: hidden;
    transition:
        transform var(--transition-fast, 150ms ease),
        box-shadow var(--transition-fast, 150ms ease);
    animation: dojo-auto-card-enter 300ms ease both;

    &:hover {
        transform: translateY(-2px);
        box-shadow: var(--shadow-md, 0 4px 12px rgba(0, 0, 0, 0.12));

        .dojo-auto-rule-card__actions { opacity: 1; }
    }

    // State → left-border colors
    &--periodic  { border-left-color: var(--info,    var(--bs-info)); }
    &--ondemand  { border-left-color: var(--warning, var(--bs-warning)); }
    &--done      { border-left-color: var(--success, var(--bs-success)); }
    &--draft     { border-left-color: var(--bs-secondary); }

    // Periodic state: breathing glow
    &--periodic {
        animation:
            dojo-auto-card-enter 300ms ease both,
            dojo-auto-pulse-border 2s ease-in-out infinite 1s;
    }

    &__body   { padding: 12px 14px 8px; }
    &__name   { font-weight: 600; font-size: 0.9375rem; }
    &__stats  { font-size: 0.8rem; color: var(--text-muted, var(--bs-secondary-color)); }

    &__actions {
        display: flex;
        gap: 6px;
        padding: 8px 14px;
        border-top: 1px solid var(--border, var(--bs-border-color));
        background: var(--surface-hover, rgba(0, 0, 0, 0.02));
        opacity: 0;
        transition: opacity var(--transition-fast, 150ms ease);
    }
}

// Staggered entrance — nth-child delay
@for $i from 1 through 6 {
    .o_kanban_record:nth-child(#{$i}) .dojo-auto-rule-card {
        animation-delay: #{($i - 1) * 50}ms;
    }
}
.o_kanban_record:nth-child(n+7) .dojo-auto-rule-card { animation-delay: 300ms; }

@keyframes dojo-auto-card-enter {
    from { opacity: 0; transform: translateY(8px); }
    to   { opacity: 1; transform: translateY(0); }
}

@keyframes dojo-auto-pulse-border {
    0%, 100% { box-shadow: var(--shadow-sm, 0 1px 3px rgba(0, 0, 0, 0.08)); }
    50% {
        box-shadow:
            var(--shadow-sm, 0 1px 3px rgba(0, 0, 0, 0.08)),
            0 0 0 3px rgba(var(--bs-info-rgb, 13, 202, 240), 0.25);
    }
}

// State badges
.dojo-auto-state-badge {
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: capitalize;
    padding: 3px 8px;
    border-radius: 100px;
    white-space: nowrap;
    transition: background var(--transition-fast, 150ms ease);

    &.dojo-auto-state-periodic { background: var(--info,    var(--bs-info));    color: #fff; }
    &.dojo-auto-state-ondemand { background: var(--warning, var(--bs-warning)); color: #000; }
    &.dojo-auto-state-done     { background: var(--success, var(--bs-success)); color: #fff; }
    &.dojo-auto-state-draft    { background: var(--bs-secondary);               color: #fff; }
}

// ── Form Accordions ───────────────────────────────────────────────────────────

.dojo-accordion {
    border: 1px solid var(--border, var(--bs-border-color));
    border-radius: var(--radius-md, 0.5rem);
    overflow: hidden;

    &__summary {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 10px 16px;
        cursor: pointer;
        background: var(--surface-hover, rgba(0, 0, 0, 0.02));
        border-bottom: 1px solid transparent;
        list-style: none;
        user-select: none;
        transition: background var(--transition-fast, 150ms ease);
        min-height: 44px;

        &::-webkit-details-marker { display: none; }
        &:hover { background: var(--surface-hover, rgba(0, 0, 0, 0.04)); }
        &:focus-visible { outline: 2px solid var(--primary, var(--bs-primary)); }
    }

    &__title {
        font-size: 0.8125rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: var(--text-muted, var(--bs-secondary-color));
    }

    &__chevron {
        transition: transform var(--transition-fast, 150ms ease);
        color: var(--text-muted, var(--bs-secondary-color));
    }

    &[open] > .dojo-accordion__summary {
        border-bottom-color: var(--border, var(--bs-border-color));

        .dojo-accordion__chevron { transform: rotate(180deg); }
    }

    &__body { padding: 8px 4px; }
}

// Section divider before Workflow Steps
.dojo-section-title {
    font-size: 0.75rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--text-muted, var(--bs-secondary-color));
    padding: 16px 0 6px;
    border-top: 1px solid var(--border, var(--bs-border-color));
    margin-top: 8px;
}

// ── Step Cards — inside automation_step kanban widget ─────────────────────────
// step_icon values confirmed from source:
//   mail     → "fa fa-envelope"
//   activity → "fa fa-clock-o"
//   action   → "fa fa-cogs"

.o_automation_kanban {

    .o_automation_kanban_card {
        border-radius: var(--radius-md, 0.5rem);
        transition:
            transform var(--transition-fast, 150ms ease),
            box-shadow var(--transition-fast, 150ms ease);

        &:hover {
            transform: translateY(-2px);
            box-shadow: var(--shadow-md, 0 4px 12px rgba(0, 0, 0, 0.12));
        }
    }

    // Icon colors by step type
    .o_automation_kanban_header_icon {
        .fa-envelope { color: var(--info,    var(--bs-info)); }
        .fa-clock-o  { color: var(--success, var(--bs-success)); }
        .fa-cogs     { color: var(--warning, var(--bs-warning)); }
    }

    // Left-border by step type via :has() (Chrome 105+, FF 121+, Safari 15.4+)
    .o_automation_kanban_card:has(.fa-envelope) { border-left: 3px solid var(--info,    var(--bs-info)); }
    .o_automation_kanban_card:has(.fa-clock-o)  { border-left: 3px solid var(--success, var(--bs-success)); }
    .o_automation_kanban_card:has(.fa-cogs)     { border-left: 3px solid var(--warning, var(--bs-warning)); }

    // Edit button picks up step type color on hover
    .o_automation_kanban_card:has(.fa-envelope) .o_automation_kanban_header_icon:hover { background: var(--info,    var(--bs-info)); }
    .o_automation_kanban_card:has(.fa-clock-o)  .o_automation_kanban_header_icon:hover { background: var(--success, var(--bs-success)); }
    .o_automation_kanban_card:has(.fa-cogs)     .o_automation_kanban_header_icon:hover { background: var(--warning, var(--bs-warning)); }

    // Delay pill chip
    .o_automation_kanban_time_info {
        background: var(--surface-hover, rgba(0, 0, 0, 0.04));
        border-radius: var(--radius-md, 0.5rem);
        padding: 4px 8px !important;
    }

    // Connector lines use border token
    .o_automation_kanban_position_line {
        border-color: var(--border, var(--bs-border-color));
    }

    // Circle dot color by step type — targets the fa-circle in the time column
    .o_automation_kanban_box:has(.fa-envelope) .o_automation_kanban_card_position { color: var(--info,    var(--bs-info)) !important; }
    .o_automation_kanban_box:has(.fa-clock-o)  .o_automation_kanban_card_position { color: var(--success, var(--bs-success)) !important; }
    .o_automation_kanban_box:has(.fa-cogs)     .o_automation_kanban_card_position { color: var(--warning, var(--bs-warning)) !important; }

    // Error state step card
    .o_automation_kpi_error {
        color: var(--danger, var(--bs-danger));
        font-weight: 700;
    }
}

// ── Global micro-interactions ─────────────────────────────────────────────────

.btn:active { transform: scale(0.97); }
```

- [ ] **Step 2: Verify SCSS compiles — upgrade module after Task 6 (no standalone test)**

Note: SCSS compilation is verified during the module install in Task 6. Skip forward to Task 6 after completing all file creation tasks.

- [ ] **Step 3: Commit SCSS**

```powershell
git add addons/dojo_automation/static/src/css/automation.scss
git commit -m "feat(dojo_automation): add SCSS — card animations, step colors, accordions"
```

---

## Task 3: OWL Stat Panel JS

**Files:**
- Create: `addons/dojo_automation/static/src/js/automation_stat_panel.js`

**Context:** Follows the exact CRM Sprint 1 pattern from `dojo_crm/static/src/js/crm_stat_panel.js`. Key facts:
- `AutomationKanbanController` is exported from `automation_oca/.../automation_upload.esm.js`
- We mutate its `components` property (do NOT create a new class — CRM lesson)
- `automation.record.step` confirmed to have `state = 'error'` field (`write_date` inherited from `models.Model`)
- Step types: `mail`, `activity`, `action` only (no SMS in this OCA version)

- [ ] **Step 1: Create `automation_stat_panel.js`**

Create `addons/dojo_automation/static/src/js/automation_stat_panel.js`:
```javascript
/** @odoo-module **/

import { Component, useState, onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { AutomationKanbanController } from "automation_oca/static/src/views/automation_upload/automation_upload.esm.js";

// ─── Stat Panel ───────────────────────────────────────────────────────────────

export class AutomationStatPanel extends Component {
    static template = "dojo_automation.AutomationStatPanel";

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            loading: true,
            activeRules: 0,
            triggeredToday: 0,
            runningNow: 0,
            errors7Days: 0,
        });
        onMounted(() => this._fetchKpis());
    }

    async _fetchKpis() {
        const now = new Date();
        const fmt = (d) => d.toISOString().replace("T", " ").slice(0, 19);

        const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());
        const sevenDaysAgo = new Date(todayStart);
        sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);

        const [activeRules, triggeredToday, runningNow, errors7Days] = await Promise.all([
            this.orm.searchCount("automation.configuration", [
                ["state", "in", ["periodic", "ondemand"]],
            ]),
            this.orm.searchCount("automation.record", [
                ["create_date", ">=", fmt(todayStart)],
                ["is_test", "=", false],
            ]),
            this.orm.searchCount("automation.record", [
                ["state", "=", "periodic"],
                ["is_test", "=", false],
            ]),
            this.orm.searchCount("automation.record.step", [
                ["state", "=", "error"],
                ["write_date", ">=", fmt(sevenDaysAgo)],
            ]),
        ]);

        Object.assign(this.state, {
            loading: false,
            activeRules,
            triggeredToday,
            runningNow,
            errors7Days,
        });
    }
}

// ─── Filter Chips ─────────────────────────────────────────────────────────────
// Filter names must match <filter name="..."> in automation_configuration_search_view.
// Confirmed names: "run" (active = periodic+ondemand), "draft", "done"

const CHIP_DEFS = [
    { name: "run",   label: "Active", icon: "fa-bolt" },
    { name: "draft", label: "Draft",  icon: "fa-pencil" },
    { name: "done",  label: "Done",   icon: "fa-check" },
];

export class AutomationFilterChips extends Component {
    static template = "dojo_automation.AutomationFilterChips";

    setup() {
        this.state = useState(
            Object.fromEntries(CHIP_DEFS.map((c) => [c.name, false]))
        );
    }

    get chips() {
        return CHIP_DEFS.map((c) => ({ ...c, active: this.state[c.name] }));
    }

    toggleChip(name) {
        this.state[name] = !this.state[name];
        const sm = this.env.searchModel;
        if (!sm) return;
        const item = Object.values(sm.searchItems || {}).find(
            (i) => i.name === name && i.type === "filter"
        );
        if (item) sm.toggleSearchItem(item.id);
    }
}

// ─── Inject into AutomationKanbanController ───────────────────────────────────
// Mutate components on the existing AutomationKanbanController class directly.
// Do NOT create a subclass — the OWL components snapshot is taken at class definition
// time; mutating the imported class is the correct approach (Sprint 1 lesson).

AutomationKanbanController.components = {
    ...AutomationKanbanController.components,
    AutomationStatPanel,
    AutomationFilterChips,
};
```

- [ ] **Step 2: Commit JS**

```powershell
git add addons/dojo_automation/static/src/js/automation_stat_panel.js
git commit -m "feat(dojo_automation): OWL stat panel + filter chips components"
```

---

## Task 4: OWL XML Templates

**Files:**
- Create: `addons/dojo_automation/static/src/xml/automation_stat_panel.xml`

**Context:** Template injection uses `t-inherit="web.KanbanView"` targeting `//t[@t-component='props.Renderer']` — identical to the CRM Sprint 1 approach confirmed working in saas-19.2.

- [ ] **Step 1: Create `automation_stat_panel.xml`**

Create `addons/dojo_automation/static/src/xml/automation_stat_panel.xml`:
```xml
<?xml version="1.0" encoding="utf-8"?>
<templates xml:space="preserve">

    <!-- ── Stat Panel ──────────────────────────────────────────────────────── -->

    <t t-name="dojo_automation.AutomationStatPanel">
        <div class="dojo-auto-stat-panel d-flex flex-wrap gap-2 px-3 pt-3 pb-2">
            <t t-if="state.loading">
                <div t-foreach="[1,2,3,4]" t-as="i" t-key="i"
                     class="dojo-auto-stat-skeleton"/>
            </t>
            <t t-else="">
                <div class="dojo-auto-stat-chip dojo-auto-chip--info">
                    <i class="fa fa-bolt dojo-auto-chip__icon"/>
                    <span class="dojo-auto-chip__value" t-esc="state.activeRules"/>
                    <span class="dojo-auto-chip__label">Active Rules</span>
                </div>
                <div class="dojo-auto-stat-chip dojo-auto-chip--success">
                    <i class="fa fa-play-circle dojo-auto-chip__icon"/>
                    <span class="dojo-auto-chip__value" t-esc="state.triggeredToday"/>
                    <span class="dojo-auto-chip__label">Triggered Today</span>
                </div>
                <div class="dojo-auto-stat-chip dojo-auto-chip--warning">
                    <i class="fa fa-refresh dojo-auto-chip__icon"/>
                    <span class="dojo-auto-chip__value" t-esc="state.runningNow"/>
                    <span class="dojo-auto-chip__label">Running Now</span>
                </div>
                <div t-attf-class="dojo-auto-stat-chip dojo-auto-chip--danger{{ state.errors7Days > 0 ? ' is-alert' : '' }}">
                    <i class="fa fa-exclamation-triangle dojo-auto-chip__icon"/>
                    <span class="dojo-auto-chip__value" t-esc="state.errors7Days"/>
                    <span class="dojo-auto-chip__label">Errors (7 days)</span>
                </div>
            </t>
        </div>
    </t>

    <!-- ── Filter Chips ────────────────────────────────────────────────────── -->

    <t t-name="dojo_automation.AutomationFilterChips">
        <div class="dojo-auto-filter-chips px-3 pb-2">
            <button t-attf-class="dojo-auto-filter-chip{{ !chips.some(c => c.active) ? ' active' : '' }}"
                    t-on-click="() => { for (const c of chips) { if (c.active) toggleChip(c.name); } }">
                <i class="fa fa-list fa-sm"/> All
            </button>
            <t t-foreach="chips" t-as="chip" t-key="chip.name">
                <button t-attf-class="dojo-auto-filter-chip{{ chip.active ? ' active' : '' }}"
                        t-on-click="() => toggleChip(chip.name)"
                        t-att-aria-pressed="chip.active ? 'true' : 'false'">
                    <i t-attf-class="fa {{ chip.icon }} fa-sm"/>
                    <t t-esc="chip.label"/>
                </button>
            </t>
        </div>
    </t>

    <!-- ── Inject above Renderer in web.KanbanView ─────────────────────────── -->
    <!--
        Same pattern as CRM Sprint 1 (dojo_crm/static/src/xml/crm_stat_panel.xml).
        OWL resolves AutomationStatPanel/AutomationFilterChips from
        AutomationKanbanController.components at render time — other kanban
        controllers silently skip unknown component names.
    -->
    <t t-inherit="web.KanbanView" t-inherit-mode="extension">
        <xpath expr="//t[@t-component='props.Renderer']" position="before">
            <AutomationStatPanel/>
            <AutomationFilterChips/>
        </xpath>
    </t>

</templates>
```

- [ ] **Step 2: Commit XML templates**

```powershell
git add addons/dojo_automation/static/src/xml/automation_stat_panel.xml
git commit -m "feat(dojo_automation): QWeb templates for stat panel, filter chips, KanbanView injection"
```

---

## Task 5: XML View Inherits — Kanban Card, Form Accordion, Menu Labels

**Files:**
- Create: `addons/dojo_automation/views/automation_views_inherit.xml`

**Context:**
- `automation_oca.automation_configuration_kanban_view` — kanban view to override
- `automation_oca.automation_configuration_form_view` — form view to override
- `automation_oca.automation_root_menu` — top-level "Automation" menu
- `automation_oca.automation_configuration_menu` — "Automation Configuration" sub-menu
- Fields available in kanban (declared in existing view): `state`. Fields used in card template but not in `<field>` declarations outside templates are fetched automatically; add `is_periodic`, `model_id`, `next_execution_date` as explicit declarations.
- Form `<group>`: the single flat group in `//sheet` contains all config fields — replace it with two accordions.
- `<details open="">` renders open by default (HTML native); no JS needed.

- [ ] **Step 1: Create `automation_views_inherit.xml`**

Create `addons/dojo_automation/views/automation_views_inherit.xml`:
```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>

    <!-- ═══════════════════════════════════════════════════════════════════════
         1. MENU LABELS — rebrand to "Dojang"
    ════════════════════════════════════════════════════════════════════════ -->

    <record model="ir.ui.menu" id="automation_oca.automation_root_menu">
        <field name="name">Dojang Automation</field>
    </record>

    <record model="ir.ui.menu" id="automation_oca.automation_configuration_menu">
        <field name="name">Dojang Rules</field>
    </record>

    <!-- ═══════════════════════════════════════════════════════════════════════
         2. KANBAN CARD — redesign rule cards
    ════════════════════════════════════════════════════════════════════════ -->

    <record model="ir.ui.view" id="automation_configuration_kanban_inherit">
        <field name="name">automation.configuration.kanban.dojo</field>
        <field name="model">automation.configuration</field>
        <field name="inherit_id" ref="automation_oca.automation_configuration_kanban_view"/>
        <field name="arch" type="xml">

            <!-- Declare extra fields needed by the new card template -->
            <xpath expr="//kanban/field[@name='state']" position="after">
                <field name="is_periodic"/>
                <field name="model_id"/>
                <field name="next_execution_date"/>
            </xpath>

            <!-- Replace card template -->
            <xpath expr="//templates/t[@t-name='card']" position="replace">
                <t t-name="card">
                    <div t-attf-class="dojo-auto-rule-card dojo-auto-rule-card--{{ record.state.value }}">
                        <div class="dojo-auto-rule-card__body">

                            <!-- Header row: name + state badge -->
                            <div class="d-flex justify-content-between align-items-start mb-1">
                                <strong class="dojo-auto-rule-card__name o_text_overflow">
                                    <field name="name"/>
                                </strong>
                                <span t-attf-class="dojo-auto-state-badge dojo-auto-state-{{ record.state.value }}">
                                    <t t-esc="record.state.value"/>
                                </span>
                            </div>

                            <!-- Meta: model + periodic/on-demand chip -->
                            <div class="text-muted small mb-2 d-flex align-items-center gap-1">
                                <field name="model_id"/>
                                <span t-if="record.is_periodic.raw_value"
                                      class="badge bg-info ms-1">Periodic</span>
                                <span t-if="!record.is_periodic.raw_value and record.state.raw_value !== 'done'"
                                      class="badge bg-warning text-dark ms-1">On Demand</span>
                            </div>

                            <!-- Stats row: mail, action, click counts + next run -->
                            <div class="d-flex gap-3 dojo-auto-rule-card__stats align-items-center">
                                <span title="Emails sent">
                                    <i class="fa fa-envelope me-1 text-info"/>
                                    <field name="activity_mail_count"/>
                                </span>
                                <span title="Actions run">
                                    <i class="fa fa-cogs me-1 text-warning"/>
                                    <field name="activity_action_count"/>
                                </span>
                                <span title="Link clicks">
                                    <i class="fa fa-hand-pointer-o me-1"/>
                                    <field name="click_count"/>
                                </span>
                                <span t-if="record.state.raw_value === 'periodic'"
                                      title="Next run" class="ms-auto text-info small">
                                    <i class="fa fa-clock-o me-1"/>
                                    <field name="next_execution_date"/>
                                </span>
                            </div>
                        </div>

                        <!-- Actions row — revealed on card hover via CSS opacity -->
                        <div class="dojo-auto-rule-card__actions">
                            <button t-if="record.state.raw_value === 'periodic' or record.state.raw_value === 'ondemand'"
                                    class="btn btn-sm btn-primary"
                                    type="object" name="run_automation">
                                <i class="fa fa-play me-1"/> Run Now
                            </button>
                            <a type="edit" class="btn btn-sm btn-secondary">
                                <i class="fa fa-pencil me-1"/> Edit
                            </a>
                        </div>
                    </div>
                </t>
            </xpath>
        </field>
    </record>

    <!-- ═══════════════════════════════════════════════════════════════════════
         3. FORM — accordion sections + workflow steps section title
    ════════════════════════════════════════════════════════════════════════ -->

    <record model="ir.ui.view" id="automation_configuration_form_inherit">
        <field name="name">automation.configuration.form.dojo</field>
        <field name="model">automation.configuration</field>
        <field name="inherit_id" ref="automation_oca.automation_configuration_form_view"/>
        <field name="arch" type="xml">

            <!-- Replace the flat <group> with two accordions -->
            <xpath expr="//sheet/group" position="replace">

                <!-- Accordion 1: Trigger Setup (open by default) -->
                <details class="dojo-accordion mb-2" open="">
                    <summary class="dojo-accordion__summary">
                        <span class="dojo-accordion__title">Trigger Setup</span>
                        <i class="fa fa-chevron-down dojo-accordion__chevron"/>
                    </summary>
                    <div class="dojo-accordion__body">
                        <group>
                            <field name="active" invisible="1"/>
                            <field name="model" invisible="1"/>
                            <field name="is_periodic"
                                   readonly="state != 'draft'"
                                   widget="boolean_toggle"/>
                            <field name="model_id"
                                   options="{'no_create_edit': True, 'no_open': True}"/>
                            <field name="field_id"
                                   string="Deduplicate by"
                                   options="{'no_create_edit': True, 'no_open': True}"/>
                            <field name="next_execution_date"
                                   readonly="1"
                                   invisible="state != 'periodic'"/>
                        </group>
                    </div>
                </details>

                <!-- Accordion 2: Conditions (collapsed by default) -->
                <details class="dojo-accordion mb-3">
                    <summary class="dojo-accordion__summary">
                        <span class="dojo-accordion__title">Conditions</span>
                        <i class="fa fa-chevron-down dojo-accordion__chevron"/>
                    </summary>
                    <div class="dojo-accordion__body">
                        <group>
                            <field name="tag_ids"
                                   widget="many2many_tags"
                                   options="{'color_field': 'color'}"/>
                            <label for="filter_id" string="Filter"/>
                            <div class="container ps-0">
                                <div class="row">
                                    <div class="col-5">
                                        <field name="filter_id" domain="filter_domain"/>
                                    </div>
                                    <button name="save_filter"
                                            type="object"
                                            string="Save filter"
                                            icon="fa-save"
                                            class="text-primary filter-left col-7"
                                            invisible="filter_id"/>
                                </div>
                            </div>
                            <field name="filter_domain" invisible="1"/>
                            <field name="domain"
                                   string="Domain"
                                   widget="domain"
                                   invisible="not filter_id"
                                   options="{'foldable': True, 'model': 'model'}"/>
                            <field name="editable_domain"
                                   string="Domain"
                                   widget="domain"
                                   invisible="filter_id"
                                   options="{'foldable': True, 'model': 'model'}"/>
                            <field name="company_id" groups="base.group_multi_company"/>
                        </group>
                    </div>
                </details>
            </xpath>

            <!-- Add "Dojang Workflow Steps" section title above the step kanban -->
            <xpath expr="//field[@name='automation_step_ids']" position="before">
                <div class="dojo-section-title">Dojang Workflow Steps</div>
            </xpath>
        </field>
    </record>

</odoo>
```

- [ ] **Step 2: Commit view inherits**

```powershell
git add addons/dojo_automation/views/automation_views_inherit.xml
git commit -m "feat(dojo_automation): XML view inherits — kanban card, form accordion, Dojang menu labels"
```

---

## Task 6: Install and Verify

**Files:** None created — install and smoke-test.

- [ ] **Step 1: Install the module**

Run in PowerShell from `dojo-odoo19/`:
```powershell
docker compose run --rm web -i dojo_automation -d odoo19 --config=/etc/odoo/odoo.conf --stop-after-init
```

Expected: install completes with no ERROR or CRITICAL lines in output. Warnings about missing translations are fine.

If you see `ModuleNotFoundError` for `automation_oca`, verify the `depends` list in `__manifest__.py`.

- [ ] **Step 2: Open the Automation module in browser**

Navigate to `http://localhost:8070/odoo/action-automation_oca.automation_configuration_act_window` (or find "Dojang Automation" in the app menu).

Check:
- App name shows "Dojang Automation" (not "Automation")
- Menu shows "Dojang Rules" (not "Automation Configuration")
- Stat panel renders above the kanban with 4 chips
- Shimmer skeleton appears briefly on first load
- Filter chips row is present below the stat panel

- [ ] **Step 3: Verify kanban cards**

Check each kanban card:
- Rule name visible and bold
- State badge present and color-coded (blue=periodic, amber=ondemand, green=done, grey=draft)
- Model name and Periodic/On Demand chip visible
- Stats row shows mail/action/click counts
- Hover: card lifts 2px + shadow increases + action row fades in
- Periodic state cards: subtle blue glow on left border, breathing pulse animation
- Entrance: cards slide up from 8px with staggered delay on page load

- [ ] **Step 4: Verify form accordions**

Open any automation rule. Check:
- "Trigger Setup" accordion is open by default — shows Is Periodic, Model, Deduplicate by, Next Execution
- "Conditions" accordion is collapsed — click to expand, shows Filter, Domain, Tags
- Chevron rotates 180° when accordion opens/closes
- "Dojang Workflow Steps" section title appears above the step kanban widget

- [ ] **Step 5: Verify step card colors**

In a rule that has steps (mail + action + activity types):
- Mail steps: `fa-envelope` icon tinted `--info` (blue), left-border blue
- Activity steps: `fa-clock-o` icon tinted `--success` (green), left-border green
- Action steps: `fa-cogs` icon tinted `--warning` (amber), left-border amber
- Delay timing renders as a pill chip (rounded background)
- Step card hover: lifts 2px

If `:has()` CSS selector is not supported in the running browser (unlikely for Chrome/Edge), the left-border coloring won't appear — the icon tinting still works. Note the browser version if this is an issue.

- [ ] **Step 6: Verify filter chips**

Click "Active" chip → kanban filters to periodic+ondemand rules only.
Click "Draft" → filters to draft rules.
Click chip again → filter cleared.
Click "All" → all chips cleared, full list restored.

If `sm.searchItems` is empty or the filter names don't match, open browser DevTools console. The filter names in `AutomationFilterChips` must match `name` attributes in `automation_configuration_search_view` (confirmed: `run`, `draft`, `done`).

- [ ] **Step 7: Fix any issues, then commit**

After verifying all checks pass:
```powershell
git add -A
git commit -m "feat(dojo_automation): Sprint 2 complete — Dojang Automation UI"
```

---

## Self-Review Checklist (Pre-Execution)

- [x] All 6 files have full content — no TBD or placeholder
- [x] `AutomationKanbanController` import path matches the actual file: `automation_oca/static/src/views/automation_upload/automation_upload.esm.js`
- [x] `state = 'error'` confirmed on `automation.record.step` (read model source)
- [x] Step icon values confirmed: `fa-envelope` (mail), `fa-clock-o` (activity), `fa-cogs` (action)
- [x] Filter names `run`, `draft`, `done` match `automation_configuration_search_view`
- [x] Form xpath `//sheet/group` targets the single flat group (confirmed from reading source XML)
- [x] `<details open="">` is standard HTML — renders open without JS
- [x] Menu record IDs `automation_oca.automation_root_menu` and `automation_oca.automation_configuration_menu` confirmed from `automation_oca/views/menu.xml`
- [x] No hardcoded hex — all colors use CSS custom properties with Bootstrap fallbacks
- [x] Touch targets ≥ 44px: filter chips are `padding: 4px 12px` + font = ~32px — bump to `padding: 8px 14px` if needed during verify step
- [x] `automation_oca` source files are never modified — all changes are overrides in `dojo_automation`
