# Sprint 2 — Dojang Automation UI Design Spec

**Date:** 2026-04-25
**Sprint:** 2 of 10 — Automation Workflows
**Module:** `automation_oca` (third-party, read-only) + new `dojo_automation` override module
**Audience:** ADMIN
**Tech:** OWL + XML inherits + SCSS

---

## Goals

Automation rules should be scannable at a glance. Each rule card communicates its state,
trigger type, and recent activity without opening the form. The form groups config fields
into logical sections and makes the step workflow visually readable.
Theme: `--info` accent throughout, semantic step-type colors, animated entrance/pulse/hover.

---

## Sprint 1 Lessons Applied

| Lesson | Application |
|--------|-------------|
| Verify template names in source before `t-inherit` | Read `automation_upload.esm.js` — confirmed `AutomationKanbanController` is the target class |
| Target the specific view's JS class, not the Odoo base | Import `AutomationKanbanView` from `automation_oca`, extend its Controller, re-register under new `js_class` |
| Use PowerShell for all Docker commands | All module install/upgrade commands use PowerShell tool |

---

## Module Structure

```
addons/dojo_automation/
  __init__.py
  __manifest__.py
  views/
    automation_views_inherit.xml
  static/src/
    js/
      automation_stat_panel.js
    xml/
      automation_stat_panel.xml
    css/
      automation.scss
  security/
    ir.model.access.csv
```

**`__manifest__.py` key fields:**
- `name`: `"Dojang Automation"`
- `depends`: `['dojo_core', 'automation_oca']`
- assets registered in `web.assets_backend`
- No Python models — pure frontend override

**UI branding rule:** Every user-visible string uses "Dojang" prefix — app name, menu labels,
page titles, section headers, empty states. Never expose "OCA", "automation_oca", or raw
model/field names in the UI.

---

## Section 1: Stat Panel

**Component:** `AutomationStatPanel` (OWL)

**Injection strategy:**
1. Import `AutomationKanbanView` from `automation_oca/static/src/views/automation_upload/automation_upload.esm.js`
2. Create `DojoAutomationKanbanController extends AutomationKanbanController`
3. Add `AutomationStatPanel` to its `static components`
4. Register as `"dojo_automation_kanban"` in the views registry
5. Override `js_class` on `automation_configuration_kanban_view` via XML inherit to `"dojo_automation_kanban"`

**4 KPI chips:**

| Chip | Query | Tint |
|------|-------|------|
| Active Rules | `automation.configuration` count `state in ['periodic','ondemand']` | `--info` |
| Triggered Today | `automation.record` count `create_date >= today`, `is_test = False` | `--success` |
| Running Now | `automation.record` count `state = 'periodic'`, `is_test = False` | `--warning` |
| Errors (7 days) | `automation.record.step` count `state = 'error'`, `write_date >= -7d` | `--danger` (tinted when > 0) — **verify `state` field exists on this model during impl; fall back to `automation.record` if not** |

- Shimmer skeleton while loading (CSS animated gradient, never a spinner)
- Errors chip gets alert tint when count > 0

**Filter chips (below stat panel):**

`All · Active · Periodic · On Demand · Draft · Done`

- Bridges to Odoo search model via `sm.toggleSearchItem`
- Targets existing search filters: `draft`, `run`, `done` in `automation_configuration_search_view`
- "Active" = `run` filter (periodic + ondemand combined)
- Active chip: filled `--info` background. Inactive: outlined. Transition: `--transition-fast`

---

## Section 2: Kanban Card Redesign

Override via `t-inherit` on `automation_oca.automation_configuration_kanban_view`.

**Card anatomy:**
```
┌──────────────────────────────────────┐
│ ▌  [Rule Name]          [State badge]│  ← left-border = state color
│    [Model name] · [Periodic/On demand│
│    tag chip]                         │
│                                      │
│  📧 12  ⚙️ 4  👆 8    ↻ Next: 2h    │  ← stats row
│ ─────────────────────────────────── │  ← revealed on hover
│  [Run Now]  [Edit]  [⋯]             │
└──────────────────────────────────────┘
```

**State → color mapping:**
| State | Token | Extra |
|-------|-------|-------|
| `draft` | `--text-muted` | — |
| `periodic` | `--info` | pulse glow animation on left-border |
| `ondemand` | `--warning` | — |
| `done` | `--success` | — |

**Contextual actions (hover-revealed row):**
- "Run Now" — visible only when `state in ['periodic', 'ondemand']`
- "Edit" — always visible
- "Archive" — in `⋯` overflow menu (destructive, never primary)

**Animations:**
- **Entrance:** cards animate in with `translateY(8px) → 0` + `opacity 0 → 1`, staggered 50ms per card using `animation-delay: calc(var(--card-index) * 50ms)`. CSS `@keyframes dojo-card-enter`.
- **Hover lift:** `transform: translateY(-2px)` + `box-shadow: var(--shadow-md)`, `150ms ease`
- **Periodic pulse:** `@keyframes dojo-pulse-border` — `box-shadow: 0 0 0 2px var(--bs-info)` breathing at 2s interval, applied to left-border of `periodic` state cards only
- **Action row reveal:** `opacity: 0 → 1` on card hover, `--transition-fast`

