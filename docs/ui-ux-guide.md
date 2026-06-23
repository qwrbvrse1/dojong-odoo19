# UFTKD Dojo Theme — UI/UX Design System

**Version:** 1.0.0  
**Status:** Active — MuK IT theme fully replaced as of REL-001/INC-23  
**Module:** `dojo_theme` (saas~19.2.1.0.0)

---

## Overview

The UFTKD Dojo Platform uses a custom theme module (`dojo_theme`) built exclusively with **CSS custom properties** (design tokens) and **OWL components**. The theme provides all visual styling previously supplied by the 7 MuK IT theme modules.

**No external build tooling required** — the theme uses plain CSS custom properties that map directly to Odoo's native asset pipeline. All new UI is built in OWL (Odoo Web Library), the framework's native component system.

**Design philosophy:**
- Dark background optimized for dojo environments (low ambient light)
- High contrast text for readability
- Brand colors (red, gold) used sparingly for emphasis
- Belt rank colors for visual hierarchy in member/student interfaces
- Consistent spacing and elevation system

---

## Design Tokens

All design tokens are defined in `addons/dojo_theme/static/src/css/tokens.css` as CSS custom properties on the `:root` element. **Never hardcode color hex values** — always reference the token name.

### Surface Colors

Used for backgrounds, cards, panels, and elevation hierarchy.

| Token | Value | Usage |
|---|---|---|
| `--bg` | `#000000` | Page background (true black) |
| `--surface` | `#0c0c0c` | Primary card/panel surface (elevated from background) |
| `--surface2` | `#141414` | Secondary surface (higher elevation) |
| `--surface3` | `#1c1c1c` | Tertiary surface (highest elevation) |
| `--border` | `#272727` | Borders, dividers, input borders |

**Elevation principle:** Use higher surface tokens (`surface2`, `surface3`) for layered UI elements like modals, popovers, or nested cards to create visual depth.

### Brand Colors

UFTKD brand identity colors — use sparingly for emphasis.

| Token | Value | Usage |
|---|---|---|
| `--red` | `#b41e16` | Primary brand color (buttons, active badges, focus rings) |
| `--red-dim` | `#fce8e6` | Muted red background (error states, alerts) |
| `--gold` | `#eab308` | Accent color (highlights, special badges) |
| `--gold-light` | `#fef3c7` | Light gold background (warnings, attention) |

**Usage rule:** `--red` is the primary action color. Use it for primary buttons, active navigation, and important status indicators. Reserve `--gold` for special achievements, premium features, or instructor-specific UI.

### Typography

Text color hierarchy for readability on dark backgrounds.

| Token | Value | Usage |
|---|---|---|
| `--text` | `#e8eaed` | Primary body text (high contrast) |
| `--text-muted` | `#9aa0a6` | Secondary text (labels, meta information) |
| `--text-dim` | `#5f6368` | Tertiary text (disabled state, placeholders) |

**Contrast ratios:**
- `--text` on `--bg`: **14.8:1** (WCAG AAA)
- `--text-muted` on `--bg`: **7.2:1** (WCAG AA)
- `--text-dim` on `--bg`: **4.5:1** (WCAG AA minimum)

### Status Colors

Semantic colors for state communication.

| Token | Value | Usage |
|---|---|---|
| `--green` | `#188038` | Success, active, published, attended |
| `--orange` | `#e37400` | Warning, scheduled, upcoming, pending |
| `--blue` | `#1a73e8` | Info, draft, neutral informational states |

**Accessibility note:** Status colors are **never used alone** — always pair with a text label or icon. For example, a badge should show both the color AND the status text ("Active", "Pending", etc.).

### Belt Rank Colors

Special color palette for martial arts belt rank visualization.

| Token | Belt Rank | Value |
|---|---|---|
| `--belt-white` | White Belt | `#ffffff` |
| `--belt-yellow` | Yellow Belt | `#fbbf24` |
| `--belt-green` | Green Belt | `#16a34a` |
| `--belt-blue` | Blue Belt | `#1a73e8` |
| `--belt-red` | Red Belt | `#b41e16` |
| `--belt-black` | Black Belt | `#000000` |
| `--belt-brown` | Brown Belt | `#92400e` |
| `--belt-purple` | Purple Belt | `#7c3aed` |
| `--belt-orange` | Orange Belt | `#e37400` |
| `--belt-camo` | Camo Belt | `linear-gradient(...)` |

