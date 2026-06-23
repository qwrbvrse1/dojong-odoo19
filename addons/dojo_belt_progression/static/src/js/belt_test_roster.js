/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

class BeltTestRosterApp extends Component {
    setup() {
        this.rpc = useService("rpc");
        this.action = useService("action");

        this.state = useState({
            members: [],
            templates: [],
            ranks: [],
            filterTemplateId: null,
            filterRankId: null,
            filterText: '',
            selectedMembers: new Set(),
            rosterName: '',
            testDate: this.getToday(),
        });

        onWillStart(async () => {
            await this.loadData();
        });
    }

    getToday() {
        const today = new Date();
        const year = today.getFullYear();
        const month = String(today.getMonth() + 1).padStart(2, '0');
        const day = String(today.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    }

    async loadData() {
        const data = await this.rpc("/belt_test/roster/data", {});
        this.state.members = data.members;
        this.state.templates = data.templates;
        this.state.ranks = data.ranks;
    }

    get filteredMembers() {
        let filtered = this.state.members;

        if (this.state.filterTemplateId) {
            const templateId = parseInt(this.state.filterTemplateId);
            filtered = filtered.filter(m =>
                m.template_ids.includes(templateId)
            );
        }

        if (this.state.filterRankId) {
            const rankId = parseInt(this.state.filterRankId);
            filtered = filtered.filter(m =>
                m.current_rank_id === rankId
            );
        }

        if (this.state.filterText) {
            const searchText = this.state.filterText.toLowerCase();
            filtered = filtered.filter(m =>
                m.name.toLowerCase().includes(searchText)
            );
        }

        return filtered.sort((a, b) => a.name.localeCompare(b.name));
    }

    toggleMember(memberId) {
        if (this.state.selectedMembers.has(memberId)) {
            this.state.selectedMembers.delete(memberId);
        } else {
            this.state.selectedMembers.add(memberId);
        }
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

    updateFilter(type, event) {
        const value = event.target.value;
        if (type === 'template') {
            this.state.filterTemplateId = value || null;
        } else if (type === 'rank') {
            this.state.filterRankId = value || null;
        } else if (type === 'text') {
            this.state.filterText = value;
        }
    }

    updateRosterName(event) {
        this.state.rosterName = event.target.value;
    }

    updateTestDate(event) {
        this.state.testDate = event.target.value;
    }

    async saveRoster() {
        if (this.state.selectedMembers.size === 0) {
            alert('Please select at least one member for the roster.');
            return;
        }

        const name = this.state.rosterName || `Belt Test ${this.state.testDate}`;
        const memberIds = Array.from(this.state.selectedMembers);

        const result = await this.rpc("/belt_test/roster/save", {
            name: name,
            test_date: this.state.testDate,
            member_ids: memberIds,
            template_id: this.state.filterTemplateId ? parseInt(this.state.filterTemplateId) : null,
            rank_id: this.state.filterRankId ? parseInt(this.state.filterRankId) : null,
        });

        if (result.id) {
            alert(`Roster "${result.name}" saved successfully!`);
            this.state.rosterName = '';
            this.deselectAll();
        }
    }

    printRoster() {
        window.print();
    }

    viewSavedRosters() {
        this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'dojo.belt.test',
            name: 'Saved Belt Test Rosters',
            view_mode: 'list,form',
            views: [[false, 'list'], [false, 'form']],
            domain: [],
        });
    }
}

BeltTestRosterApp.template = "dojo_belt_progression.BeltTestRosterTemplate";

registry.category("actions").add("dojo_belt_progression.roster_action", BeltTestRosterApp);