---

## Section 3: Form — Accordion Sections

Override via `t-inherit` on `automation_oca.automation_configuration_form_view`, targeting the `<sheet>` `<group>` block with xpath.

**Implementation:** CSS-only accordion using `<details>/<summary>` pattern (confirmed safe in Odoo's OWL renderer — used in Sprint 1 CRM token section). SCSS handles `max-height` open/close transition.

**Section 1 — "Trigger Setup"** (open by default)
- Is Periodic toggle (`boolean_toggle` widget, prominent)
- Model field ("What records does this rule target?")
- Unicity field (labelled "Deduplicate by", optional)
- Next execution date (read-only, visible only when `state = 'periodic'`)

**Section 2 — "Conditions"** (collapsed by default)
- Filter selector + Save filter inline button
- Domain editor (foldable, existing `domain` widget)
- Company (visible only with `base.group_multi_company`)
- Tags (`many2many_tags` with color)

**Section 3 — "Dojang Workflow Steps"** (always visible, no accordion)
- Uppercase small-caps section divider label
- The existing `automation_step` kanban widget directly below
- No structural changes to the widget itself — only the step cards inside are restyled (Section 4)

---

## Section 4: Step Cards (Inside Workflow Kanban)

Override the kanban card template inside `automation_configuration_form_view` via nested xpath on the `<templates>` block.

**Step type → color mapping:**
| Type | Token | Icon |
|------|-------|------|
| `mail` | `--info` | `fa-envelope` |
| `action` | `--warning` | `fa-cogs` |
| `activity` | `--success` | `fa-tasks` |
| `sms` | `--primary` | `fa-comment` |

**Plain-English summary line** (subtitle below step name):
- Uses existing `step_name` computed field, surfaced as a visible subtitle
- Format: "Send email after 2 days" / "Run action immediately" / "Create activity after 1 hour"

**Step card micro-interactions:**
- Hover: `translateY(-2px)` + left-border brightens from 40% to 100% opacity
- Edit button: fills with step type color on hover (not generic `--primary`)
- "Add child activity" panel: slides up from hidden on parent card hover (`max-height` transition, 150ms)
- Error state: `--danger` left-border + subtle red background tint + "!" overlay on graph count

**Timing column polish:**
- Connector lines use `--border` color token (not raw CSS)
- Circle dot (`fa-circle`) color matches step type color
- Delay text rendered as a pill chip (`--surface` bg, `--radius-md`, small padding)

---

## Done Criteria

- [ ] Stat panel shows 4 live KPI chips with shimmer skeleton
- [ ] Filter chips functional — bridge to existing search filters
- [ ] Rule cards show: name, model, state badge, stats row, contextual actions on hover
- [ ] Active/inactive state is visually prominent (color + badge label, not a buried checkbox)
- [ ] Periodic state cards have a pulse glow on their left-border
- [ ] Card entrance animation: staggered slide-up + fade-in
- [ ] Form uses accordion sections — Trigger Setup (open) + Conditions (collapsed) + Workflow Steps
- [ ] Step cards colored by type (mail/action/activity/sms)
- [ ] Step cards show plain-English timing summary as subtitle
- [ ] Error state steps show `--danger` styling and "!" indicator
- [ ] All UI strings use "Dojang" branding — no raw OCA/model names visible
- [ ] No hardcoded hex values — all colors use MuK/Bootstrap design tokens
- [ ] All touch targets >= 44px
- [ ] Color never used as sole state indicator — always paired with text label or icon

---

## Files to Create

| File | Purpose |
|------|---------|
| `addons/dojo_automation/__init__.py` | Empty init |
| `addons/dojo_automation/__manifest__.py` | Module manifest |
| `addons/dojo_automation/security/ir.model.access.csv` | Read access for base user |
| `addons/dojo_automation/views/automation_views_inherit.xml` | All XML view inherits |
| `addons/dojo_automation/static/src/js/automation_stat_panel.js` | OWL components + view registration |
| `addons/dojo_automation/static/src/xml/automation_stat_panel.xml` | QWeb templates |
| `addons/dojo_automation/static/src/css/automation.scss` | All animations and styles |

## Files to Read (do not edit)

| File | Why |
|------|-----|
| `addons/automation_oca/static/src/views/automation_upload/automation_upload.esm.js` | Import `AutomationKanbanView` and `AutomationKanbanController` |
| `addons/automation_oca/views/automation_configuration.xml` | All view IDs for xpath targets |
| `addons/dojo_crm/static/src/js/crm_stat_panel.js` | Reference implementation for OWL stat panel pattern |
| `addons/dojo_crm/static/src/css/crm_pipeline.scss` | Reference for animation patterns |
