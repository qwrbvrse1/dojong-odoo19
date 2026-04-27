from odoo import fields, models


class DojoKioskPinAttempt(models.Model):
    _name = "dojo.kiosk.pin.attempt"
    _description = "Dojo Kiosk PIN Attempt Tracker"
    _rec_name = "config_id"

    config_id = fields.Many2one(
        "dojo.kiosk.config",
        required=True,
        ondelete="cascade",
        index=True,
    )
    failed_attempts = fields.Integer(default=0)
    locked_until = fields.Datetime()
    last_attempt_at = fields.Datetime()

    _dojo_kiosk_pin_attempt_unique_config = models.Constraint(
        "unique(config_id)",
        "Only one PIN attempt tracker can exist per kiosk.",
    )