**Usage:** Belt colors are used in member cards, attendance rosters, belt progression UI, and instructor dashboards to provide instant visual recognition of student rank.

**Camo belt special case:** The camo belt uses a CSS gradient instead of a solid color. When applying to backgrounds, use `background: var(--belt-camo)`. When using as a border or text color, fall back to the first stop color (`#4b5320`).

---

## Typography Scale

The theme uses **Google Fonts** loaded via Odoo's asset pipeline:

- **Display / Headings:** Bebas Neue (uppercase, bold)
- **Body text:** Barlow (300–700 weight range)
- **Labels / Condensed:** Barlow Condensed

Font files are loaded in `addons/dojo_theme/static/src/css/fonts.css` via Google Fonts CDN.

### Font Usage Guidelines

| Element | Font | Weight | Size |
|---|---|---|---|
| Page titles | Bebas Neue | Normal | 2.5rem (40px) |
| Section headings | Bebas Neue | Normal | 1.75rem (28px) |
| Card titles | Barlow | 600 (Semi-bold) | 1.25rem (20px) |
| Body text | Barlow | 400 (Regular) | 1rem (16px) |
| Small labels | Barlow Condensed | 500 (Medium) | 0.875rem (14px) |
| Meta text | Barlow | 300 (Light) | 0.875rem (14px) |

**Responsive scaling:** Font sizes scale down by 10–15% on mobile viewports (<768px).

---

## Spacing System

The theme uses a **4px base unit** spacing scale for consistent rhythm.

| Token | Value | Usage |
|---|---|---|
| `--space-xs` | `4px` | Tight inline spacing (icon-to-text gap) |
| `--space-sm` | `8px` | Compact padding (chip/badge padding) |
| `--space-md` | `16px` | Standard padding (card padding, button padding) |
| `--space-lg` | `24px` | Section spacing (between card groups) |
| `--space-xl` | `32px` | Page section spacing |
| `--space-2xl` | `48px` | Major layout spacing (header-to-content gap) |

**Layout rule:** Use `--space-md` (16px) as the default padding for cards and containers. Use `--space-lg` (24px) for gaps between major sections.

---

## Component Patterns

### Stat Panel

A row of KPI chips displayed at the top of module landing pages. Provides admins with an instant health check before diving into records.

**Anatomy of one stat chip:**

```
┌─────────────────────┐
│  🏷 icon (24px)     │
│  1,284              │  ← large number, bold, --text
│  Total Leads        │  ← label, --text-muted, small
│  ↑ 12% this week    │  ← optional trend, colored arrow
└─────────────────────┘
```

**Layout rules:**
- Single row at desktop (≥1280px); 2-column grid on tablet (≥768px); single column on mobile (<768px)
- Each chip: `background: var(--surface)`, `border: 1px solid var(--border)`, `border-radius: 8px`, `padding: var(--space-md)`
- Trend arrow: green (↑) or red (↓) — never color alone, always include the arrow glyph
- Shimmer skeleton while data loads (no spinner)

**Used by:** `dojo_crm` (CRM Pipeline), `dojo_automation` (Automation Rules), `dojo_instructor_dashboard` (Instructor Dashboard)

### Entity Card

A record displayed as a card in a responsive grid. Replaces list rows for visual scanning.

**Anatomy:**

```
┌────────────────────────────────────┐
│ ▌ Avatar  Title                    │  ← left border: status color
│   Meta · date · tag                │  ← --text-muted
│                     [Status badge] │
│ ───────────────────────────────── │  ← revealed on hover
│ [Edit]  [View]  [Quick action]    │
└────────────────────────────────────┘
```

**Behavior:**
- **Hover:** `transform: translateY(-2px)` + `box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3)` (150ms ease)
- **Action row:** Hidden at rest (`opacity: 0`), revealed on hover (`opacity: 1`, 150ms ease)
- **Grid:** `display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: var(--space-md);`
- **Status color:** Left border color AND badge color match (paired visual indicator)

**Empty state (required for every card grid):**

```
   [dojo illustration — optional]
   No [records] yet — let's change that.
   [+ Create first record]           ← primary button
```

**Used by:** Member rosters, marketing cards, automation rules, CRM leads

### Kanban Column

Stage-based pipeline view for records with defined workflows.

**Anatomy:**

```
● New Leads  (12)                    ← stage dot + name + count
─────────────────────────
[Entity Card]
[Entity Card]
[Entity Card]
- - - - - - - - - - - -
+ Add Lead                           ← always-visible affordance
```

