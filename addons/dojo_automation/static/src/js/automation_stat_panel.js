/** @odoo-module **/

import { Component, useState, onMounted, onWillUnmount } from "@odoo/owl";
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
// Chip names match <filter name="..."> in automation_configuration_search_view.
// Active state is derived from the live searchModel query (not local state) so
// chips always stay in sync even when the user also uses the search bar.

const CHIP_DEFS = [
    { name: "run",   label: "Active", icon: "fa-bolt" },
    { name: "draft", label: "Draft",  icon: "fa-pencil" },
    { name: "done",  label: "Done",   icon: "fa-check" },
];

export class AutomationFilterChips extends Component {
    static template = "dojo_automation.AutomationFilterChips";

    setup() {
        // Tiny reactive counter — bumped on every searchModel "update" event so
        // the chips getter re-runs and reflects the real search query state.
        this.state = useState({ tick: 0 });
        this._onSmUpdate = () => { this.state.tick++; };

        onMounted(() => {
            const sm = this.env.searchModel;
            if (sm) sm.addEventListener("update", this._onSmUpdate);
        });
        onWillUnmount(() => {
            const sm = this.env.searchModel;
            if (sm) sm.removeEventListener("update", this._onSmUpdate);
        });
    }

    // Derive active state from the live searchModel query.
    // Accessing `this.state.tick` makes OWL re-evaluate this getter
    // whenever the tick increments (i.e., after every sm update).
    get chips() {
        void this.state.tick; // reactive dependency
        const sm = this.env.searchModel;
        if (!sm) return CHIP_DEFS.map((c) => ({ ...c, active: false }));

        const activeIds = new Set(sm.query.map((q) => q.searchItemId));
        const itemsByName = Object.fromEntries(
            Object.values(sm.searchItems).map((i) => [i.name, i])
        );
        return CHIP_DEFS.map((c) => ({
            ...c,
            active: itemsByName[c.name] ? activeIds.has(itemsByName[c.name].id) : false,
        }));
    }

    // Use data-chip-name instead of inline arrow with argument (OWL 2 safe)
    onChipClick(ev) {
        const name = ev.currentTarget.dataset.chipName;
        this.toggleChip(name);
    }

    toggleChip(name) {
        const sm = this.env.searchModel;
        if (!sm) return;
        const item = Object.values(sm.searchItems).find((i) => i.name === name);
        if (item) sm.toggleSearchItem(item.id);
    }

    clearAll() {
        const sm = this.env.searchModel;
        if (!sm) return;
        for (const c of CHIP_DEFS) {
            const item = Object.values(sm.searchItems).find((i) => i.name === c.name);
            if (!item) continue;
            const inQuery = sm.query.some((q) => q.searchItemId === item.id);
            if (inQuery) sm.toggleSearchItem(item.id);
        }
    }
}

// ─── Inject into AutomationKanbanController ───────────────────────────────────

AutomationKanbanController.template = "dojo_automation.AutomationKanbanView";
AutomationKanbanController.components = {
    ...AutomationKanbanController.components,
    AutomationStatPanel,
    AutomationFilterChips,
};

// Always open the builder instead of the OCA form.
AutomationKanbanController.prototype.openRecord = async function (record) {
    await this.actionService.doAction(
        { type: "ir.actions.client", tag: "dojo_automation_builder", target: "current" },
        { additionalContext: { config_id: record.resId } }
    );
};

AutomationKanbanController.prototype.createRecord = async function () {
    await this.actionService.doAction({
        type: "ir.actions.client",
        tag: "dojo_automation_builder",
        target: "current",
    });
};

