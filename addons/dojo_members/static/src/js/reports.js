/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

// ── Inactive Student Report ──────────────────────────────────────────────

class InactiveStudentReport extends Component {
    static template = "dojo_members.InactiveStudentReport";

    setup() {
        this.rpc = useService("rpc");
        this.state = useState({
            members: [],
            days: 30,
            loading: false,
        });
        onWillStart(() => this.loadData());
    }

    async loadData() {
        this.state.loading = true;
        try {
            const members = await this.rpc('/dojo_members/api/inactive_report', {
                days: this.state.days,
            });
            this.state.members = members;
        } finally {
            this.state.loading = false;
        }
    }

    onDaysChange(ev) {
        this.state.days = parseInt(ev.target.value, 10) || 30;
    }

    async onRefresh() {
        await this.loadData();
    }
}

registry.category("actions").add("dojo_members.inactive_report_action", InactiveStudentReport);

// ── Contact Report ────────────────────────────────────────────────────────

class ContactReport extends Component {
    static template = "dojo_members.ContactReport";

    setup() {
        this.rpc = useService("rpc");
        this.state = useState({
            members: [],
            loading: false,
        });
        onWillStart(() => this.loadData());
    }

    async loadData() {
        this.state.loading = true;
        try {
            const members = await this.rpc('/dojo_members/api/contact_report', {});
            this.state.members = members;
        } finally {
            this.state.loading = false;
        }
    }

    async onRefresh() {
        await this.loadData();
    }
}

registry.category("actions").add("dojo_members.contact_report_action", ContactReport);

// ── Family Report ─────────────────────────────────────────────────────────

class FamilyReport extends Component {
    static template = "dojo_members.FamilyReport";

    setup() {
        this.rpc = useService("rpc");
        this.state = useState({
            families: [],
            loading: false,
        });
        onWillStart(() => this.loadData());
    }

    async loadData() {
        this.state.loading = true;
        try {
            const families = await this.rpc('/dojo_members/api/family_report', {});
            this.state.families = families;
        } finally {
            this.state.loading = false;
        }
    }

    async onRefresh() {
        await this.loadData();
    }
}

registry.category("actions").add("dojo_members.family_report_action", FamilyReport);
