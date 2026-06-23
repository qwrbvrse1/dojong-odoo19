/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

class MassPromoteApp extends Component {
    setup() {
        this.rpc = useService("rpc");
        this.action = useService("action");

        this.state = useState({
            members: [],
            ranks: [],
            selectedMembers: new Set(),
            targetRankId: null,
            undoStack: [],
            filterText: '',
            filterRankId: null,
        });

        onWillStart(async () => {
            await this.loadData();
        });
    }

    async loadData() {
        const data = await this.rpc("/belt_progression/data", {});
        this.state.members = data.members;
        this.state.ranks = data.ranks;
    }

    get filteredMembers() {
        let filtered = this.state.members;

        // Filter by name
        if (this.state.filterText) {
            const searchText = this.state.filterText.toLowerCase();
            filtered = filtered.filter(m =>
                m.name.toLowerCase().includes(searchText)
            );
        }

        // Filter by current rank
        if (this.state.filterRankId) {
            filtered = filtered.filter(m =>
                m.current_rank_id === this.state.filterRankId
            );
        }

        return filtered;
    }

    toggleMember(memberId) {
        if (this.state.selectedMembers.has(memberId)) {
            this.state.selectedMembers.delete(memberId);
        } else {
            this.state.selectedMembers.add(memberId);
        }
        // Force re-render
        this.state.selectedMembers = new Set(this.state.selectedMembers);
    }

    selectAll() {
        const filtered = this.filteredMembers;
        for (const member of filtered) {
            this.state.selectedMembers.add(member.id);
        }
        this.state.selectedMembers = new Set(this.state.selectedMembers);
    }

    deselectAll() {
        this.state.selectedMembers.clear();
        this.state.selectedMembers = new Set();
    }

    setTargetRank(rankId) {
        this.state.targetRankId = rankId;
    }

    async promoteSelected() {
        if (this.state.selectedMembers.size === 0) {
            alert('Please select at least one member.');
            return;
        }
        if (!this.state.targetRankId) {
            alert('Please select a target rank.');
            return;
        }

        const memberIds = Array.from(this.state.selectedMembers);
        const result = await this.rpc("/belt_progression/promote", {
            member_ids: memberIds,
            target_rank_id: this.state.targetRankId,
        });

        if (result.error) {
            alert(`Error: ${result.error}`);
            return;
        }

        // Add to undo stack
        this.state.undoStack.push({
            records: result.records,
            memberIds: memberIds,
            targetRankId: this.state.targetRankId,
        });

        // Reload data to reflect changes
        await this.loadData();

        // Clear selection
        this.deselectAll();
        this.state.targetRankId = null;

        alert(`Successfully promoted ${result.promoted_count} member(s).`);
    }

    async undoLastPromotion() {
        if (this.state.undoStack.length === 0) {
            alert('Nothing to undo.');
            return;
        }

        const lastAction = this.state.undoStack.pop();
        const recordIds = lastAction.records.map(r => r.id);

        const result = await this.rpc("/belt_progression/undo", {
            record_ids: recordIds,
        });

        if (result.error) {
            alert(`Error: ${result.error}`);
            return;
        }

        // Reload data
        await this.loadData();
        this.state.undoStack = [...this.state.undoStack];

        alert(`Undid promotion of ${result.deleted_count} member(s).`);
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

    onFilterTextChange(event) {
        this.state.filterText = event.target.value;
    }

    onFilterRankChange(event) {
        const value = event.target.value;
        this.state.filterRankId = value ? parseInt(value) : null;
    }
}

MassPromoteApp.template = "dojo_belt_progression.MassPromote";

registry.category("actions").add("dojo_belt_progression.action", MassPromoteApp);
