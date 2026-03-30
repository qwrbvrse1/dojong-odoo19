from odoo import _, api, models
from odoo.exceptions import ValidationError


class DojoClassEnrollment(models.Model):
    _inherit = 'dojo.class.enrollment'

    @api.constrains('session_id', 'member_id', 'status')
    def _check_subscription_constraints(self):
        # Allow cron session generation, auto-enroll, and onboarding wizard to
        # bypass this constraint — they always create the subscription first.
        if self.env.context.get('skip_subscription_check'):
            return
        for rec in self:
            if rec.status != 'registered':
                continue

            member = rec.member_id
            template = rec.session_id.template_id

            # ── Rule 1: an active subscription is required ─────────────────
            active_subs = self.env['sale.subscription'].search([
                ('member_id', '=', member.id),
                ('state', '=', 'active'),
            ])
            if not active_subs:
                raise ValidationError(_(
                    'A subscription is required to enrol in sessions. '
                    'Please set up a subscription for %s before enrolling.',
                    member.name,
                ))

            # ── Rule 2: at least one plan must permit this class ───────────
            # - Program-based: template's program_id must match sub's program_id
            # - Course-based: template must be in allowed_template_ids (or list empty = all)
            permitting_subs = []
            for sub in active_subs:
                plan = sub.plan_id
                if plan.plan_type == 'program':
                    if sub.program_id and template.program_id == sub.program_id:
                        permitting_subs.append(sub)
                else:  # course-based
                    if not plan.allowed_template_ids or template in plan.allowed_template_ids:
                        permitting_subs.append(sub)

            if not permitting_subs:
                plan_names = ', '.join(s.plan_id.name for s in active_subs)
                raise ValidationError(_(
                    'The class "%s" is not included in the current subscription plan(s): %s.\n'
                    'For Program-Based plans the class must belong to the subscribed program. '
                    'For Course-Based plans the class must be listed in the allowed courses.',
                    template.name, plan_names,
                ))



