"""Post-migration: finalize sale.subscription records after ORM load.

Runs AFTER the new model definitions are loaded.  Links xmlids for
close reasons and recomputes stored computed fields.

Version bump: 19.0.4.3.0 → 19.0.5.0.0
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return

    # ──────────────────────────────────────────────────────────────────────
    # 1.  Ensure close_reason xmlids are linked
    # ──────────────────────────────────────────────────────────────────────
    # The pre-migrate may have created close reasons before data files loaded.
    # Ensure the xmlids point to the right records.
    for xmlid_name, reason_name in [
        ('close_reason_expired', 'Subscription Expired'),
        ('close_reason_cancelled', 'Subscription Cancelled'),
    ]:
        cr.execute("""
            SELECT id FROM sale_subscription_close_reason
            WHERE name = %s LIMIT 1
        """, [reason_name])
        row = cr.fetchone()
        if not row:
            continue
        reason_id = row[0]
        cr.execute("""
            SELECT id FROM ir_model_data
            WHERE module = 'dojo_subscriptions' AND name = %s
        """, [xmlid_name])
        if cr.fetchone():
            cr.execute("""
                UPDATE ir_model_data
                   SET res_id = %s
                 WHERE module = 'dojo_subscriptions' AND name = %s
            """, [reason_id, xmlid_name])
        else:
            cr.execute("""
                INSERT INTO ir_model_data (module, name, model, res_id, noupdate)
                VALUES ('dojo_subscriptions', %s, 'sale.subscription.close.reason', %s, true)
            """, [xmlid_name, reason_id])

    # ──────────────────────────────────────────────────────────────────────
    # 2.  Clean up old ir.model references
    # ──────────────────────────────────────────────────────────────────────
    cr.execute("""
        DELETE FROM ir_model_fields
        WHERE model_id IN (
            SELECT id FROM ir_model WHERE model = 'dojo.member.subscription'
        )
    """)
    cr.execute("""
        DELETE FROM ir_model_constraint
        WHERE model IN (
            SELECT id FROM ir_model WHERE model = 'dojo.member.subscription'
        )
    """)
    cr.execute("""
        DELETE FROM ir_model_relation
        WHERE model IN (
            SELECT id FROM ir_model WHERE model = 'dojo.member.subscription'
        )
    """)
    cr.execute("""
        DELETE FROM ir_model WHERE model = 'dojo.member.subscription'
    """)
    if cr.rowcount:
        _logger.info("Removed ir.model entry for dojo.member.subscription.")

    # ──────────────────────────────────────────────────────────────────────
    # 3.  Clean up old ir.model.access entries
    # ──────────────────────────────────────────────────────────────────────
    cr.execute("""
        DELETE FROM ir_model_access
        WHERE name LIKE '%%dojo_member_subscription%%'
          AND model_id NOT IN (
              SELECT id FROM ir_model WHERE model = 'sale.subscription'
          )
    """)

    # ──────────────────────────────────────────────────────────────────────
    # 4.  Clean up old views for dojo.member.subscription model
    # ──────────────────────────────────────────────────────────────────────
    cr.execute("""
        DELETE FROM ir_ui_view
        WHERE model = 'dojo.member.subscription'
    """)
    if cr.rowcount:
        _logger.info("Removed %d old views for dojo.member.subscription.", cr.rowcount)

    # ──────────────────────────────────────────────────────────────────────
    # 5.  Update old ir.actions.act_window targeting old model
    # ──────────────────────────────────────────────────────────────────────
    cr.execute("""
        UPDATE ir_act_window
           SET res_model = 'sale.subscription'
         WHERE res_model = 'dojo.member.subscription'
    """)
    if cr.rowcount:
        _logger.info("Updated %d actions from dojo.member.subscription → sale.subscription.", cr.rowcount)

    # ──────────────────────────────────────────────────────────────────────
    # 6.  Update old ir.cron references
    # ──────────────────────────────────────────────────────────────────────
    cr.execute("""
        SELECT id FROM ir_model WHERE model = 'sale.subscription' LIMIT 1
    """)
    row = cr.fetchone()
    if row:
        new_model_id = row[0]
        cr.execute("""
            SELECT id FROM ir_model WHERE model = 'dojo.member.subscription' LIMIT 1
        """)
        old_row = cr.fetchone()
        if old_row:
            cr.execute("""
                UPDATE ir_cron
                   SET model_id = %s
                 WHERE model_id = %s
            """, [new_model_id, old_row[0]])

    # ──────────────────────────────────────────────────────────────────────
    # 7.  Update old record rules
    # ──────────────────────────────────────────────────────────────────────
    cr.execute("""
        UPDATE ir_rule
           SET model_id = (SELECT id FROM ir_model WHERE model = 'sale.subscription' LIMIT 1)
         WHERE model_id IN (
             SELECT id FROM ir_model WHERE model = 'dojo.member.subscription'
         )
    """)

    _logger.info("Post-migration complete for dojo_subscriptions 19.0.5.0.0.")
