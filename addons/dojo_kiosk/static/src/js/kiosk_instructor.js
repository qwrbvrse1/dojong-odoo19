/**
 * Kiosk Instructor Three-Panel Layout Component
 * Renders active session info, countdown timer, roster grid, and alerts.
 * Part of the existing kiosk_app.js OWL SPA; assumes owl globals are available.
 */
/* global owl, jsonPost, KIOSK_TOKEN, Component, useState, onMounted, onWillUnmount, xml */
// owl globals already destructured by kiosk_app.js — do not re-declare here

class KioskInstructorLayout extends Component {
    static template = xml`
        <div class="k-instructor-layout">
            <!-- Left Panel: Active Session + Countdown -->
            <div class="k-instructor-left">
                <t t-if="state.session">
                    <div class="k-session-card">
                        <div class="k-session-card__name" t-esc="state.session.template_name || state.session.session_name"/>
                        <div class="k-session-card__time">
                            <t t-esc="formatTime(state.session.start_datetime)"/> – <t t-esc="formatTime(state.session.end_datetime)"/>
                        </div>
                        <div class="k-session-card__countdown" t-esc="state.countdown"/>

                        <div class="k-session-card__summary">
                            <div class="k-summary-stat k-summary-stat--present">
                                <span class="k-summary-stat__count" t-esc="state.session.present_count || 0"/>
                                <span class="k-summary-stat__label">Present</span>
                            </div>
                            <div class="k-summary-stat k-summary-stat--late">
                                <span class="k-summary-stat__count" t-esc="state.session.late_count || 0"/>
                                <span class="k-summary-stat__label">Late</span>
                            </div>
                            <div class="k-summary-stat k-summary-stat--absent">
                                <span class="k-summary-stat__count" t-esc="state.session.absent_count || 0"/>
                                <span class="k-summary-stat__label">Absent</span>
                            </div>
                        </div>
                    </div>
                </t>
                <t t-else="">
                    <div class="k-session-card">
                        <div class="k-session-card__name">No Active Session</div>
                        <div class="k-session-card__time">Select a session from the list to begin.</div>
                    </div>
                </t>
            </div>

            <!-- Main Panel: Roster Grid -->
            <div class="k-instructor-main">
                <div class="k-roster-grid">
                    <t t-foreach="state.roster" t-as="member" t-key="member.member_id">
                        <div class="k-roster-card"
                            t-att-data-member-id="member.member_id || member.lead_id || ''"
                            t-att-data-attendance-state="member.attendance_state || 'pending'"
                            t-att-data-onboarding-pct="member.onboarding_pct || 0"
                            t-att-data-open-task-count="member.open_task_count || 0"
                            t-att-data-membership-state="member.membership_state || ''">
                            <div class="k-roster-card__name" t-esc="member.name"/>
                            <div class="k-roster-card__belt" t-esc="member.belt_rank"/>
                            <div t-attf-class="k-roster-status k-roster-status--#{member.attendance_state || 'pending'}"
                                t-esc="attendanceLabel(member.attendance_state)"/>
                            <t t-if="member.onboarding_pct and member.onboarding_pct > 0">
                                <div class="k-roster-card__progress">
                                    <div class="k-roster-card__progress-bar">
                                        <div class="k-roster-card__progress-fill" t-att-style="'width: ' + member.onboarding_pct + '%'"/>
                                    </div>
                                    <div class="k-roster-card__progress-label" t-esc="member.onboarding_pct + '%'"/>
                                </div>
                            </t>
                            <t t-if="member.open_task_count and member.open_task_count > 0">
                                <div class="k-roster-card__badge" t-esc="member.open_task_count"/>
                            </t>
                        </div>
                    </t>
                </div>
            </div>

            <!-- Right Panel: Alerts &amp; Notes -->
            <div class="k-instructor-right">
                <t t-if="state.alerts.onboarding.length">
                    <div class="k-alert-section">
                        <div class="k-alert-section__title">Onboarding Incomplete</div>
                        <t t-foreach="state.alerts.onboarding" t-as="alert" t-key="alert_index">
                            <div class="k-alert-item k-alert-item--onboarding">
                                <div class="k-alert-item__name" t-esc="alert.name"/>
                                <div class="k-alert-item__detail" t-esc="alert.detail"/>
                            </div>
                        </t>
                    </div>
                </t>

                <t t-if="state.alerts.membership.length">
                    <div class="k-alert-section">
                        <div class="k-alert-section__title">Membership Issues</div>
                        <t t-foreach="state.alerts.membership" t-as="alert" t-key="alert_index">
                            <div class="k-alert-item k-alert-item--membership">
                                <div class="k-alert-item__name" t-esc="alert.name"/>
                                <div class="k-alert-item__detail" t-esc="alert.detail"/>
                            </div>
                        </t>
                    </div>
                </t>

                <t t-if="state.alerts.tasks.length">
                    <div class="k-alert-section">
                        <div class="k-alert-section__title">Instructor Tasks</div>
                        <t t-foreach="state.alerts.tasks" t-as="alert" t-key="alert_index">
                            <div class="k-alert-item k-alert-item--task">
                                <div class="k-alert-item__name" t-esc="alert.name"/>
                                <div class="k-alert-item__detail" t-esc="alert.detail"/>
                            </div>
                        </t>
                    </div>
                </t>
            </div>
        </div>
    `;

