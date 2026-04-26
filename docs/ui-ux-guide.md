# Dojo UI/UX Guide

> **How to use this guide:**
> Check the Sprint Order table below. Pick the next `[ ] Not started` sprint. Read the sprint
> section — it tells you what to build, which files to touch, and when you're done. Update status
> markers inline as you go. Finish one sprint before starting the next.
>
> **Status key:** `[ ]` Not started · `[~]` In progress · `[x]` Done
>
> **Audience tags:** `ADMIN` `INSTRUCTOR` `MEMBER` `PUBLIC`

---

## Dojo Admin Design Language

This section is the single source of truth for visual decisions. Every sprint references it.
Do not introduce colors, shadows, or spacing values that aren't defined here.

### Color Tokens

All tokens map to MuK theme CSS variables or Bootstrap utilities already loaded in the Odoo
shell. Never hardcode hex values — always use the token name.

| Token | Maps to | Usage |
|-------|---------|-------|
| `--primary` | MuK primary | Buttons, active badges, kanban column headers, focus rings |
| `--surface` | `--bs-body-bg` / MuK card bg | Card and panel backgrounds |
| `--surface-hover` | `--surface` darkened 4% | Card hover background |
| `--border` | `--bs-border-color` | Card borders, dividers, input borders |
| `--text-primary` | `--bs-body-color` | All primary body text |
| `--text-muted` | `--bs-secondary-color` | Meta lines, timestamps, placeholders |
| `--success` | `--bs-success` | Active/published/done badges |
| `--warning` | `--bs-warning` | Scheduled/pending/attention badges |
| `--danger` | `--bs-danger` | Failed/error/cancelled badges |
| `--info` | `--bs-info` | Draft/neutral informational badges |
| `--shadow-sm` | `0 1px 3px rgba(0,0,0,.08)` | Card resting state |
| `--shadow-md` | `0 4px 12px rgba(0,0,0,.12)` | Card hover/lifted state |
| `--radius-md` | `0.5rem` | Card, badge, chip border radius |
| `--transition-fast` | `150ms ease` | All micro-interaction transitions |

Check `muk_web_theme` SCSS variables first — the above names may already exist under slightly
different aliases. Use whatever the theme exposes; these are the semantic meanings to map to.

---

### Three Core UI Patterns

#### Pattern 1 — Stat Panel

A row of KPI chips at the top of any module landing page. Gives admins an instant health check
before they dive into records.

**Anatomy of one chip:**
```
┌─────────────────────┐
│  🏷 icon (24px)     │
│  1,284              │  ← large number, bold
│  Total Leads        │  ← label, --text-muted, small
│  ↑ 12% this week    │  ← optional trend, colored arrow
└─────────────────────┘
```

**Layout rules:**
- Single row at 1280px+; 2-column grid below 768px
- Each chip: `--surface` background, `--radius-md`, `--shadow-sm`, 16px padding
- Trend arrow: green (↑) or red (↓) — never color alone, always the arrow glyph too
- Skeleton shimmer while data loads (not a spinner)

**Used by:** dojo_crm, automation_oca, dojo_social, ai_assistant, connect

---

#### Pattern 2 — Entity Card

A single record displayed as a card in a responsive grid. Replaces list rows everywhere records
benefit from visual scanning.

**Anatomy:**
```
┌──────────────────────────────────┐
│ ▌  Avatar/Icon   Title           │  ← colored left-border (status color)
│    Meta line — date · tag        │
│                   [Status badge] │
│ ─────────────────────────────── │  ← revealed on hover
│ [Edit]  [View]  [Quick action]  │
└──────────────────────────────────┘
```

**Behavior rules:**
- Hover: `transform: translateY(-2px)` + transition to `--shadow-md` in `--transition-fast`
- Action row hidden at rest, revealed on hover (opacity 0→1, `--transition-fast`)
- Grid: `display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr))`
- Status color maps to the left-border color AND the badge color (paired with text label)

**Empty state (required for every card grid):**
```
   [dojo illustration]
   No [records] yet — let's change that.
   [+ Create first record]           ← primary button
```

**Used by:** dojo_marketing (card thumbnails), dojo_social (post cards), ai_assistant (conversations)

---

#### Pattern 3 — Kanban Column

A stage-based pipeline view. Use when records have a defined workflow with named stages.

**Anatomy:**
```
● New Leads  (12)                    ← stage dot (colored) + name + count badge
─────────────────────────
[Entity Card]
[Entity Card]
[Entity Card]
- - - - - - - - - - - -
+ Add Lead                           ← always-visible add affordance at bottom
```

**Behavior rules:**
- Column header: sticky on vertical scroll
- Empty column: dashed border, "Drop here" label
- Drag handle: appears on card hover (`cursor: grab`)
- Column color: header dot + left-border of cards use same stage color

**Used by:** dojo_crm (lead pipeline), automation_oca (workflow stages), dojo_ai_caller (campaign stages)

---

### Design Upgrades (Applied Globally)

These apply to every sprint. Do not repeat them in individual sprint sections.

**1. Micro-interactions**
- Cards lift on hover: `transform: translateY(-2px)` + `box-shadow: var(--shadow-md)`, 150ms ease
- Status badges color-transition smoothly (not an instant flash)
- Button press: `transform: scale(0.97)` on `:active`
- Form field focus: border transitions to `--primary`, 150ms ease

**2. Progressive disclosure**
- Advanced/rarely-used fields behind a "Show advanced options" toggle
- Wizard steps: only current step fields visible — no internal scroll within a step
- Config forms: accordion sections (Basic / Advanced / Danger zone)

