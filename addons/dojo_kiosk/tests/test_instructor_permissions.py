from datetime import timedelta

from odoo import fields
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestInstructorPermissions(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.instructor_group = cls.env.ref("dojo_core.group_dojo_instructor")
        cls.admin_group = cls.env.ref("dojo_core.group_dojo_admin")
        cls.instructor_user = cls.env["res.users"].with_context(
            no_reset_password=True,
            mail_create_nolog=True,
            tracking_disable=True,
        ).create({
            "name": "Permission Test Instructor",
            "login": "permission.instructor@example.com",
            "email": "permission.instructor@example.com",
            "group_ids": [(6, 0, [cls.instructor_group.id])],
        })
        cls.other_instructor_user = cls.env["res.users"].with_context(
            no_reset_password=True,
            mail_create_nolog=True,
            tracking_disable=True,
        ).create({
            "name": "Other Permission Instructor",
            "login": "other.permission.instructor@example.com",
            "email": "other.permission.instructor@example.com",
            "group_ids": [(6, 0, [cls.instructor_group.id])],
        })
        cls.instructor_profile = cls.env["dojo.instructor.profile"].create({
            "name": cls.instructor_user.name,
            "user_id": cls.instructor_user.id,
            "partner_id": cls.instructor_user.partner_id.id,
        })
        cls.other_instructor_profile = cls.env["dojo.instructor.profile"].create({
            "name": cls.other_instructor_user.name,
            "user_id": cls.other_instructor_user.id,
            "partner_id": cls.other_instructor_user.partner_id.id,
        })
        cls.relevant_member = cls.env["dojo.member"].create({"name": "Relevant Student"})
        cls.unrelated_member = cls.env["dojo.member"].create({"name": "Unrelated Student"})
        cls.template = cls.env["dojo.class.template"].create({
            "name": "Relevant Course",
            "instructor_profile_ids": [(6, 0, [cls.instructor_profile.id])],
        })
        cls.other_template = cls.env["dojo.class.template"].create({
            "name": "Unrelated Course",
            "instructor_profile_ids": [(6, 0, [cls.other_instructor_profile.id])],
        })
        start = fields.Datetime.now()
        cls.session = cls.env["dojo.class.session"].create({
            "template_id": cls.template.id,
            "instructor_profile_id": cls.instructor_profile.id,
            "start_datetime": start,
            "end_datetime": start + timedelta(hours=1),
            "state": "open",
        })
        cls.other_session = cls.env["dojo.class.session"].create({
            "template_id": cls.other_template.id,
            "instructor_profile_id": cls.other_instructor_profile.id,
            "start_datetime": start + timedelta(hours=2),
            "end_datetime": start + timedelta(hours=3),
            "state": "open",
        })
        cls.env["dojo.class.enrollment"].with_context(skip_subscription_check=True).create({
            "session_id": cls.session.id,
            "member_id": cls.relevant_member.id,
            "status": "registered",
        })
        cls.env["dojo.class.enrollment"].with_context(skip_subscription_check=True).create({
            "session_id": cls.other_session.id,
            "member_id": cls.unrelated_member.id,
            "status": "registered",
        })
        if "dojo.credit.transaction" in cls.env:
            pricelist = cls.env["product.pricelist"].search([], limit=1)
            if not pricelist:
                pricelist = cls.env["product.pricelist"].create({
                    "name": "Permission Test Pricelist",
                    "currency_id": cls.env.company.currency_id.id,
                })
            program = cls.env["dojo.program"].create({"name": "Permission Test Program"})
            plan = cls.env["dojo.subscription.plan"].create({
                "name": "Permission Test Plan",
                "price": 100,
                "program_ids": [(6, 0, program.ids)],
            })
            stage = cls.env["sale.subscription.stage"].search(
                [("type", "=", "in_progress")],
                limit=1,
            )
            relevant_subscription = cls.env["sale.subscription"].create({
                "member_id": cls.relevant_member.id,
                "plan_id": plan.id,
                "pricelist_id": pricelist.id,
                "stage_id": stage.id,
            })
            unrelated_subscription = cls.env["sale.subscription"].create({
                "member_id": cls.unrelated_member.id,
                "plan_id": plan.id,
                "pricelist_id": pricelist.id,
                "stage_id": stage.id,
            })
            cls.relevant_credit_transaction = cls.env["dojo.credit.transaction"].create({
                "subscription_id": relevant_subscription.id,
                "transaction_type": "grant",
                "amount": 1,
                "status": "confirmed",
            })
            cls.unrelated_credit_transaction = cls.env["dojo.credit.transaction"].create({
                "subscription_id": unrelated_subscription.id,
                "transaction_type": "grant",
                "amount": 1,
                "status": "confirmed",
            })

    def test_instructor_group_keeps_core_operational_access(self):
        self.assertTrue(self.instructor_user.has_group("base.group_user"))
        self.assertTrue(self.instructor_user.has_group("base.group_partner_manager"))
        self.assertTrue(self.instructor_user.has_group("project.group_project_user"))

        for model_name, operation in (
            ("dojo.member", "write"),
            ("dojo.class.session", "write"),
            ("dojo.class.session", "create"),
            ("dojo.class.enrollment", "write"),
            ("dojo.class.enrollment", "create"),
            ("dojo.attendance.log", "create"),
            ("project.task", "read"),
        ):
            with self.subTest(model_name=model_name, operation=operation):
                self.assertTrue(
                    self.env[model_name].with_user(self.instructor_user).has_access(operation)
                )

    def test_instructor_group_does_not_imply_admin_heavy_groups(self):
        self.assertFalse(self.instructor_user.has_group("account.group_account_invoice"))
        self.assertFalse(self.instructor_user.has_group("hr.group_hr_user"))

    def test_instructor_subscription_access_is_read_only(self):
        Subscription = self.env["sale.subscription"].with_user(self.instructor_user)
        Plan = self.env["dojo.subscription.plan"].with_user(self.instructor_user)
        ProgramEnrollment = self.env["dojo.program.enrollment"].with_user(self.instructor_user)

        for model in (Subscription, Plan, ProgramEnrollment):
            with self.subTest(model=model._name):
                self.assertTrue(model.has_access("read"))
                self.assertFalse(model.has_access("write"))
                self.assertFalse(model.has_access("create"))
                self.assertFalse(model.has_access("unlink"))

    def test_instructor_configuration_access_is_read_only(self):
        read_only_models = [
            "dojo.instructor.profile",
            "dojo.martial.art.style",
            "dojo.program",
            "dojo.class.template",
            "dojo.belt.rank",
            "dojo.kiosk.config",
            "dojo.kiosk.announcement",
        ]
        if "dojo.credit.transaction" in self.env:
            read_only_models.append("dojo.credit.transaction")

        for model_name in read_only_models:
            model = self.env[model_name].with_user(self.instructor_user)
            with self.subTest(model=model_name):
                self.assertTrue(model.has_access("read"))
                self.assertFalse(model.has_access("write"))
                self.assertFalse(model.has_access("create"))
                self.assertFalse(model.has_access("unlink"))

    def test_instructor_onboarding_record_access_is_limited_when_installed(self):
        if "dojo.onboarding.record" not in self.env:
            self.skipTest("dojo_onboarding is not installed")

        Onboarding = self.env["dojo.onboarding.record"]
        relevant = Onboarding.create({
            "member_id": self.relevant_member.id,
            "company_id": self.env.company.id,
        })
        unrelated = Onboarding.create({
            "member_id": self.unrelated_member.id,
            "company_id": self.env.company.id,
        })
        instructor_model = Onboarding.with_user(self.instructor_user)

        self.assertTrue(instructor_model.has_access("read"))
        self.assertTrue(instructor_model.has_access("write"))
        self.assertFalse(instructor_model.has_access("create"))
        self.assertFalse(instructor_model.has_access("unlink"))

        visible = instructor_model.search([])
        self.assertIn(relevant, visible)
        self.assertNotIn(unrelated, visible)

    def test_instructor_record_rules_limit_to_assigned_operational_data(self):
        instructor_profile_model = self.env["dojo.instructor.profile"].with_user(
            self.instructor_user
        )
        member_model = self.env["dojo.member"].with_user(self.instructor_user)
        session_model = self.env["dojo.class.session"].with_user(self.instructor_user)
        enrollment_model = self.env["dojo.class.enrollment"].with_user(
            self.instructor_user
        )

        self.assertEqual(instructor_profile_model.search([]), self.instructor_profile)
        self.assertIn(self.relevant_member, member_model.search([]))
        self.assertNotIn(self.unrelated_member, member_model.search([]))
        self.assertIn(self.session, session_model.search([]))
        self.assertNotIn(self.other_session, session_model.search([]))
        self.assertIn(self.session.enrollment_ids, enrollment_model.search([]))
        self.assertNotIn(self.other_session.enrollment_ids, enrollment_model.search([]))
        if "dojo.credit.transaction" in self.env:
            credit_model = self.env["dojo.credit.transaction"].with_user(
                self.instructor_user
            )
            self.assertIn(self.relevant_credit_transaction, credit_model.search([]))
            self.assertNotIn(self.unrelated_credit_transaction, credit_model.search([]))

    def test_instructor_dashboard_service_loads_with_tightened_rules(self):
        profile = self.env["dojo.instructor.profile"].with_user(
            self.instructor_user
        ).get_my_profile_data()

        self.assertTrue(profile)
        self.assertEqual(profile["id"], self.instructor_profile.id)
        self.assertIn(
            self.relevant_member.id,
            [student["id"] for student in profile["recent_students"]],
        )

    def test_subscription_menus_are_admin_only(self):
        for xmlid in (
            "dojo_subscriptions.menu_dojo_subscriptions_root",
            "dojo_subscriptions.menu_dojo_member_subscriptions",
            "dojo_subscriptions.menu_dojo_subscription_plans",
            "dojo_credits.menu_dojo_credits_root",
            "dojo_credits.menu_dojo_credit_transaction",
            "dojo_onboarding.menu_dojo_onboarding_new",
        ):
            menu = self.env.ref(xmlid, raise_if_not_found=False)
            if not menu:
                continue
            with self.subTest(menu=xmlid):
                self.assertIn(self.admin_group, menu.group_ids)
                self.assertNotIn(self.instructor_group, menu.group_ids)
