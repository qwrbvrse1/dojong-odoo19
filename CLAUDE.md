# CLAUDE.md — Dojo Odoo19 Project

## Project Overview
Custom Odoo 19 implementation for a martial arts dojo client.
Migrating from SparkMembership to Odoo. UI should closely match SparkMembership's internal tool.

## Architecture Priority
**CRM-first:** All modules must connect through `crm.lead` as the central lifecycle hub.
Boss direction as of 2026-03 — scope decisions should favor CRM connectivity over other cleanup.

## Boss Context
Non-technical, gives vague requests. Ask "what would you do differently Monday morning?" to extract concrete scope.

## Active Workstreams (2026-03)
CRM connections build order: Connection 1 (public `/dojo/trial` page) → Connection 3 (subscription cancel/expire re-engagement lead) → Connection 2 (attendance check-in → auto-advance lead stage) → Connection 4 (onboarding wizard → auto-create/link CRM lead) → Connection 5 (belt promotion → CRM chatter note)
Kiosk pending: camera capture modal in instructor mode (photo upload to `res.partner.image_1920`)

## Stack
- Odoo 19 (Docker container: odoo-dojo:latest)
- PostgreSQL (Docker container: dojo-odoo19-db-1)
- Custom modules: all dojo_* folders
- Theme: muk_web_* modules (third-party Odoo theme framework)

## VM Commands (Production — GCP Instance)

```bash
# --- Service control ---
sudo systemctl restart odoo19          # restart after controller/Python changes
sudo systemctl stop odoo19
sudo systemctl start odoo19
systemctl is-active odoo19             # check it's running

# --- Logs ---
sudo journalctl -u odoo19 -f           # live tail
sudo journalctl -u odoo19 -n 100       # last 100 lines
sudo journalctl -u odoo19 --since "5 min ago" | grep -i error

# --- Upgrade a module (no restart needed for pure Python/XML changes) ---
sudo -u odoo19 /opt/odoo19/odoo19-venv/bin/python3 /opt/odoo19/odoo19/odoo-bin \
  -c /etc/odoo19.conf -d prod -u <module_name> --stop-after-init

# upgrade multiple modules
sudo -u odoo19 /opt/odoo19/odoo19-venv/bin/python3 /opt/odoo19/odoo19/odoo-bin \
  -c /etc/odoo19.conf -d prod -u dojo_website,dojo_crm --stop-after-init

# upgrade all (slow — only when needed)
sudo -u odoo19 /opt/odoo19/odoo19-venv/bin/python3 /opt/odoo19/odoo19/odoo-bin \
  -c /etc/odoo19.conf -d prod -u all --stop-after-init

# --- After CSS/JS/QWeb changes (no upgrade needed) ---
sudo systemctl restart odoo19
# Then hard-refresh browser: Ctrl+Shift+R

# --- Key paths ---
# Config:        /etc/odoo19.conf
# Custom addons: /opt/odoo19/odoo19/custom-addons/
# Venv python:   /opt/odoo19/odoo19-venv/bin/python3
# Odoo binary:   /opt/odoo19/odoo19/odoo-bin
# DB:            prod  @  127.0.0.1:5432  (user: odoo19)
```

## Running Locally
```bash
cd dojo-odoo19
docker compose up --build -d
# Access at http://localhost:8069
# Login: admin / admin (for local)
```

## Active Branch
- Main development: `main` — push directly for fullstack work (tight schedule)
- UI-only work: `ui-change-only` — still available for isolated CSS/view changes; never touch models/migrations here

## Key Contacts
- Lead Dev: Calvin (CalvinDoesCS) — owns backend/models architecture
- Fullstack Dev: [your name] — AI assistant (`dojo_assistant`), social media (`dojo_social`), kiosk, and all fullstack features; pushes to `main`

## Rules for This Repo
- Always `git pull origin main` before starting a work session
- When on `ui-change-only`: views, SCSS, CSS, JS, and QWeb templates only — no model or migration edits
- When on `main`: coordinate with Calvin before touching core models (`dojo_base`, `dojo_subscriptions`, `dojo_classes`)
- Stage specific files — never `git add -A` (avoid accidentally committing .env or large binaries)

