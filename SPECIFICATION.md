# SPECIFICATION.md — UFTKD Dojo Platform (dojong-odoo19)

**Version:** 2026-06-20  
**Status:** Living document — update with every Release merge.  
**Conventions:** See `UnattendedBuild/templates/spec-changelog-conventions.md`.

---

## 1. Platform Overview

UFTKD is a **software platform provider** that supplies dojo management software to dojo operators. The platform is a multi-tenant Odoo application deployed on GCP; each dojo operator is a separate Odoo installation (separate database and, where needed, separate Odoo process). UFTKD is the provider; dojo operators are the customers.

The stack is Odoo **saas~19.2** — a rolling SaaS branch pinned at the point the dev VM image was built. It is not a stable community release. All custom module versions carry the `saas~19.2.x.x.x` prefix.

---

## 2. Environments

### 2.1 Development — Docker Compose (local VM / dev laptop)

| Component | Detail |
|---|---|
| Compose file | `repos/dojong-odoo19/docker-compose.yml` |
| db service | `pgvector/pgvector:pg17` · DB `postgres` · user `odoo` · password `odoo` · volume `odoo-db-data-19-2` |
| web service | custom image `odoo-saas-19-2:latest` (built from `Dockerfile`) · host port **8070** → container **8069** · addons at `./addons:/mnt/extra-addons` |
| n8n service | `n8nio/n8n:latest` · port **5678** · auth `admin / dojo-n8n-dev` · `ODOO_BASE_URL=http://web:8069` |
| Odoo database | `odoo19` (set via `dbfilter = ^odoo19$`) |
| Config file | `config/odoo.conf` |
| Health check | `curl -f http://127.0.0.1:8070/web/login` |
| Module install | `docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 --workers=0 --no-http -i <modules> --stop-after-init` |
| Module test | `docker compose run --rm --entrypoint /opt/odoo/odoo-bin web -c /etc/odoo/odoo.conf -d odoo19 -u <module> --test-enable --stop-after-init --workers=0` |
| Bootstrap script | `scripts/prepare-vm.sh` — build image, start services, install core modules, verify |
| Dev VM | `192.168.1.149` (local network) · user `johnbentleyii` · SSH key `automation/johnbentleyii-ai-dev-dojang` |

### 2.2 Production — GCP VM

| Component | Detail |
|---|---|
| VM | `dojo-solution` · e2-medium · `us-central1-c` · IP `34.61.41.123` |
| Cloud SQL | `free-trial-first-project` · db-perf-optimized-N-2 · PostgreSQL 18 · 100 GB · **backups DISABLED** |
| Cloud SQL Proxy | `127.0.0.1:5432` on the VM |
| Instances | prod (port 8069, DB `prod`) + prod2 (port 8089, DB `prod2`) |
| Addons path | `custom-addons/addons` — shared by both instances; a code change hits both simultaneously |
| Git | **No git on production VM.** Code is manually deployed. No version tracking in production. |

---

## 3. Module Inventory

Modules are organized by category. All custom/UFTKD modules use `saas~19.2.x.x.x` versioning.

### 3.1 Core Domain — UFTKD Custom Modules

| Module | Version | Summary |
|---|---|---|
| `dojo_core` | saas~19.2.4.0.0 | Core martial arts school management: members, classes, attendance, belt progression, instructor dashboard |
| `dojo_instructor_dashboard` | saas~19.2.1.0.0 | OWL-based instructor dashboard with stats, belt distribution, birthdays, and expiring memberships |
| `dojo_belt_progression` | saas~19.2.1.0.0 | OWL-based mass belt promotion with multi-select, single-click promote-all, undo, and promotion history |
| `dojo_members` | saas~19.2.1.0.0 | Member reports: inactive students, contact validation, family groupings |
| `dojo_kiosk` | saas~19.2.1.1.0 | Tablet check-in kiosk for dojang members and instructors |
| `dojo_subscriptions` | saas~19.2.6.0.0 | Membership plans and subscriptions |
| `dojo_onboarding` | saas~19.2.1.0.0 | Step-by-step member onboarding wizard |
| `dojo_onboarding_stripe` | saas~19.2.1.0.0 | Collects a Stripe payment method during member onboarding |
| `dojo_crm` | saas~19.2.2.0.0 | CRM stages, automations, lead scoring, trial booking, AI integration, convert-to-member |
| `dojo_communications` | saas~19.2.1.0.0 | Automated SMS/email for check-in parent alerts, session reminders, instructor messaging |
| `dojo_marketing` | saas~19.2.3.0.0 | Promotional cards with QR codes — kiosk carousel and member portal |
| `dojo_sign` | saas~19.2.2.0.0 | Inline waiver signing during member onboarding (Community-compatible) |
| `dojo_stripe` | saas~19.2.2.0.0 | Stripe Billing (subscriptions) + Stripe Issuing (employee cards) |
| `dojo_members_portal` | saas~19.2.3.0.0 | Self-service portal for parents and students |
| `dojo_website` | saas~19.2.1.0.0 | Custom dojang website with trial lesson forms integrated into CRM |
| `dojo_events` | saas~19.2.1.0.0 | Links members to Odoo Events |
| `dojo_calendar` | saas~19.2.1.0.0 | Class calendar — sync sessions to `calendar.event` |
| `dojo_automation` | saas~19.2.1.1.0 | Spark-Membership-style automation builder |
| `dojo_points` | saas~19.2.1.0.0 | Pokémon GO-style points — auto-award on attendance, streaks, belt promotions |
| `dojo_credits` | saas~19.2.1.0.0 | Class credit ledger |
| `dojo_social` | saas~19.2.1.0.0 | Facebook/Instagram post scheduling |
| `dojo_bridge` | saas~19.2.2.0.0 | Headless API bridge: Control Plane (NestJS) ↔ Odoo Business Plane; versioned REST API secured by HS256 JWTs |
| `dojo_checkout` | saas~19.2.2.0.0 | Public checkout flow: plan selection, day picker, upsells, invoice or pay-now, portal upgrade |
| `dojo_firebase` | saas~19.2.1.0.0 | Email relay via Gmail/Firebase Cloud Functions + FCM web push notifications for the member portal |
| `dojo_management` | saas~19.2.1.0.0 | Comprehensive martial arts school management with belt ranking and analytics |
| `dojo_migration` | saas~19.2.1.0.0 | SparkMembership → Odoo CSV migration tool (admin only) |
| `dojo_theme` | saas~19.2.1.0.0 | UFTKD brand theme — design tokens, fonts, and visual styling |

