from . import models
from . import controllers


def post_init_hook(env):
    """Hide ``automation_oca`` from the Apps list.

    The OCA module is a hidden technical dependency of dojo_automation; the
    user-facing entry point is the "Automations" top-level menu owned by
    this module.
    """
    oca = env["ir.module.module"].search([("name", "=", "automation_oca")], limit=1)
    if oca:
        oca.write({"application": False})