## Active Modules (Fullstack Owner)
### `dojo_core` — Unified App Entry Point
- `dojo_core/__manifest__.py` — `application=True`, depends on all 23 dojo_* modules
- `dojo_core/views/dojo_core_menus.xml` — unified menu tree (all features under one root)
- `dojo_core/views/dojo_core_settings.xml` — Dojo Integrations tile + full QA checklist in Settings
- Installed as **"Dojo Management"** in Odoo Apps
- **NOTE:** `dojo_instructor_dashboard` intentionally excluded from deps (has `project`/`account` dep chain that causes cascading install failures); its `dojo.instructor.profile` action is defined locally in `dojo_core_menus.xml`

### `dojo_assistant` — AI Voice/Text Assistant
- `dojo_assistant/models/ai_assistant_service.py` — core intent parsing + execution; compound chain logic
- `dojo_assistant/models/ai_processor_ext.py` — intent parser; supports `"intents"` array for compound commands
- `dojo_assistant/models/ai_intent_schema.py` — intent types + role-based permission matrix
- `dojo_assistant/models/ai_action_log.py` — audit trail; `parent_action_id` links compound step records to header
- `dojo_assistant/models/ai_undo_snapshot.py` — 60-min undo window
- `dojo_assistant/controllers/main.py` — HTTP endpoints
- `dojo_instructor_dashboard/static/src/js/voice_assistant.js` — renders compound step results in chat UI
- Surfaced in kiosk (`/kiosk/ai/text`, `/kiosk/ai/voice`) and instructor dashboard
- Settings: Settings → AI Assistant (confidence + logs)

**Compound command chaining (2026-03):**
- User can issue multi-step commands in one phrase: *"Look up Jordan and then show today's schedule"*
- `_is_compound_phrase()` detects "and then / then / and \<verb\>" patterns via `_COMPOUND_SIGNALS` regex (~line 40 of `ai_assistant_service.py`)
- Matched phrases route to JSON-mode parsing; LLM returns `{"intents": [...]}` array
- `handle_compound_command()` validates chain (max 5 steps, confidence ≥ 0.7, role permissions) and returns numbered confirmation
- `execute_confirmed()` detects `intent_type = "compound_chain"` → `_execute_compound_chain()` runs each step sequentially; failed step triggers best-effort snapshot rollback
- Step records linked to compound header via `parent_action_id` on `dojo.ai.action.log`

### `dojo_sign` — Member Waiver Signing (Calvin, 2026-03)
- Replaced Odoo Enterprise sign.request with Community-compatible inline signature
- `dojo_sign/models/dojo_member_waiver.py` — extends `dojo.member` with `waiver_signature` (Image), `waiver_signed_by`, `waiver_signed_at`; generates QWeb PDF attached to member record
- Captured via `widget="signature"` canvas in onboarding wizard step

### `dojo_instructor_dashboard` — Instructor Todos Automation (Calvin, 2026-03)
- `dojo_instructor_dashboard/models/dojo_instructor_todos.py` — auto-creates `project.task` records in "Instructor Alerts" project for 6 trigger points:
  1. New trial/onboarding member
  2. Member paused or cancelled
  3. Attendance milestone (10/25/50/100/200 classes)
  4. Attendance not marked after session ends
  5. Student inactivity (30-day daily cron)
  6. Belt test eligibility
- Tasks appear in instructor dashboard "My Todos" panel immediately

### `dojo_classes` — 12h Time Formatting Widget (Calvin, 2026-03)
- `dojo_classes/static/src/js/float_time_12h.js` + `float_time_12h.xml` — OWL field widget converting Odoo float time (0–24) to/from 12h AM/PM display
- Migration `19.0.1.3.0` added to `dojo_classes/migrations/`
- `dojo_classes/models/dojo_program.py` — new instructor management fields on Program