### 3.2 AI Layer — UFTKD Custom Modules

| Module | Version | Summary |
|---|---|---|
| `ai_assistant` | saas~19.2.1.0.0 | Reusable AI voice assistant service; exposes `/api/v1/ai/health`, `/api/v1/ai/discover`, `/api/v1/ai/execute` |
| `ai_vector` | saas~19.2.1.0.0 | Vector embedding layer for AI intent routing and multi-agent orchestration |
| `ai_mcp` | saas~19.2.1.0.0 | Model Context Protocol server — exposes AI tools to external LLMs |
| `elevenlabs_connector` | saas~19.2.1.0.0 | Hands-free voice assistant — ElevenLabs STT + OpenAI/Gemini |
| `dojo_connect_ai` | saas~19.2.1.0.0 | AI receptionist (Kai) with CRM lead generation from phone calls |
| `dojo_ai_caller` | saas~19.2.1.0.0 | AI-powered outbound calling campaigns via ElevenLabs Conversational AI |

### 3.3 Third-Party / OCA Modules

| Module | Version | Summary |
|---|---|---|
| `automation_oca` | saas~19.2.1.0.1 | Automate actions in threaded models (OCA) |
| `subscription_oca` | saas~19.2.1.0.0 | Generate recurring invoices (OCA) |
| `bi_all_digital_sign` | — | Digital signature support (BI Solutions) |
| `connect` | 1.0.2 | Twilio and Odoo integration |
| `sms_twilio` | — | Send SMS messages using Twilio (now version-tracked) |

### 3.4 MuK IT Theme (Retired — REL-001/INC-23)

**Status:** ✅ **Fully retired as of 2026-06-23** — All 7 `muk_web_*` modules uninstalled and removed from `addons/`.

The MuK IT theme modules have been completely replaced by the `dojo_theme` custom theme module (saas~19.2.1.0.0). The platform now uses a design token system defined in `addons/dojo_theme/static/src/css/tokens.css` for all visual styling.

**Removed modules:**

| Module | Version | Retirement Date | Replaced By |
|---|---|---|---|
| `muk_web_theme` | saas~19.2.1.4.2 | 2026-06-23 | `dojo_theme` (color system, typography) |
| `muk_web_colors` | saas~19.2.1.0.5 | 2026-06-23 | `dojo_theme` (design tokens) |
| `muk_web_appsbar` | saas~19.2.1.1.5 | 2026-06-23 | Odoo Community default sidebar |
| `muk_web_chatter` | saas~19.2.1.4.2 | 2026-06-23 | Odoo Community default chatter |
| `muk_web_dialog` | saas~19.2.1.0.5 | 2026-06-23 | Odoo Community default dialogs |
| `muk_web_refresh` | saas~19.2.1.0.5 | 2026-06-23 | Browser refresh |
| `muk_web_group` | saas~19.2.1.0.2 | 2026-06-23 | Odoo Community default |

**Feature coverage:** `dojo_theme` provides 41 CSS custom properties (design tokens) covering surface colors, brand colors, typography, status colors, and belt rank colors. MuK's layout SCSS features (navbar customization, fullscreen appsmenu, form borders) were evaluated as acceptable losses; Odoo Community defaults provide sufficient functionality. If visual regression is observed in production, layout SCSS will be added in a future increment.

**Documentation:** See `docs/ui-ux-guide.md` for the complete `dojo_theme` design system reference.

### 3.5 Stub / Reserved Modules

The following directories exist in `addons/` but contain only an `access_rights` security file and no `__manifest__.py`. They appear to be placeholder namespaces reserved for future implementation.

- `dojo_attendance`
- `dojo_classes`
- `dojo_base`

---

## 4. Core Data Model

### 4.1 dojo_core Models

| Model | Purpose |
|---|---|
| `dojo.member` | Central member record — personal info, emergency contacts, status, linked `res.partner` |
| `dojo.member.rank` | Member's current and historical belt rank assignments |
| `dojo.belt.rank` | Belt rank definitions (16 ranks: White through 4th Dan — see Section 8) |
| `dojo.belt.test` | Belt testing events |
| `dojo.belt.test.registration` | Member registration for a specific belt test |
| `dojo.belt.promotion.wizard` | Transient wizard: process belt promotions in bulk |
| `dojo.class.template` | Class template — defines a recurring class type |
| `dojo.class.session` | Individual class session generated from a template |
| `dojo.class.enrollment` | Member enrollment in a class template |
| `dojo.attendance.log` | Per-session attendance record |
| `dojo.attendance.quick.wizard` | Transient wizard: rapid bulk attendance entry |
| `dojo.instructor.profile` | Instructor profile — linked to `res.users` |
| `dojo.instructor.kpi` | Instructor KPI metrics (computed) |
| `dojo.instructor.todos` | Instructor to-do items |
| `dojo.program` | Training program grouping class templates |
| `dojo.course.auto.enroll` | Auto-enrollment preference rules |
| `dojo.emergency.contact` | Emergency contact linked to a member |
| `dojo.martial.art.style` | Martial art style definitions |

### 4.2 Domain Models from Other Modules

| Model | Module | Purpose |
|---|---|---|
| `dojo.kiosk.config` | dojo_kiosk | Kiosk configuration per location |
| `dojo.kiosk.action.log` | dojo_kiosk | Audit log of kiosk actions |
| `dojo.kiosk.announcement` | dojo_kiosk | Rotating announcements displayed on kiosk |
| `dojo.kiosk.pin.attempt` | dojo_kiosk | PIN attempt tracking for security |
| `dojo.kiosk.service` | dojo_kiosk | Kiosk service / integration record |
| `dojo.subscription.plan` | dojo_subscriptions | Subscription plan definitions |
| `dojo.program.enrollment` | dojo_subscriptions | Member enrollment in a subscription plan |
| `dojo.onboarding.record` | dojo_onboarding | Persisted onboarding session state |
| `dojo.onboarding.wizard` | dojo_onboarding | Transient onboarding wizard |
| `dojo.points.config` | dojo_points | Points award configuration |
| `dojo.points.transaction` | dojo_points | Individual points transactions |
| `dojo.credit.transaction` | dojo_credits | Class credit ledger entries |
| `dojo.marketing.card` | dojo_marketing | Marketing card with embedded QR code |
| `crm.pipeline.service` | dojo_crm | CRM pipeline stage extension |

