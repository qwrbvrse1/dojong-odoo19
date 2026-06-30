from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestKioskPublicRoster(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.KioskService = cls.env["dojo.kiosk.service"]
        cls.Member = cls.env["dojo.member"]
        cls.other_company = cls.env["res.company"].sudo().create({
            "name": "Other Kiosk Company",
        })
        cls.env.user.sudo().company_ids |= cls.other_company

    def _member(self, name, company):
        return self.Member.with_context(
            mail_create_nolog=True,
            tracking_disable=True,
        ).sudo().create({
            "name": name,
            "company_id": company.id if company else False,
            "membership_state": "active",
        })

    def test_public_student_roster_excludes_other_company_members(self):
        current_member = self._member("Current Company Student", self.env.company)
        global_member = self._member("Global Student", False)
        other_member = self._member("Other Company Student", self.other_company)

        roster = self.KioskService.with_company(self.env.company).get_public_student_roster(limit=20)
        roster_ids = {member.id for member in roster}

        self.assertIn(current_member.id, roster_ids)
        self.assertIn(global_member.id, roster_ids)
        self.assertNotIn(other_member.id, roster_ids)
