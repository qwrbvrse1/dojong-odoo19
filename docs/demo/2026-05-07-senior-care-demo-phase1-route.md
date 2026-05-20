# Senior-Care Demo Route: Phase 1 Lock

## Goal

Define one exact demo path for a 3-5 minute senior-care operations presentation using the existing Odoo/dojo codebase as the shell.

## Current Runtime Reality

- Active database `odoo19` currently has only base/web modules installed.
- Demo surfaces exist in local source but are not yet installed in the database.
- Host-browser access to `127.0.0.1:8070` is still inconsistent, so this route is locked from authoritative local source plus live module-state inspection.

## Exact Demo Path

1. Command center
   - Surface: `dojo_core` admin dashboard
   - User-facing role in demo: senior-care operations command center
   - Primary entry:
     - Menu XML id: `dojo_core.menu_dojo_core_dashboard`
     - Action XML id: `dojo_core.action_admin_dashboard_client`
     - Client action tag: `dojo_admin_dashboard`

2. Workflow / incident progression
   - Surface: `dojo_automation` automations list, then automation builder
   - User-facing role in demo: incident response and follow-up workflow
   - Primary entry:
     - Root menu XML id: `dojo_automation.menu_root`
     - List action XML id: `dojo_automation.action_dojo_automations`
     - Builder action XML id: `dojo_automation.action_open_builder`
     - Client action tag: `dojo_automation_builder`

3. Typed copilot UI
   - Surface: `ai_assistant` full-page assistant in text mode
   - User-facing role in demo: typed care-ops copilot
   - Primary entry:
     - Root menu XML id: `ai_assistant.menu_ai_assistant_root`
     - Page menu XML id: `ai_assistant.menu_ai_voice_assistant`
     - Action XML id: `ai_assistant.action_dojo_voice_assistant_page`
     - Client action tag: `ai_assistant.voice_assistant_page`
   - Demo mode:
     - Open directly in text mode
     - Do not depend on voice capture
     - Do not depend on live model quality for acceptance

4. Architecture close
   - Surface: narrated close anchored to the typed copilot page
   - User-facing role in demo: future device/control-plane expansion
   - Live behavior required: none
   - Show as narrative only:
     - same assistant service can later back kiosk / device endpoints
     - no live Twilio / ElevenLabs / hardware / walkie flow in demo

## Show List

- `dojo_core` admin dashboard shell
- `dojo_automation` automation list
- `dojo_automation` builder timeline/canvas
- `ai_assistant` typed assistant page

## Do-Not-Show List

- `dojo_management`
  - module state is `uninstallable`
  - old dashboard path is excluded
- `dojo_kiosk`
  - no live kiosk/voice path in demo
- `connect`
  - Twilio / telephony / messaging control surfaces excluded
- `dojo_ai_caller`
  - ElevenLabs outbound calling excluded
- `dojo_connect_ai`
  - voice receptionist flow excluded
- `dojo_onboarding_stripe`, `dojo_stripe`, Stripe-linked payment flows excluded
- `dojo_firebase`, push-notification flows excluded
- martial-arts-specific surfaces outside the selected path:
  - belts
  - rank progression
  - classes/programs calendars unless reused inside the command center after reframing

## Screen Ownership Map

### 1. Command center

- Menu definitions:
  - `/Users/johnbentleyii/Projects/Clients/QWRBQL/repos/dojong-odoo19/addons/dojo_core/views/dojo_core_menus.xml`
- Action definitions:
  - `/Users/johnbentleyii/Projects/Clients/QWRBQL/repos/dojong-odoo19/addons/dojo_core/views/dojo_instructor_dashboard_views.xml`
- UI template:
  - `/Users/johnbentleyii/Projects/Clients/QWRBQL/repos/dojong-odoo19/addons/dojo_core/static/src/xml/admin_dashboard.xml`
- UI behavior:
  - `/Users/johnbentleyii/Projects/Clients/QWRBQL/repos/dojong-odoo19/addons/dojo_core/static/src/js/admin_dashboard.js`

### 2. Workflow / incident progression

- Menu/action definitions:
  - `/Users/johnbentleyii/Projects/Clients/QWRBQL/repos/dojong-odoo19/addons/dojo_automation/views/automation_menus.xml`
- Builder entry wiring:
  - `/Users/johnbentleyii/Projects/Clients/QWRBQL/repos/dojong-odoo19/addons/dojo_automation/views/automation_builder_views.xml`
- Builder UI template:
  - `/Users/johnbentleyii/Projects/Clients/QWRBQL/repos/dojong-odoo19/addons/dojo_automation/static/src/builder/builder.xml`
- Builder UI behavior:
  - `/Users/johnbentleyii/Projects/Clients/QWRBQL/repos/dojong-odoo19/addons/dojo_automation/static/src/builder/builder.js`
- Builder backend endpoints:
  - `/Users/johnbentleyii/Projects/Clients/QWRBQL/repos/dojong-odoo19/addons/dojo_automation/controllers/builder_controller.py`

### 3. Typed copilot UI

- Menu/action definitions:
  - `/Users/johnbentleyii/Projects/Clients/QWRBQL/repos/dojong-odoo19/addons/ai_assistant/views/ai_assistant_views.xml`
- Full-page UI template:
  - `/Users/johnbentleyii/Projects/Clients/QWRBQL/repos/dojong-odoo19/addons/ai_assistant/static/src/xml/dojo_voice_assistant_page.xml`
- Full-page UI behavior:
  - `/Users/johnbentleyii/Projects/Clients/QWRBQL/repos/dojong-odoo19/addons/ai_assistant/static/src/js/dojo_voice_assistant_page.js`
- HTTP endpoints:
  - `/Users/johnbentleyii/Projects/Clients/QWRBQL/repos/dojong-odoo19/addons/ai_assistant/controllers/main.py`

## Operator Flow Draft

1. Open the command center dashboard.
2. Show the top KPIs and one concise care-ops narrative.
3. Move to the workflow list.
4. Open one pre-staged workflow in the builder.
5. Explain the incident-to-follow-up progression on the workflow timeline.
6. Open the AI assistant page.
7. Use text mode only.
8. Close with the architecture story from the copilot surface.

## Branches Eliminated

- No alternate dashboard path.
- No CRM pipeline path.
- No kiosk path.
- No voice-first AI path.
- No payment, telephony, or push-notification dependency in the visible route.
