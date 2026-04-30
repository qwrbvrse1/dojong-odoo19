/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";

// ─── Constants ────────────────────────────────────────────────────────────────

const STEP_KINDS = [
    { kind: "email", label: "Send an Email", icon: "fa-paper-plane", color: "info" },
    { kind: "task",  label: "Assign a Task", icon: "fa-check-square-o", color: "warning" },
    { kind: "sms",   label: "Send an SMS",   icon: "fa-comment", color: "success" },
];

const DEFAULT_DELAYS = [0, 1, 3, 7, 14, 30];

// ─── Trigger Picker ───────────────────────────────────────────────────────────

class TriggerPicker extends Component {
    static template = "dojo_automation.TriggerPicker";
    static props = {
        templates: Array,
        categories: Array,
        selectedId: [Number, { value: false }],
        onSelect: Function,
    };

    get groupedTemplates() {
        const byCat = {};
        for (const t of this.props.templates) {
            if (!byCat[t.category]) byCat[t.category] = [];
            byCat[t.category].push(t);
        }
        return this.props.categories
            .map((c) => ({ ...c, items: byCat[c.value] || [] }))
            .filter((c) => c.items.length);
    }

    onPick(ev) {
        const id = parseInt(ev.target.value, 10);
        this.props.onSelect(id);
    }
}

// ─── Tag Chip Input ───────────────────────────────────────────────────────────

class TagChipInput extends Component {
    static template = "dojo_automation.TagChipInput";
    static props = {
        label: String,
        placeholder: { type: String, optional: true },
        selectedIds: Array,
        availableTags: Array, // [{id, name, color}]
        onChange: Function,
    };

    setup() {
        this.state = useState({ query: "" });
    }

    get suggestions() {
        const q = (this.state.query || "").toLowerCase().trim();
        const taken = new Set(this.props.selectedIds);
        return this.props.availableTags
            .filter((t) => !taken.has(t.id))
            .filter((t) => !q || (t.name || "").toLowerCase().includes(q))
            .slice(0, 8);
    }

    get selectedTags() {
        const byId = new Map(this.props.availableTags.map((t) => [t.id, t]));
        return this.props.selectedIds.map((id) => byId.get(id)).filter(Boolean);
    }

    onQueryInput(ev) {
        this.state.query = ev.target.value;
    }

    addTag(tagId) {
        const next = [...this.props.selectedIds, tagId];
        this.props.onChange(next);
        this.state.query = "";
    }

    removeTag(tagId) {
        const next = this.props.selectedIds.filter((id) => id !== tagId);
        this.props.onChange(next);
    }
}

// ─── Step Card ────────────────────────────────────────────────────────────────

class StepCard extends Component {
    static template = "dojo_automation.StepCard";
    static props = {
        step: Object,
        index: Number,
        side: String, // "left" | "right"
        canMoveUp: Boolean,
        canMoveDown: Boolean,
        onEdit: Function,
        onDelete: Function,
        onMoveUp: Function,
        onMoveDown: Function,
    };

    get kindMeta() {
        return STEP_KINDS.find((k) => k.kind === this.props.step.kind) || STEP_KINDS[0];
    }

    get delayLabel() {
        const d = this.props.step.delay_days || 0;
        if (this.props.index === 0) return _t("Immediately");
        if (d === 0) return _t("Same day");
        if (d === 1) return _t("On Day 1");
        return _t("On Day %s", d);
    }

    get summary() {
        const s = this.props.step;
        if (s.kind === "email") return _t("Send: %s", s.name || _t("Email"));
        if (s.kind === "task")  return _t("Assign: %s", s.name || _t("Task"));
        if (s.kind === "sms")   return _t("SMS: %s", s.name || _t("Message"));
        return s.name || "";
    }

    onEditClick() { this.props.onEdit(this.props.index); }
    onDeleteClick() { this.props.onDelete(this.props.index); }
    onMoveUpClick() { this.props.onMoveUp(this.props.index); }
    onMoveDownClick() { this.props.onMoveDown(this.props.index); }
}

// ─── Step Composer (modal-ish drawer) ─────────────────────────────────────────

class StepComposer extends Component {
    static template = "dojo_automation.StepComposer";
    static props = {
        step: Object, // working draft
        mailTemplates: Array,
        activityTypes: Array,
        smsTemplates: Array,
        onSave: Function,
        onCancel: Function,
        title: String,
    };

    setup() {
        this.state = useState({
            step: { ...this.props.step },
        });
    }

