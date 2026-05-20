import json

user = env.ref("base.user_admin")
ActionLog = env["ai.action.log"].sudo()

entries = [
    {
        "session_key": "demo-copilot-rounds",
        "input_text": "Summarize today's North Wing rounds and flag anyone needing follow-up.",
        "intent_type": "schedule_today",
        "confidence": 0.94,
        "execution_result": {
            "summary": "North Wing has one active round today. Walter Scott remains on fall-monitoring follow-up, and Lila Thompson is in first-week observation.",
        },
    },
    {
        "session_key": "demo-copilot-family",
        "input_text": "What family continuity update is pending for Walter Scott?",
        "intent_type": "task_list",
        "confidence": 0.91,
        "execution_result": {
            "summary": "Family continuity update is scheduled for the next day after the first follow-up round, with Nina Scott as the primary contact.",
        },
    },
]

for entry in entries:
    log = ActionLog.search([("session_key", "=", entry["session_key"])], limit=1)
    vals = {
        "session_key": entry["session_key"],
        "user_id": user.id,
        "role": "admin",
        "input_type": "text",
        "input_text": entry["input_text"],
        "intent_type": entry["intent_type"],
        "confidence": entry["confidence"],
        "requires_confirmation": False,
        "confirmation_status": "auto",
        "execution_status": "success",
        "execution_result": json.dumps(entry["execution_result"]),
        "is_undoable": False,
    }
    if log:
        log.write(vals)
    else:
        ActionLog.create(vals)

env.cr.commit()
print("Copilot history staged")