**3. Contextual actions**
- Buttons appear based on record state ("Convert to Member" only on qualified leads, "Retry" only on failed posts)
- Bulk action bar slides in from the bottom when records are multi-selected (not a top toolbar)
- Primary action: top-right of form header. Destructive actions: behind a `⋯` overflow menu

**4. Quick filter chips**
- Horizontal scrolling chip row above every kanban or card grid
- Default chips: `All · Mine · This week · Active · Needs attention` (adjust per module)
- Active chip: filled `--primary` background. Inactive: outlined. Transition: `--transition-fast`
- Filter updates the view inline — no full page reload

**5. Skeleton loading**
- Card grids use shimmer skeleton placeholders while data loads
- Shimmer: CSS animated gradient from `--surface` to `--surface-hover`
- Never use a centered spinner for a card grid

**6. Activity timeline (CRM, Connect, AI caller)**
- Vertical timeline on record forms showing all touchpoints: calls, emails, stage changes, notes
- Each entry: colored icon + one-line summary + relative timestamp ("2 hours ago")
- Collapsed beyond 5 entries; "Show all" expands inline without navigation

**7. Empty states with personality**
- Use a dojo-themed illustration (belt, training dummy, gi — pick one per module)
- Heading: friendly, active voice ("No leads yet — let's change that")
- One primary CTA button — the #1 create action for that module
- Never a blank area, never "No records found"

**8. Form field grouping**
- No more than 5 fields visible before a section break
- Section dividers: uppercase small-caps label, no heavy border
- Related fields on the same row: first/last name, start/end date, amount/currency

---

## Sprint Order

| # | Sprint | Module | UI Pattern | Status |
|---|--------|--------|------------|--------|
| 1 | CRM Pipeline | `dojo_crm` | Stat Panel + Kanban | [x] |
| 2 | Automation Workflows | `automation_oca` | Stat Panel + Card grid | [x] |
| 3 | Marketing Cards | `dojo_marketing` | Stat Panel + Card grid | [ ] |
| 4 | AI Assistant | `ai_assistant` | Stat Panel + Entity Cards | [ ] |
| 5 | Social Media | `dojo_social` | Stat Panel + Card grid | [ ] |
| 6 | Connect + Kai | `connect` + `dojo_connect_ai` | Stat Panel + Timeline | [ ] |
| 7 | Admin Home | `dojo_core` | Stat Panel + Quick-action tiles | [ ] |
| 8 | Onboarding Wizard | `dojo_onboarding` | Wizard (progressive steps) | [ ] |
| 9 | Member Portal | `dojo_members_portal` | Card grid + Mobile-first | [ ] |
| 10 | Kiosk | `dojo_kiosk` | Large-touch grid (optimization) | [ ] |

Work top-to-bottom. Mark `[~]` when started, `[x]` when all done criteria pass.

---

## Sprint 1 — dojo_crm ✓

**Goal:** The CRM pipeline and lead form feel like a modern sales tool — not a data-entry form.
**Audience:** `ADMIN` `INSTRUCTOR` · **Facing:** Internal · **Tech:** `OWL` + `XML` + `SCSS`

### What was built

#### Kanban pipeline view
- **Live stat panel** — OWL component (`CrmStatPanel`) injected above the kanban board via `t-inherit="web.KanbanView"`. Shows 4 real-time KPI chips: Total Leads, Conversion Rate (30-day), Trials This Week, Expiring Offers. Shimmer skeleton while loading. Alert/warning tint on chips when non-zero.
- **Quick filter chips** — OWL component (`CrmFilterChips`) below the stat panel. 5 one-click filters: High Score · Trial Attended · No-Show · Converted · Has Booking. Active chip fills with primary color. Bridges to Odoo's search model via `sm.toggleSearchItem`.
- **Kanban card polish** — hover lift (`translateY(-2px)` + shadow), smooth badge color transitions, status badges as pill-shaped icon+text pairs.
- **Sticky column headers** — kanban group headers stay visible on scroll.

#### Lead form
- **Score block** — replaces plain progress bar. Shows bold score number + Hot/Warm/Cold label (green ≥60 / warning ≥30 / muted <30) + progress bar in one row.
- **Status strip** — color-coded pill badges (Attended · No-Show · Converted · Waiver Signed) visible immediately below the score without opening any tab.
- **2-tab layout** — 3 old tabs (Dojang Trial + Booking & Tokens + Engagement & AI) consolidated into 2: **Trial Journey** (trial info + conversion + booking links + collapsible token details) and **Engagement & AI**.
- **Decluttered header** — "Book Trial" demoted to secondary and hidden once trial is attended. "Convert to Member" (primary) only appears after `trial_attended = True`. The two custom buttons never appear simultaneously.

### Files changed
| File | What changed |
|------|-------------|
| `static/src/js/crm_stat_panel.js` | New — OWL `CrmStatPanel` + `CrmFilterChips` components; registered on `crmKanbanView.Controller.components` |
| `static/src/xml/crm_stat_panel.xml` | New — QWeb templates + `web.KanbanView` inheritance |
| `static/src/css/crm_pipeline.scss` | New — stat panel chips, filter chips, kanban polish, lead form score/badge styles |
| `views/crm_lead_view_inherit.xml` | Replaced score xpath + 3-tab xpath with score block, status strip, 2-tab layout; added sheet class for SCSS scoping; tightened header button visibility |
| `views/crm_dashboard.xml` | Added `dojo-crm-pipeline` wrapper class |
| `__manifest__.py` | Registered 3 new static assets in `web.assets_backend` |

