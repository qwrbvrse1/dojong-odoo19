"""HTTP endpoints feeding the OWL Spark-style automation builder.

All routes use ``type='jsonrpc'`` (Odoo 19 alias for the legacy ``json``).
"""

import json
import logging

from odoo import http
from odoo.exceptions import AccessError, UserError
from odoo.http import request

_logger = logging.getLogger(__name__)


# ── Step-type mapping between the Spark-style picker and automation_oca ──
#
# Spark exposes 3 actions: Email / Task / SMS. automation_oca natively
# supports mail / activity / action. SMS is implemented as ``action`` with
# a shared ir.actions.server (see data/sms_action_template.xml).
SPARK_TO_OCA_STEP = {
    "email": "mail",
    "task": "activity",
    "sms": "action",
}
OCA_TO_SPARK_STEP = {
    "mail": "email",
    "activity": "task",
    "action": "sms",  # only SMS uses the action type in this UI
}


class DojoAutomationBuilderController(http.Controller):
    """JSON-RPC endpoints used by the OWL builder.

    Auth = standard backend user; permission inherited from the
    underlying ``automation.configuration`` ACLs.
    """

    # ── Bootstrap ────────────────────────────────────────────────────────
    @http.route(
        "/dojo_automation/builder/bootstrap",
        type="jsonrpc",
        auth="user",
    )
    def bootstrap(self, config_id=None, **kw):
        """Return everything the builder needs to render: trigger templates,
        category labels, the existing config (if editing), and selectable
        templates / activity types / sms templates for the step composer.
        """
        env = request.env
        env["automation.configuration"].check_access("read")

        templates = (
            env["dojo.automation.trigger.template"]
            .search([("active", "=", True)])
            .with_context(active_test=False)
        )
        # Category labels come from the model selection
        category_field = env["dojo.automation.trigger.template"]._fields["category"]
        categories = [
            {"value": k, "label": str(v)} for k, v in category_field.selection
        ]
        contact_types = [
            {"value": k, "label": str(v)}
            for k, v in env["automation.configuration"]._fields["contact_type"].selection
        ]

        config_payload = None
        if config_id:
            config = env["automation.configuration"].browse(int(config_id))
            config.check_access("read")
            config_payload = self._serialize_config(config)

        # Lookups
        mail_templates = env["mail.template"].search_read(
            [], ["id", "name", "model_id", "model"], limit=200,
        )
        activity_types = env["mail.activity.type"].search_read(
            [], ["id", "name"], limit=200,
        )
        try:
            sms_templates = env["sms.template"].search_read(
                [], ["id", "name", "model_id", "model"], limit=200,
            )
        except Exception:
            sms_templates = []

        return {
            "trigger_templates": [t.get_picker_payload() for t in templates],
            "categories": categories,
            "contact_types": contact_types,
            "config": config_payload,
            "mail_templates": mail_templates,
            "activity_types": activity_types,
            "sms_templates": sms_templates,
            "sms_action_id": env.ref(
                "dojo_automation.action_send_sms", raise_if_not_found=False
            ).id or False,
        }

    # ── Save (create or update) ──────────────────────────────────────────
    @http.route(
        "/dojo_automation/builder/save",
        type="jsonrpc",
        auth="user",
    )
    def save(self, payload, **kw):
        """Persist a builder document.

        ``payload`` shape::

            {
              "id": <int|None>,
              "name": <str>,
              "active": <bool>,
              "trigger_template_id": <int|None>,
              "tag_include_ids": [int, ...],
              "tag_exclude_ids": [int, ...],
              "contact_type": <str>,
              "is_periodic": <bool>,
              "model_id": <int>,
              "field_id": <int|None>,
              "editable_domain": <str>,
              "steps": [
                {
                  "kind": "email"|"task"|"sms",
                  "name": <str>,
                  "delay_days": <int>,
                  "mail_template_id": <int|None>,
                  "activity_type_id": <int|None>,
                  "activity_summary": <str|None>,
                  "activity_note": <str|None>,
                  "sms_template_id": <int|None>,
                  "phone_field": <str|None>,
                },
                ...
              ]
            }
        """
        env = request.env
        Configuration = env["automation.configuration"]
        config_id = payload.get("id")

        vals = self._config_vals_from_payload(payload)
        if config_id:
            config = Configuration.browse(int(config_id))
            config.check_access("write")
            config.write(vals)
        else:
            Configuration.check_access("create")
            config = Configuration.create(vals)

        # Replace steps wholesale (linear chain only)
        config.automation_step_ids.unlink()
        self._create_steps(config, payload.get("steps") or [])

        return {"id": config.id, "config": self._serialize_config(config)}

    # ── Toggle active ────────────────────────────────────────────────────
    @http.route(
        "/dojo_automation/builder/set_active",
        type="jsonrpc",
        auth="user",
    )
    def set_active(self, config_id, active, **kw):
        env = request.env
        config = env["automation.configuration"].browse(int(config_id))
        config.check_access("write")
        active = bool(active)
        # When activating, transition out of draft so the cron picks it up.
        config.active = active
        if active and config.state == "draft":
            try:
                config.start_automation()
            except Exception as exc:  # noqa: BLE001
                _logger.warning(
                    "dojo_automation: start_automation failed for %s: %s",
                    config.id, exc,
                )
        return {"id": config.id, "active": config.active, "state": config.state}

    # ── Run now ──────────────────────────────────────────────────────────
    @http.route(
        "/dojo_automation/builder/run_now",
        type="jsonrpc",
        auth="user",
    )
    def run_now(self, config_id, **kw):
        env = request.env
        config = env["automation.configuration"].browse(int(config_id))
        config.check_access("write")
        config.run_automation()
        return {"id": config.id, "ok": True}

    # ─────────────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────────────
    def _config_vals_from_payload(self, payload):
        """Translate a builder payload into ``automation.configuration`` vals."""
        vals = {
            "name": payload.get("name") or "Untitled Automation",
            "active": bool(payload.get("active", True)),
            "is_periodic": bool(payload.get("is_periodic", True)),
            "model_id": int(payload.get("model_id")) if payload.get("model_id") else False,
            "field_id": int(payload.get("field_id")) if payload.get("field_id") else False,
            "editable_domain": payload.get("editable_domain") or "[]",
            "trigger_template_id": (
                int(payload.get("trigger_template_id"))
                if payload.get("trigger_template_id") else False
            ),
            "tag_include_ids": [(6, 0, [int(i) for i in (payload.get("tag_include_ids") or [])])],
            "tag_exclude_ids": [(6, 0, [int(i) for i in (payload.get("tag_exclude_ids") or [])])],
            "contact_type": payload.get("contact_type") or "any",
        }
        return vals

    def _create_steps(self, config, steps):
        """Create a linear chain of steps. Each step's parent is the previous
        one (trigger_type='after_step'); the first step has trigger_type='start'.
        """
        Step = request.env["automation.configuration.step"]
        sms_action = request.env.ref(
            "dojo_automation.action_send_sms", raise_if_not_found=False
        )
        previous = False
        for idx, step_data in enumerate(steps):
            kind = step_data.get("kind")
            oca_type = SPARK_TO_OCA_STEP.get(kind)
            if not oca_type:
                raise UserError("Unknown step kind: %s" % kind)
            step_vals = {
                "name": step_data.get("name") or kind.title(),
                "configuration_id": config.id,
                "step_type": oca_type,
                "trigger_type": "start" if idx == 0 else "after_step",
                "parent_id": previous.id if previous else False,
                "trigger_interval": int(step_data.get("delay_days") or 0),
                "trigger_interval_type": "days",
                "trigger_date_kind": "offset",
                "apply_parent_domain": True,
            }
            if kind == "email":
                step_vals["mail_template_id"] = (
                    int(step_data.get("mail_template_id"))
                    if step_data.get("mail_template_id") else False
                )
            elif kind == "task":
                step_vals["activity_type_id"] = (
                    int(step_data.get("activity_type_id"))
                    if step_data.get("activity_type_id") else False
                )
                step_vals["activity_summary"] = step_data.get("activity_summary") or step_data.get("name") or "Task"
                step_vals["activity_note"] = step_data.get("activity_note") or ""
                step_vals["activity_user_type"] = "specific"
            elif kind == "sms":
                if not sms_action:
                    raise UserError(
                        "SMS step requires the dojo_automation.action_send_sms record."
                    )
                step_vals["server_action_id"] = sms_action.id
                step_vals["sms_template_id"] = (
                    int(step_data.get("sms_template_id"))
                    if step_data.get("sms_template_id") else False
                )
                step_vals["phone_field"] = step_data.get("phone_field") or ""
            previous = Step.create(step_vals)

    def _serialize_config(self, config):
        return {
            "id": config.id,
            "name": config.name,
            "active": config.active,
            "state": config.state,
            "trigger_template_id": config.trigger_template_id.id or False,
            "trigger_template_code": config.trigger_template_code or "",
            "model_id": config.model_id.id or False,
            "model": config.model or "",
            "field_id": config.field_id.id or False,
            "is_periodic": config.is_periodic,
            "editable_domain": config.editable_domain or "[]",
            "domain": config.domain or "[]",
            "tag_include_ids": config.tag_include_ids.ids,
            "tag_exclude_ids": config.tag_exclude_ids.ids,
            "contact_type": config.contact_type or "any",
            "steps": [self._serialize_step(s) for s in self._linear_steps(config)],
        }

    def _linear_steps(self, config):
        """Return steps in execution order assuming a linear chain (start → after_step → ...)."""
        roots = config.automation_step_ids.filtered(lambda s: s.trigger_type == "start")
        if not roots:
            return list(config.automation_step_ids)
        ordered = [roots[:1]]
        current = roots[:1]
        # Walk children: take the first child each iteration (linear)
        while current:
            children = current.child_ids.filtered(lambda s: s.trigger_type == "after_step")
            if not children:
                break
            current = children[:1]
            ordered.append(current)
        return [rs[0] for rs in ordered if rs]

    def _serialize_step(self, step):
        kind = OCA_TO_SPARK_STEP.get(step.step_type, "task")
        return {
            "id": step.id,
            "kind": kind,
            "name": step.name,
            "delay_days": (
                step.trigger_interval if step.trigger_interval_type == "days"
                else int((step.trigger_interval or 0) / 24)
            ),
            "mail_template_id": step.mail_template_id.id or False,
            "activity_type_id": step.activity_type_id.id or False,
            "activity_summary": step.activity_summary or "",
            "activity_note": step.activity_note or "",
            "sms_template_id": step.sms_template_id.id or False,
            "phone_field": step.phone_field or "",
        }
