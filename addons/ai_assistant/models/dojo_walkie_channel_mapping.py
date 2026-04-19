# -*- coding: utf-8 -*-
"""
Maps each walkie-talkie AI channel (Attendance, Members, …) to an Odoo Discuss
channel so voice messages and AI responses are automatically posted there.
"""

from odoo import fields, models


class AiWalkieChannelMapping(models.Model):
    _name = "ai.walkie.channel.mapping"
    _description = "Walkie-Talkie → Discuss Channel Mapping"
    _order = "channel_type"

    walkie_talkie_id = fields.Many2one(
        "ai.walkie.talkie",
        string="Walkie-Talkie",
        required=True,
        ondelete="cascade",
        index=True,
    )
    channel_type = fields.Selection(
        selection=[
            ("all", "All"),
            ("attendance", "Attendance"),
            ("members", "Members"),
            ("enrollment", "Enrollment"),
            ("belts", "Belt & Ranks"),
            ("billing", "Billing"),
            ("lookup", "Lookup Only"),
        ],
        string="AI Channel",
        required=True,
    )
    discuss_channel_id = fields.Many2one(
        "discuss.channel",
        string="Discuss Channel",
        required=True,
        ondelete="restrict",
    )

    _sql_constraints = [
        (
            "walkie_channel_uniq",
            "UNIQUE(walkie_talkie_id, channel_type)",
            "Each AI channel can only be mapped once per walkie-talkie station.",
        ),
    ]