---

## 5. Deployed Functionality

### 5.1 Member Management (dojo_core)

Full member lifecycle: create member, assign belt rank, enroll in classes, log attendance. Belt promotion wizard supports bulk processing of test results. Emergency contacts and instructor profiles are first-class records. Auto-enrollment rules drive members into programs based on rank or age group.

**Surname-first search**: `dojo.member._name_search` override parses the search query, identifies the last token as a probable surname, and ranks members whose `last_name` starts with that token above members with the query elsewhere in their name. For example, searching "Smith" returns members with surname "Smith" ranked above members with "Smith" in their first or middle name. Multi-token queries (e.g., "John Smith") use the last token ("Smith") as the probable surname. The `last_name` field is stored, computed from the full name, and indexed for performance.

**Membership expiry tracking**: `dojo.member.expdate` is a stored, indexed Date field computed from the linked subscription state. The field holds the end date of the latest active subscription (ordered by `date` descending). When no active subscription exists, or when `dojo_subscriptions` is not installed, the field is `False`. This allows efficient filtering and sorting of members by membership expiry date in list views and reports (e.g., "expiring within 30 days").

### 5.2 Instructor Dashboard (dojo_instructor_dashboard)

OWL-based instructor dashboard providing at-a-glance metrics and action lists. Accessed via menu under "Dojang Management" → "Instructor Dashboard". The dashboard is rendered as a client action using Odoo Web Framework components and styled exclusively with `dojo_theme` design tokens.

**Features:**

1. **Four stat cards** — Active students count, today's check-ins (present + late), upcoming birthdays (next 7 days), expiring memberships (next 30 days).
2. **Belt distribution bar chart** — Horizontal bar chart showing active member breakdown by belt rank. Each rank is color-coded using `dojo.belt.rank.color`. Includes an "Unranked" category for members without a current rank. Sorted by rank sequence.
3. **Birthday list** — Members with birthdays in the next 7 days, calculated year-agnostically (handles year boundaries correctly). Each entry shows member name, belt rank badge, date of birth, and countdown ("in X days" or "Today!"). Sorted by days until birthday. Clicking a member opens their form view.
4. **Expiring memberships list** — Active members with `expdate` within 30 days. Each entry shows member name, belt rank badge, and expiry date. Sorted by expiry date ascending. Clicking a member opens their form view.

**Attendance Analytics:**

A dedicated analytics view provides insight into class attendance patterns and member engagement. Accessed via menu under "Dojang Management" → "Attendance Analytics".

1. **Time period selector** — Toggle between "Last 30 Days" and "Last 90 Days" to adjust the analysis window. All three analytics sections update when the period changes.
2. **Busiest Classes** — Top 10 class sessions ranked by check-in count (present + late) within the selected period. Shows session name, start datetime, and check-in count. Clicking a session opens its form view.
3. **Most Attendance** — Top 10 members ranked by check-in count within the selected period. Shows member name, current belt rank badge, and check-in count. Clicking a member opens their form view.
4. **Inactive Members** — Active members with zero check-ins (present or late) in the selected period. Shows member name, current belt rank badge, and last seen date (the most recent check-in from any period, or "Never" if no attendance records exist). Useful for identifying at-risk members who may need follow-up.

**CSV Export Wizard:**

The instructor dashboard and member reports include a CSV export wizard accessible via an "Export Data" action. The wizard (`dojo.export.wizard`, a transient model) presents four export types:

1. **Students (All Fields)** — exports all members with: member number, name, first name, last name, email, phone, date of birth, gender, membership state, current belt, membership expiry, emergency contacts, blood type, allergies, medical notes, total sessions, and attendance rate.
2. **Attendance Log** — exports all `dojo.attendance.log` records with: date, member number, member name, session, status, check-in time, check-out time, duration (hours), performance rating, and notes.
3. **Promotion History** — exports all `dojo.member.rank` records with: date awarded, member number, member name, belt rank, stripes, program, awarded by, and notes.
4. **Belt Test Rosters** — exports all `dojo.belt.test` records and their registrations with: test date, test name, location, program, lead instructor, status, member number, member name, current belt, testing for rank, registration status, and result.

The wizard returns a CSV file download via the `/instructor_dashboard/export?type=<export_type>` HTTP controller (`addons/dojo_instructor_dashboard/controllers/export.py`). The controller generates the CSV dynamically and returns it with `Content-Type: text/csv` and a `Content-Disposition: attachment` header.

**Technical implementation:**

- **Controllers**: `/instructor_dashboard/data` JSON-RPC endpoint (`addons/dojo_instructor_dashboard/controllers/dashboard.py`) computes dashboard metrics; `/instructor_dashboard/analytics` JSON-RPC endpoint (`addons/dojo_instructor_dashboard/controllers/analytics.py`) computes attendance analytics accepting a `days` parameter (30 or 90); `/instructor_dashboard/export` HTTP endpoint (`addons/dojo_instructor_dashboard/controllers/export.py`) generates and returns CSV exports.
- **OWL components**: `InstructorDashboardApp` (`addons/dojo_instructor_dashboard/static/src/js/dashboard.js`) registered as `dojo_instructor_dashboard.action`; `AttendanceAnalyticsApp` (`addons/dojo_instructor_dashboard/static/src/js/analytics.js`) registered as `dojo_instructor_dashboard.analytics_action`.
- **Templates**: QWeb templates `dojo_instructor_dashboard.Dashboard` and `dojo_instructor_dashboard.Analytics` (`addons/dojo_instructor_dashboard/static/src/xml/dashboard.xml`).
- **Models**: `dojo.export.wizard` transient model (`addons/dojo_instructor_dashboard/models/export_wizard.py`) with methods `_export_students()`, `_export_attendance()`, `_export_promotion_history()`, `_export_belt_test_rosters()`.
- **Styling**: All CSS uses `dojo_theme` tokens (`--bg`, `--surface`, `--text`, `--gold`, `--red`, etc.) defined in `addons/dojo_theme/static/src/css/tokens.css`.

