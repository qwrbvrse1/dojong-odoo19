/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

class InstructorDashboardApp extends Component {
    setup() {
        this.rpc = useService("rpc");
        this.action = useService("action");

        this.state = useState({
            active_students: 0,
            todays_checkins: 0,
            upcoming_birthdays: 0,
            expiring_memberships: 0,
            belt_distribution: [],
            birthday_list: [],
            expiring_list: [],
        });

        onWillStart(async () => {
            await this.loadData();
        });
    }

    async loadData() {
        const data = await this.rpc("/instructor_dashboard/data", {});
        Object.assign(this.state, data);
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

    formatCountdown(days) {
        if (days === 0) {
            return "Today!";
        } else if (days === 1) {
            return "Tomorrow";
        } else {
            return `in ${days} days`;
        }
    }
}

InstructorDashboardApp.template = "dojo_instructor_dashboard.Dashboard";

registry.category("actions").add("dojo_instructor_dashboard.action", InstructorDashboardApp);
