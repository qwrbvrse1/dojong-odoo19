/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

// ── Inactive Student Report ──────────────────────────────────────────────

class InactiveStudentReport extends Component {
    static template = "dojo_members.InactiveStudentReport";

    setup() {
        this.rpc = useService("rpc");
        this.notification = useService("notification");
        this.state = useState({
            members: [],
            days: 30,
            loading: false,
            selectedIds: new Set(),
            showFollowupDialog: false,
            sendingEmail: false,
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
            this.state.selectedIds.clear();
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

    toggleSelection(memberId) {
        if (this.state.selectedIds.has(memberId)) {
            this.state.selectedIds.delete(memberId);
        } else {
            this.state.selectedIds.add(memberId);
        }
    }

    toggleSelectAll() {
        if (this.state.selectedIds.size === this.state.members.length) {
            this.state.selectedIds.clear();
        } else {
            this.state.selectedIds.clear();
            this.state.members.forEach(m => this.state.selectedIds.add(m.id));
        }
    }

    get allSelected() {
        return this.state.members.length > 0 && this.state.selectedIds.size === this.state.members.length;
    }

    get hasSelection() {
        return this.state.selectedIds.size > 0;
    }

    openFollowupDialog() {
        if (!this.hasSelection) {
            this.notification.add("Please select at least one member to send follow-up email.", {
                type: "warning",
            });
            return;
        }
        this.state.showFollowupDialog = true;
    }

    closeFollowupDialog() {
        this.state.showFollowupDialog = false;
    }

    async sendFollowup() {
        const memberIds = Array.from(this.state.selectedIds);
        this.state.sendingEmail = true;

        try {
            const result = await this.rpc('/dojo_members/send_followup', {
                member_ids: memberIds,
            });

            if (result.success) {
                this.notification.add(
                    `Follow-up email sent to ${result.sent_count} member(s).`,
                    { type: "success" }
                );
                this.state.showFollowupDialog = false;
                this.state.selectedIds.clear();
            } else {
                this.notification.add(
                    result.error || "Failed to send follow-up emails.",
                    { type: "danger" }
                );
            }
        } catch (error) {
            this.notification.add(
                "Error sending follow-up emails. Please try again.",
                { type: "danger" }
            );
        } finally {
            this.state.sendingEmail = false;
        }
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
