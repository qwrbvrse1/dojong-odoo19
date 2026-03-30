from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    # subscription_id is already defined by subscription_oca → sale.subscription
    # We only add the M2m for household-consolidated invoices.
    dojo_subscription_ids = fields.Many2many(
        "sale.subscription",
        "dojo_invoice_sub_rel",
        "invoice_id",
        "subscription_id",
        string="Dojang Subscriptions",
        help="All subscriptions included in this consolidated household invoice.",
    )

    def _compute_payment_state(self):
        if self.ids:
            self.env.cr.execute(
                "SELECT id, payment_state FROM account_move WHERE id = ANY(%s)",
                (list(self.ids),),
            )
            old_states = dict(self.env.cr.fetchall())
        else:
            old_states = {}

        super()._compute_payment_state()

        pending_subs = self.env['sale.subscription']
        for move in self:
            old = old_states.get(move.id)
            if old not in ('paid', 'in_payment') and move.payment_state in ('paid', 'in_payment'):
                if move.subscription_id and move.subscription_id.state == 'pending':
                    pending_subs |= move.subscription_id
                for sub in move.dojo_subscription_ids.filtered(lambda s: s.state == 'pending'):
                    pending_subs |= sub

        for sub in pending_subs:
            sub.sudo().action_set_active()