### Known gaps / future sprint candidates
- Stat panel KPIs are global — do not react to active kanban filters. Needs `useSubEnv` + search model listener to update on filter change.
- Filter chip → search model bridge assumes filter `name` attributes match exactly in the CRM search view XML. Verify chip names match `<filter name="...">` in `crm_dashboard.xml`.
- `<details>/<summary>` token section in form view: Odoo's OWL renderer passes it through as HTML, but this should be verified on a lead that has a real `trial_booking_token`.
- Lead card information density (program interest, trial date chip, stage age badge) was deferred — cards still show stock Odoo layout.

**Progress:** `[x]` Done — 2026-04-26

---

## Sprint 2 — automation_oca ✓

**Goal:** Automation rules scannable at a glance — state, trigger type, and recent activity visible without opening a form.
**Audience:** `ADMIN` · **Facing:** Internal · **Tech:** `OWL` + `XML inherits` + `SCSS` · **Module:** `dojo_automation` (new)

### What was built

#### New module: `dojo_automation`
Pure frontend overlay (no Python models) over the third-party `automation_oca`. Branding rule: every user-visible string uses "Dojang" prefix. Module directory is `dojo_automation` but the app is labelled "Dojang Automation" and the menu is "Dojang Rules".

#### Stat panel + filter chips
- `AutomationStatPanel` OWL component — 4 live KPI chips: **Active Rules** (info/blue), **Triggered Today** (success/green), **Running Now** (warning/amber), **Errors (7 days)** (danger/red, tinted when > 0). Shimmer skeleton while loading.
- `AutomationFilterChips` OWL component — 6 chips: All · Active · Periodic · On Demand · Draft · Done. Bridges to Odoo search model via `sm.toggleSearchItem`. Filter names match `<filter name="...">` in `automation_configuration_search_view`: `run`, `draft`, `done`.
- Both components injected by mutating `AutomationKanbanController.template` + `.components` with a module-specific `primary` template (`dojo_automation.AutomationKanbanView`).

#### Kanban card redesign
- State-colored left border: periodic=`--info` (blue), ondemand=`--warning` (amber), done=`--success` (green), draft=`--text-muted` (grey)
- Header: rule name + state badge; meta row: model name + Periodic/On Demand chip
- Stats row: mail count · action count · click count + next run time for periodic rules
- Hover: card lifts 2px + action row fades in (Run Now conditional on `periodic|ondemand`, Edit always)
- **Entrance animation:** staggered `translateY(8px) → 0` + `opacity 0 → 1` (50ms × card index, capped at 300ms)
- **Periodic pulse:** `@keyframes dojo-auto-pulse-border` — breathing blue glow on left border at 2s interval, periodic cards only

#### Form accordions
- **Trigger Setup** (`<details open="">`) — Is Periodic toggle, Model, Deduplicate by, Next Execution (read-only, only when periodic)
- **Conditions** (collapsed by default) — Filter selector + Save filter, Domain editor, Tags, Company (multi-company only)
- **Dojang Workflow Steps** — always visible, section title above the existing `automation_step_ids` kanban widget; no structural changes to the widget

#### Step card coloring
- CSS-only via `:has()` selectors targeting the icon classes rendered by `automation_oca`:
  - `.fa-envelope` → `--info` (blue) — mail steps
  - `.fa-clock-o` → `--success` (green) — activity steps
  - `.fa-cogs` → `--warning` (amber) — action steps
- Left border + icon tint per type; step hover: lift 2px
- Timing pill chip (rounded background) on delay values

### Files created
| File | Purpose |
|------|---------|
| `addons/dojo_automation/__init__.py` | Empty init |
| `addons/dojo_automation/__manifest__.py` | Module manifest; depends: `dojo_core`, `automation_oca` |
| `addons/dojo_automation/views/automation_views_inherit.xml` | Menu rebranding + kanban card override + form accordions |
| `addons/dojo_automation/static/src/js/automation_stat_panel.js` | OWL components + controller template/components mutation |
| `addons/dojo_automation/static/src/xml/automation_stat_panel.xml` | QWeb templates + `dojo_automation.AutomationKanbanView` primary template |
| `addons/dojo_automation/static/src/css/automation.scss` | All animations, step colors, card styles, shimmer, accordions |

### Known gaps / future sprint candidates
- Stat panel KPIs are global — do not react to active kanban filters. Would need search model listener.
- Step cards: plain-English timing summary ("Send email after 2 days") was partially implemented via existing `step_name` field display but not fully customized.
- Error state step styling (`--danger` left border + "!" overlay) is present in SCSS but requires a rule with `state='error'` steps to visually verify.
- `:has()` CSS is supported Chrome 105+, Firefox 121+, Safari 15.4+ — note in browser requirements.

### Done criteria
- [x] Stat panel shows 4 live KPI chips with shimmer skeleton
- [x] Filter chips functional — bridge to existing search filters
- [x] Rule cards show: name, model, state badge, stats row, contextual actions on hover
- [x] Active/inactive state is visually prominent (color + badge label, not a buried checkbox)
- [x] Periodic state cards have a pulse glow on their left-border
- [x] Card entrance animation: staggered slide-up + fade-in
- [x] Form uses accordion sections — Trigger Setup (open) + Conditions (collapsed) + Workflow Steps
- [x] Step cards colored by type (mail/action/activity)
- [x] All UI strings use "Dojang" branding — no raw OCA/model names visible
- [x] No hardcoded hex values — all colors use MuK/Bootstrap design tokens

