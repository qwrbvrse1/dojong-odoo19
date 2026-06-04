# Stage 2 Analysis — Admin & Instructor UI Loading Errors

## Gate Failures (from s2.sh output)

Both admin and instructor logins fail with identical JS errors:
1. **Missing module**: `@ai_assistant/js/voice_assistant` not defined
2. **Cascading failures**: `@dojo_core/js/instructor_dashboard` and `@dojo_core/js/admin_dashboard` cannot load (unmet dependency)
3. **Action registry error**: `Cannot find key "dojo_instructor_dashboard" in the "actions" registry`

Menus PASS (admin sees 17 root menus including Kiosk), so the server-side state is correct.

## Root Cause

**Module dependency mismatch**: `ai_assistant` module is **uninstalled** but `dojo_core` JavaScript imports from it.

```sql
     name     |    state    
--------------+-------------
 ai_assistant | uninstalled
 dojo_core    | installed
 dojo_kiosk   | installed
```

### Evidence Chain

1. **dojo_core/static/src/js/instructor_dashboard.js:7**
   ```javascript
   import { DojoVoiceAssistant } from "@ai_assistant/js/voice_assistant";
   ```

2. **dojo_core/static/src/js/admin_dashboard.js** — likely has same import (not yet verified but error log confirms)

3. **dojo_core/__manifest__.py** — lists `ai_assistant` assets in `web.assets_backend` BUT does NOT list `ai_assistant` in `depends`

4. Browser console → module loader cannot resolve `@ai_assistant/js/voice_assistant` → import chain breaks → dashboard components never register → action tag `dojo_instructor_dashboard` never added to registry → menu click throws KeyNotFoundError

## Secondary Issues (non-blocking for gate, but logged)

- **Websocket errors** (500s on `/websocket?version=19.0-2`): port 8072 not exposed. Non-fatal — long-polling fallback works. Out of scope per contract.

## Fix Strategy (smallest viable change)

Two options:
1. **Install `ai_assistant`** — requires checking dependencies (elevenlabs_connector, etc.), may cascade further missing modules
2. **Remove voice assistant imports from dashboards** — surgical, low risk

**Decision**: Option 2 (remove imports). Reasons:
- Installing `ai_assistant` risks new breakage (landmine from DEMO_RESCUE.md: avoid scope creep)
- Voice assistant is NOT in Phase 1 smoke checklist
- Time-boxed: <5 min fix vs unknown install + upgrade time

## Files to Change

1. `addons/dojo_core/static/src/js/instructor_dashboard.js` — remove line 7 import, remove from components list
2. `addons/dojo_core/static/src/js/admin_dashboard.js` — verify + same fix
3. `addons/dojo_core/static/src/xml/instructor_dashboard.xml` — verify template doesn't reference `<DojoVoiceAssistant/>`
4. `addons/dojo_core/static/src/xml/admin_dashboard.xml` — verify template doesn't reference `<DojoVoiceAssistant/>`

After fix: restart web container (asset bundle change) + re-run gate.

## Rollback Plan

If removing imports breaks something else:
```bash
git checkout -- addons/dojo_core/static/src/js/instructor_dashboard.js
git checkout -- addons/dojo_core/static/src/js/admin_dashboard.js
docker compose restart web
```
Then pivot to Option 1 (install ai_assistant).
