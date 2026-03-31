"""
pre-migrate.py — saas~19.2.6.0.0

Converts dojo.subscription.plan's program_id (Many2one) to program_ids (Many2many)
by creating the junction table and copying existing plan→program pairs into it.

The old `program_id` column on dojo_subscription_plan is intentionally left in
place — Odoo never auto-drops columns, and the column becomes harmless orphaned
data once the ORM no longer references it.
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    # Create the junction table (idempotent — IF NOT EXISTS).
    cr.execute("""
        CREATE TABLE IF NOT EXISTS dojo_sub_plan_program_rel (
            plan_id    INTEGER NOT NULL
                       REFERENCES dojo_subscription_plan(id) ON DELETE CASCADE,
            program_id INTEGER NOT NULL
                       REFERENCES dojo_program(id) ON DELETE CASCADE,
            PRIMARY KEY (plan_id, program_id)
        );
    """)

    # Seed it from the existing Many2one column, skipping any rows where
    # program_id is NULL (plans that had no program assigned).
    cr.execute("""
        INSERT INTO dojo_sub_plan_program_rel (plan_id, program_id)
        SELECT id, program_id
        FROM   dojo_subscription_plan
        WHERE  program_id IS NOT NULL
        ON CONFLICT DO NOTHING;
    """)

    _logger.info(
        "dojo_subscriptions saas~19.2.6.0.0: seeded %d plan→program row(s) "
        "into dojo_sub_plan_program_rel",
        cr.rowcount,
    )
