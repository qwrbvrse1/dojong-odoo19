/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

class AttendanceAnalyticsApp extends Component {
    setup() {
        this.rpc = useService("rpc");
        this.action = useService("action");

        this.state = useState({
            busiest_sessions: [],
            top_attending_members: [],
            inactive_members: [],
            period_days: 30,
        });

        onWillStart(async () => {
            await this.loadData();
        });
    }

    async loadData() {
        const data = await this.rpc("/instructor_dashboard/analytics", {
            days: this.state.period_days,
        });
        Object.assign(this.state, data);
    }

    async changePeriod(days) {
        this.state.period_days = days;
        await this.loadData();
    }

    openSessionRecord(sessionId) {
        this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'dojo.class.session',
            res_id: sessionId,
            views: [[false, 'form']],
            target: 'current',
        });
    }

    openMemberRecord(memberId) {
        this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'dojo.member',
            res_id: memberId,
            views: [[false, 'form']],
            target: 'current',
        });
    }
}

AttendanceAnalyticsApp.template = "dojo_instructor_dashboard.Analytics";

registry.category("actions").add("dojo_instructor_dashboard.analytics_action", AttendanceAnalyticsApp);