    static props = {
        sessionId: { type: Number, optional: true },
        onSessionChange: { type: Function, optional: true },
    };

    setup() {
        this.state = useState({
            session: null,
            countdown: "--:--",
            roster: [],
            alerts: {
                onboarding: [],
                membership: [],
                tasks: [],
            },
        });

        onMounted(() => {
            if (this.props.sessionId) {
                this.loadSession(this.props.sessionId);
            }
            this._countdownInterval = setInterval(() => this.updateCountdown(), 1000);
        });

        onWillUnmount(() => {
            if (this._countdownInterval) {
                clearInterval(this._countdownInterval);
            }
        });
    }

    async loadSession(sessionId) {
        try {
            const summary = await jsonPost("/kiosk/api/session_summary", { session_id: sessionId });
            if (summary.success) {
                this.state.session = summary;
                await this.loadRoster(sessionId);
                this.updateAlerts();
            }
        } catch (error) {
            console.error("Failed to load session summary:", error);
        }
    }

    async loadRoster(sessionId) {
        try {
            const roster = await jsonPost("/kiosk/roster", { session_id: sessionId });
            this.state.roster = roster || [];
            this.updateAlerts();
        } catch (error) {
            console.error("Failed to load roster:", error);
        }
    }

    updateCountdown() {
        if (!this.state.session || !this.state.session.end_datetime) {
            this.state.countdown = "--:--";
            return;
        }

        const now = new Date();
        const end = new Date(this.state.session.end_datetime.replace(" ", "T") + "Z");
        const diffMs = end - now;

        if (diffMs <= 0) {
            this.state.countdown = "00:00";
            return;
        }

        const totalSeconds = Math.floor(diffMs / 1000);
        const minutes = Math.floor(totalSeconds / 60);
        const seconds = totalSeconds % 60;
        this.state.countdown = `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
    }

    updateAlerts() {
        const onboarding = [];
        const membership = [];
        const tasks = [];

        for (const member of this.state.roster) {
            const workflow = member.workflow_status || {};

            if (workflow.onboarding && !workflow.onboarding.complete) {
                onboarding.push({
                    name: member.name,
                    detail: `${workflow.onboarding.progress_pct || 0}% complete`,
                });
            }

            if (workflow.subscription && workflow.subscription.alerts) {
                for (const alert of workflow.subscription.alerts) {
                    membership.push({
                        name: member.name,
                        detail: alert.label || alert.code,
                    });
                }
            }

            if (workflow.tasks && workflow.tasks.open_count) {
                tasks.push({
                    name: member.name,
                    detail: `${workflow.tasks.open_count} open task${workflow.tasks.open_count === 1 ? "" : "s"}`,
                });
            }
        }

        this.state.alerts = { onboarding, membership, tasks };
    }

    formatTime(dtStr) {
        if (!dtStr) return "";
        const d = new Date(dtStr.replace(" ", "T") + "Z");
        return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    }

    attendanceLabel(state) {
        const labels = {
            present: "Present",
            late: "Late",
            absent: "Absent",
            checked_out: "Checked out",
            pending: "Pending",
        };
        return labels[state || "pending"] || state || "Pending";
    }
}

// Export for use in kiosk_app.js if needed
window.KioskInstructorLayout = KioskInstructorLayout;
