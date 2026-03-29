import logging

from odoo import api, models

_logger = logging.getLogger(__name__)

# Milestones: (attendance_count, config_field_name)
_MILESTONES = [
    (10, "milestone_10_points"),
    (25, "milestone_25_points"),
    (50, "milestone_50_points"),
    (100, "milestone_100_points"),
    (200, "milestone_200_points"),
]

# Streak thresholds: (streak_count, config_field_name)
_STREAK_BONUSES = [
    (3, "streak_bonus_3"),
    (7, "streak_bonus_7"),
    (30, "streak_bonus_30"),
]


class DojoAttendanceLogPointsExtend(models.Model):
    """Hooks into dojo.attendance.log.create() to auto-award points."""

    _inherit = "dojo.attendance.log"

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        config = self.env["dojo.points.config"].sudo().get_singleton()
        for log in records:
            try:
                self._award_points_for_log(log, config)
            except Exception:
                # Never let a points error block an attendance record from saving
                _logger.exception(
                    "dojo_points: failed to award points for attendance log %s", log.id
                )
        return records

    def _award_points_for_log(self, log, config):
        """Core points-and-streak logic for a single attendance log."""
        member = log.member_id
        if not member:
            return

        status = log.status

        # ── Absent / Excused / Sick / Injury / Vacation / Other: reset streak ──
        if status in ("absent", "excused", "sick", "injury", "vacation", "other"):
            if member.current_streak != 0:
                member.sudo().write({"current_streak": 0})
            return

        # ── Present / Late: award base attendance points ──────────────────
        if status == "present":
            base_pts = config.attendance_points
            source_type = "attendance"
            note = f"Class attendance — {log.session_id.name or 'session'}"
        else:  # late
            base_pts = config.late_attendance_points
            source_type = "late_attendance"
            note = f"Late attendance — {log.session_id.name or 'session'}"

        if base_pts > 0:
            self.env["dojo.points.transaction"].sudo().create({
                "member_id": member.id,
                "source_type": source_type,
                "amount": base_pts,
                "note": note,
                "attendance_log_id": log.id,
            })

        # ── Update streak ─────────────────────────────────────────────────
        new_streak = (member.current_streak or 0) + 1
        write_vals = {"current_streak": new_streak}
        if new_streak > (member.longest_streak or 0):
            write_vals["longest_streak"] = new_streak
        member.sudo().write(write_vals)

        # ── Streak bonus (awarded only at the exact threshold hit) ────────
        for threshold, field_name in _STREAK_BONUSES:
            if new_streak == threshold:
                bonus_pts = getattr(config, field_name, 0)
                if bonus_pts > 0:
                    self.env["dojo.points.transaction"].sudo().create({
                        "member_id": member.id,
                        "source_type": "streak_bonus",
                        "amount": bonus_pts,
                        "note": f"{threshold}-class streak bonus! 🔥",
                        "streak_length": new_streak,
                        "attendance_log_id": log.id,
                    })
                break  # only one bonus per log

        # ── Attendance milestone (lifetime total, one-time per milestone) ──
        total_attended = self.env["dojo.attendance.log"].sudo().search_count([
            ("member_id", "=", member.id),
            ("status", "in", ["present", "late"]),
        ])

        sent_str = member.milestone_points_sent or ""
        sent = set(s for s in sent_str.split(",") if s)
        new_sent = set(sent)

        for milestone_count, field_name in _MILESTONES:
            if total_attended >= milestone_count and str(milestone_count) not in sent:
                pts = getattr(config, field_name, 0)
                if pts > 0:
                    self.env["dojo.points.transaction"].sudo().create({
                        "member_id": member.id,
                        "source_type": "attendance_milestone",
                        "amount": pts,
                        "note": f"{milestone_count}-class milestone! 🎯",
                        "attendance_log_id": log.id,
                    })
                new_sent.add(str(milestone_count))

        if new_sent != sent:
            updated = ",".join(str(m) for m in sorted(int(x) for x in new_sent))
            member.sudo().write({"milestone_points_sent": updated})