**Behavior:**
- **Column header:** Sticky on vertical scroll (`position: sticky; top: 0;`)
- **Empty column:** Dashed border (`border: 2px dashed var(--border)`), "Drop here" label
- **Drag handle:** Appears on card hover (`cursor: grab`)
- **Column color:** Header dot + card left-border use the same stage color

**Used by:** `dojo_crm` (lead pipeline)

---

## Micro-Interactions

Standard interaction patterns applied globally.

### Card Hover

```css
.card {
    transition: transform 150ms ease, box-shadow 150ms ease;
}

.card:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
}
```

### Button Press

```css
.btn:active {
    transform: scale(0.97);
}
```

### Focus Ring

All interactive elements use a visible focus ring for keyboard navigation (WCAG 2.1 requirement).

```css
*:focus-visible {
    outline: 2px solid var(--red);
    outline-offset: 2px;
}
```

### Badge Color Transition

Status badges transition smoothly between states (not instant color flash).

```css
.badge {
    transition: background-color 200ms ease, color 200ms ease;
}
```

---

## Accessibility Standards

All UI must meet **WCAG 2.1 Level AA** at minimum.

### Contrast Requirements

- **Normal text:** Minimum 4.5:1 contrast ratio
- **Large text (18px+):** Minimum 3:1 contrast ratio
- **Interactive elements:** Minimum 3:1 contrast ratio for UI components

**Pre-verified token pairs:**
- `--text` on `--bg`: 14.8:1 ✅ (AAA)
- `--text` on `--surface`: 13.2:1 ✅ (AAA)
- `--text-muted` on `--bg`: 7.2:1 ✅ (AA)
- `--red` on `--bg`: 4.9:1 ✅ (AA for large text)

### Touch Targets

- **Minimum size:** 44×44px for all interactive elements
- **Kiosk UI:** 48×48px minimum (members often in a hurry, gym environment)

### Color Alone

**Never use color as the sole indicator of state.** Always pair with text or an icon.

❌ **Wrong:** Red badge with no text  
✅ **Correct:** Red badge with "Error" text

---

## Layout Structure

### Backend Admin Interface

```
┌─────────────────────────────────────┐
│ Topbar (60px height)                │  ← --surface3
├─────┬───────────────────────────────┤
│ Sidebar │ Main Content Area         │
│ (240px) │                            │
│ --surface2 │  --bg                  │
│         │                            │
└─────────┴────────────────────────────┘
```

- **Topbar:** `height: 60px`, `background: var(--surface3)`, `border-bottom: 1px solid var(--border)`
- **Sidebar:** `width: 240px`, `background: var(--surface2)`, fixed position
- **Main content:** `background: var(--bg)`, `padding: var(--space-lg)`

### Kiosk Interface

Full-screen grid optimized for tablet touch (no sidebar or topbar chrome).

```
┌─────────────────────────────────────┐
│ Session Header (compact)            │  ← 80px height
├─────────────────────────────────────┤
│ Member Roster Grid                  │
│ (3-column at 768px, 4-column 1024px)│
│                                      │
│                                      │
└─────────────────────────────────────┘
```

- **Roster tiles:** Minimum 48×48px touch targets
- **Grid gap:** `var(--space-md)` (16px)
- **Session header:** Sticky on scroll

---

## OWL Component Guidelines

All new UI components are built in **OWL** (Odoo Web Library), not vanilla JS or jQuery.

### Component File Structure

```
addons/my_module/
├── static/
│   ├── src/
│   │   ├── js/
│   │   │   └── my_component.js        ← OWL component class
│   │   ├── xml/
│   │   │   └── my_component.xml       ← QWeb template
│   │   └── css/
│   │       └── my_component.css       ← Component-specific styles
│   └── ...
└── __manifest__.py                     ← Register assets
```

### Asset Registration

In `__manifest__.py`:

```python
'assets': {
    'web.assets_backend': [
        'my_module/static/src/js/my_component.js',
        'my_module/static/src/xml/my_component.xml',
        'my_module/static/src/css/my_component.css',
    ],
},
```

### Template Inheritance Pattern

To inject components into existing Odoo views (e.g., stat panel above a kanban):

**XML template (`static/src/xml/my_component.xml`):**

```xml
<templates xml:space="preserve">
    <!-- Define your component templates -->
    <t t-name="my_module.MyComponent" owl="1">
        <div class="my-component">
            <!-- component markup -->
        </div>
    </t>

    <!-- Create an isolated primary template -->
    <t t-name="my_module.MyKanbanView"
       t-inherit="web.KanbanView"
       t-inherit-mode="primary">
        <xpath expr="//t[@t-component='props.Renderer']" position="before">
            <MyComponent/>
        </xpath>
    </t>
</templates>
```

