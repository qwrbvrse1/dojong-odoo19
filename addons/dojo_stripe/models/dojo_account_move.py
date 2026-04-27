import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .dojo_member_subscription_stripe import _is_connection_error

_logger = logging.getLogger(__name__)


class DojoStripeAccountMove(models.Model):
    _inherit = "account.move"

    dojo_auto_charge_deferred = fields.Boolean(
        string="Deferred Stripe Charge",
        copy=False,
        readonly=True,
    )
    dojo_auto_charge_scheduled_date = fields.Date(
        string="Scheduled Stripe Charge Date",
        copy=False,
        readonly=True,
        index=True,
    )
    dojo_auto_charge_notice_sent = fields.Boolean(copy=False, readonly=True)
    dojo_auto_charge_sms_sent = fields.Boolean(copy=False, readonly=True)
    dojo_auto_charge_attempted_at = fields.Datetime(copy=False, readonly=True)
    dojo_auto_charge_last_error = fields.Char(copy=False, readonly=True)

    def _get_dojo_linked_subscriptions(self):
        self.ensure_one()
        return (self.subscription_id | self.dojo_subscription_ids).exists()

    def _get_dojo_billing_household(self):
        self.ensure_one()
        if self.partner_id and self.partner_id.is_household:
            return self.partner_id
        household = self.partner_id.parent_id
        if household and household.is_household:
            return household
        subscriptions = self._get_dojo_linked_subscriptions()
        if subscriptions:
            household = subscriptions[0].member_id.partner_id.parent_id
            if household and household.is_household:
                return household
        return self.env["res.partner"].browse()

    def _has_dojo_blocking_charge_transaction(self):
        self.ensure_one()
        transactions = self.transaction_ids.filtered(
            lambda tx: tx.provider_code == 'stripe' and tx.operation == 'offline'
        )
        return bool(transactions.filtered(lambda tx: tx.state in ('pending', 'authorized', 'done')))

    def action_schedule_dojo_auto_charge(self, scheduled_date):
        self.ensure_one()
        if not scheduled_date:
            return False
        self.sudo().write({
            'dojo_auto_charge_deferred': True,
            'dojo_auto_charge_scheduled_date': scheduled_date,
            'dojo_auto_charge_notice_sent': False,
            'dojo_auto_charge_sms_sent': False,
            'dojo_auto_charge_last_error': False,
            'invoice_date_due': scheduled_date,
        })
        return True

    def _send_dojo_deferred_charge_email(self):
        self.ensure_one()
        if self.dojo_auto_charge_notice_sent or not self.partner_id.email:
            return False
        company_name = self.company_id.name or 'the Dojang'
        scheduled_date = self.dojo_auto_charge_scheduled_date or self.invoice_date_due
        body_html = _(
            '<p>Hi %(name)s,</p>'
            '<p>Your invoice <strong>%(invoice)s</strong> for <strong>%(amount)s</strong> '
            'has been created by %(company)s.</p>'
            '<p>The saved card on file will be charged on <strong>%(scheduled)s</strong>. '
            'If you want to update your payment method before then, please do so before that date.</p>'
            '<p>If you have questions, reply to this email and we can help.</p>',
            name=self.partner_id.name or '',
            invoice=self.name or '',
            amount=self.currency_id and self.amount_total and self.currency_id.symbol
            and '%s %.2f' % (self.currency_id.symbol, self.amount_total)
            or self.amount_total,
            company=company_name,
            scheduled=scheduled_date,
        )
        try:
            self.env['mail.mail'].sudo().create({
                'subject': _(
                    '%(company)s invoice %(invoice)s — saved card will charge in 3 days',
                    company=company_name,
                    invoice=self.name or 'n/a',
                ),
                'body_html': body_html,
                'email_to': self.partner_id.email,
                'email_from': (
                    self.invoice_user_id.email_formatted
                    or self.company_id.email_formatted
                    or self.env.user.email_formatted
                ),
                'author_id': self.env.user.partner_id.id,
                'model': 'account.move',
                'res_id': self.id,
            }).send()
            self.sudo().write({'dojo_auto_charge_notice_sent': True})
            return True
        except Exception:
            _logger.warning(
                'Dojo Stripe: could not send deferred charge invoice email for %s.',
                self.name,
                exc_info=True,
            )
            return False

    def _send_dojo_deferred_charge_sms(self):
        self.ensure_one()
        if self.dojo_auto_charge_sms_sent:
            return False
        mobile = getattr(self.partner_id, 'mobile', None) or self.partner_id.phone
        if not mobile:
            return False
        scheduled_date = self.dojo_auto_charge_scheduled_date or self.invoice_date_due
        body_plain = _(
            'Hi %(name)s, your invoice %(invoice)s for %(amount)s is ready. '
            'The saved card on file will be charged on %(scheduled)s. '
            'Update your payment method before then if needed.',
            name=self.partner_id.name or '',
            invoice=self.name or '',
            amount=self.currency_id and self.amount_total and self.currency_id.symbol
            and '%s %.2f' % (self.currency_id.symbol, self.amount_total)
            or self.amount_total,
            scheduled=scheduled_date,
        )
        try:
            self.env['sms.sms'].create({
                'number': mobile,
                'body': body_plain,
                'partner_id': self.partner_id.id,
            }).send()
            self.sudo().write({'dojo_auto_charge_sms_sent': True})
            return True
        except Exception:
            _logger.warning(
                'Dojo Stripe: could not send deferred charge SMS for %s.',
                self.name,
                exc_info=True,
            )
            return False

    def action_send_dojo_deferred_charge_notifications(self):
        self.ensure_one()
        if not self.dojo_auto_charge_deferred:
            return False
        email_sent = self._send_dojo_deferred_charge_email()
        sms_sent = self._send_dojo_deferred_charge_sms()
        return email_sent or sms_sent

    @api.model
    def _cron_charge_deferred_dojo_invoices(self):
        today = fields.Date.today()
        invoices = self.search([
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('dojo_auto_charge_deferred', '=', True),
            ('dojo_auto_charge_scheduled_date', '!=', False),
            ('dojo_auto_charge_scheduled_date', '<=', today),
            ('payment_state', 'in', ('not_paid', 'partial')),
        ])
        for invoice in invoices:
            if invoice._has_dojo_blocking_charge_transaction():
                continue

            household = invoice._get_dojo_billing_household()
            subscriptions = invoice._get_dojo_linked_subscriptions()
            if not household:
                message = _('No household found for deferred charge invoice %s.') % invoice.name
                invoice.sudo().write({'dojo_auto_charge_last_error': message})
                _logger.warning('Dojo Stripe: %s', message)
                continue

            invoice.sudo().write({
                'dojo_auto_charge_attempted_at': fields.Datetime.now(),
                'dojo_auto_charge_last_error': False,
            })
            try:
                tx = household.action_charge_invoice(invoice)
            except UserError as exc:
                invoice.sudo().write({'dojo_auto_charge_last_error': str(exc)})
                if _is_connection_error(exc):
                    _logger.warning(
                        'Dojo Stripe: connection error charging deferred invoice %s — will retry: %s',
                        invoice.name,
                        exc,
                    )
                    continue
                for subscription in subscriptions:
                    subscription._handle_billing_failure(exc)
                continue
            except Exception as exc:
                invoice.sudo().write({'dojo_auto_charge_last_error': str(exc)})
                if _is_connection_error(exc):
                    _logger.warning(
                        'Dojo Stripe: connection error charging deferred invoice %s — will retry: %s',
                        invoice.name,
                        exc,
                    )
                    continue
                _logger.error(
                    'Dojo Stripe: unexpected error charging deferred invoice %s: %s',
                    invoice.name,
                    exc,
                    exc_info=True,
                )
                for subscription in subscriptions:
                    subscription._handle_billing_failure(exc)
                continue

            state = tx.state if tx else ''
            if state == 'done':
                for subscription in subscriptions:
                    if subscription.billing_failure_count:
                        subscription._reset_billing_failures()
                invoice.sudo().write({'dojo_auto_charge_last_error': False})
                _logger.info(
                    'Dojo Stripe: deferred auto-charge succeeded for invoice %s.',
                    invoice.name,
                )
            elif state == 'error':
                error_msg = getattr(tx, 'state_message', None) or 'Stripe payment failed'
                invoice.sudo().write({'dojo_auto_charge_last_error': error_msg})
                exc = UserError(_(error_msg))
                for subscription in subscriptions:
                    subscription._handle_billing_failure(exc)
            else:
                _logger.info(
                    'Dojo Stripe: deferred auto-charge transaction %s for invoice %s is %r.',
                    tx.id if tx else 'N/A',
                    invoice.name,
                    state,
                )