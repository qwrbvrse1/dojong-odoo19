# Admin Dashboard UI/UX Redesign — Design Spec
**Date:** 2026-03-27
**Module:** `dojo_instructor_dashboard`
**Files in scope:** `static/src/xml/admin_dashboard.xml`, `static/src/css/instructor_dashboard.css`
**Files NOT in scope:** `admin_dashboard.js` (logic untouched), Python models, instructor dashboard template

---

## Goals

Modernise the admin dashboard OWL template and CSS to match a "Dojang Admin" design language inspired by a Google Stitch/Material You concept — warm cream palette, bold red primary, heavy typography, clean cards with ghost watermarks, circular command-center buttons.

## Constraints

1. No changes to functional JS logic (data loading, navigation, formatters)
2. OWL/QWeb templates + CSS only
3. No changes to global/default Odoo UI or MuK theme modules
4. No blank icons — all FA icons replaced with appropriate Material Symbols
5. JS edits limited to UI/UX animations (none needed for this spec — all hover effects are pure CSS)

---

## Design Decisions

| Topic | Decision |
|---|---|
| Icons | Material Symbols Outlined, loaded via `@import` in CSS |
| Font | Inherited from MuK theme (no Google Fonts import) |
| Background | Warm neutral only on cards/containers — not the full Odoo chrome |
| Stat chips | Uniform white cards with 3px colored left-border accents |
| Animations | Hover-only — no load/entrance animations |
| Approach | Full CSS rewrite scoped to admin-specific classes; instructor dashboard CSS untouched |

---

## Color Palette

| Token | Value | Usage |
|---|---|---|
| `--ad-primary` | `#b41e16` | Buttons, accents, icon fills |
| `--ad-primary-light` | `rgba(180,30,22,0.08)` | Icon box bg, card hover tint |
| `--ad-surface` | `#fcf8f8` | Card body background |
| `--ad-surface-low` | `#f6f3f2` | Page root bg, Recent Sessions card |
| `--ad-surface-high` | `#ebe7e7` | Hover state for buttons/chips |
| `--ad-on-surface` | `#1c1b1b` | Primary text |
| `--ad-secondary` | `#5f5e5e` | Secondary/muted text |
| `--ad-border` | `rgba(227,190,184,0.35)` | Card and chip borders |
| `--ad-shadow` | `0 8px 32px rgba(28,27,27,0.04)` | Card tonal elevation |

Semantic left-border accents on stat chips:
- Indigo `#7c3aed` — Instructors
- Green `#1e8e3e` — Active Students, New Members
- Blue `#1a73e8` — Sessions Today
- Orange `#f57c00` — Avg Fill Rate
- Purple `#9c27b0` — Attendance Rate
- Red `#b41e16` — Dropped Enrollments
- Teal `#00796b` — Revenue Month, Revenue YTD
- Amber `#f59e0b` — Outstanding Balance

---

## Section Specs

### 1. CSS Architecture

- `@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200')` at top of CSS file
- All new admin-specific rules prefixed `.o_ad_` (already partially done in current file)
- Existing `.o_di_*` rules for the instructor dashboard are **not touched**
- CSS variables declared on `.o_di_root` (scoped, not global)

### 2. Page Header

**XML changes:**
- Header icon: `<span class="material-symbols-outlined">dashboard</span>` inside `.o_di_header_icon`; icon box loses solid color, gains `--ad-primary-light` bg + `--ad-primary` icon color
- Header title: unchanged text, new class `.o_ad_header_title`
- Header date: unchanged logic (`todayLabel`), new class `.o_ad_header_date` — adds `ELITE MANAGEMENT MODE` suffix or keeps existing date format in uppercase
- Action buttons: class changes from `.o_di_hdr_btn` to `.o_ad_hdr_btn` — rectangular rounded-md, surface-low bg, warm border
- Refresh button icon: `<span class="material-symbols-outlined">refresh</span>`; CSS adds `transition: transform 0.5s` + `.o_ad_hdr_btn:hover .material-symbols-outlined { transform: rotate(180deg) }` scoped to the refresh button

**CSS:**
```
.o_ad_header_title   { font-size: 1.5rem; font-weight: 900; letter-spacing: -0.02em; color: #1c1b1b }
.o_ad_header_date    { font-size: 0.7rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.12em; color: #5f5e5e; margin-top: 3px }
.o_ad_hdr_btn        { border-radius: 6px; border: 1px solid rgba(227,190,184,0.4); background: #f6f3f2; font-weight: 600; font-size: 0.8rem; … }
.o_ad_hdr_btn:hover  { background: #ebe7e7 }
```

### 3. KPI Stat Grid

**XML changes:**
- `.o_di_stat_row` → `.o_ad_stat_row`
- Each chip: `.o_di_stat_chip o_di_stat_*` → `.o_ad_stat_chip o_ad_stat_<color>` (color only drives the left-border)
- Value div: `.o_di_stat_value` → `.o_ad_stat_value`
- Label div: `.o_di_stat_label` → `.o_ad_stat_label`
- Sub div: `.o_di_stat_sub` → `.o_ad_stat_sub`

**CSS:**
```
.o_ad_stat_row       { display: grid; grid-template-columns: repeat(10,1fr); gap: 12px; padding: 20px 28px }
.o_ad_stat_chip      { background: #fff; border: 1px solid rgba(227,190,184,0.3); border-radius: 8px; padding: 16px 12px; text-align: center; box-shadow: 0 2px 8px rgba(28,27,27,0.04); border-left: 3px solid <color> }
.o_ad_stat_value     { font-size: 1.5rem; font-weight: 800; color: #1c1b1b }
.o_ad_stat_label     { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; color: #5f5e5e; margin-top: 4px }
.o_ad_stat_sub       { font-size: 9px; color: #8f706b; font-style: italic; margin-top: 2px }
.o_ad_stat_chip.is-clickable:hover { background: #f6f3f2; cursor: pointer }
```
Each `.o_ad_stat_<color>` sets `border-left-color` only.

