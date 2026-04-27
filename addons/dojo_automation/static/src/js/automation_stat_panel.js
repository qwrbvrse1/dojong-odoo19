/** @odoo-module **/

import { Component, useState, onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { AutomationKanbanController } from "@automation_oca/views/automation_upload/automation_upload.esm";

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

// ─── Inject into AutomationKanbanController — isolated template per module ────
// Set AutomationKanbanController.template to our dedicated primary template
// (dojo_automation.AutomationKanbanView) so only this controller uses the
// template that has AutomationStatPanel/AutomationFilterChips injected.
// web.KanbanView itself is unchanged (primary mode creates an independent copy),
// so all other kanbans continue to render without these components.

AutomationKanbanController.template = "dojo_automation.AutomationKanbanView";
AutomationKanbanController.components = {
    ...AutomationKanbanController.components,
    AutomationStatPanel,
    AutomationFilterChips,
};
