# Stage 2 Plan — Remove ai_assistant Dependency from Dashboards

## Goal
Make admin & instructor dashboards load cleanly by removing the uninstalled `ai_assistant` module dependency.

## Steps

### 1. Edit instructor_dashboard.js
**File**: `addons/dojo_core/static/src/js/instructor_dashboard.js`

- **Line 7**: Delete `import { DojoVoiceAssistant } from "@ai_assistant/js/voice_assistant";`
- **Line 12**: Change `static components = { DojoVoiceAssistant, MiniCalendar };` to `static components = { MiniCalendar };`

**Rollback**: `git checkout -- addons/dojo_core/static/src/js/instructor_dashboard.js`

### 2. Edit admin_dashboard.js
**File**: `addons/dojo_core/static/src/js/admin_dashboard.js`

- **Line 6**: Delete `import { DojoVoiceAssistant } from "@ai_assistant/js/voice_assistant";`
- **Line 11**: Change `static components = { DojoVoiceAssistant, MiniCalendar };` to `static components = { MiniCalendar };`

**Rollback**: `git checkout -- addons/dojo_core/static/src/js/admin_dashboard.js`

### 3. Edit instructor_dashboard.xml
**File**: `addons/dojo_core/static/src/xml/instructor_dashboard.xml`

- **Line 411**: Delete or comment `<DojoVoiceAssistant/>`

**Rollback**: `git checkout -- addons/dojo_core/static/src/xml/instructor_dashboard.xml`

### 4. Edit admin_dashboard.xml
**File**: `addons/dojo_core/static/src/xml/admin_dashboard.xml`

- **Line 481**: Delete or comment `<DojoVoiceAssistant/>`

**Rollback**: `git checkout -- addons/dojo_core/static/src/xml/admin_dashboard.xml`

### 5. Restart web container
**Command**: `docker compose restart web`

Asset bundle changes require a restart to take effect. The browser will fetch the new compiled bundle.

**Rollback**: N/A (restart is always safe)

### 6. Clear browser cache (optional but recommended)
The gate script runs in a fresh Playwright context, so this only matters for manual verification.

### 7. Install Playwright in orchestrator directory
**Command**: 
```bash
cd /home/ainzellan/demo_rescue && npm install playwright && npx playwright install chromium
```

The orchestrator runs gate scripts from `/home/ainzellan/demo_rescue/verify/` which needs its own playwright installation. ESM module resolution doesn't automatically find global node_modules without a local package.json.

**Rollback**: N/A (installation is additive)

### 8. Run gate verification
**Command**: `bash scripts/demo_rescue/verify/s2.sh`

**Expected**: 
- PASS: browser smoke: admin UI loads, no JS errors
- PASS: browser smoke: instructor UI loads, no JS errors
- PASS: admin sees ≥6 root menus
- PASS: Kiosk root menu present
- GATE: PASSED

**If gate still fails**: Check gate output for NEW errors. If errors reference different missing modules/imports, repeat analysis cycle. If errors persist on same modules, revert all 4 files and escalate.

### 9. Commit
**Command**: `git add -A && git commit -m "rescue S2: remove ai_assistant dependency from core dashboards"`

Only commit if gate passes.

## Time Budget
- Edits: 3 minutes
- Restart + gate: 2 minutes
- **Total**: 5 minutes (well under 15-minute time-box)

## Risk Assessment
**Low**. Removing unused UI component from dashboards. Voice assistant is not part of Phase 1 smoke checklist. If this creates unexpected breakage (unlikely), the rollback is four `git checkout` commands.

## Success Criteria
Gate passes with zero JS console errors for both admin@demo.com and instructor1@demo.com.
