from odoo import api, fields, models


class DojoOnboardingRecord(models.Model):
    _name = 'dojo.onboarding.record'
    _description = 'Member Onboarding Record'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _rec_name = 'member_id'

    member_id = fields.Many2one(
        'dojo.member',
        string='Member',
        required=True,
        ondelete='cascade',
        index=True,
    )
    company_id = fields.Many2one('res.company', string='Company', index=True)

    state = fields.Selection(
        selection=[
            ('in_progress', 'In Progress'),
            ('completed', 'Completed'),
        ],
        default='in_progress',
        required=True,
        tracking=True,
    )

    # Step completion flags (legacy data-entry steps, kept for compatibility)
    step_member_info = fields.Boolean('Member Info', default=False)
    step_household = fields.Boolean('Household', default=False)
    step_enrollment = fields.Boolean('Class Enrollment', default=False)
    step_subscription = fields.Boolean('Subscription', default=False)
    step_portal_access = fields.Boolean('Portal Access', default=False)

    # Lifecycle step completion flags (derived + manual)
    step_trial_booked = fields.Boolean('Trial Booked', default=False)
    step_waiver_signed = fields.Boolean('Waiver Signed', default=False)
    step_intro_completed = fields.Boolean('Intro Session Completed', default=False)
    step_membership_activated = fields.Boolean('Membership Activated', default=False)
    step_uniform_issued = fields.Boolean('Uniform Issued', default=False)

    progress_pct = fields.Integer(
        string='Progress (%)',
        compute='_compute_progress',
        store=True,
    )

    missing_steps = fields.Char(
        string='Missing Steps',
        compute='_compute_missing_steps',
        store=True,
    )

    @api.depends(
        'step_trial_booked', 'step_waiver_signed', 'step_intro_completed',
        'step_membership_activated', 'step_uniform_issued',
    )
    def _compute_progress(self):
        lifecycle_steps = [
            'step_trial_booked', 'step_waiver_signed', 'step_intro_completed',
            'step_membership_activated', 'step_uniform_issued',
        ]
        for rec in self:
            completed = sum(1 for s in lifecycle_steps if getattr(rec, s))
            rec.progress_pct = int(completed / len(lifecycle_steps) * 100)

    @api.depends(
        'step_trial_booked', 'step_waiver_signed', 'step_intro_completed',
        'step_membership_activated', 'step_uniform_issued',
    )
    def _compute_missing_steps(self):
        step_labels = {
            'step_trial_booked': 'Trial Booked',
            'step_waiver_signed': 'Waiver Signed',
            'step_intro_completed': 'Intro Completed',
            'step_membership_activated': 'Membership Activated',
            'step_uniform_issued': 'Uniform Issued',
        }
        for rec in self:
            missing = [label for key, label in step_labels.items() if not getattr(rec, key)]
            rec.missing_steps = ', '.join(missing) if missing else ''

    def _sync_derived_steps(self):
        """Sync derived lifecycle steps from member state."""
        for rec in self:
            member = rec.member_id
            if not member:
                continue

            # step_waiver_signed: check dojo_sign fields if available
            if hasattr(member, 'waiver_signed_on'):
                rec.step_waiver_signed = bool(member.waiver_signed_on)
            elif hasattr(member, 'has_signed_waiver'):
                rec.step_waiver_signed = bool(member.has_signed_waiver)

            # step_membership_activated: active membership
            rec.step_membership_activated = (member.membership_state == 'active')

            # step_trial_booked: trial or active state (CRM booking check omitted for now)
            rec.step_trial_booked = (member.membership_state in ('trial', 'active'))

            # Recompute state: completed only if ALL five lifecycle steps true
            if all([
                rec.step_trial_booked,
                rec.step_waiver_signed,
                rec.step_intro_completed,
                rec.step_membership_activated,
                rec.step_uniform_issued,
            ]):
                rec.state = 'completed'
            else:
                rec.state = 'in_progress'