### `dojo_social` — Facebook/Instagram Posting
- `dojo_social/models/dojo_social_account.py` — OAuth account management (Page ID + access token)
- `dojo_social/models/dojo_social_post.py` — post creation, scheduling, publishing (Graph API v19.0)
- `dojo_social/controllers/oauth.py` — Facebook OAuth callback
- `dojo_social/data/ir_cron_social.xml` — scheduled post cron
- Integrated with AI assistant: `social_post_create` / `social_post_schedule` intents

## UI Files Reference

### Global Theme (start here — affects everything)
- `muk_web_theme/static/src/scss/colors.scss` — primary brand colors
- `muk_web_theme/static/src/scss/variables.scss` — spacing, fonts, border radius
- `muk_web_colors/static/src/scss/colors_light.scss` — light mode palette
- `muk_web_colors/static/src/scss/colors_dark.scss` — dark mode palette

### Navigation
- `muk_web_theme/static/src/webclient/navbar/navbar.scss` — top navbar
- `muk_web_theme/static/src/webclient/navbar/navbar.xml` — top navbar template
- `muk_web_appsbar/static/src/webclient/appsbar/appsbar.scss` — left sidebar
- `muk_web_appsbar/static/src/scss/variables.scss` — sidebar variables

### Module Views
- `dojo_base/views/dojo_member_views.xml` — member form/list
- `dojo_members/views/dojo_member_views.xml` — member detail
- `dojo_classes/views/dojo_class_views.xml` — classes list/form
- `dojo_attendance/views/dojo_attendance_views.xml` — attendance
- `dojo_belt_progression/views/dojo_belt_views.xml` — belt/rank views
- `muk_web_theme/static/src/views/form/form.scss` — global form styling

### Dashboard
- `dojo_instructor_dashboard/static/src/css/instructor_dashboard.css`
- `dojo_instructor_dashboard/static/src/xml/instructor_dashboard.xml`
- `dojo_instructor_dashboard/static/src/xml/admin_dashboard.xml`
- `dojo_instructor_dashboard/static/src/xml/member_profile.xml`

### Portal (student/parent facing)
- `dojo_members_portal/static/src/css/dojo_portal.css`
- `dojo_members_portal/views/portal_layout.xml`

## Git Workflow
```bash
# Fullstack work (main)
git checkout main && git pull origin main
# ... make changes ...
git add <specific files>
git commit -m "feat: description"
git push origin main

# UI-only work (isolated branch)
git checkout main && git pull origin main
git checkout ui-change-only && git merge main
# ... CSS/view changes only ...
git add <specific files>
git commit -m "ui: description"
git push origin ui-change-only
# Open PR: ui-change-only → main when ready
```

## After Any CSS/SCSS Change
```bash
docker compose restart web
# Then hard-refresh browser: Ctrl+Shift+R
```

---

## Kiosk Module (`dojo_kiosk`)

### Architecture
- **Standalone SPA** served at `GET /kiosk/<token>` — NOT part of Odoo's asset bundles
- HTML shell: `dojo_kiosk/controllers/kiosk_controller.py` (generates page, loads scripts)
- Scripts loaded as plain `<script>` tags (NOT Odoo modules):
  - `/web/static/lib/owl/owl.js` — OWL framework (global `owl` object)
  - `dojo_kiosk/static/src/kiosk_app.js` — all 16+ OWL components in one file
  - `dojo_kiosk/static/src/kiosk.css` — all styles, CSS custom properties (`--k-*` vars)
- **No TypeScript, no build step** — plain JS with OWL templates via `xml\`...\``
- Static files served directly — **no docker restart needed after CSS/JS edits**, just hard refresh

### Key Files
| File | Purpose |
|------|---------|
| `dojo_kiosk/static/src/kiosk_app.js` | All OWL components (KioskApp, HomeContent, StudentCheckinModal, MemberCard, etc.) |
| `dojo_kiosk/static/src/kiosk.css` | All kiosk styles; CSS vars in `:root` + theme overrides |
| `dojo_kiosk/controllers/kiosk_controller.py` | HTML shell + JSON-RPC endpoints (`/kiosk/search`, `/kiosk/checkin`, etc.) |
| `dojo_kiosk/models/dojo_kiosk_service.py` | Business logic: `get_enrolled_sessions_today`, `checkin_member` |
| `dojo_kiosk/views/dojo_kiosk_views.xml` | Odoo backend config form/list for kiosk settings |

