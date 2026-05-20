member_model = env.ref("dojo_core.model_dojo_member")
membership_field = env.ref("dojo_core.field_dojo_member__membership_state")
trigger = env["dojo.automation.trigger.template"].search(
    [("code", "=", "member_paused_cancelled")], limit=1
)
todo_type = env["mail.activity.type"].search([("name", "=", "To-Do")], limit=1)
falls_tag = env["res.partner.category"].search([("name", "=", "Falls Monitoring")], limit=1)

if not trigger or not todo_type or not falls_tag:
    raise RuntimeError("Missing trigger template, To-Do activity type, or Falls Monitoring tag")

config = env["automation.configuration"].search(
    [("name", "=", "Fall Incident Continuity Workflow")],
    limit=1,
)

config_vals = {
    "name": "Fall Incident Continuity Workflow",
    "active": True,
    "is_periodic": True,
    "model_id": member_model.id,
    "field_id": membership_field.id,
    "editable_domain": '[("membership_state", "in", ["paused", "cancelled"])]',
    "trigger_template_id": trigger.id,
    "contact_type": "paused",
    "tag_include_ids": [(6, 0, [falls_tag.id])],
    "tag_exclude_ids": [(6, 0, [])],
}

if config:
    config.write(config_vals)
else:
    config = env["automation.configuration"].create(config_vals)

config.automation_step_ids.unlink()

step_specs = [
    {
        "name": "Immediate clinical triage",
        "delay_days": 0,
        "summary": "Review missed mobility round and document incident severity",
        "note": "Confirm resident status, review room notes, and record whether nurse escalation is required.",
    },
    {
        "name": "Assign charge nurse follow-up",
        "delay_days": 0,
        "summary": "Create same-day nursing follow-up task",
        "note": "Route the incident to the charge nurse and verify the next in-person assessment window.",
    },
    {
        "name": "Family continuity update",
        "delay_days": 1,
        "summary": "Prepare family update after the first follow-up round",
        "note": "Use the emergency contact record to confirm the resident update and next planned visit.",
    },
    {
        "name": "Compliance closeout review",
        "delay_days": 3,
        "summary": "Review open follow-up items and close the compliance trail",
        "note": "Confirm the incident note, recovery plan, and family communication are all complete.",
    },
]

previous = False
for index, spec in enumerate(step_specs):
    previous = env["automation.configuration.step"].create({
        "name": spec["name"],
        "configuration_id": config.id,
        "step_type": "activity",
        "trigger_type": "start" if index == 0 else "after_step",
        "parent_id": previous.id if previous else False,
        "trigger_interval": spec["delay_days"],
        "trigger_interval_type": "days",
        "trigger_date_kind": "offset",
        "apply_parent_domain": True,
        "activity_type_id": todo_type.id,
        "activity_summary": spec["summary"],
        "activity_note": spec["note"],
        "activity_user_type": "specific",
    })

env.cr.commit()

print("Workflow staged")
print("config_id={}".format(config.id))
for step in config.automation_step_ids.sorted("id"):
    print("{}|{}|{}|{}".format(step.name, step.step_type, step.trigger_type, step.trigger_interval))