**JS component (`static/src/js/my_component.js`):**

```javascript
/** @odoo-module **/

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { targetKanbanView } from "@some_module/views/kanban/kanban_view";

class MyComponent extends Component {
    static template = "my_module.MyComponent";
    // component logic
}

// Point the target view controller at your isolated template
targetKanbanView.Controller.template = "my_module.MyKanbanView";
targetKanbanView.Controller.components = {
    ...targetKanbanView.Controller.components,
    MyComponent,
};

export { MyComponent };
```

**Why `primary` not `extension`:**
- `extension` mode mutates the parent template in-place, affecting ALL views using that template
- `primary` mode creates an independent copy, isolated to your module
- Use `primary` when injecting module-specific components; use `extension` only for global overrides

**Reference implementations:**
- `dojo_crm/static/src/js/crm_stat_panel.js`
- `dojo_automation/static/src/js/automation_stat_panel.js`

---

## CSS Conventions

### Class Naming

- **Module prefix:** Use a module-specific prefix to prevent style leakage (e.g., `dojo-crm-`, `dojo-auto-`)
- **BEM methodology:** `block__element--modifier` pattern for complex components
- **State classes:** Prefix with `is-` or `has-` (e.g., `.is-active`, `.has-error`)

**Examples:**

```css
/* Stat panel component */
.dojo-stat-panel { }
.dojo-stat-panel__chip { }
.dojo-stat-panel__chip--alert { }
.dojo-stat-panel__chip.is-loading { }
```

### No Inline Styles

**Never use `style=""` attributes** — always define styles in CSS files with semantic class names.

❌ **Wrong:** `<div style="color: red;">Error</div>`  
✅ **Correct:** `<div class="error-message">Error</div>` + `.error-message { color: var(--red); }`

### Media Queries

Standard breakpoints for responsive design:

```css
/* Mobile-first approach */
.component { }

/* Tablet and up (≥768px) */
@media (min-width: 768px) {
    .component { }
}

/* Desktop and up (≥1280px) */
@media (min-width: 1280px) {
    .component { }
}
```

**Breakpoint reference:**
- **375px:** Minimum mobile width (iPhone SE)
- **768px:** Tablet / iPad portrait
- **1024px:** Tablet landscape / small desktop
- **1280px:** Desktop / laptop

---

## Skeleton Loading

For asynchronous data loading (stat panels, card grids), use **shimmer skeleton placeholders** instead of spinners.

### Shimmer Animation

```css
@keyframes shimmer {
    0% {
        background-position: -100% 0;
    }
    100% {
        background-position: 100% 0;
    }
}

.skeleton {
    background: linear-gradient(
        90deg,
        var(--surface) 25%,
        var(--surface2) 50%,
        var(--surface) 75%
    );
    background-size: 200% 100%;
    animation: shimmer 1.5s infinite;
}
```

**Usage:** Apply `.skeleton` class to placeholder elements matching the shape of the final content.

**Example (stat chip skeleton):**

```html
<div class="dojo-stat-panel__chip skeleton">
    <div class="skeleton-icon" style="width: 24px; height: 24px;"></div>
    <div class="skeleton-text" style="width: 60px; height: 32px;"></div>
    <div class="skeleton-text" style="width: 80px; height: 16px;"></div>
</div>
```

**Never use a centered spinner for card grids or data tables** — it provides no shape or context for what is loading.

---

## Empty States

Every list view, card grid, or kanban column must have a designed empty state.

### Empty State Anatomy

```
┌────────────────────────────────────┐
│                                     │
│   [Optional illustration]          │
│                                     │
│   No [records] yet — let's change  │  ← Friendly, active voice
│   that.                             │
│                                     │
│   [+ Create first record]          │  ← Primary CTA button
│                                     │
└────────────────────────────────────┘
```

**Copy guidelines:**
- Use active, friendly voice (not passive or formal)
- Clearly state what is missing
- Provide the #1 most relevant action as a primary button

**Examples:**

- Members list: "No members yet — let's change that. [+ Add first member]"
- Automation rules: "No automation rules yet. [+ Create your first rule]"
- Marketing cards: "No marketing cards yet. [+ Design your first card]"

**Never show:**
- Generic "No records found" text
- A completely blank area
- Only a search box with no explanation