### 5.3 Belt Progression (dojo_belt_progression)

OWL-based mass belt promotion with multi-select member grid, single-click promote-all, and in-session undo. Belt test roster builder with print-ready layout and saved records. Accessed via menu under "Dojang Management" → "Mass Promote" and "Belt Test Roster". All views are rendered as client actions using Odoo Web Framework components and styled exclusively with `dojo_theme` design tokens.

**Mass Promotion Features:**

1. **Member selection grid** — Grid of member cards showing name and current belt rank (color-coded). Click to toggle selection. Filter by name (text search) or current belt rank (dropdown). "Select All" and "Deselect All" buttons. Selection count display.
2. **Target rank selector** — Buttons for each belt rank ordered by sequence. Click to select target rank. Selected rank is highlighted.
3. **Promote button** — Disabled until at least one member is selected and a target rank is chosen. Click to promote all selected members to the target rank in a single action. Creates `dojo.member.rank` records for each promoted member with `date_awarded` set to today and notes recording "Mass promotion to [Rank Name]".
4. **Undo stack** — In-memory stack of promotion actions within the current session. "Undo Last Promotion" button deletes the most recent batch of `dojo.member.rank` records created by the last promote action. Undo is only available within the same browser session; closing the page clears the stack.
5. **Promotion History** — Read-only list view of all `dojo.member.rank` records showing date awarded, member, rank, awarded by, program, stripe count, and notes. Ordered by `date_awarded` descending (most recent first). Accessible via menu under "Dojang Management" → "Promotion History".

**Belt Test Roster Features:**

1. **Filterable member list** — Filter members by class group (course template), belt rank, and name search. All filters update the displayed member list in real-time.
2. **Member selection** — Click individual members to toggle selection or use "Select All" / "Deselect All" buttons. Selection count display shows total selected members.
3. **Roster metadata** — Input fields for roster name (defaults to "Belt Test [date]") and test date (defaults to today). Both are editable before saving.
4. **Print-ready layout** — Print button triggers `@media print` CSS that hides screen-only controls and displays a formatted roster with member names, current ranks, and signature lines for Pass/Fail results. Print layout is optimized for physical paper with page-break-inside avoidance.
5. **Save to database** — "Save Roster" button creates a `dojo.belt.test` record with the roster name, test date, and program (derived from the class group filter if set). For each selected member, a `dojo.belt.test.registration` record is created with `target_rank_id` set to either: the filtered rank (if rank filter is active), the next rank in sequence after the member's current rank, or the first rank in sequence for unranked members.
6. **View saved rosters** — "View Saved Rosters" button opens the standard Odoo list view of `dojo.belt.test` records, showing all previously saved rosters with their names, dates, states, and programs. Each record can be opened in form view to see registrations, update test results, or add notes.

**Technical implementation:**

- **Controllers**: `/belt_progression/data` (returns members and ranks), `/belt_progression/promote` (creates rank records, returns record IDs for undo), `/belt_progression/undo` (deletes specified rank records), `/belt_test/roster/data` (returns members with class enrollments, class templates, and ranks), `/belt_test/roster/save` (creates `dojo.belt.test` record with registrations).
- **OWL components**: `MassPromoteApp` (`addons/dojo_belt_progression/static/src/js/mass_promote.js`) registered as `dojo_belt_progression.action`; `BeltTestRosterApp` (`addons/dojo_belt_progression/static/src/js/belt_test_roster.js`) registered as `dojo_belt_progression.roster_action`.
- **Templates**: QWeb templates `dojo_belt_progression.MassPromote` (`addons/dojo_belt_progression/static/src/xml/mass_promote.xml`) and `dojo_belt_progression.BeltTestRosterTemplate` (`addons/dojo_belt_progression/static/src/xml/belt_test_roster.xml`).
- **Styling**: All CSS uses `dojo_theme` tokens defined in `addons/dojo_theme/static/src/css/tokens.css`. Print-specific styles in `addons/dojo_belt_progression/static/src/css/roster_print.css`.

### 5.4 Kiosk (dojo_kiosk)

Tablet check-in interface. Members check in via PIN or QR code. Action log tracks every check-in/check-out event. Kiosk carousel displays marketing announcements. Parent SMS alerts fire on check-in via `dojo_communications`. Config record is per-location. See Section 7 for full kiosk detail.

### 5.5 Subscriptions (dojo_subscriptions + subscription_oca)

Subscription plans map to Odoo recurring invoices via `subscription_oca`. `dojo_subscriptions` adds the dojo-specific plan definitions and program enrollment records. Stripe integration via `dojo_stripe` handles payment collection.

### 5.6 Onboarding (dojo_onboarding + dojo_onboarding_stripe + dojo_sign)

Multi-step wizard: collect member info → sign waiver (`dojo_sign`) → select subscription plan → collect Stripe payment method (`dojo_onboarding_stripe`) → create member record. Wizard state persisted in `dojo.onboarding.record` to allow resume on disconnection.

### 5.7 CRM (dojo_crm)

Pipeline stages, lead scoring, trial lesson booking. Leads sourced from website trial forms (`dojo_website`), AI phone calls (`dojo_connect_ai`), and manual entry. Convert-to-member action promotes a won lead directly into the onboarding flow. Automation rules managed via `dojo_automation`.

### 5.8 Communications (dojo_communications + dojo_firebase + connect)

Automated SMS via Twilio (`connect` module). Email relay via Firebase Cloud Functions / Gmail (`dojo_firebase`). FCM web push to the member portal. Triggers: check-in parent alerts, class session reminders, instructor messages.

**Email Center**: OWL-based interface for composing and sending mass emails to member segments. Accessed via menu under "Communications" → "Email Center". The Email Center provides audience segmentation by membership status, class groups, belt rank, and expiring memberships. All sent emails are logged in the Email History.

**Email Center Features:**

1. **Audience Segmentation** — Filter members by:
   - Membership status (active, trial, paused, cancelled) with multi-select checkboxes
   - Class groups (multi-select checkboxes)
   - Belt rank (single-select dropdown, with "All Ranks" option)
   - Expiring memberships (checkbox to include members with `expdate` within a configurable number of days, default 30)

