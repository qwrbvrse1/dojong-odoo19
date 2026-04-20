# -*- coding: utf-8 -*-
from . import models


def post_init_hook(env):
    """Set cron model_id after module tables are created."""
    model_rec = env['ir.model'].search([('model', '=', 'ai.vector.store')], limit=1)
    if model_rec:
        cron = env.ref('ai_vector.ir_cron_rebuild_vector_embeddings', raise_if_not_found=False)
        if cron:
            cron.model_id = model_rec


def _refresh_intent_schemas(env):
    """Force-update intent schema records that need refreshing after an upgrade.

    This is needed because the data files use noupdate=1 to avoid overwriting
    DB customisations, but certain schema improvements (like adding date support
    to schedule_today) must always propagate.
    """
    updates = [
        {
            "xmlid": "ai_vector.intent_schedule_today",
            "values": {
                "name": "Today's / Date Schedule",
                "description": (
                    "Get the class schedule for today or a specific date "
                    "(tomorrow, yesterday, or YYYY-MM-DD)"
                ),
                "parameters_schema": """{
    "type": "object",
    "properties": {
        "date": {
            "type": "string",
            "description": "Date to get schedule for. Use 'today' (default), 'tomorrow', 'yesterday', or ISO date YYYY-MM-DD"
        }
    }
}""",
                "example_phrases": (
                    "What's the schedule today?\n"
                    "Show today's classes\n"
                    "What classes are happening now?\n"
                    "What's on the schedule?\n"
                    "What do we have today?\n"
                    "Show tomorrow's schedule\n"
                    "What's on tomorrow?\n"
                    "Classes for tomorrow\n"
                    "Schedule for tomorrow\n"
                    "What classes are tomorrow?\n"
                    "What's the schedule for Monday?\n"
                    "Show schedule for 2026-04-20\n"
                    "Classes this week"
                ),
            },
        },
    ]

    IntentSchema = env["ai.intent.schema"]
    for item in updates:
        record = env.ref(item["xmlid"], raise_if_not_found=False)
        if record:
            record.write(item["values"])


def post_migrate(env, version_from, version_to):
    """Called after every upgrade — refresh pinned intent schemas."""
    _refresh_intent_schemas(env)