**Progress:** `[x]` Done — 2026-04-26

---

## Sprint 3 — dojo_marketing

**Goal:** The marketing card builder should feel like a mini content studio — not a backend form.
**Audience:** `ADMIN` · **Facing:** Internal (builder) + External (portal banner) · **Tech:** `QWEB` `SCSS`

### Current state
- Standard list/form backend views for marketing card records
- Portal banner injected but visual polish may be lacking
- No visual preview of the card while editing

### Target state
- Stat panel: Total cards · Active cards · Cards on kiosk · Portal banners live
- Card grid: each marketing card shown as a visual preview thumbnail (not a list row)
- Card form: live preview panel side-by-side with the fields
- Portal banner: positioned below hero, with a visible dismiss action

### UI patterns to use
- Stat Panel (top) + Entity Card grid (card thumbnails)
- Progressive disclosure: QR code settings and scheduling in an accordion
- Contextual actions: "Push to kiosk" and "Add to portal" only appear on published cards

### Files to touch
- `addons/dojo_marketing/views/dojo_marketing_card_views.xml`
- `addons/dojo_marketing/views/portal_marketing_banner.xml`
- `addons/dojo_marketing/static/src/dojo_marketing.css`

### Known issues / areas to review
> Confirm what fields the card record has (image, title, QR code, schedule dates).
> Check banner placement in portal — does it currently overlap primary content?

### Done criteria
- [ ] Card list renders as a visual thumbnail grid — not a plain list
- [ ] Card form has a live preview panel showing the rendered card
- [ ] Portal banner is positioned below the hero section, not overlapping content
- [ ] Banner has a visible dismiss/close action
- [ ] Empty state on card grid is a clear "Create first card" CTA

**Progress:** `[ ]` Not started

---

## Sprint 4 — ai_assistant

**Goal:** The AI assistant should feel like a polished voice-first interface — not a developer widget.
**Audience:** `ADMIN` `INSTRUCTOR` · **Facing:** Internal · **Tech:** `OWL` `SCSS`

> **Note:** Only polish production modes: `walkie_talkie`, `discuss_ai_panel`,
> `dojo_voice_assistant_page`. Do NOT touch `walkie_channel` or `walkie_elder` — they are
> prototypes.

### Current state
- Walkie-talkie widget, discuss panel, and full-page voice UI all exist
- Recording state indicator may rely on color change alone
- Transcript display may not auto-scroll to the latest entry
- Backend config form exposes raw API field names

### Target state
- Walkie-talkie: pulsing animated ring while recording (not just a color change)
- Discuss panel: chat-bubble layout (user right, AI left) with relative timestamps
- Full-page voice UI: large centered mic button, transcript scrolls below, action chips above
- Backend config: provider selector prominent at top, API keys in "Advanced" accordion
- Conversation history: card grid with last message preview + timestamp

### UI patterns to use
- Entity Cards for conversation history list
- Stat Panel on the config overview page (conversations today, avg response time, active sessions)
- Full-page voice UI uses its own centered layout — does not follow standard patterns

### Files to touch
- `addons/ai_assistant/static/src/xml/walkie_talkie.xml`
- `addons/ai_assistant/static/src/css/walkie_talkie.css`
- `addons/ai_assistant/static/src/xml/discuss_ai_panel.xml`
- `addons/ai_assistant/static/src/css/discuss_ai_panel.css`
- `addons/ai_assistant/static/src/xml/dojo_voice_assistant_page.xml`
- `addons/ai_assistant/static/src/css/dojo_voice_assistant_page.css`
- `addons/ai_assistant/views/ai_assistant_views.xml`

### Known issues / areas to review
> Check recording active state — pulsing mic vs color change only.
> Verify transcript auto-scroll behavior.
> Review confirm/cancel button placement and size.
> Check discuss panel against MuK theme sidebar colors.

### Done criteria
- [ ] Recording state has an animated pulsing ring — not just a color change
- [ ] Transcript uses chat-bubble layout with auto-scroll to latest entry
- [ ] Confirm/cancel actions are large and clearly separated — not adjacent small buttons
- [ ] Discuss panel respects MuK theme sidebar colors and padding
- [ ] Config form groups API keys behind "Advanced" accordion
- [ ] Conversation history is a card grid with preview text — not a plain list

**Progress:** `[ ]` Not started

---

## Sprint 5 — dojo_social

**Goal:** Social media management should feel like a lightweight post scheduler — not a data entry module.
**Audience:** `ADMIN` · **Facing:** Internal · **Tech:** `XML-ONLY`

### Current state
- Standard list/form views for posts and social account config
- Post status is likely a plain field value with no visual differentiation

### Target state
- Stat panel: Posts this month · Scheduled · Published · Failed
- Post card grid: thumbnail (if media attached) + platform icons + scheduled date + status badge
- Compose form: character counter per platform, scheduled time prominent, image preview
- Quick filters: `All · Draft · Scheduled · Published · Failed`

### UI patterns to use
- Stat Panel (top) + Entity Card grid (posts)
- Contextual actions: "Reschedule" only on scheduled posts, "Retry" only on failed posts

### Files to touch
- `addons/dojo_social/views/dojo_social_post_views.xml`
- `addons/dojo_social/views/dojo_social_account_views.xml`

### Known issues / areas to review
> Confirm what media/image field is available on the post model.
> Check scheduled date/time field — is it using 12-hour time per dojo convention?
> Verify what platform types are supported (Facebook / Instagram only?).