2. **Member Loading** — "Load Members" button fetches members matching the selected filters via `/dojo/email_center/members` JSON-RPC endpoint. Returns member list with name, email, membership state, and current rank.

3. **Recipient Selection** — Loaded members appear in a recipient list with checkboxes. Individual members can be toggled, or all/none selected. Shows count of selected recipients vs total loaded members.

4. **Email Composer** — Subject (text input) and body (textarea supporting plain text or HTML). Both are required before sending.

5. **Send Action** — "Send Email" button creates `mail.mail` records for each selected member (routing to guardian email via `_mail_get_partners()` when applicable), sends the emails via Odoo's mail system, and creates a `dojo.email.history` record logging the subject, body, recipient count, audience filter description, and recipient member IDs.

6. **Email History** — Read-only list view of all sent emails (`dojo.email.history`) showing sent date, subject, sender, recipient count, and audience filter description. Form view displays the full email body (HTML widget) and a notebook tab showing the recipient member list. History records cannot be edited or deleted by regular users (only managers with `base.group_system`).

**Technical implementation:**

- **Model**: `dojo.email.history` (`addons/dojo_communications/models/email_history.py`) with fields: `subject`, `body`, `sent_date`, `sender_id`, `recipient_count`, `audience_filter`, `member_ids`.
- **Controllers**: `/dojo/email_center/send` (sends emails and creates history record), `/dojo/email_center/members` (returns filtered member list), both JSON-RPC endpoints in `addons/dojo_communications/controllers/email_center.py`.
- **OWL component**: `EmailCenter` (`addons/dojo_communications/static/src/js/email_center.js`) registered as `dojo_communications.email_center`.
- **Templates**: QWeb template `dojo_communications.EmailCenter` (`addons/dojo_communications/static/src/xml/email_center.xml`).
- **Styling**: All CSS uses `dojo_theme` tokens defined in `addons/dojo_theme/static/src/css/tokens.css`.

### 5.9 Marketing (dojo_marketing)

Promotional cards with embedded QR codes. Cards appear in the kiosk carousel and member portal. QR codes deep-link to website pages or trial forms.

### 5.10 Points and Credits (dojo_points + dojo_credits)

`dojo_points`: auto-award points on attendance (streak bonuses), belt promotions, and configured events. `dojo_credits`: class credit ledger for drop-in and prepaid class packs. Both integrate with the member portal.

### 5.11 Calendar (dojo_calendar + dojo_events)

Class sessions sync to `calendar.event` for visibility in the Odoo calendar view. `dojo_events` links members to Odoo native Events (tournaments, seminars).

### 5.12 Automation Builder (dojo_automation)

Spark-Membership-style visual automation builder: trigger → condition → action chains. Drives communications and points awards without code changes.

**Birthday Email Automation:**

Daily automated birthday emails are sent to members via an `ir.cron` scheduled action that runs at 6:00 AM server time. The automation finds members with birthdays today (or within N days ahead if configured) and sends the "Dojo – Birthday Wishes" email template to each matching member.

**Features:**
1. **Daily Cron Job** — `ir_cron_birthday_emails` runs daily, calling `dojo.member._cron_send_birthday_emails()`. Active by default.
2. **Configuration** — `dojo_automation.birthday_days_ahead` ir.config_parameter controls how many days ahead to check (default: 0 = today only). Set to 1 to send emails to members with birthdays today or tomorrow; set to 7 to send up to a week in advance.
3. **Email Template** — `email_tpl_birthday` (`dojo_automation.email_tpl_birthday`) provides a branded birthday message with celebration styling, member's current rank display (if set), and a call-to-action button linking to the member portal.
4. **Filtering** — Only active members with a `date_of_birth` set and a valid `partner_id.email` receive the birthday email. Inactive members and members without email are excluded.
5. **Logging** — Each sent email is logged via `_logger.info` with the member name, date of birth, and email address. Send failures are logged as errors but do not halt the cron job.

**Technical implementation:**
- **Cron record**: `ir_cron_birthday_emails` (`addons/dojo_automation/data/birthday_automation.xml`) — daily interval, runs `dojo.member._cron_send_birthday_emails()`.
- **Method**: `_cron_send_birthday_emails()` (`addons/dojo_core/models/member.py`) — queries members by birthday month/day match, calls `mail.template.send_mail()` for each.
- **Template**: `email_tpl_birthday` (`addons/dojo_automation/data/birthday_template.xml`) — Mako template targeting `dojo.member` model.
- **Config parameter**: `dojo_automation.birthday_days_ahead` (`addons/dojo_automation/data/birthday_automation.xml`) — default value `0`.

**Membership Expiry Warning Automation:**

Daily automated membership expiry warning emails are sent to members via an `ir.cron` scheduled action that runs at 7:00 AM server time. The automation finds members whose membership is expiring within N days (configurable) and sends the "Dojo – Membership Expiry Warning" email template to each matching member.

**Features:**
1. **Daily Cron Job** — `ir_cron_expiry_warning_emails` runs daily, calling `dojo.member._cron_send_expiry_warning_emails()`. Active by default.
2. **Configuration** — `dojo_automation.expiry_days_ahead` ir.config_parameter controls how many days ahead to check (default: 30 = within 30 days). Set to 7 to send warnings only to members expiring within a week; set to 60 to send warnings up to two months in advance.
3. **Email Template** — `email_tpl_expiry_warning` (`dojo_automation.email_tpl_expiry_warning`) provides a branded expiry warning message with the member's expiry date prominently displayed, current rank (if set), and a call-to-action encouraging renewal.
4. **Filtering** — Only active members with an `expdate` set within the configured threshold and a valid `partner_id.email` receive the warning email. Members without expiry dates, members whose membership already expired (expdate < today), members expiring beyond the threshold, and members without email are excluded.
5. **Logging** — Each sent email is logged via `_logger.info` with the member name, expiry date, and email address. Send failures are logged as errors but do not halt the cron job.

