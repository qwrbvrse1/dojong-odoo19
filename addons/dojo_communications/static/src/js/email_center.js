/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

class EmailCenter extends Component {
    static template = "dojo_communications.EmailCenter";

    setup() {
        this.rpc = useService("rpc");
        this.notification = useService("notification");
        this.orm = useService("orm");

        this.state = useState({
            subject: "",
            body: "",
            filters: {
                membership_state: [],
                class_group_ids: [],
                belt_rank_id: null,
                expiring_soon: false,
                expiring_days: 30,
            },
            members: [],
            selectedMemberIds: [],
            membershipStates: [
                { value: "active", label: "Active" },
                { value: "trial", label: "Trial" },
                { value: "paused", label: "Paused" },
                { value: "cancelled", label: "Cancelled" },
            ],
            classGroups: [],
            beltRanks: [],
            sending: false,
        });

        onWillStart(async () => {
            this.state.classGroups = await this.orm.searchRead(
                "dojo.class.group",
                [],
                ["id", "name"]
            );
            this.state.beltRanks = await this.orm.searchRead(
                "dojo.belt.rank",
                [],
                ["id", "name"]
            );
        });
    }

    async loadMembers() {
        const result = await this.rpc("/dojo/email_center/members", {
            filters: this.state.filters,
        });
        this.state.members = result.members;
        this.state.selectedMemberIds = result.members.map(m => m.id);
    }

    toggleMembershipState(stateValue) {
        const idx = this.state.filters.membership_state.indexOf(stateValue);
        if (idx >= 0) {
            this.state.filters.membership_state.splice(idx, 1);
        } else {
            this.state.filters.membership_state.push(stateValue);
        }
        this.loadMembers();
    }

    toggleClassGroup(groupId) {
        const idx = this.state.filters.class_group_ids.indexOf(groupId);
        if (idx >= 0) {
            this.state.filters.class_group_ids.splice(idx, 1);
        } else {
            this.state.filters.class_group_ids.push(groupId);
        }
        this.loadMembers();
    }

    onBeltRankChange(ev) {
        this.state.filters.belt_rank_id = ev.target.value ? parseInt(ev.target.value) : null;
        this.loadMembers();
    }

    toggleExpiringFilter() {
        this.state.filters.expiring_soon = !this.state.filters.expiring_soon;
        this.loadMembers();
    }

    toggleMember(memberId) {
        const idx = this.state.selectedMemberIds.indexOf(memberId);
        if (idx >= 0) {
            this.state.selectedMemberIds.splice(idx, 1);
        } else {
            this.state.selectedMemberIds.push(memberId);
        }
    }

    async sendEmail() {
        if (!this.state.subject.trim()) {
            this.notification.add("Subject is required", { type: "warning" });
            return;
        }
        if (!this.state.selectedMemberIds.length) {
            this.notification.add("No recipients selected", { type: "warning" });
            return;
        }

        this.state.sending = true;

        try {
            const audienceFilter = this._buildAudienceDescription();
            const result = await this.rpc("/dojo/email_center/send", {
                subject: this.state.subject,
                body: this.state.body,
                audience_filter: audienceFilter,
                member_ids: this.state.selectedMemberIds,
            });

            if (result.success) {
                this.notification.add(
                    `Email sent to ${result.sent_count} recipient(s)`,
                    { type: "success" }
                );
                this.state.subject = "";
                this.state.body = "";
                this.state.members = [];
                this.state.selectedMemberIds = [];
            } else {
                this.notification.add(result.error || "Failed to send email", {
                    type: "danger",
                });
            }
        } catch (error) {
            this.notification.add("Failed to send email", { type: "danger" });
        } finally {
            this.state.sending = false;
        }
    }

    _buildAudienceDescription() {
        const parts = [];
        if (this.state.filters.membership_state.length) {
            parts.push(`States: ${this.state.filters.membership_state.join(", ")}`);
        }
        if (this.state.filters.class_group_ids.length) {
            const groups = this.state.classGroups
                .filter(g => this.state.filters.class_group_ids.includes(g.id))
                .map(g => g.name);
            parts.push(`Classes: ${groups.join(", ")}`);
        }
        if (this.state.filters.belt_rank_id) {
            const rank = this.state.beltRanks.find(
                r => r.id === this.state.filters.belt_rank_id
            );
            if (rank) {
                parts.push(`Belt: ${rank.name}`);
            }
        }
        if (this.state.filters.expiring_soon) {
            parts.push(`Expiring within ${this.state.filters.expiring_days} days`);
        }
        return parts.join("; ") || "All members";
    }
}

registry.category("actions").add("dojo_communications.email_center", EmailCenter);