### Done criteria
- [ ] Post list renders as a card grid with image thumbnail where available
- [ ] Status badges: Draft (grey) / Scheduled (blue) / Published (green) / Failed (red)
- [ ] Failed posts have a visible "Retry" contextual action button
- [ ] Compose form shows per-platform character count
- [ ] Scheduled date/time field is prominent and uses 12-hour format
- [ ] Quick filter chips are functional above the post grid
- [ ] Stat panel shows 4 KPIs

**Progress:** `[ ]` Not started

---

## Sprint 6 — connect + dojo_connect_ai

**Goal:** The phone system and AI receptionist should feel like a modern comms dashboard — not a telephony admin panel.
**Audience:** `ADMIN` · **Facing:** Internal · **Tech:** `OWL` (connect) + `XML-ONLY` (dojo_connect_ai inherits)

> **Important:** Do NOT edit `connect` source files directly. All changes go through
> `dojo_connect_ai` view inherits only.

### Current state
- Third-party `connect` module provides base call log and phone number views
- `dojo_connect_ai` adds AI agent config and transcript display via inherits
- Transcript display may be raw or hard to read inline

### Target state
- Stat panel: Calls today · AI-handled · Leads generated · Avg call duration
- Call log: timeline-style entries with outcome badges (Answered / Voicemail / Missed / Error)
- AI transcript collapsed by default per call entry, expands inline on click
- AI agent config: plain English labels (not API field names), advanced settings in accordion
- Phone number routing: readable flow summary (number → AI agent → fallback)

### UI patterns to use
- Stat Panel (top) + Activity Timeline (call log)
- Progressive disclosure: transcript collapsed by default, expands inline
- Contextual action: "View CRM lead" button only on calls that generated a lead

### Files to touch
- `addons/dojo_connect_ai/views/connect_ai_agent_views.xml`
- `addons/dojo_connect_ai/views/connect_call_views.xml`
- `addons/dojo_connect_ai/views/connect_number_views.xml`

### Known issues / areas to review
> Review existing call log view — is transcript currently a raw JSON field or formatted text?
> Check AI agent config field labels — are they human-readable or raw API names?
> Verify what fields are available for the stat panel (calls today, AI-handled flag, lead link).

### Done criteria
- [ ] Call log shows outcome badge + AI-handled indicator per entry
- [ ] AI transcript is collapsed by default and expands inline (not a popup or navigation)
- [ ] AI agent config uses plain English labels throughout
- [ ] Stat panel shows 4 KPIs
- [ ] Phone number routing config has a readable flow summary, not just a field list

**Progress:** `[ ]` Not started

---

## Sprint 7 — dojo_core (Admin Home — optimization)

**Goal:** The admin dashboard is mostly done. Align it with the Design Language tokens and fix the remaining rough edges.
**Audience:** `ADMIN` `INSTRUCTOR` · **Facing:** Internal · **Tech:** `OWL` `XML-ONLY`

### Current state
- Admin dashboard OWL component exists with KPI chips and charts
- Instructor dashboard exists separately
- Belt rank list shows hex codes, not visual swatches
- Member form tab order may not be logical

### Target state
- KPI chips match the Stat Panel pattern from the Design Language section above
- Color tokens and spacing consistent with sprints 1–6
- Belt rank list shows a color swatch alongside the name
- Member form tabs in logical order

### UI patterns to use
- Stat Panel conventions applied to existing KPI chips
- No new patterns needed — this is an alignment sprint

### Files to touch
- `addons/dojo_core/static/src/xml/admin_dashboard.xml`
- `addons/dojo_core/static/src/xml/instructor_dashboard.xml`
- `addons/dojo_core/static/src/css/instructor_dashboard.css`
- `addons/dojo_core/views/member_views.xml`
- `addons/dojo_core/views/belt_views.xml`

### Done criteria
- [ ] KPI chips use Design Language token names (not one-off color values)
- [ ] Belt rank list shows a visual color swatch alongside the rank name
- [ ] Member form tabs ordered: Core info → Enrollment → Belt → Billing → Emergency
- [ ] Admin dashboard zero-data state (fresh install) renders gracefully — no blank areas
- [ ] Instructor dashboard mini-calendar prev/next tap targets >= 44px

**Progress:** `[ ]` Not started

---

## Sprint 8 — dojo_onboarding

**Goal:** Onboarding a new member should feel guided and calm — like a modern SaaS setup wizard.
**Audience:** `ADMIN` `INSTRUCTOR` · **Facing:** Internal · **Tech:** `XML-ONLY` + `OWL` (Stripe step)

### Current state
- Multi-step XML wizard (dialog-based)
- Steps may require scrolling within a single dialog
- Progress indicator may be minimal or absent
- Stripe step may not visually match the rest of the wizard

### Target state
- Step header: "Step 2 of 6 — Enrollment" — always visible at top of dialog
- Each step fits within dialog height — no internal scroll at 768px+
- Fields grouped with labeled section dividers, required fields consistently marked
- Stripe step visually consistent with the rest of the wizard
- Final step: warm success summary ("Welcome to the dojo! Here's what's next.")

### UI patterns to use
- Wizard with progressive disclosure per step
- Form field grouping conventions from the Design Language section

### Files to touch
- `addons/dojo_onboarding/views/dojo_onboarding_wizard_views.xml`
- `addons/dojo_onboarding/views/dojo_onboarding_views.xml`
- `addons/dojo_onboarding_stripe/views/dojo_onboarding_wizard_stripe_inherit.xml`
- `addons/dojo_onboarding_stripe/static/src/xml/onboarding_stripe_payment.xml`