**Technical implementation:**
- **Cron record**: `ir_cron_expiry_warning_emails` (`addons/dojo_automation/data/expiry_automation.xml`) — daily interval, runs `dojo.member._cron_send_expiry_warning_emails()`.
- **Method**: `_cron_send_expiry_warning_emails()` (`addons/dojo_core/models/member.py`) — queries members by expdate range (today <= expdate <= today + days_ahead), calls `mail.template.send_mail()` for each.
- **Template**: `email_tpl_expiry_warning` (`addons/dojo_automation/data/expiry_template.xml`) — Mako template targeting `dojo.member` model.
- **Config parameter**: `dojo_automation.expiry_days_ahead` (`addons/dojo_automation/data/expiry_automation.xml`) — default value `30`.

### 5.13 Social (dojo_social)

Facebook/Instagram post scheduling from inside Odoo. Allows dojos to schedule social media content around events and promotions.

### 5.14 Member Reports (dojo_members)

Three OWL-based member reports accessible from the backend:

- **Inactive Student Report** — lists members with no attendance in the last N days (configurable, default 30). Shows member number, name, email, phone, and last attendance date. Includes checkbox selection for individual or bulk selection of members, and a "Send Follow-up" action button that triggers a follow-up email workflow to selected inactive students.
- **Contact Report** — lists members missing parent/guardian email or phone. Highlights missing fields to drive contact data completeness.
- **Family Report** — groups members by household, showing primary guardian and all household members. Useful for family billing and communication.

All reports are OWL components with refresh controls, filterable data, and JSON API endpoints.

**Follow-up Email Action:**

The Inactive Student Report includes a mass email action accessible via the "Send Follow-up" button. The workflow:

1. **Selection** — Instructors check individual members or use "Select All" to mark inactive students for follow-up. The button label shows the count of selected members.
2. **Confirmation Dialog** — Clicking "Send Follow-up" opens a modal dialog confirming the action and showing the count of recipients. The dialog explains that a default "We miss you at the dojo" message will be sent.
3. **Email Sending** — Confirmation triggers the `/dojo_members/send_followup` JSON-RPC endpoint which creates and sends `mail.mail` records for each selected member (routing to their partner email). Only members with valid email addresses receive the email; members without email are silently skipped.
4. **Success Notification** — A toast notification confirms the sent count, and the selection is cleared.

The endpoint requires `dojo_core.group_dojo_instructor` or `group_dojo_admin` permission. The default email subject is "We miss you at the dojo!" and the default body is a friendly re-engagement message. Custom subject and body can be passed as optional parameters by future implementations (Email Center integration). All follow-up emails sent via this action are logged via standard Odoo `mail.mail` tracking but do not create `dojo.email.history` records (reserved for the Email Center mass-send feature).

**Technical implementation:**

- **Controllers**: `/dojo_members/api/inactive_report` (returns inactive members), `/dojo_members/api/contact_report` (returns incomplete contacts), `/dojo_members/api/family_report` (returns household groupings), `/dojo_members/send_followup` (sends follow-up emails). All JSON-RPC endpoints in `addons/dojo_members/controllers/reports.py` and `addons/dojo_members/controllers/followup.py`.
- **OWL components**: `InactiveStudentReport`, `ContactReport`, `FamilyReport` (`addons/dojo_members/static/src/js/reports.js`) registered as client actions.
- **Templates**: QWeb templates `dojo_members.InactiveStudentReport`, `dojo_members.ContactReport`, `dojo_members.FamilyReport` (`addons/dojo_members/static/src/xml/reports.xml`).
- **Styling**: Components use standard Odoo classes and `dojo_theme` tokens where custom styling is needed.

### 5.15 Member Portal (dojo_members_portal)

Self-service portal for parents and students. Shows attendance history, belt rank, points, credits, upcoming classes. Receives FCM push notifications. Public checkout flow via `dojo_checkout`.

### 5.15 Website (dojo_website)

Custom dojang public website with trial lesson booking forms. Forms submit leads into `dojo_crm`.

### 5.16 Stripe (dojo_stripe)

Stripe Billing for subscription recurring payments. Stripe Issuing for dojo employee/instructor cards. Payment method collection during onboarding via `dojo_onboarding_stripe`.

### 5.17 API Bridge (dojo_bridge)

Headless REST API. Exposes versioned, stateless endpoints secured by HS256 JWTs. Intended to allow a NestJS Control Plane or other external clients to drive Odoo as the Business Plane without coupling to Odoo's web client.

### 5.18 Checkout (dojo_checkout)

Public-facing checkout pages: plan selection, day picker, optional upsells, invoice or pay-now flow, portal account upgrade. Operates without requiring a logged-in Odoo session.

### 5.19 Data Migration (dojo_migration)

Admin-only tool. Imports SparkMembership CSV exports into the dojo data model. One-time use per operator onboarding.

---

## 6. Kiosk Detail

The kiosk is a full-screen tablet application running in Odoo's web client, served from `dojo_kiosk`.

**Check-in flow**: Member enters PIN or scans QR code → kiosk resolves identity via `dojo.kiosk.service` → creates `dojo.attendance.log` record → fires `dojo_communications` SMS to parent (configurable) → shows confirmation overlay with member photo, name, and belt rank. The confirmation overlay displays full-screen for 3 seconds with a fade-in animation, plays an audio chime (800 Hz tone via Web Audio API), and auto-dismisses back to the kiosk home screen.

**Carousel**: Marketing announcements from `dojo.kiosk.announcement` rotate between check-ins.

**Security**: `dojo.kiosk.pin.attempt` tracks failed PIN attempts and triggers lockout after threshold. The kiosk config record (`dojo.kiosk.config`) is per-location with configurable timeouts and announcement interval.

**Photo display**: Member photos are stored in Odoo's `ir.attachment` (binary field on `dojo.member`). The design prototype (`UFT_SUPABASE_STORAGE_PHOTOS.html`) used Supabase Storage as a reference design; production implementation stores photos in Odoo.

**Instructor three-panel layout**: When the kiosk is in instructor mode, the view is organized as a three-column grid:

- **Left panel**: Active session card with session name, time range, countdown timer (showing minutes:seconds remaining until session end), and attendance summary showing present/late/absent counts.
- **Main panel**: Member roster displayed as a grid of cards, one per enrolled member. Each roster card shows the member name, belt rank, an onboarding progress bar (when onboarding is incomplete, 0-99%), and an open task count badge (when instructor tasks exist for the member).
- **Right panel**: Alerts and notes organized into sections: onboarding incomplete, membership issues, and instructor tasks. Each alert shows the member name and a brief detail.