### Student Check-In Flow
1. Student arrives at kiosk URL → idle screen (auto-dismisses on touch)
2. Welcome screen shows centered with search bar — student types name
3. Member tiles appear; student taps their tile
4. `StudentCheckinModal` opens — shows their enrolled sessions for today
5. Student taps a session → check-in recorded → green success screen (auto-dismisses)

### Pre-Enrollment (by design)
- The session picker **only shows sessions the student is pre-enrolled in**
- Pre-enrollment records live on `dojo.class.enrollment` (`status=registered`)
- Instructors add students via **"Assign Roster"** button in instructor mode (kiosk)
  or via the Odoo backend
- `get_enrolled_sessions_today` in `dojo_kiosk_service.py` filters by enrollment status
- **Do NOT change this to show all open sessions** — walk-in behavior is not the design

### Instructor Mode
- Access: tap 🥋 button in header → enter PIN
- Instructor sees session list with attendance roster per session
- Can assign roster (pre-enroll students), mark attendance, manage sessions

### CSS Architecture
- All CSS vars prefixed `--k-*` defined in `:root` (base) and overridden per theme:
  - `body.kiosk-theme-dark` — dark mode overrides
  - `body.kiosk-theme-light` — light mode overrides
- Key vars: `--k-accent`, `--k-surface`, `--k-surface-2`, `--k-border`, `--k-text`,
  `--k-success-dim`, `--k-danger-dim`, `--k-radius`, `--k-radius-pill`, `--k-transition`

### UI Improvements Applied (tablet UX — 2026-03)
All changes are in `kiosk.css` and `kiosk_app.js` unless noted.

| Area | What changed |
|------|-------------|
| **Search bar location** | Moved OUT of header into body; centered vertically with welcome text in idle state |
| **Search bar width** | `max-width: 560px` — comfortable tablet width, not edge-to-edge |
| **Search idle state** | `.k-home--idle` — flex centered; shows 🥋 icon, "Welcome!", sub-text, then search |
| **Search active state** | `.k-home--active` — search at top, results fill below |
| **Member tiles** | Grid min 140px (was 110px); avatar 120px (was 88px); name 15px (was 13px) |
| **Session picker** | Vertical flex list (was 2-col grid); full-width buttons with `→` arrow on right |
| **Session button layout** | Row layout: `.k-checkin-session-btn__info` wraps text, arrow via `::after` |
| **"That's not me" btn** | De-emphasized to grey underlined text link (was red outlined pill) |
| **Success screen** | Green background (`.k-success-view:not(.k-success-view--error)`), 96px icon, 2.4rem name |
| **Header (student mode)** | Now only logo + actions; search removed from header entirely |

### OWL Component Notes
- `var`/`function` declarations go on `window`; `const`/`class` do NOT — relevant if ever splitting files
- `t-model` only works on component's own state; use `t-att-value` + `t-on-input` for prop-driven inputs
- `HomeContent` receives `onInput` and `onClear` callbacks from `KioskApp` to update parent state
- Do NOT split `kiosk_app.js` into multiple files — the plain `<script>` loader doesn't support modules

---

## Workflow Reference

### Instructor Setup
1. **Settings → Users & Companies → Users → New** — fill Name + Email, set role to **Dojo Instructor**
2. **Admin Dashboard → Instructor → New** — create Instructor Profile (Name, User, Contact, Bio); Employee record auto-created on save
3. **Issue Stripe Card** — open Employee record → click “Issue Stripe Card” (requires Stripe secret key configured); creates Stripe Cardholder + virtual card; view via Stripe Issuing tab on Employee

### Kiosk Workflow
- **Permissions:** Instructors — view + changes only; Admins — full config (create kiosks, etc.)
- **Student View:** Enter name → tap tile → tap enrolled session → check-in recorded; can repeat to check out
- **Instructor Mode:** Tap 🥋 → PIN 123456 → view rosters, add sessions; hold student icon → profile modal (attendance, belt promo, contact guardian, add/remove sessions); checkmark on tile = quick attendance mark
- **AI Voice:** Bottom-right assistant; example: “Add [name] to earliest next week” → confirmation popup