### Known issues / areas to review
> Count the current number of wizard steps — confirm the step numbering.
> Check if any step currently requires internal scroll at 768px.
> Review Stripe step styling vs the rest of the wizard.

### Done criteria
- [ ] Step header shows "Step N of N — Step Name" at all times
- [ ] No wizard step requires internal scroll at 768px+ viewport
- [ ] Stripe step matches the wizard's visual style (fonts, spacing, button style)
- [ ] Back navigation preserves form state on each step
- [ ] Final success step has warm copy and a summary of what was just created

**Progress:** `[ ]` Not started

---

## Sprint 9 — dojo_members_portal

**Goal:** The member portal should feel like a mobile app — not a generic Odoo portal.
**Audience:** `MEMBER` · **Facing:** External · **Tech:** `QWEB` `SCSS`

### Current state
- QWeb portal pages at `/my/dojo/*`
- May not be fully optimized for 375px mobile
- Navigation may rely on top tabs (awkward on mobile)

### Target state
- Welcome hero card: avatar + belt badge + member name, fits above fold at 375px
- Schedule page: card per session — class name, date/time, instructor, status
- Billing page: invoice status badges with color + text label, PDF link obvious
- Bottom navigation for mobile (not top tabs)
- Push notification opt-in after a user gesture — never on page load

### UI patterns to use
- Entity Cards for sessions and invoices
- Mobile-first layout with bottom nav bar on screens below 768px

### Files to touch
- `addons/dojo_members_portal/views/portal_layout.xml`
- `addons/dojo_members_portal/static/src/css/dojo_portal.css`
- `addons/dojo_members_portal/static/src/js/dojo_portal.js`

### Known issues / areas to review
> Check current navigation structure — top tabs or sidebar?
> Check hero card height at 375px — does it exceed the fold?
> Verify push notification prompt timing (currently fires on page load?).

### Done criteria
- [ ] All portal pages usable at 375px without horizontal scroll
- [ ] Hero card does not exceed viewport fold at 375px
- [ ] Invoice badges: color + text label — never color alone
- [ ] Schedule cards show: class name, date/time, instructor, full/available status
- [ ] Push permission prompt does NOT fire automatically on page load
- [ ] Touch targets >= 44px throughout

**Progress:** `[ ]` Not started

---

## Sprint 10 — dojo_kiosk (optimization)

**Goal:** Kiosk is largely done. Ensure it's consistent with the Design Language and handles edge cases gracefully.
**Audience:** `MEMBER` (kiosk) `INSTRUCTOR` `ADMIN` (admin panel) · **Facing:** External/Internal · **Tech:** `OWL` CSS

> **Note:** OWL templates for the kiosk SPA are inline `` xml`...` `` tagged template literals
> inside `kiosk_app.js` — not a separate `.xml` file. Edit those blocks directly.

### Current state
- OWL SPA with member roster tiles and check-in flow — largely functional
- Potential inconsistencies in avatar fallback and error states

### Target state
- Roster tiles consistent with Entity Card token conventions at tablet scale
- Avatar fallback (initials circle) uses belt-color background with AA-compliant contrast text
- Check-in success animation is satisfying and auto-dismisses in 2–3 seconds
- All error states show friendly staff-facing messages — not raw JS errors

### Files to touch
- `addons/dojo_kiosk/static/src/kiosk_app.js` (inline OWL templates)
- `addons/dojo_kiosk/static/src/kiosk.css`

### Done criteria
- [ ] All touch targets >= 48px (gym use — members often in a hurry)
- [ ] Avatar fallback has belt-color background with WCAG AA contrast text
- [ ] Check-in success auto-dismisses with animation in 2–3 seconds
- [ ] Network error state shows "Please contact staff" — not a console error or blank screen
- [ ] Token-expired state shows "Please contact staff" with a clear visual indicator
- [ ] Roster grid fills the screen at both 768px and 1024px tablet widths

**Progress:** `[ ]` Not started

---

## Backlog

These modules are preserved but deprioritized. Do not start them until all 10 sprints above are
marked `[x]`.

| Module | Why deferred |
|--------|-------------|
| `dojo_checkout` | Public signup flow — high impact but deserves a dedicated session |
| `dojo_subscriptions` | Admin plan management — functional, low visual debt |
| `dojo_credits` | Low-frequency admin tool |
| `dojo_points` | Gamification polish — nice to have |
| `dojo_stripe` | Stripe Elements handles most styling natively |
| `dojo_sign` | Embedded in the onboarding wizard — revisit after Sprint 8 |
| `dojo_communications` | SMS/email send wizard — functional |
| `dojo_website` | Public website — separate project scope |
| `dojo_firebase` | Push notification plumbing — one checklist item |
| `elevenlabs_connector` | Underlying AI widget — polished through Sprint 4 |
| `dojo_migration` | One-time import tool — no UI polish needed |
| `dojo_calendar` | Odoo native calendar — minimal customization |
| `dojo_events` | Thin module — one inherited view |
| `subscription_oca` | Third-party — read-only reference only |
| `dojo_ai_caller` | AI outbound campaigns — revisit after Sprint 6 |

---

## Global UI/UX Rules

Apply to every sprint. These are not repeated in individual sections.

- No hardcoded pixel font sizes — use MuK/Bootstrap design tokens or `fs-*` utilities
- All interactive elements have visible `:focus-visible` outlines (WCAG 2.1 AA)
- Touch targets: 44×44px minimum (48px on kiosk)
- Color is never the sole indicator of state — always pair with an icon or text label
- Skeleton shimmer for async card grid loads — never a centered spinner
- Empty states: friendly message + CTA — never a blank area or "No records found"
- Responsive breakpoints: 375px (mobile portal) · 768px (tablet/kiosk) · 1280px (admin)
- No inline `style=""` attributes — use semantic CSS class names
- MuK theme color variables used throughout — never hardcode hex values
- Never modify `muk_web_*` source files — override from your own module only