The countdown timer updates every second via `setInterval` and displays `MM:SS` format. The session summary data (attendance counts, session info) is fetched via `/kiosk/api/session_summary` which calls `get_session_summary()` on `dojo.kiosk.service`.

**Session auto-select and visual states**: Each session in the instructor view has a `time_state` field computed relative to the current server time: `active` (session is currently in progress), `upcoming_soon` (session starts within 15 minutes), `upcoming` (session starts later), or `done` (session end time has passed). On page load and every 60 seconds, the kiosk automatically selects the first `active` or `upcoming_soon` session. Session cards render with CSS state classes `k-session--active`, `k-session--soon`, `k-session--upcoming`, `k-session--done` to visually distinguish their time state via border color and opacity.

### 6.1 Kiosk API Endpoints

All kiosk endpoints require a valid `token` (per-tablet kiosk token from `dojo.kiosk.config`) and `instructor_key` (session key from PIN verification).

**Member Profile** — `get_member_profile(member_id, session_id=None, instructor_key=None)`

Returns member profile data including onboarding status. When called without `instructor_key`, returns a minimal profile. With valid `instructor_key`, returns the full profile including:

- `workflow_status`: Dict containing:
  - `onboarding`: Dict with keys:
    - `available` (bool): Whether onboarding module is installed
    - `record_id` (int|False): ID of the onboarding record
    - `state` (str): One of `not_started`, `in_progress`, `completed`, `not_installed`
    - `complete` (bool): Whether all onboarding steps are complete
    - `progress_pct` (int): Percentage of legacy data-entry steps complete (0-100)
    - `steps` (list): List of dicts with `key`, `label`, `complete` for each step
    - `missing_steps` (list): Labels of incomplete steps
  - `waiver`, `subscription`, `attendance`, `grading`, `tasks`: Status dicts for other workflows
  - `alerts` (list): List of alert dicts with `code` and `label`
  - `alert_count` (int): Total number of alerts

**Onboarding Actions** — POST endpoints:

- `/kiosk/api/onboarding/complete_step` — Mark an onboarding step as complete
  - Params: `member_id` (int), `step_key` (str), `token`, `instructor_key`
  - Returns: `{"success": bool, "workflow_status": dict}`

- `/kiosk/api/onboarding/send_reminder` — Send onboarding reminder to guardians
  - Params: `member_id` (int), `message` (str, optional), `token`, `instructor_key`
  - Returns: `{"success": bool, "sent_via": list, "recipients": list, "workflow_status": dict}`

### 6.2 Member Profile Card — Onboarding Workflow

The `MemberProfileCard` component includes an **Onboarding Workflow** section in the Manage tab (instructor mode only). This section provides real-time onboarding status and action controls.

**Display:**
- Step checklist: Shows each onboarding step with label and completion status
- Progress indicator: Each incomplete step shows a "Mark Done" button
- Completed steps: Display a "Done" indicator instead of action buttons
- Loading states: All action buttons disable while an API call is in progress
- Error/success messages: Displayed inline below the action buttons

**Actions:**
- **Mark Complete**: Calls `/kiosk/api/onboarding/complete_step` with `member_id` and `step_key`
- **Send Reminder**: Calls `/kiosk/api/onboarding/send_reminder` with `member_id` and optional `message` from the note field
- **Add Note**: Adds operational context to the onboarding record (legacy endpoint)
- **Escalate**: Creates an escalation task for the first incomplete step (legacy endpoint)

**Behavior:**
- All actions set `state.onboardingBusy` flag to disable UI during the request
- Successful actions trigger a profile refresh via `onRefreshProfile()` callback
- Send Reminder reports sent channels (SMS/email) and recipient count in success message
- Note/message field clears on successful Add Note or Send Reminder
- Error states persist until next action or field edit

---

## 7. AI Layer

