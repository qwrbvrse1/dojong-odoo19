/** @odoo-module **/

import { Component, useState, onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import {
    AutomationKanbanController,
    AutomationKanbanView,
} from "automation_oca/static/src/views/automation_upload/automation_upload.esm.js";

// ─── Stat Panel ───────────────────────────────────────────────────────────────

export class AutomationStatPanel extends Component {
    static template = "dojo_automation.AutomationStatPanel";

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            loading: true,
            activeRules: 0,
            triggeredToday: 0,
            runningNow: 0,
            errors7Days: 0,
        });
        onMounted(() => this._fetchKpis());
    }

    async _fetchKpis() {
        const now = new Date();
        const fmt = (d) => d.toISOString().replace("T", " ").slice(0, 19);

        const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());
        const sevenDaysAgo = new Date(todayStart);
        sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);

        const [activeRules, triggeredToday, runningNow, errors7Days] = await Promise.all([
            this.orm.searchCount("automation.configuration", [
                ["state", "in", ["periodic", "ondemand"]],
            ]),
            this.orm.searchCount("automation.record", [
                ["create_date", ">=", fmt(todayStart)],
                ["is_test", "=", false],
            ]),
            this.orm.searchCount("automation.record", [
                ["state", "=", "periodic"],
                ["is_test", "=", false],
            ]),
            this.orm.searchCount("automation.record.step", [
                ["state", "=", "error"],
                ["write_date", ">=", fmt(sevenDaysAgo)],
            ]),
        ]);

        Object.assign(this.state, {
            loading: false,
            activeRules,
            triggeredToday,
            runningNow,
            errors7Days,
        });
    }
}

// ─── Filter Chips ─────────────────────────────────────────────────────────────
// Filter names match <filter name="..."> in automation_configuration_search_view:
//   "run"   → state in ['periodic', 'ondemand']
//   "draft" → state = 'draft'
//   "done"  → state = 'done'

const CHIP_DEFS = [
    { name: "run",   label: "Active", icon: "fa-bolt" },
    { name: "draft", label: "Draft",  icon: "fa-pencil" },
    { name: "done",  label: "Done",   icon: "fa-check" },
];

export class AutomationFilterChips extends Component {
    static template = "dojo_automation.AutomationFilterChips";

    setup() {
        this.state = useState(
            Object.fromEntries(CHIP_DEFS.map((c) => [c.name, false]))
        );
    }

    get chips() {
        return CHIP_DEFS.map((c) => ({ ...c, active: this.state[c.name] }));
    }

    toggleChip(name) {
        this.state[name] = !this.state[name];
        const sm = this.env.searchModel;
        if (!sm) return;
        const item = Object.values(sm.searchItems || {}).find(
            (i) => i.name === name && i.type === "filter"
        );
        if (item) sm.toggleSearchItem(item.id);
    }
}

// ─── Dedicated controller + view — isolated template per module ───────────────
// Subclass AutomationKanbanController so it owns a dedicated template
// (dojo_automation.AutomationKanbanView). That template is a named child of
// web.KanbanView and ONLY injects AutomationStatPanel/AutomationFilterChips.
// No mutation of the shared web.KanbanView template — other kanban views are
// unaffected. The automation kanban view is pointed here via js_class in XML.

class DojoAutomationKanbanController extends AutomationKanbanController {
    static template = "dojo_automation.AutomationKanbanView";
}
DojoAutomationKanbanController.components = {
    ...AutomationKanbanController.components,
    AutomationStatPanel,
    AutomationFilterChips,
};

const dojoAutomationKanbanView = {
    ...AutomationKanbanView,
    Controller: DojoAutomationKanbanController,
};

registry.category("views").add("dojo_automation_kanban", dojoAutomationKanbanView);