---

## Appendix A — OWL Component Edit Pattern

1. Find the `.xml` template file (e.g., `static/src/xml/foo.xml`)
2. Read the matching `.js` file first — understand `useState`, `useRef`, event handlers before touching markup
3. **Kiosk SPA only:** templates are inline `` xml`...` `` tagged template literals inside
   `kiosk_app.js` — edit those blocks directly (there is no separate `.xml` file)
4. CSS lives in `static/src/css/` — create a new file and register in `__manifest__.py` if missing
5. Restart assets after changes: `-u module_name` in the Odoo CLI

---

## Appendix B — CSS / SCSS Conventions

- Class prefix: `dojo-` for portal/website/public-facing components
- Follow existing naming conventions visible in each OWL template for backend components
- Check `muk_web_theme` SCSS variables before defining any new color — use theme tokens
- No `!important` unless overriding a third-party rule — always add a comment explaining why
- No inline `style=""` attributes — move all styles to a CSS file with a semantic class name

---

## Appendix C — Session Handoff Checklist

At the end of each working session:
1. Update status markers in the Sprint Order table (`[ ]` → `[~]` → `[x]`)
2. Add discovered issues under "Known issues" for any sprint worked this session
3. Note any new files discovered that are not listed in "Files to touch"
4. Note cross-sprint dependencies (e.g., "Design Language token changes affect all sprints — update tokens first")

---

## Changelog

### Sprint 1 — dojo_crm (2026-04-26)

#### What was added

**Kanban pipeline (`crm_stat_panel.js`, `crm_stat_panel.xml`, `crm_pipeline.scss`)**
- `CrmStatPanel` OWL component — 4 live KPI chips above the kanban board (Total Leads, Conversion Rate, Trials This Week, Expiring Offers) with shimmer skeleton loading state
- `CrmFilterChips` OWL component — 5 one-click filter chips (High Score, Trial Attended, No-Show, Converted, Has Booking) that bridge to Odoo's search model
- Both components injected via `t-inherit="web.KanbanView"` template extension and registered on `crmKanbanView.Controller.components`
- Kanban card hover lift, sticky column headers, pill-shaped status badges

**Lead form (`crm_lead_view_inherit.xml`)**
- Score block: bold score number + Hot/Warm/Cold contextual label + progress bar in one row
- Status strip: Attended / No-Show / Converted / Waiver Signed badges visible without opening any tab
- Consolidated 3 custom tabs → 2: "Trial Journey" and "Engagement & AI"
- Token fields collapsed under a native `<details>` toggle (hidden until token exists)
- Header decluttered: "Book Trial" is secondary weight and hides once trial attended; "Convert to Member" (primary) only shows after `trial_attended = True`

#### What went wrong and how to avoid it next sprint

| Problem | Root cause | Prevention |
|---------|-----------|------------|
| `Missing parent template: web.KanbanController` | Template name changed in Odoo saas-19.2 — correct name is `web.KanbanView`, not `web.KanbanController` | Before writing any `t-inherit`, read the actual Odoo source template file to confirm the name. Check `odoo/addons/<module>/static/src/views/` first. |
| `Cannot find component 'CrmStatPanel'` (attempt 1) | Assigned to `KanbanController.components` directly — mutations to a parent class don't propagate to subclasses whose `static components` snapshot was already taken | For any view that overrides a base controller (CRM, inventory, etc.), import the specific view object and assign to its Controller directly, not to the base class. |
| `Cannot find component 'CrmStatPanel'` (attempt 2) | CRM uses its own anonymous Controller class in `crm_kanban_view.js` with a separate `static components` snapshot | Always read `<module>_kanban_view.js` to check if a custom Controller class is defined. If it is, import that view and mutate its Controller, not the Odoo base. |
| Module upgrade run from wrong directory | `docker compose` found no `docker-compose.yml` — path was not set | Always `Set-Location` to the project root (`dojo-odoo19/`) before running Docker commands, or use the PowerShell tool which inherits the working directory. Use `MSYS_NO_PATHCONV=1` in Git Bash only; PowerShell needs no prefix. |
| Git Bash path conversion on `--config` flag | Bash converts `/etc/odoo/odoo.conf` to a Windows path | Use the PowerShell tool for all Docker commands. Bash tool on Windows mangles Unix paths. |

---

### Sprint 2 — dojo_automation (2026-04-26)

#### What was added

**New module: `dojo_automation`**
- Standalone UI overlay module; depends on `dojo_core` + `automation_oca`; no Python models
- Menu labels rebranded to "Dojang Automation" / "Dojang Rules" via `ir.ui.menu` record overrides

**Kanban + stat panel (`automation_stat_panel.js`, `automation_stat_panel.xml`, `automation.scss`)**
- `AutomationStatPanel` OWL component — 4 live KPI chips (Active Rules, Triggered Today, Running Now, Errors 7 days); shimmer skeleton; errors chip tints danger when > 0
- `AutomationFilterChips` OWL component — All · Active · Periodic · On Demand · Draft · Done; bridges to `automation_configuration_search_view` filters (`run`, `draft`, `done`)
- Both injected via `AutomationKanbanController.template = "dojo_automation.AutomationKanbanView"` and `.components` mutation
- Kanban card: state-colored left border (periodic=blue pulse, ondemand=amber, done=green, draft=grey); stats row; hover-revealed action row; staggered entrance animation

