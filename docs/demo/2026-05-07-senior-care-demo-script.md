# Senior-Care Demo Script

## Login

- URL: local Odoo demo instance
- Database: `odoo19`
- Username: `admin`
- Password: `admin`

## Primary Script

### 1. Command Center

- Click `Care Operations` -> `Command Center`.
- Say: "This is the senior-care operations command center. We can see who is on duty, today's active rounds, check-in completion, and the current escalation watchlist."
- Point out:
  - `Staff On Duty`: 2
  - `Active Residents`: 4
  - `Rounds Today`: 1
  - `Escalations Open`: 1
- Mention the visible resident names:
  - Evelyn Parker
  - Walter Scott
  - Ruth Alvarez
  - James Holloway
  - Lila Thompson

### 2. Incident Workflow

- Click `Care Workflows` -> `Care Workflows`.
- Open `Fall Incident Continuity Workflow`.
- Say: "This workflow is pre-staged for a fall-related continuity event. It starts with clinical triage, routes a charge-nurse follow-up, prepares a family update, and closes the compliance trail."
- Point out the response timeline:
  - `Immediate clinical triage`
  - `Assign charge nurse follow-up`
  - `Family continuity update`
  - `Compliance closeout review`
- Anchor the story to Walter Scott in the command-center escalation list.

### 3. Typed Copilot

- Click `Care Copilot` -> `Copilot Console`.
- Say: "The copilot is intentionally typed-first for this demo. It sits in the same operations shell and can summarize rounds or surface continuity context without requiring voice."
- Show:
  - typed input box
  - `Typed Mode` badge
  - recent activity entries for rounds and family continuity

### 4. Architecture Close

- Say: "What we are showing live is the local typed command surface. The same architecture can later fan out to kiosk, device, and control-plane integrations, but this demo stays on the stable local operations path."

## Fallback Script

- If the copilot page is skipped, stop after the workflow builder.
- Say: "The same workflow state can be surfaced in the typed copilot, but for reliability we can stay on the command-center and workflow views."

## Do Not Click

- `Settings`
- `Billing`
- `Trigger Templates`
- belt or rank configuration surfaces
- any voice, kiosk, telephony, Stripe, Firebase, or external integration paths

## Time Box

- Command Center: 60-90 seconds
- Workflow: 90-120 seconds
- Copilot: 45-60 seconds
- Architecture close: 30-45 seconds

## Stability Notes

- The workflow is intentionally staged, not dependent on live outbound messaging.
- The copilot acceptance is UI presence plus typed interaction, not live model quality.
- If host browser networking is inconsistent, rely on the already-verified local stack state rather than restarting services mid-demo.
