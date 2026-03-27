import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class DojoMemberRankPointsExtend(models.Model):
    """Awards belt promotion points whenever a new dojo.member.rank is created."""

    _inherit = "dojo.member.rank"

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        try:
            config = self.env["dojo.points.config"].sudo().get_singleton()
            belt_pts = config.belt_promotion_points
            if belt_pts > 0:
                for rank_rec in records:
                    rank_name = rank_rec.rank_id.name if rank_rec.rank_id else "New Belt"
                    self.env["dojo.points.transaction"].sudo().create({
                        "member_id": rank_rec.member_id.id,
                        "source_type": "belt_promotion",
                        "amount": belt_pts,
                        "note": f"Belt promotion: {rank_name} 🥋",
                        "member_rank_id": rank_rec.id,
                    })
        except Exception:
            _logger.exception("dojo_points: failed to award belt promotion points")
        return records