**Form (`automation_views_inherit.xml`)**
- Replaced flat `<sheet><group>` with two `<details>` accordions: Trigger Setup (open by default) + Conditions (collapsed)
- "Dojang Workflow Steps" section title above the step kanban widget

**Step card coloring (`automation.scss`)**
- CSS-only `:has()` targeting icon classes from `automation_oca`: `.fa-envelope` (info/blue), `.fa-clock-o` (success/green), `.fa-cogs` (warning/amber)
- Timing values rendered as pill chips; step hover lift

#### What went wrong and how to avoid it next sprint

| Problem | Root cause | Prevention |
|---------|-----------|------------|
| `Forbidden owl directive used in arch (t-esc)` | Odoo 19 disallows `t-esc` inside view arch XML (`<field name="arch">` blocks) | Use `t-out` everywhere inside `arch` XML. `t-esc` is only allowed in OWL component templates (`.xml` assets), not in server-side view definitions. |
| `Cannot find component "AutomationStatPanel"` after both modules installed | Sprint 1 used `t-inherit="web.KanbanView" t-inherit-mode="extension"` — `extension` mutates the parent regardless of `t-name`. When two modules both inject via `extension`, every kanban tries to find components from both modules and fails. | Use `t-inherit-mode="primary"` for module-specific templates. `primary` creates a true independent copy. `extension` always mutates the parent. |
| `Cannot find key "dojo_automation_kanban" in the "views" registry` | Tried to use `js_class` xpath + `registry.category("views").add(...)`. The JS file's `registry.add` call must complete before the view loads — timing not guaranteed. | Do NOT use `js_class` + views registry for stat panel injection. Instead, mutate `controller.template` and `controller.components` directly — same approach as Sprint 1's component mutation, just also changing `.template`. |
| `js_class` is not a field on `ir.ui.view` | Attempted `<field name="js_class">value</field>` in a data record — `ir.ui.view` has no such field | `js_class` is an attribute on the view arch root element (e.g., `<kanban js_class="...">`). Set it via xpath: `<xpath expr="//kanban" position="attributes"><attribute name="js_class">...</attribute></xpath>`. |
| `<a>` tag with `btn` class must have `role="button"` | Odoo 19 OWL accessibility validator enforces `role="button"` on anchor elements styled as buttons | Always add `role="button"` to `<a class="btn ...">` elements inside view arch XML. |

---

### Cross-Sprint Lessons Learned (Sprints 1–2)

#### The canonical OWL kanban stat panel pattern

After three iterations across two sprints, the correct, stable pattern for injecting module-specific components above a kanban renderer is:

**Step 1 — XML (`static/src/xml/`):** Create a named `primary` template — an independent copy of `web.KanbanView` with your components injected:
```xml
<t t-name="my_module.MyKanbanView"
   t-inherit="web.KanbanView"
   t-inherit-mode="primary">
    <xpath expr="//t[@t-component='props.Renderer']" position="before">
        <MyStatPanel/>
        <MyFilterChips/>
    </xpath>
</t>
```

**Step 2 — JS (`static/src/js/`):** Mutate the specific controller's `.template` and `.components`:
```javascript
import { targetKanbanView } from "@some_module/views/kanban/kanban_view";

// Point the controller at your isolated template
targetKanbanView.Controller.template = "my_module.MyKanbanView";
// Register your components on that controller
targetKanbanView.Controller.components = {
    ...targetKanbanView.Controller.components,
    MyStatPanel,
    MyFilterChips,
};
```

**Why `primary` not `extension`:** `extension` always patches the parent (`web.KanbanView`) in-place, even when `t-name` is provided. This means every kanban in the entire app inherits the injection, and any controller that doesn't own those components crashes. `primary` creates a completely independent template — the parent stays clean.

**Why direct mutation not `js_class` + registry:** Setting `js_class` via xpath writes to the database record. The browser then looks for the named view type in the JS `views` registry. If the JS file that calls `registry.add(...)` hasn't finished executing when the view loads, Odoo throws `Cannot find key`. Direct template mutation is synchronous and avoids the timing race.

**Reference files:** `dojo_crm/static/src/js/crm_stat_panel.js` · `dojo_automation/static/src/js/automation_stat_panel.js`

#### Architecture decisions that held

- `<details>/<summary>` accordions work in Odoo's OWL renderer without JS — confirmed in both sprints
- CSS `:has()` for contextual styling (Sprint 2 step card colors) works in all modern browsers (Chrome 105+, FF 121+, Safari 15.4+)
- BEM naming with module-scoped prefix (`.dojo-crm-*`, `.dojo-auto-*`) cleanly prevents style leakage between modules
- Reading the source JS class before any `t-inherit` or component mutation prevents the entire class of "wrong target" errors

#### What to do differently in future sprints

1. **Read the controller source first** before writing any kanban injection — confirm which class the view uses and what its `static components` snapshot contains
2. **Use `t-out` inside arch XML, `t-esc` only in OWL templates** — they are different contexts
3. **Use PowerShell for all Docker commands** — Git Bash mangles Unix paths on Windows
4. **Verify fields exist in the model** before referencing them in arch XML — `automation.record.step.state` was confirmed, `is_periodic` on `automation.configuration` was confirmed; these checks saved broken view errors
5. **Test with multiple dojo modules installed simultaneously** — issues that only appear from module interaction (the `web.KanbanView` mutation crash) only surface after step 5, not after step 1