    get kinds() { return STEP_KINDS; }
    get delayPresets() { return DEFAULT_DELAYS; }

    setKind(kind) {
        this.state.step.kind = kind;
    }

    onNameInput(ev) {
        this.state.step.name = ev.target.value;
    }

    onDelayInput(ev) {
        const v = parseInt(ev.target.value, 10);
        this.state.step.delay_days = isNaN(v) ? 0 : v;
    }

    pickDelayPreset(d) {
        this.state.step.delay_days = d;
    }

    onMailTemplateChange(ev) {
        const id = parseInt(ev.target.value, 10) || false;
        this.state.step.mail_template_id = id;
    }

    onActivityTypeChange(ev) {
        const id = parseInt(ev.target.value, 10) || false;
        this.state.step.activity_type_id = id;
    }

    onActivitySummaryInput(ev) {
        this.state.step.activity_summary = ev.target.value;
    }

    onActivityNoteInput(ev) {
        this.state.step.activity_note = ev.target.value;
    }

    onSmsTemplateChange(ev) {
        const id = parseInt(ev.target.value, 10) || false;
        this.state.step.sms_template_id = id;
    }

    onPhoneFieldInput(ev) {
        this.state.step.phone_field = ev.target.value;
    }

    save() {
        this.props.onSave({ ...this.state.step });
    }

    cancel() {
        this.props.onCancel();
    }
}

// ─── Workflow Canvas (alternating timeline) ───────────────────────────────────

class WorkflowCanvas extends Component {
    static template = "dojo_automation.WorkflowCanvas";
    static components = { StepCard };
    static props = {
        steps: Array,
        onAdd: Function,
        onEdit: Function,
        onDelete: Function,
        onMoveUp: Function,
        onMoveDown: Function,
    };

    sideFor(idx) {
        return idx % 2 === 0 ? "left" : "right";
    }

    onAddClick() { this.props.onAdd(null); }
}

// ─── Builder Root ─────────────────────────────────────────────────────────────

class AutomationBuilder extends Component {
    static template = "dojo_automation.AutomationBuilder";
    static components = { TriggerPicker, TagChipInput, WorkflowCanvas, StepComposer };
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.action = useService("action");

        this.state = useState({
            loading: true,
            saving: false,
            // Server payload caches
            triggerTemplates: [],
            categories: [],
            contactTypes: [],
            mailTemplates: [],
            activityTypes: [],
            smsTemplates: [],
            availableTags: [],
            // Builder document
            doc: this._emptyDoc(),
            // Composer state
            composerOpen: false,
            composerStep: null,
            composerIndex: -1,
            composerTitle: "",
        });

