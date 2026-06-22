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

### 3.4 MuK IT Theme (Active — Scheduled for Replacement)

Seven modules from MuK IT providing the current backend UI theme. All targeted for retirement when the custom OWL/plain-CSS theme module is delivered.

| Module | Version |
|---|---|
| `muk_web_theme` | saas~19.2.1.4.2 |
| `muk_web_chatter` | saas~19.2.1.4.2 |
| `muk_web_appsbar` | saas~19.2.1.1.5 |
| `muk_web_colors` | saas~19.2.1.0.5 |
| `muk_web_dialog` | saas~19.2.1.0.5 |
| `muk_web_refresh` | saas~19.2.1.0.5 |
| `muk_web_group` | saas~19.2.1.0.2 |

### 3.5 Stub / Reserved Modules

The following directories exist in `addons/` but contain only an `access_rights` security file and no `__manifest__.py`. They appear to be placeholder namespaces reserved for future implementation.

- `dojo_attendance`
- `dojo_belt_progression`
- `dojo_classes`
- `dojo_members`
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

### 5.2 Kiosk (dojo_kiosk)

Tablet check-in interface. Members check in via PIN or QR code. Action log tracks every check-in/check-out event. Kiosk carousel displays marketing announcements. Parent SMS alerts fire on check-in via `dojo_communications`. Config record is per-location. See Section 7 for full kiosk detail.

### 5.3 Subscriptions (dojo_subscriptions + subscription_oca)

Subscription plans map to Odoo recurring invoices via `subscription_oca`. `dojo_subscriptions` adds the dojo-specific plan definitions and program enrollment records. Stripe integration via `dojo_stripe` handles payment collection.

### 5.4 Onboarding (dojo_onboarding + dojo_onboarding_stripe + dojo_sign)

Multi-step wizard: collect member info → sign waiver (`dojo_sign`) → select subscription plan → collect Stripe payment method (`dojo_onboarding_stripe`) → create member record. Wizard state persisted in `dojo.onboarding.record` to allow resume on disconnection.

### 5.5 CRM (dojo_crm)

Pipeline stages, lead scoring, trial lesson booking. Leads sourced from website trial forms (`dojo_website`), AI phone calls (`dojo_connect_ai`), and manual entry. Convert-to-member action promotes a won lead directly into the onboarding flow. Automation rules managed via `dojo_automation`.

### 5.6 Communications (dojo_communications + dojo_firebase + connect)

Automated SMS via Twilio (`connect` module). Email relay via Firebase Cloud Functions / Gmail (`dojo_firebase`). FCM web push to the member portal. Triggers: check-in parent alerts, class session reminders, instructor messages.

### 5.7 Marketing (dojo_marketing)

Promotional cards with embedded QR codes. Cards appear in the kiosk carousel and member portal. QR codes deep-link to website pages or trial forms.

### 5.8 Points and Credits (dojo_points + dojo_credits)

`dojo_points`: auto-award points on attendance (streak bonuses), belt promotions, and configured events. `dojo_credits`: class credit ledger for drop-in and prepaid class packs. Both integrate with the member portal.

### 5.9 Calendar (dojo_calendar + dojo_events)

Class sessions sync to `calendar.event` for visibility in the Odoo calendar view. `dojo_events` links members to Odoo native Events (tournaments, seminars).

### 5.10 Automation Builder (dojo_automation)

Spark-Membership-style visual automation builder: trigger → condition → action chains. Drives communications and points awards without code changes.

### 5.11 Social (dojo_social)

Facebook/Instagram post scheduling from inside Odoo. Allows dojos to schedule social media content around events and promotions.

### 5.12 Member Portal (dojo_members_portal)

Self-service portal for parents and students. Shows attendance history, belt rank, points, credits, upcoming classes. Receives FCM push notifications. Public checkout flow via `dojo_checkout`.

### 5.13 Website (dojo_website)

Custom dojang public website with trial lesson booking forms. Forms submit leads into `dojo_crm`.

### 5.14 Stripe (dojo_stripe)