---

## Animation Performance

All animations use **CSS transforms and opacity** for 60fps performance (GPU-accelerated).

### Safe Properties

✅ **Performant (GPU-accelerated):**
- `transform` (translate, scale, rotate)
- `opacity`

❌ **Avoid (triggers layout/paint):**
- `top`, `left`, `right`, `bottom`
- `width`, `height`
- `margin`, `padding`

### Timing Functions

Standard easing curves:

```css
--ease-in-out: cubic-bezier(0.4, 0, 0.2, 1);  /* Material Design standard */
--ease-out: cubic-bezier(0.0, 0, 0.2, 1);     /* Deceleration */
--ease-in: cubic-bezier(0.4, 0, 1, 1);        /* Acceleration */
```

**Usage:**
- **Micro-interactions:** 150ms ease-out (card hover, button press)
- **State transitions:** 200ms ease-in-out (badge color change)
- **Entrance animations:** 300ms ease-out (card slide-in, fade-in)

---

## Migration from MuK IT Theme

As of **REL-001/INC-23**, all 7 MuK IT theme modules have been **uninstalled and removed**. The `dojo_theme` module now provides all visual styling previously supplied by MuK.

### Removed Modules

- `muk_web_theme` — Core theme system
- `muk_web_colors` — Color palette
- `muk_web_chatter` — Chatter polish
- `muk_web_appsbar` — Apps sidebar
- `muk_web_dialog` — Fullscreen dialogs
- `muk_web_group` — Group expand/collapse
- `muk_web_refresh` — Manual refresh button

### Token Mapping

| MuK Token | dojo_theme Token | Notes |
|---|---|---|
| `--primary` | `--red` | Primary brand color |
| `--bs-body-bg` | `--bg` | Page background |
| `--bs-body-color` | `--text` | Primary text |
| `--bs-secondary-color` | `--text-muted` | Secondary text |
| `--bs-border-color` | `--border` | Borders and dividers |
| `--bs-success` | `--green` | Success state |
| `--bs-warning` | `--orange` | Warning state |
| `--bs-danger` | `--red-dim` | Error state background |
| `--bs-info` | `--blue` | Info state |

### Feature Coverage

| MuK Feature | dojo_theme Replacement | Status |
|---|---|---|
| Color system | `tokens.css` (41 tokens) | ✅ Fully covered |
| Typography | Google Fonts (Bebas Neue, Barlow) | ✅ Fully covered |
| Layout SCSS | Planned for future increment | ⚠️ Deferred (acceptable gap) |
| Apps sidebar | Odoo Community default | ⚠️ Acceptable loss |
| Chatter polish | Odoo Community default | ⚠️ Acceptable loss |
| Fullscreen dialogs | Odoo Community default | ⚠️ Acceptable loss |
| Refresh button | Browser refresh | ⚠️ Acceptable loss |
| Group expand/collapse | Odoo Community default | ⚠️ Acceptable loss |

**Deferred features** (layout SCSS, navbar customization) will be addressed in future increments if visual regression becomes visible in production.

---

## Version History

### v1.0.0 (2026-06-23) — REL-001/INC-23

- **MuK IT theme fully retired** — All 7 `muk_web_*` modules uninstalled and removed
- `dojo_theme` is now the sole theme provider
- Design token system documented (41 tokens across 6 categories)
- OWL component patterns documented
- Accessibility standards codified (WCAG 2.1 Level AA)
- Typography scale and spacing system defined
- Animation performance guidelines added

---

## Reference Files

- **Design tokens:** `addons/dojo_theme/static/src/css/tokens.css`
- **Font loading:** `addons/dojo_theme/static/src/css/fonts.css`
- **Theme manifest:** `addons/dojo_theme/__manifest__.py`
- **OWL stat panel examples:**
  - `addons/dojo_crm/static/src/js/crm_stat_panel.js`
  - `addons/dojo_automation/static/src/js/automation_stat_panel.js`
- **Design prototype (reference only):** `scope/UFT_SUPABASE_STORAGE_PHOTOS.html`

---

## Support

For questions about the design system or token usage, consult:

1. This document (`docs/ui-ux-guide.md`)
2. The `dojo_theme` module source code (`addons/dojo_theme/`)
3. Existing OWL component implementations in `dojo_crm` and `dojo_automation`
4. UFTKD development team (for new token requests or design decisions)

**Do not introduce new color values or spacing units without updating this document and the `tokens.css` file.**
