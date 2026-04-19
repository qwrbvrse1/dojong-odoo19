# -*- coding: utf-8 -*-
from . import models


def post_init_hook(env):
    """Set cron model_id after module tables are created."""
    model_rec = env['ir.model'].search([('model', '=', 'ai.vector.store')], limit=1)
    if model_rec:
        cron = env.ref('ai_vector.ir_cron_rebuild_vector_embeddings', raise_if_not_found=False)
        if cron:
            cron.model_id = model_rec