        onWillStart(async () => {
            await this._bootstrap();
        });
    }

    _emptyDoc() {
        return {
            id: null,
            name: "",
            active: true,
            trigger_template_id: false,
            tag_include_ids: [],
            tag_exclude_ids: [],
            contact_type: "any",
            is_periodic: true,
            model_id: false,
            field_id: false,
            editable_domain: "[]",
            steps: [],
        };
    }

    async _bootstrap() {
        const props = this.props.action || {};
        const ctx = (props.context || {});
        const configId =
            ctx.default_config_id || ctx.active_id || ctx.config_id || null;

        let result;
        try {
            result = await rpc("/dojo_automation/builder/bootstrap", {
                config_id: configId,
            });
        } catch (e) {
            this.notification.add(_t("Could not load builder data"), { type: "danger" });
            this.state.loading = false;
            return;
        }
        Object.assign(this.state, {
            triggerTemplates: result.trigger_templates || [],
            categories: result.categories || [],
            contactTypes: result.contact_types || [],
            mailTemplates: result.mail_templates || [],
            activityTypes: result.activity_types || [],
            smsTemplates: result.sms_templates || [],
            sms_action_id: result.sms_action_id,
        });
        if (result.config) {
            this.state.doc = { ...this._emptyDoc(), ...result.config };
        }
        // Tags: read all res.partner.category
        try {
            this.state.availableTags = await this.orm.searchRead(
                "res.partner.category", [], ["id", "name", "color"], { limit: 500 }
            );
        } catch (e) {
            this.state.availableTags = [];
        }
        this.state.loading = false;
    }

    // ── Trigger / Filters ────────────────────────────────────────────
    get selectedTemplate() {
        const id = this.state.doc.trigger_template_id;
        return id ? this.state.triggerTemplates.find((t) => t.id === id) : null;
    }

    onSelectTemplate(id) {
        const tpl = this.state.triggerTemplates.find((t) => t.id === id);
        if (!tpl) return;
        Object.assign(this.state.doc, {
            trigger_template_id: tpl.id,
            model_id: tpl.model_id,
            field_id: tpl.default_field_id,
            is_periodic: tpl.is_periodic_default,
            editable_domain: tpl.default_domain || "[]",
        });
        if (!this.state.doc.name) {
            this.state.doc.name = tpl.name;
        }
    }

    onNameInput(ev) {
        this.state.doc.name = ev.target.value;
    }

    onIncludeTagsChange(ids) {
        this.state.doc.tag_include_ids = ids;
    }

    onExcludeTagsChange(ids) {
        this.state.doc.tag_exclude_ids = ids;
    }

    onContactTypeChange(ev) {
        this.state.doc.contact_type = ev.target.value;
    }

    onActiveToggle() {
        this.state.doc.active = !this.state.doc.active;
    }

    // ── Steps ────────────────────────────────────────────────────────
    get stepsView() {
        return this.state.doc.steps || [];
    }

    addStep(insertAt = null) {
        const newStep = {
            kind: "email",
            name: _t("New Email"),
            delay_days: this.state.doc.steps.length === 0 ? 0 : 7,
            mail_template_id: false,
            activity_type_id: false,
            activity_summary: "",
            activity_note: "",
            sms_template_id: false,
            phone_field: "",
        };
        const idx = insertAt === null ? this.state.doc.steps.length : insertAt;
        this.state.composerStep = newStep;
        this.state.composerIndex = idx;
        this.state.composerTitle = _t("Add Step");
        this.state.composerOpen = true;
    }

    editStep(index) {
        this.state.composerStep = { ...this.state.doc.steps[index] };
        this.state.composerIndex = index;
        this.state.composerTitle = _t("Edit Step");
        this.state.composerOpen = true;
    }

    saveComposer(stepData) {
        const idx = this.state.composerIndex;
        const list = this.state.doc.steps.slice();
        if (idx >= list.length) {
            list.push(stepData);
        } else {
            list[idx] = stepData;
        }
        this.state.doc.steps = list;
        this.cancelComposer();
    }

    cancelComposer() {
        this.state.composerOpen = false;
        this.state.composerStep = null;
        this.state.composerIndex = -1;
    }

    deleteStep(index) {
        const list = this.state.doc.steps.slice();
        list.splice(index, 1);
        this.state.doc.steps = list;
    }

    moveStepUp(index) {
        if (index <= 0) return;
        const list = this.state.doc.steps.slice();
        [list[index - 1], list[index]] = [list[index], list[index - 1]];
        this.state.doc.steps = list;
    }

    moveStepDown(index) {
        const list = this.state.doc.steps.slice();
        if (index >= list.length - 1) return;
        [list[index + 1], list[index]] = [list[index], list[index + 1]];
        this.state.doc.steps = list;
    }

    // ── Persistence ──────────────────────────────────────────────────
    async save() {
        if (!this.state.doc.name || !this.state.doc.name.trim()) {
            this.notification.add(_t("Please give your automation a name."), {
                type: "warning",
            });
            return;
        }
        if (!this.state.doc.model_id) {
            this.notification.add(_t("Pick a trigger first."), { type: "warning" });
            return;
        }
        this.state.saving = true;
        try {
            const result = await rpc("/dojo_automation/builder/save", {
                payload: this.state.doc,
            });
            this.state.doc = { ...this._emptyDoc(), ...result.config };
            this.notification.add(_t("Automation saved."), { type: "success" });
        } catch (e) {
            this.notification.add(
                _t("Save failed: %s", e.data?.message || e.message || e),
                { type: "danger" }
            );
        } finally {
            this.state.saving = false;
        }
    }

    async runNow() {
        if (!this.state.doc.id) {
            this.notification.add(_t("Save your automation first."), {
                type: "warning",
            });
            return;
        }
        try {
            await rpc("/dojo_automation/builder/run_now", {
                config_id: this.state.doc.id,
            });
            this.notification.add(_t("Automation kicked off."), { type: "success" });
        } catch (e) {
            this.notification.add(
                _t("Run failed: %s", e.data?.message || e.message || e),
                { type: "danger" }
            );
        }
    }

    backToList() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "automation.configuration",
            view_mode: "kanban,list,form",
            views: [[false, "kanban"], [false, "list"], [false, "form"]],
            target: "current",
        });
    }
}

registry.category("actions").add("dojo_automation_builder", AutomationBuilder);