Stripe Billing for subscription recurring payments. Stripe Issuing for dojo employee/instructor cards. Payment method collection during onboarding via `dojo_onboarding_stripe`.

### 5.15 API Bridge (dojo_bridge)

Headless REST API. Exposes versioned, stateless endpoints secured by HS256 JWTs. Intended to allow a NestJS Control Plane or other external clients to drive Odoo as the Business Plane without coupling to Odoo's web client.

### 5.16 Checkout (dojo_checkout)

Public-facing checkout pages: plan selection, day picker, optional upsells, invoice or pay-now flow, portal account upgrade. Operates without requiring a logged-in Odoo session.

### 5.17 Data Migration (dojo_migration)

Admin-only tool. Imports SparkMembership CSV exports into the dojo data model. One-time use per operator onboarding.

---

## 6. Kiosk Detail

The kiosk is a full-screen tablet application running in Odoo's web client, served from `dojo_kiosk`.

**Check-in flow**: Member enters PIN or scans QR code → kiosk resolves identity via `dojo.kiosk.service` → creates `dojo.attendance.log` record → fires `dojo_communications` SMS to parent (configurable) → shows confirmation screen with member photo, name, and belt rank.

**Carousel**: Marketing announcements from `dojo.kiosk.announcement` rotate between check-ins.

**Security**: `dojo.kiosk.pin.attempt` tracks failed PIN attempts and triggers lockout after threshold. The kiosk config record (`dojo.kiosk.config`) is per-location with configurable timeouts and announcement interval.

**Photo display**: Member photos are stored in Odoo's `ir.attachment` (binary field on `dojo.member`). The design prototype (`UFT_SUPABASE_STORAGE_PHOTOS.html`) used Supabase Storage as a reference design; production implementation stores photos in Odoo.

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

The backend UI currently uses the **MuK IT theme** (`muk_web_theme` + 6 supporting modules). Design tokens are MuK-defined CSS custom properties (`--primary`, `--surface`, `--border`, `--text-primary`, etc.). See `docs/ui-ux-guide.md` for the current token reference.

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

### 10.3 Migration Plan

The MuK IT modules will be replaced incrementally by a new custom OWL theme module (REL-001, Milestone 0 through Milestone 5). Implementation approach: plain CSS custom properties (no SCSS, no Tailwind, no external build tooling). OWL components for all new UI elements. MuK modules retired incrementally as OWL equivalents are validated.

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

| Item | Severity | Notes |
|---|---|---|
| **MuK IT theme** | High | 7 `muk_web_*` modules active. Replace with custom OWL/plain-CSS theme. Planned for Milestone 5 (MuK Retirement). |
| **`theme_liquid_glass`** | Medium | Cybrosys Technologies glassmorphism theme (v1.0) present in `addons/`. Not active in production. **Clean up — remove from addons directory.** Added to addons in error; conflicts with planned custom theme direction. |
| **`portalops_demo`** | Low | Dev artifact with controllers and models, no `__manifest__.py`. Not installed in production. Remove or properly manifest before next production deploy. |
| **Stub modules** | Low | `dojo_attendance`, `dojo_belt_progression`, `dojo_classes`, `dojo_members`, `dojo_base` — security-only directories, no manifests. Clarify intent: implement or remove. |
| **No git on production** | High | Code manually deployed to production VM; no version tracking. Cloud SQL backups **DISABLED**. Production has no rollback path. Address in infrastructure phase. |
| **Cloud SQL backups disabled** | Critical | `free-trial-first-project` Cloud SQL instance has backups disabled. No backup = no recovery from data loss. Enable immediately outside of any release cycle. |
| **ui-ux-guide.md** | Medium | `docs/ui-ux-guide.md` documents MuK design tokens. Must be updated to reflect new token system as part of the theme migration release. |
| **Multi-client shared addons** | Medium | prod and prod2 share `custom-addons/addons`. Any deployed change impacts both simultaneously. Deployment process must account for this. |

---

## 13. Changelog

See `CHANGELOG.md` in this repo root for the release-by-release history. This SPECIFICATION reflects the state at the date shown at the top of this document.
