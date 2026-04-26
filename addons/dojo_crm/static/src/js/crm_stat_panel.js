/** @odoo-module **/

import { Component, useState, onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { crmKanbanView } from "@crm/views/crm_kanban/crm_kanban_view";

// ─── Stat Panel ──────────────────────────────────────────────────────────────

export class CrmStatPanel extends Component {
    static template = "dojo_crm.CrmStatPanel";

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            loading: true,
            totalLeads: 0,
            conversionRate: 0,
            trialsThisWeek: 0,
            expiringOffers: 0,
        });
        onMounted(() => this._fetchKpis());
    }

    async _fetchKpis() {
        const now = new Date();
        const fmtDate = (d) => d.toISOString().slice(0, 10);

        // Total active leads (not archived, probability < 100)
        const totalLeads = await this.orm.searchCount("crm.lead", [
            ["active", "=", true],
            ["probability", "<", 100],
        ]);

        // Conversion rate over last 30 days
        const d30 = fmtDate(new Date(now - 30 * 86400000));
        const [won, all] = await Promise.all([
            this.orm.searchCount(
                "crm.lead",
                [["date_closed", ">=", d30], ["probability", "=", 100]],
                { context: { active_test: false } }
            ),
            this.orm.searchCount(
                "crm.lead",
                [["create_date", ">=", d30]],
                { context: { active_test: false } }
            ),
        ]);
        const conversionRate = all > 0 ? Math.round((won / all) * 100) : 0;

        // Trials booked this calendar week (Mon–Sun)
        const weekStart = new Date(now);
        weekStart.setDate(now.getDate() - ((now.getDay() + 6) % 7)); // ISO Monday
        weekStart.setHours(0, 0, 0, 0);
        const weekEnd = new Date(weekStart.getTime() + 7 * 86400000);
        const trialsThisWeek = await this.orm.searchCount("crm.lead", [
            ["trial_session_id", "!=", false],
            ["trial_session_id.start_datetime", ">=", weekStart.toISOString().replace("T", " ").slice(0, 19)],
            ["trial_session_id.start_datetime", "<", weekEnd.toISOString().replace("T", " ").slice(0, 19)],
        ]);

        // Expiring offers: sent >= 72 h ago, lead still active, not yet converted
        const cutoff = fmtDate(new Date(now - 3 * 86400000));
        const expiringOffers = await this.orm.searchCount("crm.lead", [
            ["offer_sent_date", "!=", false],
            ["offer_sent_date", "<=", cutoff],
            ["is_converted", "=", false],
            ["active", "=", true],
        ]);

        Object.assign(this.state, {
            loading: false,
            totalLeads,
            conversionRate,
            trialsThisWeek,
            expiringOffers,
        });
    }
}

// ─── Filter Chips ─────────────────────────────────────────────────────────────

const CHIP_DEFS = [
    { name: "high_score",       label: "High Score",      icon: "fa-star" },
    { name: "trial_attended",   label: "Trial Attended",  icon: "fa-check-circle" },
    { name: "no_show",          label: "No-Show",         icon: "fa-times-circle" },
    { name: "converted",        label: "Converted",       icon: "fa-user-plus" },
    { name: "has_booking_link", label: "Has Booking",     icon: "fa-calendar" },
];

export class CrmFilterChips extends Component {
    static template = "dojo_crm.CrmFilterChips";

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
        // Drive Odoo's search model to toggle the named filter
        const sm = this.env.searchModel;
        if (!sm) return;
        const item = Object.values(sm.searchItems || {}).find(
            (i) => i.name === name && i.type === "filter"
        );
        if (item) {
            sm.toggleSearchItem(item.id);
        }
    }
}

// ─── Inject into crmKanbanView.Controller — isolated template per module ──────
// Set crmKanbanView.Controller.template to our dedicated primary template
// (dojo_crm.CrmKanbanView) so only this controller uses the template that has
// CrmStatPanel/CrmFilterChips injected.
// web.KanbanView itself is unchanged (primary mode creates an independent copy),
// so all other kanbans continue to render without these components.

crmKanbanView.Controller.template = "dojo_crm.CrmKanbanView";
crmKanbanView.Controller.components = {
    ...crmKanbanView.Controller.components,
    CrmStatPanel,
    CrmFilterChips,
};