### 4. Command Center

**XML changes:**
- Section label `<div>` gets class `.o_ad_section_label`
- Grid `<div>` gets class `.o_ad_quick_grid`
- Each `<button>` gets class `.o_ad_quick_item`
- Icon container `<div>` gets class `.o_ad_quick_icon`
- Label `<span>` gets class `.o_ad_quick_label`
- All FA icons replaced with Material Symbols:
  - `fa-user-plus` → `assignment_ind`
  - `fa-id-card-o` → `person_add`
  - `fa-trophy` → `military_tech`
  - `fa-credit-card` → `subscriptions`
  - `fa-envelope` → `send`
  - `fa-file-text-o` → `receipt_long`
  - `fa-calendar-check-o` → `history_edu`
  - `fa-calendar` → `calendar_month`

**CSS:**
```
.o_ad_section_label  { font-size: 11px; font-weight: 900; text-transform: uppercase; letter-spacing: 0.2em; color: #5f5e5e; padding: 0 28px; margin-bottom: 16px }
.o_ad_quick_grid     { display: grid; grid-template-columns: repeat(8,1fr); gap: 16px; padding: 0 28px 28px }
.o_ad_quick_item     { display: flex; flex-direction: column; align-items: center; gap: 10px; background: none; border: none; cursor: pointer }
.o_ad_quick_icon     { width: 64px; height: 64px; border-radius: 50%; background: #f1edec; display: flex; align-items: center; justify-content: center; color: #b41e16; transition: background 0.3s, color 0.3s; box-shadow: 0 4px 16px rgba(28,27,27,0.06) }
.o_ad_quick_icon .material-symbols-outlined { font-size: 26px }
.o_ad_quick_item:hover .o_ad_quick_icon  { background: #b41e16; color: #fff }
.o_ad_quick_label    { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; color: #5f5e5e; text-align: center; transition: color 0.2s }
.o_ad_quick_item:hover .o_ad_quick_label { color: #1c1b1b }
```

### 5. Content Cards

**XML changes:**
- Content grid `<div>` keeps `.o_di_content_grid .o_ad_content_grid` (already exists)
- Each card `<div>`: add `.o_ad_card` alongside or replace `.o_di_card`
- Card header/body/title/subtitle: add `.o_ad_*` variants
- "View All" buttons: add `.o_ad_view_btn`
- Empty state icons replaced with Material Symbols:
  - Instructor Performance empty: `analytics`
  - Dropped Enrollments empty: `person_off`
  - Recently Enrolled empty: `group`
  - Recent Sessions empty: `event`
- Ghost watermark: add `<div class="o_ad_watermark">STAFF</div>` inside Instructor Performance card, `<div class="o_ad_watermark">EXIT</div>` inside Dropped Enrollments card
- Recent Sessions card: add class `.o_ad_card_footer` for the alternate background

**CSS:**
```
.o_ad_card           { background: #fff; border-radius: 12px; border: 1px solid rgba(227,190,184,0.3); box-shadow: 0 8px 32px rgba(28,27,27,0.04); position: relative; overflow: hidden }
.o_ad_card_footer    { background: #f6f3f2 }
.o_ad_card_header    { padding: 24px 24px 0; display: flex; justify-content: space-between; align-items: flex-start }
.o_ad_card_title     { font-size: 1.1rem; font-weight: 800; letter-spacing: -0.01em; color: #1c1b1b }
.o_ad_card_subtitle  { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.12em; color: #5f5e5e; margin-top: 3px }
.o_ad_view_btn       { color: #b41e16; font-weight: 700; font-size: 11px; text-transform: uppercase; letter-spacing: 0.1em; background: none; border: none; cursor: pointer }
.o_ad_view_btn:hover { text-decoration: underline }
.o_ad_watermark      { position: absolute; bottom: 8px; right: 12px; font-size: 60px; font-weight: 900; color: #5f5e5e; opacity: 0.06; pointer-events: none; user-select: none; text-transform: uppercase; line-height: 1 }
.o_ad_empty          { display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 48px 0; opacity: 0.4 }
.o_ad_empty .material-symbols-outlined { font-size: 48px; color: #5f5e5e; margin-bottom: 8px }
.o_ad_empty p        { color: #5f5e5e; font-style: italic; font-size: 0.85rem }
```

Progress bars: `height: 4px; border-radius: 2px; background: #f1edec` with colored fill — keep existing color logic.

Table rows: `border-bottom: 1px solid #f6f3f2` (no outer border), header `font-size:10px uppercase tracking-wider color:#5f5e5e`.

---

## Files Changed

| File | Change type |
|---|---|
| `static/src/xml/admin_dashboard.xml` | Class renames, icon swap (FA → Material Symbols), watermark divs added |
| `static/src/css/instructor_dashboard.css` | Add Material Symbols `@import`; add all `.o_ad_*` rules; existing `.o_di_*` rules untouched |

## Files NOT Changed

- `static/src/js/admin_dashboard.js` — zero changes
- `static/src/js/instructor_dashboard.js` — zero changes
- `static/src/xml/instructor_dashboard.xml` — zero changes
- All Python models, views, manifests — zero changes