### 7.1 API Endpoints (ai_assistant)

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/v1/ai/health` | GET | Health check — returns service status |
| `/api/v1/ai/discover` | POST | Returns available AI tools for an intent |
| `/api/v1/ai/execute` | POST | Executes a named AI tool with parameters |

### 7.2 Components

`ai_vector` provides the vector embedding layer used for intent routing. Embeddings are stored using the `pgvector` extension on the dev PostgreSQL instance (pg17 with pgvector image).

`ai_mcp` exposes an MCP (Model Context Protocol) server, allowing external LLMs to discover and invoke Odoo-backed tools via a standard protocol.

`elevenlabs_connector` wires ElevenLabs speech-to-text + OpenAI/Gemini for hands-free voice interaction within the member portal or kiosk.

`dojo_connect_ai` implements "Kai," the AI phone receptionist. Inbound calls are processed; qualified leads are created directly in `dojo_crm`.

`dojo_ai_caller` runs outbound AI calling campaigns via ElevenLabs Conversational AI. Used for re-engagement and trial conversion campaigns.

---

## 8. Reference Data

### 8.1 Belt Ranks (16 levels)

1. White
2. Yellow
3. Advanced Yellow
4. Orange
5. Green
6. Purple
7. Blue
8. Brown
9. Red
10. Advanced Red
11. Deputy Black
12. Senior Deputy Black
13. Black — 1st Dan
14. Black — 2nd Dan
15. Black — 3rd Dan
16. Black — 4th Dan

### 8.2 Class Groups (11)

Pee Wee, Children Beginner, Children Intermediate, Children Advanced, Teen/Adult Beginner, Teen/Adult Intermediate+Advanced, BBC, Black Belt, Tournament Sparring Team, Tournament Forms Team, Leadership Training

---

## 9. Integrations

| Integration | Module | Direction | Protocol |
|---|---|---|---|
| Stripe Billing | dojo_stripe | Odoo → Stripe | Stripe API |
| Stripe Issuing | dojo_stripe | Odoo ↔ Stripe | Stripe API |
| Twilio SMS | connect | Odoo → Twilio | Twilio REST |
| Firebase/Gmail email relay | dojo_firebase | Odoo → Firebase CF → Gmail | HTTPS |
| FCM push notifications | dojo_firebase | Firebase → member portal | FCM |
| ElevenLabs STT/TTS | elevenlabs_connector | Bidirectional | WebSocket/REST |
| OpenAI / Gemini | elevenlabs_connector | Odoo → AI provider | REST |
| n8n workflow automation | (docker service) | n8n → Odoo (http://web:8069) | Odoo JSON-RPC |
| Facebook/Instagram | dojo_social | Odoo → Meta | Meta Graph API |
| NestJS Control Plane | dojo_bridge | NestJS → Odoo | JWT-secured REST |

---

## 10. Design System

### 10.1 Current State

The backend UI uses the **`dojo_theme` custom theme module** (saas~19.2.1.0.0). Design tokens are defined as CSS custom properties in `addons/dojo_theme/static/src/css/tokens.css`. The theme provides 41 tokens across 6 categories: surface colors, brand colors, typography, status colors, belt rank colors, and spacing.

**Token categories:**
- **Surfaces:** `--bg`, `--surface`, `--surface2`, `--surface3`, `--border`
- **Brand:** `--red`, `--red-dim`, `--gold`, `--gold-light`
- **Typography:** `--text`, `--text-muted`, `--text-dim`
- **Status:** `--green`, `--orange`, `--blue`
- **Belt ranks:** `--belt-white`, `--belt-yellow`, `--belt-green`, `--belt-blue`, `--belt-red`, `--belt-black`, `--belt-brown`, `--belt-purple`, `--belt-orange`, `--belt-camo`

**Typography:** Google Fonts — Bebas Neue (display), Barlow (body), Barlow Condensed (labels).

See `docs/ui-ux-guide.md` for the complete design system reference, component patterns, accessibility standards, and OWL component guidelines.

### 10.2 Target State (Design Prototype Reference)

The design direction is defined by `scope/UFT_SUPABASE_STORAGE_PHOTOS.html` — a working Supabase-backed SPA used as the visual and interaction reference for the Odoo platform UI. All implementation is in Odoo/OWL; the prototype is reference only.

**Design Tokens (from prototype):**

| Variable | Value | Use |
|---|---|---|
| `--bg` | `#0a0a0c` | Page background |
| `--surface` | `#111116` | Card / panel surface |
| `--surface2` | `#18181f` | Elevated surface |
| `--surface3` | `#1f1f2a` | Highest elevation |
| `--border` | `#2a2a38` | Borders and dividers |
| `--red` | `#e8192c` | Brand red (primary action) |
| `--red-dim` | `#9b1020` | Dimmed red (hover, disabled) |
| `--gold` | `#c9a84c` | Accent gold |
| `--gold-light` | `#f0cc6e` | Light gold (highlight) |
| `--text` | `#f0f0f5` | Primary text |
| `--text-muted` | `#6b6b80` | Secondary / muted text |
| `--text-dim` | `#9999b0` | Dimmed text |
| `--green` | `#22c55e` | Success / active |
| `--orange` | `#f97316` | Warning |
| `--blue` | `#3b82f6` | Info / link |

**Typography:**
- Display: Bebas Neue
- Body: Barlow 300–700
- Labels/Condensed: Barlow Condensed

**Layout:** 220px fixed sidebar + flex main content area + 60px topbar

### 10.3 Migration Status

**✅ Migration complete** — MuK IT modules were replaced by `dojo_theme` in REL-001 (Milestone 0 through Milestone 5, completed 2026-06-23). All 7 `muk_web_*` modules have been uninstalled and removed. The `dojo_theme` module uses plain CSS custom properties (no SCSS, no Tailwind, no external build tooling). All new UI is built in OWL components.

---

## 11. Test Environment Contract

The `testenv/` directory at the repo root provides the harness interface (see `UnattendedBuild/templates/testenv-contract.md`):

| Script | Purpose |
|---|---|
| `testenv/bootstrap.sh` | Once per VM — build image, start compose, install core modules, verify |
| `testenv/reset.sh` | Before every shot — self-escalating fast→deep reset, always ends verified-healthy |
| `testenv/verify.sh` | Health check: containers up, Odoo web responding, `odoo19` DB accessible. Exit 0 = healthy. Target < 10s. |

Gate command pattern:
```bash
docker compose run --rm --entrypoint /opt/odoo/odoo-bin web \
  -c /etc/odoo/odoo.conf -d odoo19 \
  -u <module> --test-enable --stop-after-init --workers=0
```

Health check:
```bash
curl -f http://127.0.0.1:8070/web/login
```

---

## 12. Technical Debt

| Item | Severity | Status | Notes |
|---|---|---|---|
| **MuK IT theme** | High | ✅ **Resolved** | All 7 `muk_web_*` modules uninstalled and removed (REL-001/INC-23, 2026-06-23). Replaced by `dojo_theme`. |
| **ui-ux-guide.md** | Medium | ✅ **Resolved** | `docs/ui-ux-guide.md` rewritten to document `dojo_theme` design token system (REL-001/INC-23, 2026-06-23). |
| **`theme_liquid_glass`** | Medium | **Open** | Cybrosys Technologies glassmorphism theme (v1.0) present in `addons/`. Not active in production. **Clean up — remove from addons directory.** Added to addons in error; conflicts with custom theme direction. |
| **`portalops_demo`** | Low | **Open** | Dev artifact with controllers and models, no `__manifest__.py`. Not installed in production. Remove or properly manifest before next production deploy. |
| **Stub modules** | Low | **Open** | `dojo_attendance`, `dojo_classes`, `dojo_base` — security-only directories, no manifests. Clarify intent: implement or remove. |
| **No git on production** | High | **Open** | Code manually deployed to production VM; no version tracking. Cloud SQL backups **DISABLED**. Production has no rollback path. Address in infrastructure phase. |
| **Cloud SQL backups disabled** | Critical | **Open** | `free-trial-first-project` Cloud SQL instance has backups disabled. No backup = no recovery from data loss. Enable immediately outside of any release cycle. |
| **Multi-client shared addons** | Medium | **Open** | prod and prod2 share `custom-addons/addons`. Any deployed change impacts both simultaneously. Deployment process must account for this. |

---

## 13. Changelog

See `CHANGELOG.md` in this repo root for the release-by-release history. This SPECIFICATION reflects the state at the date shown at the top of this document.
