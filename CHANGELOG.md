# CHANGELOG — dojong-odoo19

Format: one entry per Release (`REL-NNN`). Each entry is written after the release audit and merge.  
Conventions: see `UnattendedBuild/templates/spec-changelog-conventions.md`.  
Full run history: `workproducts/<project>/REL-NNN/runlog.jsonl`.

---

## [Unreleased]

*(Increments merged to `main` outside a formal release cycle — pre-method work.)*

### Added
- `dojo_core` (saas~19.2.4.0.0) — member management, classes, attendance, belt progression, instructor dashboard
- `dojo_kiosk` (saas~19.2.1.1.0) — tablet check-in kiosk
- `dojo_subscriptions` (saas~19.2.6.0.0) — membership plans and subscriptions
- `dojo_onboarding` (saas~19.2.1.0.0) — member onboarding wizard
- `dojo_onboarding_stripe` (saas~19.2.1.0.0) — Stripe payment method collection during onboarding
- `dojo_crm` (saas~19.2.2.0.0) — CRM pipeline, lead scoring, trial booking, convert-to-member
- `dojo_communications` (saas~19.2.1.0.0) — automated SMS/email communications
- `dojo_marketing` (saas~19.2.3.0.0) — QR promotional cards
- `dojo_sign` (saas~19.2.2.0.0) — inline waiver signing
- `dojo_stripe` (saas~19.2.2.0.0) — Stripe Billing + Stripe Issuing
- `dojo_members_portal` (saas~19.2.3.0.0) — self-service member portal
- `dojo_website` (saas~19.2.1.0.0) — public website with trial booking
- `dojo_events` (saas~19.2.1.0.0) — member-to-events linking
- `dojo_calendar` (saas~19.2.1.0.0) — class session calendar sync
- `dojo_automation` (saas~19.2.1.1.0) — visual automation builder
- `dojo_points` (saas~19.2.1.0.0) — attendance/achievement points
- `dojo_credits` (saas~19.2.1.0.0) — class credit ledger
- `dojo_social` (saas~19.2.1.0.0) — social media post scheduling
- `dojo_connect_ai` (saas~19.2.1.0.0) — AI receptionist (Kai)
- `dojo_bridge` (saas~19.2.2.0.0) — headless REST API bridge
- `dojo_checkout` (saas~19.2.2.0.0) — public checkout pages
- `dojo_firebase` (saas~19.2.1.0.0) — Firebase email relay + FCM push
- `dojo_management` (saas~19.2.1.0.0) — belt ranking analytics
- `dojo_migration` (saas~19.2.1.0.0) — SparkMembership CSV import
- `ai_assistant` (saas~19.2.1.0.0) — AI voice assistant service
- `ai_vector` (saas~19.2.1.0.0) — vector embedding layer
- `ai_mcp` (saas~19.2.1.0.0) — MCP server
- `elevenlabs_connector` (saas~19.2.1.0.0) — ElevenLabs voice integration
- `dojo_ai_caller` (saas~19.2.1.0.0) — AI outbound calling
- MuK IT theme (`muk_web_theme` + 6 supporting modules, saas~19.2.x)
- Third-party: `automation_oca`, `subscription_oca`, `bi_all_digital_sign`, `connect` (Twilio)

---

<!--
RELEASE ENTRY TEMPLATE (copy for each REL-NNN):

## [REL-NNN] — YYYY-MM-DD — <short release title>

### Added
- `module_name` (version) — brief description of new behavior

### Changed
- `module_name` — what changed and why

### Fixed
- `module_name` — what was broken, what the fix is

### Removed
- `module_name` — what was removed and why

### Technical Debt Addressed
- List any tech-debt items from SPECIFICATION.md § 12 resolved by this release

### Deferred
- List any increments that did not pass (partial release)

Audited by: <auditor> on <date>
-->
