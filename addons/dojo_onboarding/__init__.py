from . import models


def post_init_hook(env):
    """Migrate existing onboarding records to lifecycle steps."""
    records = env['dojo.onboarding.record'].search([])
    for rec in records:
        # Grandfather completed records: set manual steps to True
        if rec.state == 'completed':
            rec.write({
                'step_intro_completed': True,
                'step_uniform_issued': True,
            })
        # Sync derived steps from current member state
        rec._sync_derived_steps()