### Households
- `res.partner` with `is_household=True` — parent record grouping family members
- **Primary Guardian** = billing contact; Stripe cards saved against them
- Child contacts flagged: **Is Student**, **Is Guardian**, **Is Minor**
- Payment Methods stat button on Household → saved Stripe tokens
- Off-session Stripe charge fires on billing date
- Portal: guardian sees only their own household

### AI Assistant
- Shown in Kiosk (voice) and Dashboard (text + voice)
- **Capabilities:** attendance check-in/out, enrollment add/remove, belt promotion, subscription management (admin), member create/update, class create/cancel, guardian messaging
- **Compound commands:** chain multiple actions in one phrase — *"Enroll [member] and then text their guardian"* → numbered confirmation → executes sequentially
- **Settings → AI Assistant** — view confidence scores, action log, intent schemas, undo snapshots
- Undo window: 60 minutes after any mutating action

### Student/Parent Portal
- Login at `/web/login`
- **Guardian:** payment methods, invoices, all linked students
- **Student:** class schedule, enrollment options, belt progress, attendance history

### Onboarding Wizard (10 steps)
**Phase 1 — Guardian & Household** (runs once):
1. Guardian Contact — name, email, phone, address (or join existing household)
2. Household — custom name or auto-generated
3. Guardian Portal — create login, send welcome email/SMS → triggers record creation

**Phase 2 — Student Registration** (repeats per student):

4. Student Contact — name, DOB, Is Minor flag
5. Member Details — emergency/medical notes
6. Enrollment — select Program, Class Rosters (recommended), specific Sessions
7. Auto-Enroll — permanent or date-range, select days
8. Subscription — select Plan, start date, Pay Later option
9. Student Portal — create login, send welcome email/SMS
10. Summary — review → **Confirm Student** creates all records; **Add Another Student** reuses Phase 1

### Dojo Structure Setup (Admin Only)
1. Create **Program** (e.g. “Brazilian Jiu-Jitsu”)
2. Create **Courses** under Program — set level, duration, capacity, recurrence schedule
3. Generate 60 days of sessions from the course
4. Create **Subscription Plan** linked to Program — price, billing period, enrollment fee

### Billing & Subscriptions (Automated)
- **Daily billing cron:** finds active subscriptions due today → consolidated invoice per household guardian → posted + emailed
- **Dunning:** Failure 1 = dunning email; Failure 2 = member Paused; Failure 3+ = Expired + 30-day grace; payment received = auto-reset
- **Expiry cron:** end date passed → Expired + member Cancelled; 30-day and 7-day renewal reminders
- **States:** Draft → Pending Payment → Active → Paused / Cancelled / Expired

### Marketing Cards & Campaigns
- **Card types:** Book Trial (`/dojo/book-trial`), Donate, Buy Merch, Register Tournament, Member Badge (personal check-in QR)
- Cards show on Kiosk, Portal, or both; QR auto-generated from URL
- **Campaigns:** email + SMS blasts; filter by membership state and role; one-time or recurring; cron dispatches daily; goes to primary guardian for households

### Social Media
- Connect Facebook Page via OAuth (stores Page ID + access token)
- Create post → **Post Now** or **Schedule** (cron picks up)
- Supports Facebook Pages + Instagram Business (Graph API v19.0)
- Failed posts show error message + retry available

### Integration Config
| Integration | Where to configure |
|---|---|
| **Stripe** | Invoicing → Configuration → Payment Providers → Stripe → enter Publishable + Secret key → set Published |
| **Twilio SMS** | Settings → Contacts → Send SMS → switch to Twilio → enter Account SID + Auth Token |
| **ElevenLabs** | Settings → ElevenLabs Voice Connector → enter API key + AI provider key → Test Connection |
| **Facebook/Instagram** | Social Media → Accounts → Connect via OAuth |

