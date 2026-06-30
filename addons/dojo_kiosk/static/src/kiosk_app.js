/**
 * Dojo Kiosk — OWL Single Page Application (v2)
 * Loaded as a plain script (no Odoo module loader).
 * Depends on /web/static/lib/owl/owl.js being loaded first.
 * Mounts to #kiosk-root on /kiosk/<token>
 */
/* global owl */
const { Component, useState, onMounted, onWillUnmount, mount, xml, useRef } = owl;

// ─── Config identity (per-tablet token from URL) ─────────────────────────────
const KIOSK_TOKEN = window.KIOSK_TOKEN || null;
const KIOSK_RELEASE_BRANCH = "rel/REL-20260629";
const KIOSK_RELEASE_INCREMENT = "INC-03";
const CHECKIN_SUCCESS_DISMISS_MS = 4000;

// ─── Utilities ────────────────────────────────────────────────────────────────

async function jsonPost(url, params = {}, { signal } = {}) {
    if (KIOSK_TOKEN) params = { token: KIOSK_TOKEN, ...params };
    const resp = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ jsonrpc: "2.0", method: "call", params }),
        signal,
    });
    const data = await resp.json();
    if (data.error) throw new Error(data.error.data?.message || data.error.message);
    return data.result;
}

// Play check-in success chime using Web Audio API
function playCheckinChime() {
    try {
        const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        const oscillator = audioCtx.createOscillator();
        const gainNode = audioCtx.createGain();

        oscillator.connect(gainNode);
        gainNode.connect(audioCtx.destination);

        // Pleasant confirmation tone: 800 Hz
        oscillator.frequency.value = 800;
        oscillator.type = "sine";

        // Volume envelope: fade in/out
        gainNode.gain.setValueAtTime(0, audioCtx.currentTime);
        gainNode.gain.linearRampToValueAtTime(0.3, audioCtx.currentTime + 0.05);
        gainNode.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.4);

        oscillator.start(audioCtx.currentTime);
        oscillator.stop(audioCtx.currentTime + 0.4);
    } catch (e) {
        console.warn("Kiosk: could not play chime", e);
    }
}

// Cache-bust map: memberId → timestamp, set after a photo upload so roster tiles & profile modal reload fresh
const _photoBust = {};

function avatarUrl(memberId) {
    const bust = _photoBust[memberId];
    return `/web/image/dojo.member/${memberId}/image_128${bust ? '?t=' + bust : ''}`;
}

function partnerAvatarUrl(partnerId) {
    return `/web/image/res.partner/${partnerId}/image_128`;
}

function initials(name) {
    if (!name) return "?";
    const parts = name.trim().split(/\s+/);
    return (parts[0][0] + (parts[1] ? parts[1][0] : "")).toUpperCase();
}

function formatTime(dtStr) {
    if (!dtStr) return "";
    const d = new Date(dtStr.replace(" ", "T") + "Z");
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function formatDateTime(dtStr) {
    if (!dtStr) return "";
    const d = new Date(dtStr.replace(" ", "T") + "Z");
    const today = new Date();
    const isToday = d.toDateString() === today.toDateString();
    const tomorrow = new Date(today);
    tomorrow.setDate(today.getDate() + 1);
    const isTomorrow = d.toDateString() === tomorrow.toDateString();
    const timeStr = d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    if (isToday) return "Today " + timeStr;
    if (isTomorrow) return "Tomorrow " + timeStr;
    return d.toLocaleDateString([], { month: "short", day: "numeric" }) + " " + timeStr;
}

function todayIso() {
    const d = new Date();
    return d.getFullYear() + "-" +
        String(d.getMonth() + 1).padStart(2, "0") + "-" +
        String(d.getDate()).padStart(2, "0");
}

function contrastColor(hexColor) {
    if (!hexColor || hexColor.length < 6) return "#1a1a1a";
    const hex = hexColor.replace("#", "");
    const r = parseInt(hex.substring(0, 2), 16);
    const g = parseInt(hex.substring(2, 4), 16);
    const b = parseInt(hex.substring(4, 6), 16);
    const lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
    return lum > 0.5 ? "#1a1a1a" : "#ffffff";
}

// ─── PinModal ─────────────────────────────────────────────────────────────────

class PinModal extends Component {
    static template = xml`
        <div class="k-modal-overlay" t-on-click.self="props.onClose">
            <div class="k-modal k-modal--sm" style="max-width:360px;">
                <button class="k-modal__close" style="position:absolute;top:14px;right:14px;" t-on-click="props.onClose">✕</button>
                <p class="k-pin-title">Instructor Mode</p>
                <p class="k-pin-subtitle">Enter 6-digit PIN to unlock</p>

                <div class="k-pin-boxes">
                    <t t-foreach="[0,1,2,3,4,5]" t-as="i" t-key="i">
                        <div t-attf-class="k-pin-box
                            #{state.pin.length === i ? ' k-pin-box--active' : ''}
                            #{state.pin.length > i ? ' k-pin-box--filled' : ''}">
                            <t t-if="state.pin.length > i">●</t>
                        </div>
                    </t>
                </div>

                <div class="k-pin-numpad">
                    <t t-foreach="['1','2','3','4','5','6','7','8','9']" t-as="d" t-key="d">
                        <button class="k-pin-key" t-on-click="() => this.pressKey(d)">
                            <t t-esc="d"/>
                        </button>
                    </t>
                    <button class="k-pin-key k-pin-key--wide" t-on-click="() => this.pressKey('0')">0</button>
                    <button class="k-pin-key k-pin-key--backspace" t-on-click="backspace">⌫</button>
                </div>

                <p class="k-pin-error">
                    <t t-if="state.error" t-esc="state.error"/>
                </p>
            </div>
        </div>
    `;

    static props = ["onClose", "onSuccess"];

    setup() {
        this.state = useState({ pin: "", error: "" });
    }

    pressKey(digit) {
        if (this.state.pin.length >= 6) return;
        this.state.pin += digit;
        this.state.error = "";
        if (this.state.pin.length === 6) this._verify();
    }

    backspace() {
        this.state.pin = this.state.pin.slice(0, -1);
        this.state.error = "";
    }

    async _verify() {
        try {
            const result = await jsonPost("/kiosk/auth/pin", { pin: this.state.pin });
            if (result.success) {
                this.props.onSuccess(result);
            } else if (result.error === "locked") {
                const mins = result.retry_in_minutes || 15;
                this.state.error = `Too many attempts. Locked for ${mins} min.`;
                this.state.pin = "";
            } else {
                const tries = result.remaining_tries;
                this.state.error = tries
                    ? `Incorrect PIN. ${tries} attempt${tries === 1 ? "" : "s"} remaining.`
                    : "Incorrect PIN. Try again.";
                this.state.pin = "";
            }
        } catch {
            this.state.error = "Could not verify PIN. Check connection.";
            this.state.pin = "";
        }
    }
}

// ─── CheckinSuccessView ───────────────────────────────────────────────────────

class CheckinSuccessView extends Component {
    static template = xml`
        <div t-attf-class="k-checkin-success-overlay k-success-view #{!props.success ? 'k-success-view--error' : ''}">
            <div class="k-success-icon">
                <t t-if="props.success">✅</t>
                <t t-else="">❌</t>
            </div>
            <div class="k-success-name" t-esc="props.memberName"/>
            <t t-if="props.success">
                <div class="k-success-session">
                    Checked in to <strong t-esc="props.sessionName"/>
                </div>
                <t t-if="props.programName">
                    <div class="k-success-program" t-esc="props.programName"/>
                </t>
                <t t-if="props.status === 'late'">
                    <div class="k-success-note k-success-note--late">⚠ Checked in late</div>
                </t>
                <t t-else="">
                    <div class="k-success-note">On time 🎉</div>
                </t>
            </t>
            <t t-else="">
                <div class="k-success-error" t-esc="props.errorMessage"/>
            </t>
            <div class="k-success-returning">Returning to kiosk…</div>
        </div>
    `;

    static props = ["success", "memberName", "sessionName", "programName", "status", "errorMessage", "onDone"];

    setup() {
        onMounted(() => {
            // Play chime on successful check-in
            if (this.props.success) {
                playCheckinChime();
            }
            this._timer = setTimeout(() => this.props.onDone(), CHECKIN_SUCCESS_DISMISS_MS);
        });
        onWillUnmount(() => clearTimeout(this._timer));
    }
}

// ─── IdleScreen ───────────────────────────────────────────────────────────────

class IdleScreen extends Component {
    static template = xml`
        <div class="k-idle-screen" t-on-click="wake" t-on-keydown="wake">
            <div class="k-idle-content">
                <t t-if="allSlides.length">
                    <t t-set="slide" t-value="currentSlide()"/>
                    <div class="k-idle-slide">
                        <div class="k-idle-slide__title" t-esc="slide.title or slide.name"/>
                        <t t-if="slide.subtitle">
                            <div class="k-idle-slide__subtitle" t-esc="slide.subtitle"/>
                        </t>
                        <t t-if="slide.body">
                            <div class="k-idle-slide__body" t-esc="slide.body"/>
                        </t>
                        <t t-if="slide.type === 'marketing'">
                            <t t-if="slide.card_type === 'badge'">
                                <div class="k-idle-slide__body">Scan your member badge at the front desk</div>
                            </t>
                            <t t-elif="slide.qr_url">
                                <img t-att-src="slide.qr_url" class="k-idle-slide__qr" alt="QR Code"/>
                            </t>
                        </t>
                    </div>
                    <t t-if="allSlides.length > 1">
                        <div class="k-idle-dots">
                            <t t-foreach="allSlides" t-as="s" t-key="s_index">
                                <div t-attf-class="k-idle-dot #{state.idx === s_index ? 'k-idle-dot--active' : ''}"/>
                            </t>
                        </div>
                    </t>
                </t>
                <t t-else="">
                    <div class="k-idle-slide">
                        <div class="k-idle-slide__dojo">🥋</div>
                        <div class="k-idle-slide__title">Welcome</div>
                        <div class="k-idle-slide__body">Tap to check in</div>
                    </div>
                </t>
                <div class="k-idle-tap-hint">Tap anywhere to continue</div>
            </div>
        </div>
    `;

    static props = ["announcements", "marketing_cards", "onWake"];

    setup() {
        this.state = useState({ idx: 0 });
        this._carouselTimer = null;
        onMounted(() => this._startCarousel());
        onWillUnmount(() => clearInterval(this._carouselTimer));
    }

    get allSlides() {
        const anns = (this.props.announcements || []).map(a => ({ ...a, type: "announcement" }));
        const cards = (this.props.marketing_cards || []).map(c => ({ ...c, type: "marketing" }));
        return [...anns, ...cards];
    }

    currentSlide() {
        const slides = this.allSlides;
        if (!slides.length) return { type: "default", title: "Welcome", body: "Tap to check in" };
        return slides[this.state.idx % slides.length];
    }

    _startCarousel() {
        const slides = this.allSlides;
        if (slides.length <= 1) return;
        this._carouselTimer = setInterval(() => {
            this.state.idx = (this.state.idx + 1) % this.allSlides.length;
        }, 5000);
    }

    wake() { this.props.onWake(); }
}

// ─── MemberProfileCard ────────────────────────────────────────────────────────

class MemberProfileCard extends Component {
    static template = xml`
        <div class="k-modal-overlay" t-on-click.self="props.onClose">
            <div class="k-modal k-modal--profile">
                <button class="k-modal__close" style="position:absolute;top:14px;right:14px;z-index:1;" t-on-click="props.onClose">✕</button>

                <!-- ── Head ── -->
                <div class="k-profile__head">
                    <div class="k-profile__avatar-wrap" style="position:relative;">
                        <t t-if="state.photoUploading">
                            <div class="k-profile__photo-uploading">
                                <div class="k-spinner"/>
                            </div>
                        </t>
                        <t t-if="props.member.image_url">
                            <img class="k-profile__avatar"
                                t-att-src="state.photoPreview || props.member.image_url"
                                t-att-alt="props.member.name"
                                t-on-error="onImgError"/>
                        </t>
                        <t t-else="">
                            <t t-if="state.photoPreview">
                                <img class="k-profile__avatar" t-att-src="state.photoPreview" t-att-alt="props.member.name"/>
                            </t>
                            <t t-else="">
                                <div class="k-profile__avatar-placeholder">
                                    <t t-esc="initials(props.member.name)"/>
                                </div>
                            </t>
                        </t>
                        <t t-if="isInstructorProfile()">
                            <button class="k-profile__photo-btn"
                                t-on-click="togglePhotoSheet"
                                t-att-disabled="state.photoUploading or undefined"
                                title="Update photo">📷</button>
                        </t>
                        <t t-if="state.showPhotoSheet">
                            <div class="k-profile__photo-sheet">
                                <button class="k-profile__photo-sheet-btn" t-on-click="takePhoto">📸 Take Photo</button>
                                <button class="k-profile__photo-sheet-btn" t-on-click="chooseFile">📁 Choose File</button>
                                <button class="k-profile__photo-sheet-btn k-profile__photo-sheet-btn--cancel" t-on-click="() => this.state.showPhotoSheet = false">Cancel</button>
                            </div>
                        </t>
                        <input type="file" accept="image/*" style="display:none;" t-ref="fileInput" t-on-change="onPhotoSelected"/>
                    </div>
                    <div class="k-profile__head-info">
                        <t t-if="state.photoError"><div class="k-profile__photo-msg k-profile__photo-msg--error" t-esc="state.photoError"/></t>
                        <t t-if="state.photoSuccess"><div class="k-profile__photo-msg k-profile__photo-msg--success" t-esc="state.photoSuccess"/></t>
                        <div class="k-profile__name" t-esc="props.member.name"/>
                        <div class="k-profile__belt" t-esc="props.member.belt_rank || 'No Rank'"/>
                        <t t-if="props.member.membership_state">
                            <span t-attf-class="k-membership-badge k-membership-badge--#{props.member.membership_state}"
                                t-esc="props.member.membership_state"/>
                        </t>
                    </div>
                </div>

                <!-- ── Tab bar ── -->
                <div class="k-profile-tabs">
                    <button t-attf-class="k-profile-tab #{state.tab === 'profile' ? 'k-profile-tab--active' : ''}"
                        t-on-click="() => this.state.tab = 'profile'">Profile</button>
                    <t t-if="isInstructorProfile()">
                        <button t-attf-class="k-profile-tab #{state.tab === 'progress' ? 'k-profile-tab--active' : ''}"
                            t-on-click="() => this.state.tab = 'progress'">Progress</button>
                        <button t-attf-class="k-profile-tab #{state.tab === 'household' ? 'k-profile-tab--active' : ''}"
                            t-on-click="() => this.state.tab = 'household'">Household</button>
                    </t>
                    <t t-if="props.instructorMode and isInstructorProfile()">
                        <button t-attf-class="k-profile-tab k-profile-tab--manage #{state.tab === 'manage' ? 'k-profile-tab--active' : ''}"
                            t-on-click="() => this.switchToManage()">⚙ Manage</button>
                    </t>
                </div>

                <!-- ══ Profile tab ══ -->
                <t t-if="state.tab === 'profile'">
                    <div class="k-profile__scroll-body">
                        <t t-if="!isInstructorProfile()">
                            <div class="k-profile-private-note">
                                <div class="k-profile-private-note__title">Check-in profile</div>
                                <div class="k-profile-private-note__body">
                                    Instructor details unlock after staff authorization.
                                </div>
                            </div>
                            <t t-if="props.member.enrolled_sessions and props.member.enrolled_sessions.length">
                                <div class="k-appointments">
                                    <div class="k-appointments__title">Today's Classes</div>
                                    <t t-foreach="props.member.enrolled_sessions" t-as="session" t-key="session.id">
                                        <div class="k-appt-row">
                                            <div class="k-appt-row__name" t-esc="session.template_name || session.name"/>
                                            <div class="k-appt-row__time" t-esc="formatDateTime(session.start)"/>
                                        </div>
                                    </t>
                                </div>
                            </t>
                        </t>

                        <t t-if="isInstructorProfile() and props.member.issues and props.member.issues.length">
                            <div class="k-warning-banner">
                                <div class="k-warning-banner__icon">!</div>
                                <div class="k-warning-banner__list">
                                    <t t-foreach="props.member.issues" t-as="issue" t-key="issue.code">
                                        <div class="k-warning-banner__item" t-esc="issue.label"/>
                                    </t>
                                </div>
                            </div>
                        </t>

                        <t t-if="isInstructorProfile()">
                            <div class="k-workflow-grid">
                                <div t-attf-class="k-workflow-card #{workflow().onboarding and workflow().onboarding.complete ? 'k-workflow-card--ok' : 'k-workflow-card--warn'}">
                                    <div class="k-workflow-card__label">Onboarding</div>
                                    <div class="k-workflow-card__value">
                                        <t t-if="workflow().onboarding and workflow().onboarding.available">
                                            <t t-esc="workflow().onboarding.progress_pct"/>%
                                        </t>
                                        <t t-else="">N/A</t>
                                    </div>
                                    <t t-if="workflow().onboarding and workflow().onboarding.missing_steps and workflow().onboarding.missing_steps.length">
                                        <div class="k-workflow-card__detail" t-esc="workflow().onboarding.missing_steps.slice(0, 2).join(', ')"/>
                                    </t>
                                </div>
                                <div t-attf-class="k-workflow-card #{workflow().waiver and workflow().waiver.signed ? 'k-workflow-card--ok' : 'k-workflow-card--warn'}">
                                    <div class="k-workflow-card__label">Waiver</div>
                                    <div class="k-workflow-card__value">
                                        <t t-if="workflow().waiver and workflow().waiver.available">
                                            <t t-esc="workflow().waiver.signed ? 'Signed' : 'Unsigned'"/>
                                        </t>
                                        <t t-else="">N/A</t>
                                    </div>
                                    <t t-if="workflow().waiver and workflow().waiver.signed_by">
                                        <div class="k-workflow-card__detail" t-esc="workflow().waiver.signed_by"/>
                                    </t>
                                </div>
                                <div t-attf-class="k-workflow-card #{workflow().subscription and workflow().subscription.good_standing ? 'k-workflow-card--ok' : 'k-workflow-card--warn'}">
                                    <div class="k-workflow-card__label">Membership</div>
                                    <div class="k-workflow-card__value">
                                        <t t-if="workflow().subscription" t-esc="workflow().subscription.state || 'none'"/>
                                    </div>
                                    <t t-if="workflow().subscription and workflow().subscription.plan_name">
                                        <div class="k-workflow-card__detail" t-esc="workflow().subscription.plan_name"/>
                                    </t>
                                </div>
                                <div t-attf-class="k-workflow-card #{workflow().grading and workflow().grading.ready ? 'k-workflow-card--ok' : ''}">
                                    <div class="k-workflow-card__label">Grading</div>
                                    <div class="k-workflow-card__value">
                                        <t t-if="workflow().grading" t-esc="workflow().grading.label"/>
                                    </div>
                                    <t t-if="workflow().grading and workflow().grading.next_rank">
                                        <div class="k-workflow-card__detail" t-esc="'Next: ' + workflow().grading.next_rank.name"/>
                                    </t>
                                </div>
                            </div>

                            <t t-if="workflow().tasks and workflow().tasks.open_count">
                                <div class="k-workflow-tasks">
                                    <div class="k-workflow-tasks__title">
                                        <t t-esc="workflow().tasks.open_count"/> Open Instructor Task<t t-if="workflow().tasks.open_count !== 1">s</t>
                                    </div>
                                    <t t-foreach="workflow().tasks.tasks || []" t-as="task" t-key="task.id">
                                        <div class="k-workflow-task-row">
                                            <span class="k-workflow-task-row__name" t-esc="task.name"/>
                                            <t t-if="task.deadline">
                                                <span class="k-workflow-task-row__deadline" t-esc="task.deadline"/>
                                            </t>
                                        </div>
                                    </t>
                                </div>
                            </t>

                            <div class="k-profile__stats">
                                <div class="k-stat">
                                    <span class="k-stat__value" t-esc="props.member.total_attendance"/>
                                    <span class="k-stat__label">Total Classes</span>
                                </div>
                                <div class="k-stat">
                                    <span class="k-stat__value">
                                        <t t-if="props.member.credits_per_period === 0">
                                            <span style="font-size:13px;font-weight:600;">Unlimited</span>
                                        </t>
                                        <t t-else="">
                                            <t t-esc="props.member.credit_balance"/>
                                            <span style="font-size:13px;font-weight:400;color:var(--k-text-3);"> / <t t-esc="props.member.credits_per_period"/></span>
                                        </t>
                                    </span>
                                    <span class="k-stat__label">Credits</span>
                                </div>
                            </div>

                            <div class="k-profile-info">
                                <t t-if="props.member.date_of_birth">
                                    <div class="k-info-row">
                                        <span class="k-info-row__label">Date of Birth</span>
                                        <span class="k-info-row__value" t-esc="props.member.date_of_birth"/>
                                    </div>
                                </t>
                                <t t-if="props.member.plan_name">
                                    <div class="k-info-row">
                                        <span class="k-info-row__label">Plan</span>
                                        <span class="k-info-row__value" t-esc="props.member.plan_name"/>
                                    </div>
                                </t>
                                <t t-if="props.member.email">
                                    <div class="k-info-row">
                                        <span class="k-info-row__label">Email</span>
                                        <span class="k-info-row__value" t-esc="props.member.email"/>
                                    </div>
                                </t>
                                <t t-if="props.member.phone">
                                    <div class="k-info-row">
                                        <span class="k-info-row__label">Phone</span>
                                        <span class="k-info-row__value" t-esc="props.member.phone"/>
                                    </div>
                                </t>
                            </div>

                            <t t-if="props.member.appointments and props.member.appointments.length">
                                <div class="k-appointments">
                                    <div class="k-appointments__title">Upcoming Classes</div>
                                    <t t-foreach="props.member.appointments" t-as="appt" t-key="appt.session_id">
                                        <div class="k-appt-row">
                                            <div class="k-appt-row__name" t-esc="appt.name"/>
                                            <div class="k-appt-row__time" t-esc="formatDateTime(appt.start)"/>
                                        </div>
                                    </t>
                                </div>
                            </t>
                        </t>
                    </div>

                    <div class="k-profile__actions">
                        <t t-if="isInstructorProfile()">
                            <div class="k-att-section">
                                <div class="k-att-section__label">Mark Attendance</div>
                                <div class="k-att-toggle--lg">
                                    <button
                                        t-attf-class="k-att-btn--lg #{props.member.attendance_state === 'present' ? 'k-att-btn--active-present' : ''}"
                                        t-on-click="() => this.markAttendance('present')">✓ Present</button>
                                    <button
                                        t-attf-class="k-att-btn--lg #{props.member.attendance_state === 'late' ? 'k-att-btn--active-late' : ''}"
                                        t-on-click="() => this.markAttendance('late')">~ Late</button>
                                    <button
                                        t-attf-class="k-att-btn--lg #{props.member.attendance_state === 'absent' ? 'k-att-btn--active-absent' : ''}"
                                        t-on-click="() => this.markAttendance('absent')">✕ Absent</button>
                                </div>
                            </div>
                            <div class="k-profile__roster-row">
                                <t t-if="!props.member.enrolled_in_session">
                                    <button class="k-btn k-btn--secondary" t-on-click="onRosterAdd">+ Add to Roster</button>
                                </t>
                                <t t-else="">
                                    <button class="k-btn k-btn--danger" t-on-click="onRosterRemove">− Remove from Roster</button>
                                </t>
                                <t t-if="state.rosterAddError">
                                    <div class="k-field-error" style="margin-top:6px;white-space:pre-line;" t-esc="state.rosterAddError"/>
                                </t>
                            </div>
                        </t>
                        <t t-else="">
                            <t t-if="props.member.attendance_state === 'present' or props.member.attendance_state === 'late'">
                                <div class="k-checkout-section">
                                    <div class="k-checkout-checkedin">✓ Already checked in</div>
                                    <button class="k-btn k-btn--checkout" t-on-click="onCheckout">Check Out</button>
                                </div>
                            </t>
                            <t t-elif="!props.sessionId">
                                <p style="text-align:center;color:var(--k-text-3);font-size:13px;">
                                    Select a session to check in.
                                </p>
                            </t>
                            <t t-elif="props.member.issues and props.member.issues.length">
                                <button class="k-btn k-btn--primary" t-on-click="onCheckin">Check In Anyway</button>
                            </t>
                            <t t-else="">
                                <button class="k-btn k-btn--primary" t-on-click="onCheckin">Check In</button>
                            </t>
                        </t>
                    </div>
                </t>

                <!-- ══ Progress tab ══ -->
                <t t-if="state.tab === 'progress' and isInstructorProfile()">
                    <div class="k-profile__scroll-body">
                        <div class="k-progress">
                            <div class="k-progress__stat">
                                <span class="k-progress__stat-value" t-esc="props.member.attendance_since_last_rank || 0"/>
                                <span class="k-progress__stat-label">Classes Since Last Belt Test</span>
                            </div>
                            <t t-if="props.member.programs and props.member.programs.length">
                                <div class="k-progress__programs-title">Programs</div>
                                <t t-foreach="props.member.programs" t-as="prog" t-key="prog.program_name">
                                    <div class="k-progress__prog-row">
                                        <div class="k-progress__prog-name" t-esc="prog.program_name"/>
                                        <div class="k-progress__prog-right">
                                            <t t-if="prog.rank_name">
                                                <span class="k-progress__rank-badge"
                                                    t-attf-style="background:#{prog.rank_color || '#e5e7eb'};color:#{computeContrast(prog.rank_color)};"
                                                    t-esc="prog.rank_name"/>
                                            </t>
                                            <span class="k-progress__att-count">
                                                <t t-esc="prog.attendance_count"/> classes
                                            </span>
                                        </div>
                                    </div>
                                </t>
                            </t>
                            <t t-else="">
                                <div class="k-empty" style="padding:24px 0;">
                                    <div class="k-empty__icon">🥋</div>
                                    <div class="k-empty__text">No rank history</div>
                                </div>
                            </t>
                        </div>
                    </div>
                </t>

                <!-- ══ Household tab ══ -->
                <t t-if="state.tab === 'household' and isInstructorProfile()">
                    <div class="k-profile__scroll-body">
                        <t t-if="props.member.household">
                            <div class="k-hh">
                                <div class="k-hh__name">🏠 <t t-esc="props.member.household.name"/></div>
                                <div class="k-hh__section-title">Members</div>
                                <div class="k-hh__members">
                                    <t t-foreach="props.member.household.members" t-as="hm" t-key="hm.id">
                                        <div class="k-hh__member-row">
                                            <div class="k-hh__member-avatar">
                                                <t t-esc="initials(hm.name)"/>
                                            </div>
                                            <div class="k-hh__member-info">
                                                <div class="k-hh__member-name" t-esc="hm.name"/>
                                                <div class="k-hh__member-role" t-esc="[hm.is_student &amp;&amp; 'Student', hm.is_guardian &amp;&amp; 'Guardian'].filter(x => x).join(' / ') || ''"/>
                                            </div>
                                        </div>
                                    </t>
                                </div>
                                <t t-if="props.member.household.emergency_contacts and props.member.household.emergency_contacts.length">
                                    <div class="k-hh__section-title">Emergency Contacts</div>
                                    <div class="k-hh__contacts">
                                        <t t-foreach="props.member.household.emergency_contacts" t-as="ec" t-key="ec_index">
                                            <div class="k-hh__contact">
                                                <div class="k-hh__contact-header">
                                                    <span class="k-hh__contact-name" t-esc="ec.name"/>
                                                    <t t-if="ec.is_primary">
                                                        <span class="k-hh__contact-primary">Primary</span>
                                                    </t>
                                                </div>
                                                <div class="k-hh__contact-rel" t-esc="ec.relationship"/>
                                                <t t-if="ec.phone">
                                                    <a t-att-href="'tel:' + ec.phone" class="k-hh__contact-phone">
                                                        📞 <t t-esc="ec.phone"/>
                                                    </a>
                                                </t>
                                            </div>
                                        </t>
                                    </div>
                                </t>
                            </div>
                        </t>
                        <t t-else="">
                            <div class="k-empty" style="padding:40px 0;">
                                <div class="k-empty__icon">🏠</div>
                                <div class="k-empty__text">No household on file</div>
                            </div>
                        </t>
                    </div>
                </t>

                <!-- ══ Manage tab (instructor only) ══ -->
                <t t-if="state.tab === 'manage' and props.instructorMode and isInstructorProfile()">
                    <div class="k-profile__scroll-body">

                        <!-- ── Onboarding Workflow ── -->
                        <div class="k-manage-section">
                            <div class="k-manage-section__title">Onboarding Workflow</div>
                            <t t-if="workflow().onboarding and workflow().onboarding.available">
                                <div class="k-onboarding-steps">
                                    <t t-foreach="workflow().onboarding.steps || []" t-as="step" t-key="step.key">
                                        <div t-attf-class="k-onboarding-step #{step.complete ? 'k-onboarding-step--done' : ''}">
                                            <span class="k-onboarding-step__label" t-esc="step.label"/>
                                            <t t-if="step.complete">
                                                <span class="k-onboarding-step__done">Done</span>
                                            </t>
                                            <t t-else="">
                                                <button class="k-btn k-btn--secondary k-onboarding-step__btn"
                                                    t-on-click="() => this.completeOnboardingStep(step.key)"
                                                    t-att-disabled="state.onboardingBusy or undefined">
                                                    Mark Complete
                                                </button>
                                            </t>
                                        </div>
                                    </t>
                                </div>
                            </t>
                            <t t-else="">
                                <div class="k-empty" style="padding:10px 0;">
                                    <div class="k-empty__text">Onboarding records unavailable</div>
                                </div>
                            </t>

                            <div class="k-field" style="margin-top:10px;margin-bottom:8px;">
                                <label class="k-field__label">Note / Reminder / Blocker</label>
                                <textarea class="k-field__input k-field__textarea" rows="3"
                                    t-model="state.onboardingNote"
                                    placeholder="Add operational context…"/>
                            </div>
                            <div class="k-onboarding-actions">
                                <button class="k-btn k-btn--secondary"
                                    t-on-click="addOnboardingNote"
                                    t-att-disabled="state.onboardingBusy or undefined">Add Note</button>
                                <button class="k-btn k-btn--secondary"
                                    t-on-click="sendOnboardingReminder"
                                    t-att-disabled="state.onboardingBusy or undefined">Send Reminder</button>
                                <button class="k-btn k-btn--danger"
                                    t-on-click="escalateOnboardingBlocker"
                                    t-att-disabled="state.onboardingBusy or undefined">Escalate</button>
                            </div>
                            <t t-if="state.onboardingSuccess">
                                <div class="k-manage__success-banner"><t t-esc="state.onboardingSuccess"/></div>
                            </t>
                            <t t-if="state.onboardingError">
                                <div class="k-field-error" style="margin-top:8px;" t-esc="state.onboardingError"/>
                            </t>
                        </div>

                        <!-- ── Belt Rank Promotion ── -->
                        <div class="k-manage-section">
                            <div class="k-manage-section__title">🥋 Belt Rank Promotion</div>
                            <t t-if="state.nextRankLoading">
                                <div style="text-align:center;padding:16px 0;"><div class="k-spinner"/></div>
                            </t>
                            <t t-elif="state.nextRankError">
                                <div class="k-field-error" t-esc="state.nextRankError"/>
                            </t>
                            <t t-elif="state.isHighestRank">
                                <div class="k-promote-highest">
                                    🏆 <t t-esc="props.member.name"/> is already at the highest rank
                                    <t t-if="state.currentRank">
                                        <span class="k-progress__rank-badge"
                                            t-attf-style="background:#{state.currentRank.color};color:#{computeContrast(state.currentRank.color)};"
                                            t-esc="state.currentRank.name"/>
                                    </t>
                                </div>
                            </t>
                            <t t-else="">
                                <div class="k-promote-step">
                                    <div class="k-promote-step__rank">
                                        <t t-if="state.currentRank">
                                            <span class="k-promote-step__chip"
                                                t-attf-style="background:#{state.currentRank.color};color:#{computeContrast(state.currentRank.color)};"
                                                t-esc="state.currentRank.name"/>
                                        </t>
                                        <t t-else="">
                                            <span class="k-promote-step__chip k-promote-step__chip--none">No Rank</span>
                                        </t>
                                    </div>
                                    <div class="k-promote-step__arrow">→</div>
                                    <div class="k-promote-step__rank">
                                        <t t-if="state.nextRank">
                                            <span class="k-promote-step__chip k-promote-step__chip--next"
                                                t-attf-style="background:#{state.nextRank.color};color:#{computeContrast(state.nextRank.color)};"
                                                t-esc="state.nextRank.name"/>
                                        </t>
                                    </div>
                                </div>
                                <t t-if="!state.promoteConfirming">
                                    <t t-if="state.promoteSuccess">
                                        <div class="k-manage__success-banner">✓ <t t-esc="state.promoteSuccess"/></div>
                                    </t>
                                    <t t-if="state.promoteError">
                                        <div class="k-field-error" t-esc="state.promoteError"/>
                                    </t>
                                    <button class="k-btn k-btn--primary k-manage__award-btn"
                                        t-on-click="startPromote"
                                        t-att-disabled="!state.nextRank or undefined">
                                        🥋 Promote to <t t-esc="state.nextRank ? state.nextRank.name : '...'"/>
                                    </button>
                                </t>
                                <t t-if="state.promoteConfirming">
                                    <div class="k-promote-confirm">
                                        <div class="k-promote-confirm__text">
                                            Promote <strong><t t-esc="props.member.name"/></strong>
                                            from <strong><t t-esc="state.currentRank ? state.currentRank.name : 'No Rank'"/></strong>
                                            to <strong><t t-esc="state.nextRank ? state.nextRank.name : ''"/></strong>?
                                        </div>
                                        <div class="k-promote-confirm__actions">
                                            <button class="k-btn k-btn--danger" t-on-click="cancelPromote">Cancel</button>
                                            <button class="k-btn k-btn--primary"
                                                t-on-click="confirmPromote"
                                                t-att-disabled="state.promoteAwarding or undefined">
                                                <t t-if="state.promoteAwarding">Promoting…</t>
                                                <t t-else="">Confirm Promotion</t>
                                            </button>
                                        </div>
                                    </div>
                                </t>
                            </t>
                        </div>

                        <!-- ── Contact Guardians ── -->
                        <div class="k-manage-section">
                            <div class="k-manage-section__title">💬 Contact Guardians</div>
                            <t t-if="props.member.guardians and props.member.guardians.length">
                                <div class="k-guardian-list">
                                    <t t-foreach="props.member.guardians" t-as="g" t-key="guardianPartnerId(g)">
                                        <div t-attf-class="k-guardian-item #{state.checkedGuardianIds.includes(guardianPartnerId(g)) ? 'k-guardian-item--checked' : ''}"
                                            t-on-click="() => this.toggleGuardian(guardianPartnerId(g))">
                                            <input type="checkbox"
                                                class="k-guardian-item__check"
                                                t-att-checked="state.checkedGuardianIds.includes(guardianPartnerId(g)) or undefined"
                                                t-on-click.stop="() => this.toggleGuardian(guardianPartnerId(g))"/>
                                            <div class="k-guardian-item__info">
                                                <div class="k-guardian-item__name">
                                                    <t t-esc="g.name"/>
                                                    <span class="k-guardian-item__relation" t-esc="' · ' + g.relation"/>
                                                    <t t-if="g.is_primary and g.relation !== 'self'">
                                                        <span class="k-guardian-item__primary">Primary</span>
                                                    </t>
                                                </div>
                                                <div class="k-guardian-item__contact">
                                                    <t t-if="g.phone"><span>📱 <t t-esc="g.phone"/></span></t>
                                                    <t t-if="g.email"><span>✉ <t t-esc="g.email"/></span></t>
                                                </div>
                                            </div>
                                        </div>
                                    </t>
                                </div>
                            </t>
                            <div class="k-field" style="margin-bottom:8px;">
                                <label class="k-field__label">Subject</label>
                                <input class="k-field__input" type="text"
                                    t-model="state.msgSubject"
                                    placeholder="Message from your Dojang"/>
                            </div>
                            <div class="k-field" style="margin-bottom:8px;">
                                <label class="k-field__label">Message</label>
                                <textarea class="k-field__input k-field__textarea" rows="3"
                                    t-model="state.msgBody"
                                    placeholder="Type your message here…"/>
                            </div>
                            <div class="k-manage__msg-channels">
                                <label class="k-check-label">
                                    <input type="checkbox"
                                        t-att-checked="state.msgSendSms or undefined"
                                        t-on-change="(ev) => this.state.msgSendSms = ev.target.checked"/>
                                    📱 SMS
                                </label>
                                <label class="k-check-label">
                                    <input type="checkbox"
                                        t-att-checked="state.msgSendEmail or undefined"
                                        t-on-change="(ev) => this.state.msgSendEmail = ev.target.checked"/>
                                    ✉ Email
                                </label>
                            </div>
                            <t t-if="state.msgSuccess">
                                <div class="k-manage__success-banner">✓ <t t-esc="state.msgSuccess"/></div>
                            </t>
                            <t t-if="state.msgError">
                                <div class="k-field-error" t-esc="state.msgError"/>
                            </t>
                            <button class="k-btn k-btn--primary k-manage__award-btn"
                                t-on-click="sendMessage"
                                t-att-disabled="state.msgSending or undefined">
                                <t t-if="state.msgSending">Sending…</t>
                                <t t-else="">Send Message</t>
                            </button>
                        </div>

                        <!-- ── Session Management ── -->
                        <div class="k-manage-section">
                            <div class="k-manage-section__title">📅 Session Management</div>
                            <t t-if="props.member.appointments and props.member.appointments.length">
                                <div class="k-manage__session-list">
                                    <t t-foreach="props.member.appointments" t-as="appt" t-key="appt.session_id">
                                        <div class="k-manage__session-row">
                                            <div class="k-manage__session-info">
                                                <div class="k-manage__session-name" t-esc="appt.name"/>
                                                <div class="k-manage__session-time" t-esc="formatDateTime(appt.start)"/>
                                            </div>
                                            <button class="k-btn k-btn--danger k-manage__session-remove"
                                                t-on-click="() => this.removeFromSession(appt.session_id)"
                                                title="Remove from this session">✕</button>
                                        </div>
                                    </t>
                                </div>
                            </t>
                            <t t-else="">
                                <div class="k-empty" style="padding:10px 0;">
                                    <div class="k-empty__text">No upcoming sessions enrolled</div>
                                </div>
                            </t>
                            <t t-if="props.sessionId and !props.member.enrolled_in_session">
                                <button class="k-btn k-btn--secondary" style="width:100%;margin-top:8px;"
                                    t-on-click="onRosterAddFromManage">
                                    + Add to Current Session
                                </button>
                                <t t-if="state.rosterAddError">
                                    <div class="k-field-error" style="margin-top:6px;white-space:pre-line;"
                                        t-esc="state.rosterAddError"/>
                                </t>
                            </t>
                            <button class="k-btn k-btn--secondary k-session-picker__toggle"
                                t-on-click="toggleSessionPicker">
                                <t t-if="state.showSessionPicker">▲ Close Session Picker</t>
                                <t t-else="">＋ Add to Another Session</t>
                            </button>
                            <t t-if="state.showSessionPicker">
                                <div class="k-session-picker">
                                    <t t-if="state.sessionsLoading">
                                        <div style="text-align:center;padding:12px;"><div class="k-spinner"/></div>
                                    </t>
                                    <t t-elif="state.sessionsLoadError">
                                        <div class="k-field-error" t-esc="state.sessionsLoadError"/>
                                    </t>
                                    <t t-elif="!state.availableSessions.length">
                                        <div class="k-empty" style="padding:10px 12px;">
                                            <div class="k-empty__text">No other sessions available for this student</div>
                                        </div>
                                    </t>
                                    <t t-else="">
                                        <t t-foreach="state.availableSessions" t-as="s" t-key="s.session_id">
                                            <div class="k-session-picker__row">
                                                <div class="k-session-picker__info">
                                                    <div class="k-session-picker__name" t-esc="s.name"/>
                                                    <div class="k-session-picker__meta">
                                                        <t t-if="s.program_name"><t t-esc="s.program_name"/> · </t>
                                                        <t t-esc="formatDateTime(s.start)"/>
                                                        <t t-if="s.seats_available and s.seats_available &lt; 99">
                                                            · <t t-esc="s.seats_available"/> seats
                                                        </t>
                                                    </div>
                                                </div>
                                                <button class="k-btn k-btn--secondary k-session-picker__add-btn"
                                                    t-on-click="() => this.addToSession(s.session_id)">Add</button>
                                            </div>
                                        </t>
                                    </t>
                                </div>
                            </t>
                            <t t-if="state.sessionRemoveMsg">
                                <div class="k-manage__success-banner" style="margin-top:8px;">
                                    ✓ <t t-esc="state.sessionRemoveMsg"/>
                                </div>
                            </t>
                        </div>

                    </div>
                </t>


            </div>
        </div>

        <!-- ── Camera capture modal ── -->
        <t t-if="state.showCamera">
            <div class="k-modal-overlay k-camera-overlay" t-on-click.self="closeCamera">
                <div class="k-camera-modal">
                    <div class="k-camera-modal__header">
                        <span class="k-camera-modal__title">Take Photo</span>
                        <button class="k-modal__close" t-on-click="closeCamera">✕</button>
                    </div>
                    <div class="k-camera-modal__body">
                        <t t-if="state.cameraError">
                            <div class="k-camera-modal__error" t-esc="state.cameraError"/>
                        </t>
                        <video t-ref="cameraVideo" class="k-camera-modal__video" autoplay="true" playsinline="true"
                            t-att-style="state.cameraCaptured ? 'display:none' : ''"/>
                        <canvas t-ref="cameraCanvas" class="k-camera-modal__canvas"
                            t-att-style="state.cameraCaptured ? '' : 'display:none'"/>
                    </div>
                    <div class="k-camera-modal__actions">
                        <t t-if="!state.cameraCaptured">
                            <button class="k-btn k-btn--primary k-camera-modal__snap" t-on-click="capturePhoto" t-att-disabled="!!state.cameraError">📸 Capture</button>
                        </t>
                        <t t-else="">
                            <button class="k-btn k-btn--secondary" t-on-click="retakePhoto">↺ Retake</button>
                            <button class="k-btn k-btn--primary" t-on-click="usePhoto">✓ Use Photo</button>
                        </t>
                    </div>
                </div>
            </div>
        </t>
    `;

    static props = ["member", "sessionId", "instructorMode", "instructorKey", "initialTab", "onClose", "onCheckin", "onMarkAttendance", "onRosterAdd", "onRosterRemove", "onCheckout", "onRosterRemoveBySession", "onRefreshProfile"];

    setup() {
        const requestedTab = (this.props.initialTab && this.props.initialTab !== "photo") ? this.props.initialTab : "profile";
        const initialTab = this.props.instructorMode && this.props.member.workflow_status ? requestedTab : "profile";
        this.state = useState({
            tab: initialTab,
            rosterAddError: "",
            // Photo update
            showPhotoSheet: this.props.initialTab === "photo" && !!(this.props.instructorMode && this.props.member.workflow_status),
            photoUploading: false,
            photoError: "",
            photoSuccess: "",
            photoPreview: null,
            // Camera modal
            showCamera: false,
            cameraError: "",
            cameraCaptured: false,
            // Manage tab — rank promotion
            nextRankLoading: false,
            nextRankError: "",
            currentRank: null,
            nextRank: null,
            isHighestRank: false,
            promoteConfirming: false,
            promoteAwarding: false,
            promoteSuccess: "",
            promoteError: "",
            // Manage tab — guardians & messaging
            checkedGuardianIds: [],
            msgSubject: "Message from your Dojang",
            msgBody: "",
            msgSendSms: true,
            msgSendEmail: true,
            msgSending: false,
            msgSuccess: "",
            msgError: "",
            // Manage tab — sessions
            showSessionPicker: false,
            availableSessions: [],
            sessionsLoading: false,
            sessionsLoadError: "",
            sessionRemoveMsg: "",
            // Manage tab — onboarding workflow
            onboardingBusy: false,
            onboardingNote: "",
            onboardingSuccess: "",
            onboardingError: "",
        });
        this.fileInputRef = useRef("fileInput");
        this.cameraVideoRef = useRef("cameraVideo");
        this.cameraCanvasRef = useRef("cameraCanvas");
        this._cameraStream = null;
    }

    initials(name) { return initials(name); }
    formatDateTime(dt) { return formatDateTime(dt); }
    computeContrast(hex) { return contrastColor(hex); }
    workflow() { return this.props.member.workflow_status || {}; }
    isInstructorProfile() { return !!(this.props.instructorMode && this.props.member.workflow_status); }
    instructorParams(params = {}) { return { ...params, instructor_key: this.props.instructorKey }; }
    guardianPartnerId(guardian) { return guardian.partner_id || guardian.member_id; }
    onImgError(ev) { ev.target.style.display = "none"; }
    onboardingStepComplete(workflow, stepKey) {
        const steps = (((workflow || {}).onboarding || {}).steps || []);
        return steps.some(step => step.key === stepKey && step.complete);
    }

    // ── Photo update ────────────────────────────────────────────
    async finishPhotoUpload(result) {
        if (result && result.success) {
            this.state.photoError = "";
            this.state.photoSuccess = "Photo updated!";
            this.state.photoPreview = result.image_url || null;
            if (this.props.onRefreshProfile) {
                await this.props.onRefreshProfile(this.props.member, result);
            }
            return true;
        }
        this.state.photoSuccess = "";
        this.state.photoError = (result && result.error) || "Upload failed.";
        this.state.photoPreview = null;
        return false;
    }

    togglePhotoSheet() {
        if (this.state.photoUploading) return;
        this.state.showPhotoSheet = !this.state.showPhotoSheet;
        this.state.photoError = "";
        this.state.photoSuccess = "";
    }
    async takePhoto() {
        this.state.showPhotoSheet = false;
        this.state.showCamera = true;
        this.state.cameraError = "";
        this.state.cameraCaptured = false;
        // Wait for DOM to render the video element
        await new Promise(r => setTimeout(r, 50));
        try {
            this._cameraStream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: "environment", width: { ideal: 640 }, height: { ideal: 640 } },
                audio: false,
            });
            if (this.cameraVideoRef.el) {
                this.cameraVideoRef.el.srcObject = this._cameraStream;
            }
        } catch (e) {
            this.state.cameraError = "Could not access camera. Please check permissions.";
        }
    }
    _stopCamera() {
        if (this._cameraStream) {
            this._cameraStream.getTracks().forEach(t => t.stop());
            this._cameraStream = null;
        }
    }
    closeCamera() {
        this._stopCamera();
        this.state.showCamera = false;
        this.state.cameraCaptured = false;
        this.state.cameraError = "";
    }
    capturePhoto() {
        const video = this.cameraVideoRef.el;
        const canvas = this.cameraCanvasRef.el;
        if (!video || !canvas) return;
        // Use square crop from the center of the video
        const size = Math.min(video.videoWidth, video.videoHeight);
        canvas.width = size;
        canvas.height = size;
        const ctx = canvas.getContext("2d");
        const sx = (video.videoWidth - size) / 2;
        const sy = (video.videoHeight - size) / 2;
        ctx.drawImage(video, sx, sy, size, size, 0, 0, size, size);
        this._stopCamera();
        this.state.cameraCaptured = true;
    }
    async retakePhoto() {
        this.state.cameraCaptured = false;
        this.state.cameraError = "";
        await new Promise(r => setTimeout(r, 50));
        try {
            this._cameraStream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: "environment", width: { ideal: 640 }, height: { ideal: 640 } },
                audio: false,
            });
            if (this.cameraVideoRef.el) {
                this.cameraVideoRef.el.srcObject = this._cameraStream;
            }
        } catch (e) {
            this.state.cameraError = "Could not access camera.";
        }
    }
    async usePhoto() {
        const canvas = this.cameraCanvasRef.el;
        if (!canvas) return;
        const dataUrl = canvas.toDataURL("image/jpeg", 0.85);
        this.closeCamera();
        this.state.photoPreview = dataUrl;
        this.state.photoUploading = true;
        this.state.photoError = "";
        this.state.photoSuccess = "";
        try {
            const base64 = dataUrl.split(",")[1];
            const result = await jsonPost("/kiosk/instructor/update_photo", this.instructorParams({
                member_id: this.props.member.member_id,
                image_data: base64,
            }));
            await this.finishPhotoUpload(result);
        } catch (e) {
            this.state.photoError = "Network error uploading photo.";
            this.state.photoSuccess = "";
            this.state.photoPreview = null;
        } finally {
            this.state.photoUploading = false;
        }
    }
    chooseFile() {
        this.state.showPhotoSheet = false;
        if (this.fileInputRef.el) { this.fileInputRef.el.value = ""; this.fileInputRef.el.click(); }
    }
    async onPhotoSelected(ev) {
        const file = ev.target.files && ev.target.files[0];
        if (!file) return;
        if (!file.type.startsWith("image/")) {
            this.state.photoError = "Please select an image file.";
            return;
        }
        if (file.size > 10 * 1024 * 1024) {
            this.state.photoError = "Image must be under 10 MB.";
            return;
        }
        this.state.photoError = "";
        this.state.photoSuccess = "";
        this.state.photoUploading = true;
        try {
            const dataUrl = await new Promise((resolve, reject) => {
                const reader = new FileReader();
                reader.onload = () => resolve(reader.result);
                reader.onerror = reject;
                reader.readAsDataURL(file);
            });
            this.state.photoPreview = dataUrl;
            const base64 = dataUrl.split(",")[1];
            const result = await jsonPost("/kiosk/instructor/update_photo", this.instructorParams({
                member_id: this.props.member.member_id,
                image_data: base64,
            }));
            await this.finishPhotoUpload(result);
        } catch (e) {
            this.state.photoError = "Network error uploading photo.";
            this.state.photoSuccess = "";
            this.state.photoPreview = null;
        } finally {
            this.state.photoUploading = false;
        }
    }

    markAttendance(status) { this.props.onMarkAttendance(this.props.member, this.props.sessionId, status); }
    onCheckin() { this.props.onCheckin(this.props.member, this.props.sessionId); }
    onCheckout() { this.props.onCheckout(this.props.member, this.props.sessionId); }
    async onRosterAdd() {
        this.state.rosterAddError = "";
        const result = await this.props.onRosterAdd(this.props.member, this.props.sessionId);
        if (result && result.success) {
            this.props.onClose();
        } else {
            this.state.rosterAddError = (result && result.error) || "Could not add to roster.";
        }
    }
    onRosterRemove() { this.props.onRosterRemove(this.props.member, this.props.sessionId); this.props.onClose(); }

    // ── Manage tab ──────────────────────────────────────────────

    async switchToManage() {
        this.state.tab = "manage";
        this.state.checkedGuardianIds = (this.props.member.guardians || []).map(g => this.guardianPartnerId(g)).filter(Boolean);
        if (!this.state.nextRankLoading && !this.state.currentRank && !this.state.nextRank && !this.state.isHighestRank) {
            await this._loadNextRank();
        }
    }

    // ── Onboarding workflow actions ──────────────────────────────
    // Per SPECIFICATION.md §6.1, onboarding actions use dedicated endpoints:
    // - POST /kiosk/api/onboarding/complete_step (params: member_id, step_key)
    // - POST /kiosk/api/onboarding/send_reminder (params: member_id, message)

    async completeOnboardingStep(stepKey) {
        this.state.onboardingBusy = true;
        this.state.onboardingError = "";
        this.state.onboardingSuccess = "";
        try {
            const result = await jsonPost("/kiosk/api/onboarding/complete_step", this.instructorParams({
                member_id: this.props.member.member_id,
                step_key: stepKey,
            }));
            if (result && result.success) {
                if (!result.changed || !this.onboardingStepComplete(result.workflow_status, stepKey)) {
                    this.state.onboardingError = "Step completion was not reflected by the workflow.";
                    return;
                }
                if (this.props.onRefreshProfile) {
                    const refreshed = await this.props.onRefreshProfile(this.props.member);
                    if (!refreshed) {
                        this.state.onboardingError = "Profile refresh failed after step completion.";
                        return;
                    }
                    if (!this.onboardingStepComplete(refreshed.workflow_status, stepKey)) {
                        this.state.onboardingError = "Profile refresh did not reflect the completed step.";
                        return;
                    }
                }
                this.state.onboardingSuccess = "Step marked complete.";
            } else {
                this.state.onboardingError = (result && result.error) || "Could not mark step complete.";
            }
        } catch (e) {
            this.state.onboardingError = "Network error.";
        } finally {
            this.state.onboardingBusy = false;
        }
    }

    async addOnboardingNote() {
        const note = (this.state.onboardingNote || "").trim();
        if (!note) {
            this.state.onboardingError = "Enter a note first.";
            return;
        }
        this.state.onboardingBusy = true;
        this.state.onboardingError = "";
        this.state.onboardingSuccess = "";
        try {
            // Note: add_note not in §6.1 spec; using legacy instructor/onboarding/action endpoint
            const result = await jsonPost("/kiosk/instructor/onboarding/action", this.instructorParams({
                member_id: this.props.member.member_id,
                action: "add_note",
                note,
            }));
            if (result && result.success) {
                this.state.onboardingSuccess = "Note added.";
                this.state.onboardingNote = "";
                if (this.props.onRefreshProfile) await this.props.onRefreshProfile(this.props.member);
            } else {
                this.state.onboardingError = (result && result.error) || "Could not add note.";
            }
        } catch {
            this.state.onboardingError = "Network error.";
        } finally {
            this.state.onboardingBusy = false;
        }
    }

    async sendOnboardingReminder() {
        const message = (this.state.onboardingNote || "").trim();
        this.state.onboardingBusy = true;
        this.state.onboardingError = "";
        this.state.onboardingSuccess = "";
        try {
            const result = await jsonPost("/kiosk/api/onboarding/send_reminder", this.instructorParams({
                member_id: this.props.member.member_id,
                message: message || undefined,
            }));
            if (result && result.success) {
                const sentVia = (result.sent_via || []).join(", ");
                const recipientCount = (result.recipients || []).length;
                this.state.onboardingSuccess = `Reminder sent${sentVia ? " via " + sentVia : ""}${recipientCount ? " to " + recipientCount + " recipient" + (recipientCount === 1 ? "" : "s") : ""}.`;
                this.state.onboardingNote = "";
                if (this.props.onRefreshProfile) await this.props.onRefreshProfile(this.props.member);
            } else {
                this.state.onboardingError = (result && result.error) || "Could not send reminder.";
            }
        } catch {
            this.state.onboardingError = "Network error.";
        } finally {
            this.state.onboardingBusy = false;
        }
    }

    async escalateOnboardingBlocker() {
        const note = (this.state.onboardingNote || "").trim();
        if (!note) {
            this.state.onboardingError = "Enter a blocker note first.";
            return;
        }
        const incomplete = ((this.workflow().onboarding || {}).steps || []).find(step => !step.complete);
        this.state.onboardingBusy = true;
        this.state.onboardingError = "";
        this.state.onboardingSuccess = "";
        try {
            // Note: escalate_blocker not in §6.1 spec; using legacy instructor/onboarding/action endpoint
            const result = await jsonPost("/kiosk/instructor/onboarding/action", this.instructorParams({
                member_id: this.props.member.member_id,
                action: "escalate_blocker",
                step_key: incomplete ? incomplete.key : null,
                note,
            }));
            if (result && result.success) {
                this.state.onboardingSuccess = "Blocker escalated.";
                this.state.onboardingNote = "";
                if (this.props.onRefreshProfile) await this.props.onRefreshProfile(this.props.member);
            } else {
                this.state.onboardingError = (result && result.error) || "Could not escalate blocker.";
            }
        } catch {
            this.state.onboardingError = "Network error.";
        } finally {
            this.state.onboardingBusy = false;
        }
    }

    async _loadNextRank() {
        this.state.nextRankLoading = true;
        this.state.nextRankError = "";
        try {
            const result = await jsonPost("/kiosk/instructor/next_rank", this.instructorParams({
                member_id: this.props.member.member_id,
            }));
            if (result && result.success) {
                this.state.currentRank = result.current_rank;
                this.state.nextRank = result.next_rank;
                this.state.isHighestRank = result.is_highest_rank || false;
            } else {
                this.state.nextRankError = (result && result.error) || "Could not load rank info.";
            }
        } catch {
            this.state.nextRankError = "Network error loading rank info.";
        } finally {
            this.state.nextRankLoading = false;
        }
    }

    startPromote() {
        this.state.promoteConfirming = true;
        this.state.promoteError = "";
        this.state.promoteSuccess = "";
    }

    cancelPromote() {
        this.state.promoteConfirming = false;
    }

    async confirmPromote() {
        if (!this.state.nextRank) return;
        this.state.promoteAwarding = true;
        this.state.promoteError = "";
        this.state.promoteSuccess = "";
        try {
            const result = await jsonPost("/kiosk/instructor/award_rank", this.instructorParams({
                member_id: this.props.member.member_id,
                rank_id: this.state.nextRank.id,
            }));
            if (result && result.success) {
                this.state.promoteSuccess = `🥋 ${result.rank_name} awarded to ${this.props.member.name}!`;
                this.state.promoteConfirming = false;
                this.state.currentRank = null;
                this.state.nextRank = null;
                this.state.isHighestRank = false;
                await this._loadNextRank();
                if (this.props.onRefreshProfile) await this.props.onRefreshProfile(this.props.member);
            } else {
                this.state.promoteError = (result && result.error) || "Could not award rank.";
                this.state.promoteConfirming = false;
            }
        } catch {
            this.state.promoteError = "Network error.";
            this.state.promoteConfirming = false;
        } finally {
            this.state.promoteAwarding = false;
        }
    }

    toggleGuardian(memberId) {
        const idx = this.state.checkedGuardianIds.indexOf(memberId);
        if (idx >= 0) {
            this.state.checkedGuardianIds = this.state.checkedGuardianIds.filter(id => id !== memberId);
        } else {
            this.state.checkedGuardianIds = [...this.state.checkedGuardianIds, memberId];
        }
    }

    async sendMessage() {
        if (!this.state.msgBody.trim()) {
            this.state.msgError = "Please enter a message.";
            return;
        }
        if (!this.state.msgSendSms && !this.state.msgSendEmail) {
            this.state.msgError = "Select at least one channel (SMS or Email).";
            return;
        }
        this.state.msgSending = true;
        this.state.msgError = "";
        this.state.msgSuccess = "";
        try {
            const result = await jsonPost("/kiosk/instructor/send_message", this.instructorParams({
                member_id: this.props.member.member_id,
                guardian_member_ids: this.state.checkedGuardianIds,
                subject: this.state.msgSubject || "Message from your Dojang",
                message: this.state.msgBody,
                send_sms: this.state.msgSendSms,
                send_email: this.state.msgSendEmail,
            }));
            if (result && result.success) {
                const channels = (result.sent_via || []).join(" & ") || "message";
                const toNames = (result.recipients || (result.recipient_name ? [result.recipient_name] : [])).join(", ");
                this.state.msgSuccess = `Sent via ${channels}${toNames ? " to " + toNames : ""}.`;
                this.state.msgBody = "";
            } else {
                this.state.msgError = (result && result.error) || "Failed to send message.";
            }
        } catch {
            this.state.msgError = "Network error.";
        } finally {
            this.state.msgSending = false;
        }
    }

    async toggleSessionPicker() {
        this.state.showSessionPicker = !this.state.showSessionPicker;
        if (this.state.showSessionPicker && !this.state.availableSessions.length && !this.state.sessionsLoading) {
            await this._loadAvailableSessions();
        }
    }

    async _loadAvailableSessions() {
        this.state.sessionsLoading = true;
        this.state.sessionsLoadError = "";
        try {
            const result = await jsonPost("/kiosk/instructor/available_sessions", this.instructorParams({
                member_id: this.props.member.member_id,
            }));
            if (result && result.success) {
                this.state.availableSessions = result.sessions || [];
            } else {
                this.state.sessionsLoadError = (result && result.error) || "Could not load sessions.";
            }
        } catch {
            this.state.sessionsLoadError = "Network error.";
        } finally {
            this.state.sessionsLoading = false;
        }
    }

    async addToSession(sessionId) {
        try {
            const result = await jsonPost("/kiosk/instructor/roster/add", this.instructorParams({
                session_id: sessionId,
                member_id: this.props.member.member_id,
                override_settings: true,
            }));
            if (result && result.success) {
                this.state.sessionRemoveMsg = "Added to session.";
                this.state.showSessionPicker = false;
                this.state.availableSessions = [];
                if (this.props.onRefreshProfile) await this.props.onRefreshProfile(this.props.member);
            } else {
                this.state.sessionsLoadError = (result && result.error) || "Could not add to session.";
            }
        } catch {
            this.state.sessionsLoadError = "Network error.";
        }
    }

    async onRosterAddFromManage() {
        this.state.rosterAddError = "";
        const result = await this.props.onRosterAdd(this.props.member, this.props.sessionId);
        if (result && result.success) {
            this.state.sessionRemoveMsg = `${this.props.member.name} added to current session.`;
        } else {
            this.state.rosterAddError = (result && result.error) || "Could not add to roster.";
        }
    }

    async removeFromSession(sessionId) {
        this.state.sessionRemoveMsg = "";
        await this.props.onRosterRemoveBySession(this.props.member, sessionId);
        this.state.sessionRemoveMsg = "Removed from session.";
    }

}

// ─── HomeContent ──────────────────────────────────────────────────────────────

class HomeContent extends Component {
    static template = xml`
        <div class="k-home">
            <t t-if="props.loading">
                <div class="k-home__searching">
                    <div class="k-spinner k-spinner--lg"/>
                </div>
            </t>
            <t t-elif="props.results.length">
                <div class="k-results-grid">
                    <t t-foreach="props.results" t-as="m" t-key="m.is_trial ? 'lead_' + m.lead_id : m.member_id">
                        <MemberCard member="m" onSelect="props.onSelect"/>
                    </t>
                </div>
            </t>
            <t t-else="">
                <div class="k-home__no-results">
                    <div class="k-home__no-results-icon">search_off</div>
                    <div t-esc="emptyMessage()"/>
                </div>
            </t>
        </div>
    `;
    static props = ["query", "results", "loading", "onSelect"];

    emptyMessage() {
        const query = (this.props.query || "").trim();
        return query
            ? `No students match "${query}"`
            : "No students are on the current class roster.";
    }
}

// ─── MemberCard (icon tile) ──────────────────────────────────────────────────

class MemberCard extends Component {
    static template = xml`
        <button type="button"
            t-attf-class="k-member-tile #{checkedIn(props.member) ? 'k-member-tile--checked-in' : ''}"
            t-att-aria-label="affordanceLabel(props.member) + ' for ' + props.member.name"
            t-att-data-student-card="props.member.is_trial ? 'trial' : 'member'"
            t-att-data-member-id="props.member.member_id || ''"
            t-att-data-lead-id="props.member.lead_id || ''"
            t-att-data-attendance-state="props.member.attendance_state || 'pending'"
            t-on-click="() => props.onSelect(props.member)">
            <div class="k-member-tile__avatar-wrap">
                <img class="k-member-tile__avatar"
                    t-att-src="memberAvatarUrl(props.member)"
                    t-att-alt="props.member.name"
                    t-on-error="onImgError"/>
            </div>
            <div class="k-member-tile__body">
                <!-- Legacy served-asset marker for older gates: k-member-tile__trial-badge -->
                <div class="k-member-tile__topline">
                    <div class="k-member-tile__name" t-att-title="props.member.name">
                        <t t-foreach="nameLines(props.member)" t-as="part" t-key="part_index">
                            <span class="k-member-tile__name-line" t-esc="part"/>
                        </t>
                    </div>
                    <t t-if="stateLabel(props.member)">
                        <span t-attf-class="k-member-tile__state k-member-tile__state--#{stateClass(props.member)}"
                            t-esc="stateLabel(props.member)"/>
                    </t>
                </div>
                <div class="k-member-tile__details">
                    <t t-if="programName(props.member)">
                        <span class="k-member-tile__program" t-esc="programName(props.member)"/>
                    </t>
                    <t t-if="props.member.belt_rank">
                        <span class="k-member-tile__belt" t-esc="props.member.belt_rank"/>
                    </t>
                </div>
                <div class="k-member-tile__affordance">
                    <span class="material-symbols-outlined">check_circle</span>
                    <span t-esc="affordanceLabel(props.member)"/>
                </div>
            </div>
        </button>
    `;
    static props = ["member", "onSelect"];
    memberAvatarUrl(member) {
        if (member.image_url) return member.image_url;
        if (member.is_trial && member.partner_id) return partnerAvatarUrl(member.partner_id);
        return avatarUrl(member.member_id);
    }
    programName(member) {
        return member.program_name || member.trial_program || "";
    }
    nameLines(member) {
        const name = (member.name || "").trim();
        if (!name) return ["Unknown"];
        const parts = name.split(/\s+/);
        if (parts.length === 1) return [parts[0]];
        return [parts[0], parts.slice(1).join(" ")];
    }
    checkedIn(member) {
        return ["present", "late"].includes(member.attendance_state || "");
    }
    stateLabel(member) {
        if (this.checkedIn(member)) return "ALREADY CHECKED IN";
        if (member.is_trial) return "TRIAL";
        return "";
    }
    stateClass(member) {
        if (this.checkedIn(member)) return "checked-in";
        return (member.membership_state || "unknown").replace(/[^a-z0-9_-]/gi, "").toLowerCase();
    }
    affordanceLabel(member) {
        if (this.checkedIn(member)) return "Already checked in";
        return member.is_trial ? "Tap for trial check-in" : "Tap to check in";
    }
    onImgError(ev) {
        const img = ev.target;
        const ph = document.createElement("div");
        ph.className = "k-member-tile__initials";
        ph.textContent = initials(this.props.member.name);
        img.parentElement.replaceChild(ph, img);
    }
}

HomeContent.components = { MemberCard };

// ─── StudentCheckinModal ─────────────────────────────────────────────────────

class StudentCheckinModal extends Component {
    static template = xml`
        <div class="k-modal-overlay" t-on-click.self="onOverlayClick">
            <div class="k-modal k-modal--checkin">

                <!-- Member head (always shown) -->
                <div class="k-checkin-modal__head">
                    <div class="k-checkin-modal__avatar-wrap">
                        <img class="k-checkin-modal__avatar"
                            t-att-src="memberAvatarUrl(props.member)"
                            t-att-alt="props.member.name"
                            t-on-error="onImgError"/>
                    </div>
                    <div class="k-checkin-modal__name" t-esc="props.member.name"/>
                    <t t-if="props.member.belt_rank">
                        <div class="k-checkin-modal__belt" t-esc="props.member.belt_rank"/>
                    </t>
                    <div class="k-checkin-modal__identity-row">
                        <t t-if="programName(props.member)">
                            <span class="k-checkin-modal__program" t-esc="programName(props.member)"/>
                        </t>
                        <t t-if="stateLabel(props.member)">
                            <span t-attf-class="k-checkin-modal__state k-checkin-modal__state--#{stateClass(props.member)}"
                                t-esc="stateLabel(props.member)"/>
                        </t>
                    </div>
                </div>

                <!-- ── Result view (checkin or checkout success/error) ── -->
                <t t-if="props.result">
                    <div class="k-checkin-modal__success">
                        <t t-if="props.result.success">
                            <div class="k-checkin-modal__success-msg">
                                <t t-if="props.result.type === 'checkout'">✓ You have been checked out</t>
                                <t t-else="">✓ You have been checked in</t>
                            </div>
                            <div class="k-checkin-modal__success-session" t-esc="props.result.sessionName"/>
                            <t t-if="props.result.type !== 'checkout'">
                                <div class="k-checkin-modal__success-chips">
                                    <t t-if="props.result.programName">
                                        <span class="k-checkin-modal__success-chip" t-esc="props.result.programName"/>
                                    </t>
                                    <t t-if="props.member.belt_rank">
                                        <span class="k-checkin-modal__success-chip" t-esc="props.member.belt_rank"/>
                                    </t>
                                </div>
                            </t>
                        </t>
                        <t t-else="">
                            <div class="k-checkin-modal__success-msg k-checkin-modal__success-msg--error">
                                ✕ <t t-esc="props.result.error || 'Action failed'"/>
                            </div>
                        </t>
                        <div class="k-checkin-modal__success-returning">Returning to kiosk…</div>
                    </div>
                </t>

                <!-- ── Checkout confirmation (already checked in) ── -->
                <t t-elif="props.checkedInSession">
                    <div class="k-checkin-modal__checkout">
                        <div class="k-checkin-modal__checkout-status">✓ Already checked in</div>
                        <div class="k-checkin-modal__checkout-session" t-esc="props.checkedInSession.template_name || props.checkedInSession.name"/>
                        <t t-if="props.checkedInSession.program_name">
                            <div class="k-checkin-modal__checkout-program" t-esc="props.checkedInSession.program_name"/>
                        </t>
                        <div class="k-checkin-modal__checkout-time">
                            <t t-esc="formatTime(props.checkedInSession.start)"/> – <t t-esc="formatTime(props.checkedInSession.end)"/>
                        </div>
                        <button class="k-btn k-checkin-modal__checkout-btn"
                            t-on-click="() => props.onCheckout(props.checkedInSession)">
                            Check Out
                        </button>
                    </div>
                    <div class="k-checkin-modal__notme-wrap">
                        <button class="k-btn k-checkin-modal__notme-btn" t-on-click="props.onClose">
                            That's not me
                        </button>
                    </div>
                </t>

                <!-- ── Class selection ── -->
                <t t-else="">
                    <div class="k-checkin-modal__prompt">Please select your class:</div>

                    <t t-if="props.loading">
                        <div class="k-checkin-modal__loading">
                            <div class="k-spinner k-spinner--lg"/>
                        </div>
                    </t>
                    <t t-elif="!props.sessions.length">
                        <div class="k-checkin-modal__empty">
                            <div style="font-size:2.5rem;margin-bottom:8px;">📅</div>
                            <div>No classes scheduled for today.</div>
                        </div>
                    </t>
                    <t t-else="">
                        <div class="k-checkin-modal__sessions">
                            <t t-foreach="props.sessions" t-as="s" t-key="s.id">
                                <button class="k-checkin-session-btn" t-on-click="() => props.onSelect(s)">
                                    <div class="k-checkin-session-btn__name" t-esc="s.template_name || s.name"/>
                                    <t t-if="s.program_name">
                                        <div class="k-checkin-session-btn__program" t-esc="s.program_name"/>
                                    </t>
                                    <div class="k-checkin-session-btn__time">
                                        <t t-esc="formatTime(s.start)"/> – <t t-esc="formatTime(s.end)"/>
                                    </div>
                                    <t t-if="s.instructor">
                                        <div class="k-checkin-session-btn__instructor">👤 <t t-esc="s.instructor"/></div>
                                    </t>
                                    <div class="k-checkin-session-btn__cta">Check in</div>
                                </button>
                            </t>
                        </div>
                    </t>

                    <!-- Not me button -->
                    <div class="k-checkin-modal__notme-wrap">
                        <button class="k-btn k-checkin-modal__notme-btn" t-on-click="props.onClose">
                            That's not me
                        </button>
                    </div>
                </t>

            </div>
        </div>
    `;

    static props = ["member", "sessions", "loading", "result", "checkedInSession", "onSelect", "onCheckout", "onClose"];
    onOverlayClick() { if (!this.props.result) this.props.onClose(); }
    memberAvatarUrl(member) {
        if (member.image_url) return member.image_url;
        if (member.is_trial && member.partner_id) return partnerAvatarUrl(member.partner_id);
        return avatarUrl(member.member_id);
    }
    formatTime(dt) { return formatTime(dt); }
    programName(member) {
        return member.program_name || member.trial_program || "";
    }
    stateLabel(member) {
        return member.membership_label || member.membership_state || "";
    }
    stateClass(member) {
        return (member.membership_state || "unknown").replace(/[^a-z0-9_-]/gi, "").toLowerCase();
    }
    onImgError(ev) {
        const img = ev.target;
        const ph = document.createElement("div");
        ph.className = "k-checkin-modal__avatar-placeholder";
        ph.textContent = initials(this.props.member.name);
        img.parentElement.replaceChild(ph, img);
    }
}

// ─── InstructorRosterTile ─────────────────────────────────────────────────────

class InstructorRosterTile extends Component {
    static template = xml`
        <div t-attf-class="k-roster-tile k-roster-tile--#{props.entry.attendance_state || 'pending'} #{state.pressing ? 'k-roster-tile--pressing' : ''} #{state.busy ? 'k-roster-tile--busy' : ''}"
             t-att-data-member-id="props.entry.member_id || props.entry.lead_id || ''"
             t-att-data-attendance-state="props.entry.attendance_state || 'pending'"
             t-att-data-onboarding-pct="props.entry.onboarding_pct || 0"
             t-att-data-open-task-count="props.entry.open_task_count || 0"
             t-att-data-membership-state="props.entry.membership_state || ''"
             t-att-aria-disabled="state.busy ? 'true' : 'false'"
             t-on-click="onTileTap"
             t-on-pointerdown="onPointerDown"
             t-on-pointerup="onPointerUp"
             t-on-pointerleave="onPointerUp"
             t-on-pointercancel="onPointerUp"
             t-on-contextmenu.prevent="">

            <!-- Warning badge: top-right — membership issue or known flags -->
            <t t-if="hasWarning()">
                <div class="k-roster-tile__warn" title="Account issues">⚠</div>
            </t>

            <!-- Trial badge: top-left area -->
            <t t-if="props.entry.is_trial">
                <div class="k-roster-tile__trial-badge">TRIAL</div>
            </t>

            <div class="k-roster-tile__photo-wrap">
                <img class="k-roster-tile__photo"
                    t-att-src="rosterAvatarUrl(props.entry)"
                    t-att-alt="props.entry.name"
                    t-on-error="onImgError"/>
            </div>

            <div class="k-roster-tile__name" t-esc="props.entry.name"/>
            <div class="k-roster-tile__attendance" t-esc="attendanceLabel()"/>

            <t t-if="props.entry.belt_rank || props.entry.program_name || props.entry.trial_program">
                <div class="k-roster-tile__meta">
                    <t t-if="props.entry.belt_rank">
                        <span class="k-roster-tile__belt" t-esc="props.entry.belt_rank"/>
                    </t>
                    <t t-if="props.entry.program_name || props.entry.trial_program">
                        <span class="k-roster-tile__program" t-esc="props.entry.program_name || props.entry.trial_program"/>
                    </t>
                </div>
            </t>

            <!-- Onboarding progress bar -->
            <t t-if="props.entry.onboarding_pct &gt; 0">
                <div class="k-roster-card__progress" t-att-title="'Onboarding ' + props.entry.onboarding_pct + '%'">
                    <div class="k-roster-card__progress-bar">
                        <div class="k-roster-card__progress-fill" t-attf-style="width: #{props.entry.onboarding_pct}%;"/>
                    </div>
                    <div class="k-roster-card__progress-label" t-esc="props.entry.onboarding_pct + '%'"/>
                </div>
            </t>

            <t t-if="workflowBadges().length">
                <div class="k-roster-tile__badges">
                    <t t-foreach="workflowBadges()" t-as="badge" t-key="badge.key">
                        <span t-attf-class="k-roster-status k-roster-status--#{badge.kind}" t-esc="badge.label"/>
                    </t>
                </div>
            </t>
        </div>
    `;

    static props = ["entry", "sessionId", "onMark", "onRemoveAttendance", "onManage"];

    setup() {
        this.state = owl.useState({ pressing: false, busy: false });
        this._lpTimer = null;
        this._lpFired = false;
    }

    rosterAvatarUrl(entry) {
        if (entry.image_url) return entry.image_url;
        if (entry.is_trial && entry.partner_id) return partnerAvatarUrl(entry.partner_id);
        return avatarUrl(entry.member_id);
    }

    hasWarning() {
        if (this.props.entry.is_trial) return false;
        if (this.props.entry.issues && this.props.entry.issues.length) return true;
        const state = this.props.entry.membership_state;
        return state && state !== "active" && state !== "trial";
    }

    attendanceLabel() {
        const state = this.props.entry.attendance_state || "pending";
        const labels = {
            present: "Present",
            late: "Late",
            absent: "Absent",
            checked_out: "Checked out",
            pending: "Pending",
        };
        return labels[state] || state;
    }

    workflowBadges() {
        const wf = this.props.entry.workflow_status || {};
        const badges = [];
        const onboarding = wf.onboarding || {};
        if (onboarding.available && !onboarding.complete) {
            badges.push({ key: "onboarding", kind: "warn", label: `OB ${onboarding.progress_pct || 0}%` });
        }
        const waiver = wf.waiver || {};
        if (waiver.available && !waiver.signed) {
            badges.push({ key: "waiver", kind: "warn", label: "Waiver" });
        }
        const subscription = wf.subscription || {};
        if (subscription.alerts && subscription.alerts.length) {
            const code = subscription.alerts[0].code || "plan";
            badges.push({ key: "subscription", kind: "danger", label: code === "credits_exhausted" ? "Credits" : "Plan" });
        }
        const grading = wf.grading || {};
        if (grading.ready) {
            badges.push({ key: "grading", kind: "ok", label: "Ready" });
        }
        const tasks = wf.tasks || {};
        if (tasks.open_count) {
            badges.push({ key: "tasks", kind: "info", label: `Tasks ${tasks.open_count}` });
        }
        return badges.slice(0, 3);
    }

    isToggleableAttendance() {
        const entry = this.props.entry || {};
        return !!(entry.member_id && !entry.is_trial);
    }

    attendanceToggleStatus() {
        const state = (this.props.entry && this.props.entry.attendance_state) || "pending";
        if (state === "present" || state === "late") return "pending";
        if (state === "pending") return "present";
        return null;
    }

    async onTileTap(ev) {
        // If long-press just fired, absorb the synthetic click
        if (this._lpFired) { this._lpFired = false; return; }
        if (this.state.busy || !this.isToggleableAttendance()) return;

        const nextStatus = this.attendanceToggleStatus();
        if (!nextStatus) return;

        const memberId = this.props.entry.member_id;
        const handler = nextStatus === "pending" ? this.props.onRemoveAttendance : this.props.onMark;
        if (typeof handler !== "function") return;

        this.state.busy = true;
        try {
            if (nextStatus === "pending") {
                await handler(memberId);
            } else {
                await handler(memberId, nextStatus);
            }
        } finally {
            this.state.busy = false;
        }
    }

    onPointerDown(ev) {
        if (this.state.busy || !this.isToggleableAttendance()) return;
        this.state.pressing = true;
        this._lpTimer = setTimeout(() => {
            this._lpFired = true;
            this.state.pressing = false;
            this._lpTimer = null;
            this.props.onManage(this.props.entry.member_id);
        }, 600);
    }

    onPointerUp(ev) {
        this.state.pressing = false;
        if (this._lpTimer) {
            clearTimeout(this._lpTimer);
            this._lpTimer = null;
        }
    }

    onImgError(ev) {
        const img = ev.target;
        const ph = document.createElement("div");
        ph.className = "k-roster-tile__initials";
        ph.textContent = initials(this.props.entry.name);
        img.parentElement.replaceChild(ph, img);
    }
}

// ─── InstructorSessionCard ────────────────────────────────────────────────────

class InstructorSessionCard extends Component {
    static template = xml`
        <div t-attf-class="k-session-card #{props.session.state === 'done' ? 'k-session-card--done' : ''} #{timeStateClass()}">
            <div class="k-session-card__header">
                <div class="k-session-card__title">
                    <t t-esc="props.session.template_name"/>
                    <t t-if="props.session.state === 'done'">
                        <span class="k-session-card__done-badge">✓ Done</span>
                    </t>
                </div>
                <div class="k-session-card__meta">
                    <span class="k-session-card__time">
                        <t t-esc="formatTime(props.session.start)"/> – <t t-esc="formatTime(props.session.end)"/>
                    </span>
                    <t t-if="props.session.instructor">
                        <span class="k-session-card__instructor">👤 <t t-esc="props.session.instructor"/></span>
                    </t>
                    <span class="k-session-card__count">
                        <t t-esc="props.session.seats_taken"/>
                        <t t-if="props.session.capacity"> / <t t-esc="props.session.capacity"/></t>
                        <t t-else=""> enrolled</t>
                    </span>
                </div>
            </div>

            <t t-if="props.loading">
                <div class="k-session-card__loading"><div class="k-spinner"/></div>
            </t>
            <t t-elif="!props.roster.length">
                <div class="k-session-card__empty">No students enrolled yet</div>
            </t>
            <t t-else="">
                <div class="k-roster-grid">
                    <t t-foreach="props.roster" t-as="entry" t-key="entry.is_trial ? 'lead_' + entry.lead_id : entry.member_id">
                        <InstructorRosterTile
                            entry="entry"
                            sessionId="props.session.id"
                            onMark="(memberId, status) => props.onMark(memberId, props.session.id, status)"
                            onRemoveAttendance="(memberId) => props.onRemoveAttendance(memberId, props.session.id)"
                            onManage="(memberId) => props.onManage(memberId, props.session.id)"/>
                    </t>
                </div>
            </t>

            <div class="k-session-card__footer">
                <t t-if="props.session.state === 'done'">
                    <button class="k-btn k-session-action k-session-action--reopen"
                        t-on-click="() => props.onReopen(props.session.id)">
                        ↺ Reopen
                    </button>
                    <button class="k-btn k-session-action k-session-action--delete"
                        t-on-click="() => props.onDelete(props.session.id)">
                        🗑 Delete
                    </button>
                </t>
                <t t-else="">
                    <button class="k-btn k-session-action k-session-action--assign"
                        t-on-click="() => props.onAssignRoster(props.session)">
                        👥 Assign Roster
                    </button>
                    <button class="k-btn k-session-action k-session-action--edit"
                        t-on-click="() => props.onEdit(props.session)">
                        ✎ Edit
                    </button>
                    <button t-attf-class="k-btn k-session-action #{hasPending() ? 'k-session-action--done-blocked' : 'k-session-action--done'}"
                        t-att-title="hasPending() ? 'All members must have attendance recorded before marking done' : 'Close this session'"
                        t-on-click="() => props.onClose(props.session.id)">
                        ✓ Mark Done
                        <t t-if="hasPending()">
                            <span class="k-session-action--done-pending-badge" title="Pending attendance remaining">
                                <t t-esc="pendingCount()"/>
                            </span>
                        </t>
                    </button>
                    <button class="k-btn k-session-action k-session-action--delete"
                        t-on-click="() => props.onDelete(props.session.id)">
                        🗑 Delete
                    </button>
                </t>
            </div>
        </div>
    `;

    static props = ["session", "roster", "loading", "onMark", "onProfile", "onRemoveAttendance", "onManage", "onClose", "onReopen", "onDelete", "onEdit", "onAssignRoster"];
    static components = { InstructorRosterTile };
    formatTime(dt) { return formatTime(dt); }

    timeStateClass() {
        const ts = this.props.session.time_state;
        if (ts === "active") return "k-session--active";
        if (ts === "upcoming_soon") return "k-session--soon";
        if (ts === "done") return "k-session--done";
        return "k-session--upcoming";
    }

    hasPending() {
        if (!this.props.roster.length) return false;
        return this.props.roster.some(e => !e.attendance_state || e.attendance_state === "pending");
    }

    pendingCount() {
        return this.props.roster.filter(e => !e.attendance_state || e.attendance_state === "pending").length;
    }
}

// ─── InstructorThreePanelLayout ───────────────────────────────────────────────

class InstructorThreePanelLayout extends Component {
    static template = xml`
        <div class="k-instructor-layout"
            t-att-data-selected-session-id="selectedSession() ? selectedSession().id : ''">

            <!-- Left panel: session context and controls -->
            <aside class="k-instructor-left">
                <div class="k-instructor-panel-heading">Session Context</div>

                <t t-if="selectedSession()">
                    <div t-attf-class="k-session-card k-session-card--context #{sessionStateClass(selectedSession())}">
                        <div class="k-session-card__eyebrow" t-esc="sessionStateLabel(selectedSession())"/>
                        <div class="k-session-card__name" t-esc="sessionName(selectedSession())"/>
                        <div class="k-session-card__time">
                            <t t-esc="formatTime(selectedSession().start)"/> - <t t-esc="formatTime(selectedSession().end)"/>
                        </div>
                        <t t-if="sessionSubline(selectedSession())">
                            <div class="k-session-card__subline" t-esc="sessionSubline(selectedSession())"/>
                        </t>
                        <div class="k-session-card__countdown" t-esc="countdownText(selectedSession())"/>

                        <div class="k-session-card__summary">
                            <div class="k-summary-stat k-summary-stat--present">
                                <span class="k-summary-stat__count" t-esc="attendanceSummary().present"/>
                                <span class="k-summary-stat__label">Present</span>
                            </div>
                            <div class="k-summary-stat k-summary-stat--late">
                                <span class="k-summary-stat__count" t-esc="attendanceSummary().late"/>
                                <span class="k-summary-stat__label">Late</span>
                            </div>
                            <div class="k-summary-stat k-summary-stat--absent">
                                <span class="k-summary-stat__count" t-esc="attendanceSummary().absent"/>
                                <span class="k-summary-stat__label">Absent</span>
                            </div>
                            <div class="k-summary-stat k-summary-stat--pending">
                                <span class="k-summary-stat__count" t-esc="attendanceSummary().pending"/>
                                <span class="k-summary-stat__label">Pending</span>
                            </div>
                        </div>

                        <div class="k-session-card__footer k-session-card__footer--context">
                            <t t-if="selectedSession().state === 'done'">
                                <button class="k-btn k-session-action k-session-action--reopen"
                                    t-on-click="() => props.onReopen(selectedSession().id)">Reopen</button>
                                <button class="k-btn k-session-action k-session-action--delete"
                                    t-on-click="() => props.onDelete(selectedSession().id)">Delete</button>
                            </t>
                            <t t-else="">
                                <button class="k-btn k-session-action k-session-action--assign"
                                    t-on-click="() => props.onAssignRoster(selectedSession())">Assign Roster</button>
                                <button class="k-btn k-session-action k-session-action--edit"
                                    t-on-click="() => props.onEdit(selectedSession())">Edit</button>
                                <button t-attf-class="k-btn k-session-action #{attendanceSummary().pending ? 'k-session-action--done-blocked' : 'k-session-action--done'}"
                                    t-on-click="() => props.onClose(selectedSession().id)">
                                    Mark Done
                                    <t t-if="attendanceSummary().pending">
                                        <span class="k-session-action--done-pending-badge" t-esc="attendanceSummary().pending"/>
                                    </t>
                                </button>
                            </t>
                        </div>
                    </div>
                </t>
                <t t-else="">
                    <div class="k-session-card k-session-card--context k-session-card--standby">
                        <div class="k-session-card__eyebrow">Standby</div>
                        <div class="k-session-card__name">No Selected Session</div>
                        <div class="k-session-card__subline" t-esc="sessionContextText()"/>
                    </div>
                </t>

                <div class="k-instructor-session-list">
                    <t t-foreach="sessions()" t-as="s" t-key="s.id">
                        <button
                            t-attf-class="k-instructor-session-option #{isSessionSelected(s) ? 'k-instructor-session-option--selected' : ''}"
                            t-on-click="() => props.onSessionChange(s.id)">
                            <span class="k-instructor-session-option__state" t-esc="sessionStateLabel(s)"/>
                            <span class="k-instructor-session-option__name" t-esc="sessionName(s)"/>
                            <span class="k-instructor-session-option__time">
                                <t t-esc="formatTime(s.start)"/>
                            </span>
                        </button>
                    </t>
                </div>
                <button class="k-btn k-btn--secondary k-instructor-create-session"
                    t-on-click="props.onCreateSession">
                    Create Session
                </button>
            </aside>

            <!-- Center panel: actionable roster -->
            <main class="k-instructor-main">
                <div class="k-instructor-main__header">
                    <div>
                        <div class="k-instructor-panel-heading">Roster</div>
                        <t t-if="selectedSession()">
                            <div class="k-instructor-main__subtitle" t-esc="sessionName(selectedSession())"/>
                        </t>
                    </div>
                    <div class="k-instructor-main__count">
                        <t t-esc="attendanceSummary().total"/> students
                    </div>
                </div>

                <t t-if="isSelectedRosterLoading()">
                    <div class="k-session-card__loading"><div class="k-spinner"/></div>
                </t>
                <t t-elif="!selectedSession()">
                    <div class="k-session-card__empty">Select a session to view the roster.</div>
                </t>
                <t t-elif="!selectedRoster().length">
                    <div class="k-session-card__empty">No students enrolled yet</div>
                </t>
                <t t-else="">
                    <div class="k-roster-grid k-roster-grid--instructor">
                        <t t-foreach="selectedRoster()" t-as="entry" t-key="entry.is_trial ? 'lead_' + entry.lead_id : entry.member_id">
                            <InstructorRosterTile
                                entry="entry"
                                sessionId="selectedSession().id"
                                onMark="(memberId, status) => props.onMark(memberId, selectedSession().id, status)"
                                onRemoveAttendance="(memberId) => props.onRemoveAttendance(memberId, selectedSession().id)"
                                onManage="(memberId) => props.onManage(memberId, selectedSession().id)"/>
                        </t>
                    </div>
                </t>
            </main>

            <!-- Right panel: operational alerts -->
            <aside class="k-instructor-right">
                <div class="k-instructor-panel-heading">Alerts</div>
                <t t-set="groups" t-value="alertGroups()"/>

                <t t-if="groups.onboarding.length">
                    <div class="k-alert-section">
                        <div class="k-alert-section__title">Onboarding</div>
                        <t t-foreach="groups.onboarding" t-as="alert" t-key="alert.key">
                            <div class="k-alert-item k-alert-item--onboarding">
                                <div class="k-alert-item__name" t-esc="alert.name"/>
                                <div class="k-alert-item__detail" t-esc="alert.detail"/>
                            </div>
                        </t>
                    </div>
                </t>

                <t t-if="groups.membership.length">
                    <div class="k-alert-section">
                        <div class="k-alert-section__title">Membership Issues</div>
                        <t t-foreach="groups.membership" t-as="alert" t-key="alert.key">
                            <div class="k-alert-item k-alert-item--membership">
                                <div class="k-alert-item__name" t-esc="alert.name"/>
                                <div class="k-alert-item__detail" t-esc="alert.detail"/>
                            </div>
                        </t>
                    </div>
                </t>

                <t t-if="groups.tasks.length">
                    <div class="k-alert-section">
                        <div class="k-alert-section__title">Instructor Tasks</div>
                        <t t-foreach="groups.tasks" t-as="alert" t-key="alert.key">
                            <div class="k-alert-item k-alert-item--task">
                                <div class="k-alert-item__name" t-esc="alert.name"/>
                                <div class="k-alert-item__detail" t-esc="alert.detail"/>
                            </div>
                        </t>
                    </div>
                </t>

                <t t-if="!groups.onboarding.length and !groups.membership.length and !groups.tasks.length">
                    <div class="k-alert-section k-alert-section--empty">
                        <div class="k-alert-section__title">Clear</div>
                        <div class="k-alert-item__detail">No roster alerts for this session.</div>
                    </div>
                </t>
            </aside>
        </div>
    `;

    static props = [
        "sessions",
        "sessionId",
        "sessionContext",
        "rosters",
        "loadingRosters",
        "onSessionChange",
        "onMark",
        "onRemoveAttendance",
        "onManage",
        "onClose",
        "onReopen",
        "onDelete",
        "onEdit",
        "onAssignRoster",
        "onCreateSession",
    ];
    static components = { InstructorRosterTile };

    setup() {
        this.state = useState({ now: Date.now() });
        onMounted(() => {
            this._clock = setInterval(() => {
                this.state.now = Date.now();
            }, 1000);
        });
        onWillUnmount(() => clearInterval(this._clock));
    }

    sessions() {
        return this.props.sessions || [];
    }

    selectedSession() {
        const sessions = this.sessions();
        const selectedId = this.props.sessionId;
        if (selectedId) {
            return sessions.find(session => session.id === selectedId) || null;
        }

        const ctx = this.props.sessionContext || {};
        if (ctx.selected_session_id) {
            const fromContext = sessions.find(session => session.id === ctx.selected_session_id);
            if (fromContext) return fromContext;
            return null;
        }
        if (ctx.mode === "standby") {
            return null;
        }

        return sessions.find(session => session.time_state === "active")
            || sessions.find(session => session.time_state === "upcoming_soon")
            || null;
    }

    selectedRoster() {
        const session = this.selectedSession();
        if (!session) return [];
        return (this.props.rosters || {})[session.id] || [];
    }

    isSessionSelected(session) {
        const selected = this.selectedSession();
        return !!(selected && session && selected.id === session.id);
    }

    isSelectedRosterLoading() {
        const session = this.selectedSession();
        if (!session) return false;
        return !!((this.props.loadingRosters || {})[session.id]);
    }

    sessionName(session) {
        return (session && (session.template_name || session.name)) || "Class";
    }

    sessionSubline(session) {
        if (!session) return "";
        const parts = [];
        if (session.program_name) parts.push(session.program_name);
        if (session.instructor) parts.push(session.instructor);
        return parts.join(" / ");
    }

    sessionStateLabel(session) {
        const state = session && session.time_state;
        if (session && session.state === "done") return "Done";
        if (state === "active") return "Active now";
        if (state === "upcoming_soon") return "Next up";
        if (state === "done") return "Ended";
        return "Upcoming";
    }

    sessionStateClass(session) {
        const state = session && session.time_state;
        if (session && session.state === "done") return "k-session--done";
        if (state === "active") return "k-session--active";
        if (state === "upcoming_soon") return "k-session--soon";
        if (state === "done") return "k-session--done";
        return "k-session--upcoming";
    }

    sessionContextText() {
        const ctx = this.props.sessionContext || {};
        return ctx.reason || "No active class or class starting soon.";
    }

    countdownText(session) {
        if (!session) return "--";
        if (session.state === "done" || session.time_state === "done") return "Complete";
        const target = session.time_state === "active" ? session.end : session.start;
        if (!target) return "--";
        const targetMs = Date.parse(target.replace(" ", "T") + "Z");
        const diffMs = targetMs - this.state.now;
        if (diffMs <= 0) return session.time_state === "active" ? "Ending now" : "Starting now";
        const prefix = session.time_state === "active" ? "Ends in " : "Starts in ";
        return prefix + this.durationText(diffMs);
    }

    durationText(diffMs) {
        const totalSeconds = Math.max(0, Math.floor(diffMs / 1000));
        const hours = Math.floor(totalSeconds / 3600);
        const minutes = Math.floor((totalSeconds % 3600) / 60);
        const seconds = totalSeconds % 60;
        if (hours > 0) return `${hours}h ${String(minutes).padStart(2, "0")}m`;
        return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
    }

    attendanceSummary() {
        const summary = { present: 0, late: 0, absent: 0, checkedOut: 0, pending: 0, total: 0 };
        for (const entry of this.selectedRoster()) {
            summary.total += 1;
            const state = entry.attendance_state || "pending";
            if (state === "present") summary.present += 1;
            else if (state === "late") summary.late += 1;
            else if (state === "absent") summary.absent += 1;
            else if (state === "checked_out") summary.checkedOut += 1;
            else summary.pending += 1;
        }
        return summary;
    }

    alertGroups() {
        const groups = { onboarding: [], membership: [], tasks: [] };
        const onboardingCodes = new Set(["onboarding_incomplete", "waiver_unsigned"]);

        for (const entry of this.selectedRoster()) {
            const wf = entry.workflow_status || {};
            const onboarding = wf.onboarding || {};
            if (onboarding.available && !onboarding.complete) {
                groups.onboarding.push({
                    key: `onboarding-${entry.member_id || entry.lead_id}`,
                    name: entry.name,
                    detail: `${onboarding.progress_pct || entry.onboarding_pct || 0}% complete`,
                });
            }

            const waiver = wf.waiver || {};
            if (waiver.available && !waiver.signed) {
                groups.onboarding.push({
                    key: `waiver-${entry.member_id || entry.lead_id}`,
                    name: entry.name,
                    detail: "Waiver unsigned",
                });
            }

            const subscriptionAlerts = ((wf.subscription || {}).alerts || []);
            const issueAlerts = (entry.issues || []).filter(issue => {
                const code = issue.code || "";
                return code !== "instructor_tasks" && !onboardingCodes.has(code);
            });
            for (const alert of [...subscriptionAlerts, ...issueAlerts]) {
                groups.membership.push({
                    key: `membership-${entry.member_id || entry.lead_id}-${alert.code || alert.label}`,
                    name: entry.name,
                    detail: alert.label || alert.code || "Membership issue",
                });
            }

            const taskCount = ((wf.tasks || {}).open_count || entry.open_task_count || 0);
            if (taskCount) {
                groups.tasks.push({
                    key: `tasks-${entry.member_id || entry.lead_id}`,
                    name: entry.name,
                    detail: `${taskCount} open task${taskCount === 1 ? "" : "s"}`,
                });
            }
        }

        return groups;
    }

    formatTime(dt) {
        return formatTime(dt);
    }
}

// ─── AttendanceRemoveConfirm ──────────────────────────────────────────────────

class AttendanceRemoveConfirm extends Component {
    static template = xml`
        <div class="k-modal-overlay" t-on-click.self="props.onCancel">
            <div class="k-modal k-modal--sm">
                <div class="k-modal__body" style="text-align:center;padding:32px 24px;">
                    <div style="font-size:40px;margin-bottom:10px;">🔄</div>
                    <div style="font-weight:700;font-size:17px;margin-bottom:6px;color:var(--k-text);">
                        Remove Attendance?
                    </div>
                    <div style="color:var(--k-text-2);font-size:14px;margin-bottom:24px;">
                        <strong t-esc="props.memberName"/> will be set back to Pending.
                    </div>
                    <div style="display:flex;gap:12px;justify-content:center;">
                        <button class="k-btn k-btn--secondary" t-on-click="props.onCancel">Cancel</button>
                        <button class="k-btn k-btn--danger" t-on-click="props.onConfirm">Remove</button>
                    </div>
                </div>
            </div>
        </div>
    `;
    static props = ["memberName", "onCancel", "onConfirm"];
}

// ─── DeleteSessionConfirm ───────────────────────────────────────────────────────

class DeleteSessionConfirm extends Component {
    static template = xml`
        <div class="k-modal-overlay" t-on-click.self="props.onCancel">
            <div class="k-modal k-modal--sm">
                <div class="k-modal__body" style="text-align:center;padding:32px 24px;">
                    <div style="font-size:40px;margin-bottom:10px;">🗑️</div>
                    <div style="font-weight:700;font-size:17px;margin-bottom:6px;color:var(--k-text);">
                        Delete Session?
                    </div>
                    <div style="color:var(--k-text-2);font-size:14px;margin-bottom:24px;">
                        This will cancel all enrollments and cannot be undone.
                    </div>
                    <div style="display:flex;gap:12px;justify-content:center;">
                        <button class="k-btn k-btn--secondary" t-on-click="props.onCancel">Cancel</button>
                        <button class="k-btn k-btn--danger" t-on-click="props.onConfirm">Delete</button>
                    </div>
                </div>
            </div>
        </div>
    `;
    static props = ["onCancel", "onConfirm"];
}

// ─── SessionEditModal ─────────────────────────────────────────────────────────

class SessionEditModal extends Component {
    static template = xml`
        <div class="k-modal-backdrop" t-on-click.self="props.onClose">
            <div class="k-modal k-modal--edit-session">
                <div class="k-modal__header">
                    <span class="k-modal__title">Edit Session</span>
                    <button class="k-modal__close" t-on-click="props.onClose">✕</button>
                </div>
                <div class="k-modal__body">
                    <div class="k-field">
                        <label class="k-field__label">Session</label>
                        <div class="k-field__value" t-esc="props.session.template_name"/>
                    </div>
                    <div class="k-field">
                        <label class="k-field__label">Time</label>
                        <div class="k-field__value">
                            <t t-esc="formatTime(props.session.start)"/> – <t t-esc="formatTime(props.session.end)"/>
                        </div>
                    </div>
                    <div class="k-field">
                        <label class="k-field__label">Capacity</label>
                        <input class="k-field__input"
                            type="number"
                            min="0"
                            t-att-value="state.capacity"
                            t-on-input="onCapacityInput"
                            placeholder="Unlimited"/>
                    </div>
                    <t t-if="state.error">
                        <div class="k-field-error" t-esc="state.error"/>
                    </t>
                </div>
                <div class="k-modal__footer">
                    <button class="k-btn k-btn--secondary" t-on-click="props.onClose">Cancel</button>
                    <button class="k-btn k-btn--primary" t-on-click="save" t-att-disabled="state.saving or undefined">
                        <t t-if="state.saving">Saving…</t>
                        <t t-else="">Save</t>
                    </button>
                </div>
            </div>
        </div>
    `;

    static props = ["session", "onClose", "onSaved"];

    setup() {
        this.state = useState({
            capacity: this.props.session.capacity || "",
            saving: false,
            error: "",
        });
    }

    formatTime(dt) { return formatTime(dt); }
    onCapacityInput(ev) { this.state.capacity = ev.target.value; this.state.error = ""; }

    async save() {
        this.state.saving = true;
        this.state.error = "";
        try {
            const cap = this.state.capacity === "" ? null : parseInt(this.state.capacity, 10);
            const result = await jsonPost("/kiosk/instructor/session/update", {
                session_id: this.props.session.id,
                capacity: cap,
            });
            if (result.success) {
                this.props.onSaved();
            } else {
                this.state.error = result.error || "Failed to save.";
            }
        } catch {
            this.state.error = "Network error.";
        } finally {
            this.state.saving = false;
        }
    }
}

// ─── CreateSessionModal ───────────────────────────────────────────────────────

class CreateSessionModal extends Component {
    static template = xml`
        <div class="k-modal-backdrop" t-on-click.self="props.onClose">
            <div class="k-modal k-modal--edit-session">
                <div class="k-modal__header">
                    <span class="k-modal__title">➕ Create Session</span>
                    <button class="k-modal__close" t-on-click="props.onClose">✕</button>
                </div>
                <div class="k-modal__body">
                    <t t-if="state.loadingTemplates">
                        <div style="text-align:center;padding:24px;"><div class="k-spinner"/></div>
                    </t>
                    <t t-elif="state.loadError">
                        <div class="k-field-error" t-esc="state.loadError"/>
                    </t>
                    <t t-else="">
                        <div class="k-field">
                            <label class="k-field__label">Course</label>
                            <select class="k-field__input" t-on-change="onTemplateChange">
                                <option value="">— Select a template —</option>
                                <t t-foreach="state.templates" t-as="tmpl" t-key="tmpl.id">
                                    <option t-att-value="tmpl.id"
                                        t-att-selected="state.selectedTemplateId === tmpl.id or undefined">
                                        <t t-esc="tmpl.name"/>
                                        <t t-if="tmpl.program_name"> · <t t-esc="tmpl.program_name"/></t>
                                    </option>
                                </t>
                            </select>
                        </div>
                        <div class="k-field">
                            <label class="k-field__label">Start Time</label>
                            <input class="k-field__input"
                                type="time"
                                t-att-value="state.startTime"
                                t-on-input="onStartTimeInput"/>
                        </div>
                        <div class="k-field">
                            <label class="k-field__label">Capacity</label>
                            <input class="k-field__input"
                                type="number"
                                min="0"
                                t-att-value="state.capacity"
                                t-on-input="onCapacityInput"
                                placeholder="Unlimited"/>
                        </div>
                        <t t-if="state.error">
                            <div class="k-field-error" t-esc="state.error"/>
                        </t>
                    </t>
                </div>
                <div class="k-modal__footer">
                    <button class="k-btn k-btn--secondary" t-on-click="props.onClose">Cancel</button>
                    <button class="k-btn k-btn--primary"
                        t-on-click="create"
                        t-att-disabled="state.saving or state.loadingTemplates or !state.selectedTemplateId or undefined">
                        <t t-if="state.saving">Creating…</t>
                        <t t-else="">Create Session</t>
                    </button>
                </div>
            </div>
        </div>
    `;

    static props = ["date", "onClose", "onCreated"];

    setup() {
        this.state = useState({
            templates: [],
            loadingTemplates: true,
            loadError: "",
            selectedTemplateId: null,
            startTime: this._defaultTime(),
            capacity: "",
            saving: false,
            error: "",
        });
        onMounted(() => this._loadTemplates());
    }

    _defaultTime() {
        const now = new Date();
        return String(now.getHours()).padStart(2, "0") + ":" + String(now.getMinutes()).padStart(2, "0");
    }

    async _loadTemplates() {
        try {
            const templates = await jsonPost("/kiosk/instructor/templates", {});
            this.state.templates = templates || [];
            this.state.loadingTemplates = false;
        } catch (e) {
            this.state.loadingTemplates = false;
            this.state.loadError = "Could not load templates: " + (e.message || "network error");
        }
    }

    onTemplateChange(ev) {
        const id = parseInt(ev.target.value, 10) || null;
        this.state.selectedTemplateId = id;
        this.state.error = "";
        if (id) {
            const tmpl = this.state.templates.find(t => t.id === id);
            if (tmpl) {
                this.state.startTime = tmpl.default_start;
                this.state.capacity = tmpl.capacity || "";
            }
        }
    }

    onStartTimeInput(ev) { this.state.startTime = ev.target.value; this.state.error = ""; }
    onCapacityInput(ev) { this.state.capacity = ev.target.value; this.state.error = ""; }

    async create() {
        if (!this.state.selectedTemplateId) {
            this.state.error = "Please select a template.";
            return;
        }
        if (!this.state.startTime) {
            this.state.error = "Please enter a start time.";
            return;
        }
        this.state.saving = true;
        this.state.error = "";
        try {
            const cap = this.state.capacity === "" ? null : parseInt(this.state.capacity, 10);
            const result = await jsonPost("/kiosk/instructor/session/create", {
                template_id: this.state.selectedTemplateId,
                start_time: this.state.startTime,
                capacity: cap,
                date: this.props.date || null,
            });
            if (result.success) {
                this.props.onCreated(result.session);
            } else {
                this.state.error = result.error || "Failed to create session.";
            }
        } catch (e) {
            this.state.error = "Network error: " + (e.message || "unknown");
        } finally {
            this.state.saving = false;
        }
    }
}

// ─── AssignRosterModal ────────────────────────────────────────────────────────

class AssignRosterModal extends Component {
    static template = xml`
        <div class="k-modal-backdrop" t-on-click.self="props.onClose">
            <div class="k-modal k-modal--assign-roster">
                <div class="k-modal__header">
                    <span class="k-modal__title">
                        <t t-if="state.step === 1">👥 Select Members</t>
                        <t t-else="">📋 Confirm &amp; Add</t>
                    </span>
                    <button class="k-modal__close" t-on-click="props.onClose">✕</button>
                </div>

                <!-- ══ Step 1: member search ══ -->
                <t t-if="state.step === 1">
                    <div class="k-modal__body">
                        <div class="k-am-search">
                            <input class="k-field__input"
                                type="text"
                                placeholder="Search member name…"
                                autofocus="true"
                                t-model="state.query"
                                t-on-input="onInput"
                                autocomplete="off"/>
                        </div>
                        <t t-if="state.chips.length">
                            <div class="k-chips-wrap">
                                <t t-foreach="state.chips" t-as="chip" t-key="chip.member_id">
                                    <div class="k-chip">
                                        <span t-esc="chip.name"/>
                                        <button class="k-chip__remove"
                                            t-on-click="() => this.removeChip(chip.member_id)">✕</button>
                                    </div>
                                </t>
                            </div>
                        </t>
                        <t t-if="state.loading">
                            <div class="k-am-loading"><div class="k-spinner"/></div>
                        </t>
                        <t t-elif="state.results.length">
                            <div class="k-am-results">
                                <t t-foreach="state.results" t-as="m" t-key="m.member_id">
                                    <div t-attf-class="k-am-result #{isSelected(m.member_id) ? 'k-am-result--selected' : ''}"
                                        t-on-click="() => this.toggleMember(m)">
                                        <img class="k-am-result__avatar"
                                            t-att-src="m.image_url"
                                            t-att-alt="m.name"
                                            t-on-error="(ev) => ev.target.style.display='none'"/>
                                        <div class="k-am-result__info">
                                            <span class="k-am-result__name" t-esc="m.name"/>
                                            <t t-if="m.belt_rank">
                                                <span class="k-am-result__belt" t-esc="m.belt_rank"/>
                                            </t>
                                        </div>
                                        <div class="k-am-result__check">✓</div>
                                    </div>
                                </t>
                            </div>
                        </t>
                        <t t-elif="state.query.length >= 2 and !state.loading">
                            <div class="k-am-empty">No members found</div>
                        </t>
                    </div>
                    <div class="k-modal__footer">
                        <button class="k-btn k-btn--secondary" t-on-click="props.onClose">Cancel</button>
                        <button class="k-btn k-btn--primary"
                            t-on-click="goToStep2"
                            t-att-disabled="!state.chips.length or undefined">
                            Next →
                        </button>
                    </div>
                </t>

                <!-- ══ Step 2: session + options + submit ══ -->
                <t t-else="">
                    <div class="k-modal__body">
                        <div class="k-field">
                            <label class="k-field__label">Session</label>
                            <select class="k-field__input" t-on-change="onSessionChange">
                                <t t-foreach="props.sessions" t-as="s" t-key="s.id">
                                    <option t-att-value="s.id"
                                        t-att-selected="state.sessionId === s.id or undefined">
                                        <t t-esc="s.template_name"/> (<t t-esc="formatTime(s.start)"/>)
                                    </option>
                                </t>
                            </select>
                        </div>

                        <div class="k-field">
                            <label class="k-field__label">Enrollment Type</label>
                            <div class="k-enroll-pills">
                                <button t-attf-class="k-enroll-pill #{state.enrollType === 'single' ? 'k-enroll-pill--active' : ''}"
                                    t-on-click="() => this.state.enrollType = 'single'">
                                    Single Day
                                </button>
                                <button t-attf-class="k-enroll-pill #{state.enrollType === 'multiday' ? 'k-enroll-pill--active' : ''}"
                                    t-on-click="() => this.state.enrollType = 'multiday'">
                                    Multiday Range
                                </button>
                                <button t-attf-class="k-enroll-pill #{state.enrollType === 'permanent' ? 'k-enroll-pill--active' : ''}"
                                    t-on-click="() => this.state.enrollType = 'permanent'">
                                    Never Remove
                                </button>
                            </div>
                        </div>

                        <t t-if="state.enrollType === 'multiday'">
                            <div class="k-field">
                                <label class="k-field__label">Date Range</label>
                                <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
                                    <input type="date" class="k-field__input"
                                        style="flex:1;min-width:130px"
                                        t-att-value="state.dateFrom"
                                        t-on-change="(ev) => this.state.dateFrom = ev.target.value"/>
                                    <span style="color:var(--k-text-muted,#aaa);font-size:.85rem">to</span>
                                    <input type="date" class="k-field__input"
                                        style="flex:1;min-width:130px"
                                        t-att-value="state.dateTo"
                                        t-on-change="(ev) => this.state.dateTo = ev.target.value"/>
                                </div>
                            </div>
                        </t>

                        <t t-if="state.enrollType === 'multiday' or state.enrollType === 'permanent'">
                            <div class="k-field">
                                <label class="k-field__label">Days of Week <span style="font-weight:400;font-size:.8rem;color:var(--k-text-muted,#aaa)">(leave all off = every day the class runs)</span></label>
                                <div class="k-enroll-pills" style="flex-wrap:wrap">
                                    <t t-foreach="[['mon','Mon'],['tue','Tue'],['wed','Wed'],['thu','Thu'],['fri','Fri'],['sat','Sat'],['sun','Sun']]" t-as="day" t-key="day[0]">
                                        <button t-attf-class="k-enroll-pill #{state.prefDays[day[0]] ? 'k-enroll-pill--active' : ''}"
                                            t-on-click="() => this.state.prefDays[day[0]] = !this.state.prefDays[day[0]]">
                                            <t t-esc="day[1]"/>
                                        </button>
                                    </t>
                                </div>
                            </div>
                        </t>

                        <div class="k-field">
                            <label class="k-check-label">
                                <input type="checkbox"
                                    t-att-checked="state.overrideCapacity or undefined"
                                    t-on-change="(ev) => this.state.overrideCapacity = ev.target.checked"/>
                                Override session capacity limit
                            </label>
                        </div>

                        <div class="k-field">
                            <label class="k-check-label">
                                <input type="checkbox"
                                    t-att-checked="state.overrideSettings or undefined"
                                    t-on-change="(ev) => this.state.overrideSettings = ev.target.checked"/>
                                Override roster settings
                            </label>
                        </div>

                        <div style="margin-bottom:14px;">
                            <div class="k-field__label" style="margin-bottom:8px;">
                                Adding <strong><t t-esc="state.chips.length"/> member(s)</strong>:
                            </div>
                            <div class="k-chips-wrap">
                                <t t-foreach="state.chips" t-as="chip" t-key="chip.member_id">
                                    <div class="k-chip"><span t-esc="chip.name"/></div>
                                </t>
                            </div>
                        </div>

                        <t t-if="state.error">
                            <div class="k-field-error" t-esc="state.error"/>
                        </t>
                    </div>
                    <div class="k-modal__footer">
                        <button class="k-btn k-btn--secondary"
                            t-on-click="() => this.state.step = 1">← Back</button>
                        <button class="k-btn k-btn--primary"
                            t-on-click="submit"
                            t-att-disabled="state.saving or undefined">
                            <t t-if="state.saving">Adding…</t>
                            <t t-else="">Add to Roster</t>
                        </button>
                    </div>
                </t>
            </div>
        </div>
    `;

    static props = ["session", "sessions", "onClose", "onAssigned"];

    setup() {
        this.state = useState({
            step: 1,
            query: "",
            results: [],
            loading: false,
            chips: [],
            sessionId: this.props.session
                ? this.props.session.id
                : (this.props.sessions[0] ? this.props.sessions[0].id : null),
            enrollType: "single",
            dateFrom: "",
            dateTo: "",
            prefDays: { mon: false, tue: false, wed: false, thu: false, fri: false, sat: false, sun: false },
            overrideCapacity: false,
            overrideSettings: false,
            saving: false,
            error: "",
        });
        this._timer = null;
    }

    formatTime(dt) { return formatTime(dt); }

    isSelected(memberId) {
        return this.state.chips.some(c => c.member_id === memberId);
    }

    toggleMember(member) {
        const idx = this.state.chips.findIndex(c => c.member_id === member.member_id);
        if (idx !== -1) {
            this.state.chips.splice(idx, 1);
        } else {
            this.state.chips.push({ member_id: member.member_id, name: member.name });
        }
    }

    removeChip(memberId) {
        const idx = this.state.chips.findIndex(c => c.member_id === memberId);
        if (idx !== -1) this.state.chips.splice(idx, 1);
    }

    onInput() {
        clearTimeout(this._timer);
        const q = this.state.query.trim();
        if (q.length < 2) { this.state.results = []; return; }
        this.state.loading = true;
        this._timer = setTimeout(async () => {
            try {
                const res = await jsonPost("/kiosk/search", { query: q });
                this.state.results = res || [];
            } catch {
                this.state.results = [];
            } finally {
                this.state.loading = false;
            }
        }, 300);
    }

    onSessionChange(ev) {
        const val = ev.target.value;
        this.state.sessionId = val ? parseInt(val, 10) : null;
    }

    goToStep2() {
        if (!this.state.chips.length) return;
        this.state.step = 2;
        this.state.error = "";
    }

    async submit() {
        if (!this.state.sessionId || !this.state.chips.length) return;
        if (this.state.enrollType === 'multiday') {
            if (!this.state.dateFrom || !this.state.dateTo) {
                this.state.error = "Please select both a From and To date for Multiday Range.";
                return;
            }
            if (this.state.dateFrom > this.state.dateTo) {
                this.state.error = "'From' date must be on or before the 'To' date.";
                return;
            }
        }
        this.state.saving = true;
        this.state.error = "";
        try {
            const memberIds = this.state.chips.map(c => c.member_id);
            const result = await jsonPost("/kiosk/instructor/roster/bulk_add", {
                session_id: this.state.sessionId,
                member_ids: memberIds,
                override_capacity: this.state.overrideCapacity,
                override_settings: this.state.overrideSettings,
                enroll_type: this.state.enrollType,
                date_from: this.state.enrollType === 'multiday' ? this.state.dateFrom : undefined,
                date_to: this.state.enrollType === 'multiday' ? this.state.dateTo : undefined,
                pref_mon: this.state.prefDays.mon,
                pref_tue: this.state.prefDays.tue,
                pref_wed: this.state.prefDays.wed,
                pref_thu: this.state.prefDays.thu,
                pref_fri: this.state.prefDays.fri,
                pref_sat: this.state.prefDays.sat,
                pref_sun: this.state.prefDays.sun,
            });
            if (result.success) {
                const added = result.added || [];
                const skipped = result.skipped || [];
                if (added.length === 0 && skipped.length > 0) {
                    // Nobody was added — keep modal open and show why each was skipped
                    this.state.error = skipped
                        .map(s => typeof s === 'object' ? s.reason : `Member could not be added`)
                        .join('\n');
                } else {
                    // At least some members added — close the modal
                    this.props.onAssigned(this.state.sessionId);
                }
            } else {
                this.state.error = result.error || "Could not add members.";
            }
        } catch {
            this.state.error = "Network error.";
        } finally {
            this.state.saving = false;
        }
    }
}

// ─── KioskSettingsModal ───────────────────────────────────────────────────────

class KioskSettingsModal extends Component {
    static template = xml`
        <div class="k-modal-backdrop" t-on-click.self="props.onClose">
            <div class="k-modal k-modal--settings">
                <div class="k-modal__header">
                    <span class="k-modal__title">⚙ Kiosk Settings</span>
                    <button class="k-modal__close" t-on-click="props.onClose">✕</button>
                </div>
                <div class="k-modal__body">
                    <div class="k-field">
                        <label class="k-field__label">Font Size</label>
                        <div class="k-settings-row">
                            <button t-attf-class="k-sz-btn #{props.fontSize === 'normal' ? 'k-sz-btn--active' : ''}"
                                t-on-click="() => props.onFontSize('normal')">Normal</button>
                            <button t-attf-class="k-sz-btn #{props.fontSize === 'large' ? 'k-sz-btn--active' : ''}"
                                t-on-click="() => props.onFontSize('large')">Large</button>
                            <button t-attf-class="k-sz-btn #{props.fontSize === 'xl' ? 'k-sz-btn--active' : ''}"
                                t-on-click="() => props.onFontSize('xl')">X-Large</button>
                        </div>
                    </div>

                    <div class="k-field">
                        <label class="k-field__label">Theme</label>
                        <div class="k-settings-row">
                            <button t-attf-class="k-sz-btn #{props.theme === 'light' ? 'k-sz-btn--active' : ''}"
                                t-on-click="() => props.onTheme('light')">☀ Light</button>
                            <button t-attf-class="k-sz-btn #{props.theme === 'dark' ? 'k-sz-btn--active' : ''}"
                                t-on-click="() => props.onTheme('dark')">🌙 Dark</button>
                        </div>
                    </div>

                    <div class="k-field">
                        <label class="k-field__label">Idle Timeout</label>
                        <div class="k-settings-row">
                            <button t-attf-class="k-sz-btn #{props.idleMinutes === 1 ? 'k-sz-btn--active' : ''}"
                                t-on-click="() => props.onIdleMinutes(1)">1 min</button>
                            <button t-attf-class="k-sz-btn #{props.idleMinutes === 3 ? 'k-sz-btn--active' : ''}"
                                t-on-click="() => props.onIdleMinutes(3)">3 min</button>
                            <button t-attf-class="k-sz-btn #{props.idleMinutes === 5 ? 'k-sz-btn--active' : ''}"
                                t-on-click="() => props.onIdleMinutes(5)">5 min</button>
                            <button t-attf-class="k-sz-btn #{props.idleMinutes === 10 ? 'k-sz-btn--active' : ''}"
                                t-on-click="() => props.onIdleMinutes(10)">10 min</button>
                        </div>
                    </div>

                    <div class="k-field">
                        <label class="k-field__label">Header Title</label>
                        <div class="k-settings-row">
                            <button t-attf-class="k-sz-btn #{props.showTitle ? 'k-sz-btn--active' : ''}"
                                t-on-click="() => props.onShowTitle(true)">Show</button>
                            <button t-attf-class="k-sz-btn #{!props.showTitle ? 'k-sz-btn--active' : ''}"
                                t-on-click="() => props.onShowTitle(false)">Hide</button>
                        </div>
                    </div>
                </div>
                <div class="k-modal__footer">
                    <button class="k-btn k-btn--primary" t-on-click="props.onClose">Done</button>
                </div>
            </div>
        </div>
    `;

    static props = ["onClose", "fontSize", "theme", "idleMinutes", "showTitle", "onFontSize", "onTheme", "onIdleMinutes", "onShowTitle"];
}

// ─── KioskVoiceAssistant ──────────────────────────────────────────────────────
/**
 * Floating AI voice assistant panel for the kiosk.
 * Uses /kiosk/ai/text and /kiosk/ai/voice (token-validated, role=kiosk).
 * No Odoo module imports — uses the same plain-fetch jsonPost utility.
 */

class KioskVoiceAssistant extends Component {
    static template = xml`
        <div class="k-ai-widget">
            <!-- Floating toggle button + kiosk name label -->
            <div class="k-ai-btn-wrap">
                <button t-attf-class="k-ai-btn #{state.open ? 'k-ai-btn--active' : ''}"
                        t-on-click="toggle"
                        title="AI Assistant">
                    🤖
                </button>
                <t t-if="props.kioskName">
                    <span class="k-ai-kiosk-label" t-esc="props.kioskName"/>
                </t>
            </div>

            <!-- Chat panel -->
            <t t-if="state.open">
                <div class="k-ai-panel">
                    <div class="k-ai-panel__header">
                        <span class="k-ai-panel__title">
                            <t t-if="props.instructorMode">🤖 Instructor AI</t>
                            <t t-else="">🤖 AI Assistant</t>
                        </span>
                        <button class="k-ai-panel__close" t-on-click="close">✕</button>
                    </div>

                    <div class="k-ai-panel__messages" t-ref="msgList">
                        <t t-foreach="state.messages" t-as="msg" t-key="msg_index">
                            <div t-attf-class="k-ai-msg k-ai-msg--#{msg.role}">
                                <div class="k-ai-msg__text" t-esc="msg.text"/>
                                <div class="k-ai-msg__time" t-esc="msg.time"/>
                            </div>
                        </t>
                        <t t-if="state.processing">
                            <div class="k-ai-msg k-ai-msg--assistant k-ai-msg--typing">
                                <span class="k-ai-typing-dot"/>
                                <span class="k-ai-typing-dot"/>
                                <span class="k-ai-typing-dot"/>
                                <t t-if="state.thinkingHint">
                                    <div class="k-ai-thinking-hint">Still thinking… complex queries take a moment</div>
                                </t>
                            </div>
                            <button class="k-ai-cancel-btn" t-on-click="cancelAiRequest">Cancel</button>
                        </t>
                        <div t-ref="msgEnd"/>
                    </div>

                    <div class="k-ai-panel__footer">
                        <input class="k-ai-input"
                            type="text"
                            placeholder="Ask something…"
                            t-att-value="state.input"
                            t-on-input="onInputChange"
                            t-on-keydown="onInputKeydown"
                            t-att-disabled="state.processing or undefined"/>
                        <button t-attf-class="k-ai-mic #{state.recording ? 'k-ai-mic--active' : ''}"
                            t-on-click="toggleRecording"
                            title="Voice input">
                            🎙️
                        </button>
                        <button class="k-ai-send"
                            t-on-click="send"
                            t-att-disabled="!state.input.trim() or state.processing or undefined">
                            ➤
                        </button>
                    </div>
                    <t t-if="state.recording">
                        <div class="k-ai-live-transcript">
                            <t t-if="state.liveTranscript">
                                <t t-esc="state.liveTranscript"/>
                            </t>
                            <t t-else="">
                                Listening…
                            </t>
                        </div>
                    </t>
                </div>
            </t>
        </div>
    `;

    static props = ["instructorMode", "kioskName"];

    setup() {
        this.state = useState({
            open: false,
            messages: [],
            input: "",
            recording: false,
            processing: false,
            thinkingHint: false,
            liveTranscript: "",
        });
        this._msgListRef = useRef("msgList");
        this._msgEndRef = useRef("msgEnd");
        this._mediaRecorder = null;
        this._audioChunks = [];
        this._stream = null;
        this._recordTimeout = null;
        this._speechSupported = ('SpeechRecognition' in window) || ('webkitSpeechRecognition' in window);
        this._recognition = null;
        this._pendingTranscript = "";
        this._silenceTimer = null;
        this._lastRole = null;
        onWillUnmount(() => {
            if (this._recognition) {
                this._recognition.abort();
                this._recognition = null;
            }
            if (this._mediaRecorder && this._mediaRecorder.state !== "inactive") {
                this._mediaRecorder.stop();
            }
            if (this._stream) {
                this._stream.getTracks().forEach(t => t.stop());
                this._stream = null;
            }
            if (this._recordTimeout) {
                clearTimeout(this._recordTimeout);
                this._recordTimeout = null;
            }
            if (this._silenceTimer) {
                clearTimeout(this._silenceTimer);
                this._silenceTimer = null;
            }
        });
    }

    get _role() {
        return this.props.instructorMode ? "instructor" : "kiosk";
    }

    _newSessionId() {
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
            const r = Math.random() * 16 | 0;
            return (c === 'x' ? r : (r & 0x3 | 0x8)).toString(16);
        });
    }

    toggle() {
        this.state.open = !this.state.open;
        // Reset conversation when switching between roles — also generate a fresh session ID
        if (this.state.open && (this.state.messages.length === 0 || this._lastRole !== this._role)) {
            this.state.messages = [];
            this._lastRole = this._role;
            this._chatSessionId = this._newSessionId();
            const greeting = this.props.instructorMode
                ? "👋 Instructor mode. I can help you manage attendance, check rosters, look up members, and more."
                : "👋 Hi! I can help you look up members, check sessions, or answer questions about the dojo. What would you like to know?";
            this._push("assistant", greeting);
        }
        if (this.state.open) setTimeout(() => this._scrollBottom(), 60);
    }

    close() { this.state.open = false; }

    onInputChange(ev) { this.state.input = ev.target.value; }

    onInputKeydown(ev) {
        if (ev.key === "Enter" && !ev.shiftKey) { ev.preventDefault(); this.send(); }
    }

    async send() {
        const text = (this.state.input || "").trim();
        if (!text || this.state.processing) return;
        this.state.input = "";
        await this._submitText(text);
    }

    async _submitText(text) {
        this._push("user", text);
        this.state.processing = true;
        this._scrollBottom();

        // Abort controller for timeout + cancel
        this._abortCtrl = new AbortController();
        const timeoutId = setTimeout(() => this._abortCtrl.abort(), 45000);

        // "Still thinking" hint after 8s
        const thinkId = setTimeout(() => {
            if (this.state.processing) {
                this.state.thinkingHint = true;
            }
        }, 8000);

        try {
            const result = await jsonPost("/kiosk/ai/text", { text, role: this._role, chat_session_id: this._chatSessionId }, { signal: this._abortCtrl.signal });
            if (result.success !== false) {
                this._push("assistant", result.response || "Sorry, I couldn't find an answer for that. Try rephrasing your question.");
            } else {
                this._push("assistant", "⚠️ " + (result.error || "Something went wrong. Please try again."));
            }
        } catch (err) {
            if (err.name === "AbortError") {
                this._push("assistant", "⚠️ That query took too long. Try a simpler question or break it into parts.");
            } else {
                this._push("assistant", "⚠️ Network error — please try again.");
            }
        } finally {
            clearTimeout(timeoutId);
            clearTimeout(thinkId);
            this.state.processing = false;
            this.state.thinkingHint = false;
            this._abortCtrl = null;
            this._scrollBottom();
        }
    }

    cancelAiRequest() {
        if (this._abortCtrl) this._abortCtrl.abort();
    }

    async toggleRecording() {
        if (this.state.recording) {
            this._stopVoiceInput();
        } else {
            await this._startVoiceInput();
        }
    }

    async _startVoiceInput() {
        if (this._speechSupported) {
            const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
            this._recognition = new SR();
            this._recognition.continuous = true;
            this._recognition.interimResults = true;
            this._recognition.lang = "en-US";
            this._pendingTranscript = "";
            this.state.liveTranscript = "";
            this.state.recording = true;

            const resetSilenceTimer = () => {
                if (this._silenceTimer) clearTimeout(this._silenceTimer);
                this._silenceTimer = setTimeout(() => {
                    this._silenceTimer = null;
                    if (this._recognition) this._recognition.stop();
                }, 2500);
            };

            this._recognition.onresult = (event) => {
                let full = "";
                for (let i = 0; i < event.results.length; i++) {
                    full += event.results[i][0].transcript;
                }
                this._pendingTranscript = full;
                this.state.liveTranscript = full;
                resetSilenceTimer();
            };

            this._recognition.onerror = (event) => {
                if (this._silenceTimer) { clearTimeout(this._silenceTimer); this._silenceTimer = null; }
                this._pendingTranscript = "";
                this.state.liveTranscript = "";
                this.state.recording = false;
                const msg = event.error === "not-allowed"
                    ? "⚠️ Microphone access denied."
                    : "⚠️ Voice recognition failed, please try again.";
                this._push("assistant", msg);
            };

            this._recognition.onend = () => {
                if (this._silenceTimer) { clearTimeout(this._silenceTimer); this._silenceTimer = null; }
                this.state.recording = false;
                this.state.liveTranscript = "";
                const text = this._pendingTranscript.trim();
                this._pendingTranscript = "";
                this._recognition = null;
                if (text) {
                    this._submitVoiceTranscript(text);
                }
            };

            this._recognition.start();
        } else {
            // Fallback: existing MediaRecorder push-to-talk
            await this._startRecording();
            this.state.liveTranscript = "Listening…";
        }
    }

    _stopVoiceInput() {
        if (this._speechSupported && this._recognition) {
            this._recognition.stop();
        } else {
            this._stopRecording();
            this.state.liveTranscript = "";
        }
    }

    _submitVoiceTranscript(text) {
        if (this.state.processing) {
            // AI is still responding — put transcript in input so user can submit manually
            this.state.input = text;
            this.state.liveTranscript = "";
            return;
        }
        this.state.liveTranscript = "";
        this._submitText(text);
    }

    async _startRecording() {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            this._push("assistant", "⚠️ Microphone not available in this browser.");
            return;
        }
        try {
            this._stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        } catch {
            this._push("assistant", "⚠️ Microphone access denied. Please allow it in your browser.");
            return;
        }

        this._audioChunks = [];
        const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
            ? "audio/webm;codecs=opus" : "audio/webm";
        this._mediaRecorder = new MediaRecorder(this._stream, { mimeType });
        this._mediaRecorder.ondataavailable = (e) => {
            if (e.data && e.data.size > 0) this._audioChunks.push(e.data);
        };
        this._mediaRecorder.onstop = () => this._processRecording();
        this._mediaRecorder.start(250);
        this.state.recording = true;
        this._recordTimeout = setTimeout(() => {
            if (this.state.recording) this._stopRecording();
        }, 60000);
    }

    _stopRecording() {
        if (this._recordTimeout) { clearTimeout(this._recordTimeout); this._recordTimeout = null; }
        if (this._mediaRecorder && this._mediaRecorder.state !== "inactive") {
            this._mediaRecorder.stop();
        }
        if (this._stream) { this._stream.getTracks().forEach(t => t.stop()); this._stream = null; }
        this.state.recording = false;
    }

    async _processRecording() {
        this.state.liveTranscript = "";
        if (!this._audioChunks.length) return;
        const blob = new Blob(this._audioChunks, { type: "audio/webm" });
        this._audioChunks = [];

        this._push("user", "🎙️ [voice message]");
        this.state.processing = true;
        this._scrollBottom();

        const formData = new FormData();
        formData.append("audio", blob, "recording.webm");
        if (KIOSK_TOKEN) formData.append("token", KIOSK_TOKEN);
        formData.append("role", this._role);

        try {
            const resp = await fetch("/kiosk/ai/voice", { method: "POST", body: formData });
            const result = await resp.json();
            if (result.success !== false) {
                const msgs = this.state.messages;
                const last = [...msgs].reverse().find(m => m.role === "user");
                if (last && last.text === "🎙️ [voice message]" && result.transcribed) {
                    last.text = "🎙️ " + result.transcribed;
                }
                this._push("assistant", result.response || "Sorry, I couldn't find an answer for that. Try rephrasing your question.");
            } else {
                this._push("assistant", "⚠️ " + (result.error || "Voice processing failed."));
            }
        } catch {
            this._push("assistant", "⚠️ Could not process voice recording.");
        } finally {
            this.state.processing = false;
            this._scrollBottom();
        }
    }

    _push(role, text) {
        const time = new Date().toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
        this.state.messages.push({ role, text, time });
    }

    _scrollBottom() {
        const el = this._msgEndRef.el;
        if (el) el.scrollIntoView({ behavior: "smooth" });
    }
}

// ─── KioskApp (root) ─────────────────────────────────────────────────────────

class KioskApp extends Component {
    static template = xml`
        <div class="k-app">

            <!-- ── Idle screen ── -->
            <t t-if="state.idle">
                <IdleScreen
                    announcements="state.announcements"
                    marketing_cards="state.marketing_cards"
                    onWake="() => this.wakeFromIdle()"/>
            </t>

            <!-- ── Check-in success overlay ── -->
            <t t-if="state.checkinResult">
                <CheckinSuccessView
                    success="state.checkinResult.success"
                    memberName="state.checkinResult.memberName || ''"
                    sessionName="state.checkinResult.sessionName || ''"
                    programName="state.checkinResult.programName || ''"
                    status="state.checkinResult.status || ''"
                    errorMessage="state.checkinResult.error || ''"
                    onDone="() => this.clearCheckinResult()"/>
            </t>

            <!-- ── Instructor header ── -->
            <t t-if="state.instructorMode">
                <div class="k-header k-header--instructor">
                    <span class="k-instructor-pill">🔓 Instructor Mode</span>
                    <t t-if="state.sessionContext">
                        <span t-attf-class="k-session-context-pill k-session-context-pill--#{state.sessionContext.mode || 'standby'}"
                            t-esc="sessionContextLabel()"/>
                    </t>
                    <div class="k-header__spacer"/>
                    <select class="k-svh-select"
                        t-att-value="state.sessionViewId || ''"
                        t-on-change="onSessionViewFilter">
                        <option value="">All Sessions</option>
                        <t t-foreach="state.sessions" t-as="s" t-key="s.id">
                            <option t-att-value="s.id"
                                t-att-selected="state.sessionViewId === s.id or undefined">
                                <t t-esc="s.template_name"/> (<t t-esc="formatTime(s.start)"/>)
                            </option>
                        </t>
                    </select>
                    <input class="k-svh-date"
                        type="date"
                        t-att-value="state.filterDate"
                        t-on-change="onDateChange"/>
                    <div class="k-header__actions">
                        <button class="k-header__action-btn" t-on-click="reloadSessions" title="Reload" t-att-disabled="state.reloading">
                            <span class="material-symbols-outlined" t-attf-style="font-size:20px;#{state.reloading ? 'animation:k-spin .6s linear infinite;' : ''}">sync</span>
                        </button>
                        <button class="k-header__action-btn" t-on-click="openSettings" title="Settings"><span class="material-symbols-outlined" style="font-size:20px;">settings</span></button>
                        <button class="k-header__action-btn" t-on-click="onInstructorToggle" title="Exit Instructor Mode" style="font-size:14px;font-weight:700;">✕ Exit</button>
                    </div>
                </div>
            </t>

            <!-- ── Body ── -->
            <div class="k-body">

                <!-- ════ STUDENT FLOW ════ -->
                <t t-if="!state.instructorMode">
                    <div class="k-prototype-home k-welcome-screen" data-prototype-contract="student-home">
                        <!-- Legacy served-asset markers for older gates: k-welcome-logo k-search-results-panel k-welcome-search-btn -->
                        <div class="k-prototype-home__topbar">
                            <div class="k-prototype-home__title k-welcome-title">CHECK IN</div>
                            <button class="k-prototype-home__exit" type="button" t-on-click="onInstructorToggle">
                                EXIT
                            </button>
                        </div>
                        <div class="k-prototype-home__search">
                            <div class="k-welcome-search-wrap k-prototype-home__search-wrap">
                                <span class="material-symbols-outlined k-welcome-search-icon">search</span>
                                <input class="k-welcome-search"
                                    type="search"
                                    placeholder="Search student name..."
                                    aria-label="Search student name"
                                    t-model="state.searchQuery"
                                    t-on-input="onSearchInput"
                                    autocomplete="off"
                                    autocorrect="off"
                                    spellcheck="false"/>
                            </div>
                        </div>
                        <t t-if="studentRosterSessionName()">
                            <div class="k-prototype-home__context" t-esc="studentRosterSessionName()"/>
                        </t>
                        <div class="k-search-results-flow k-prototype-home__roster">
                            <HomeContent
                                query="state.searchQuery"
                                results="visibleStudentRoster()"
                                loading="studentRosterLoading()"
                                onSelect="(member) => this.studentConfirm(member)"/>
                        </div>
                        <t t-if="state.studentRosterError">
                            <div class="k-prototype-home__error" t-esc="state.studentRosterError"/>
                        </t>
                    </div>
                </t>

                <!-- ════ INSTRUCTOR VIEW ════ -->
                <t t-else="">
                    <t t-if="state.sessionContext and state.sessionContext.mode === 'standby' and state.sessions.length">
                        <div class="k-session-context-banner">
                            <div class="k-session-context-banner__title">Standby</div>
                            <div class="k-session-context-banner__text" t-esc="state.sessionContext.reason"/>
                        </div>
                    </t>
                    <t t-if="!filteredSessions().length">
                        <div class="k-empty">
                            <div class="k-empty__icon">📅</div>
                            <div class="k-empty__text">No sessions today</div>
                            <button class="k-btn k-btn--primary" style="margin-top:16px;"
                                t-on-click="openCreateSession">
                                ➕ Create Session
                            </button>
                        </div>
                    </t>
                    <t t-else="">
                        <t t-if="state.sessionDoneError">
                            <div class="k-sessions-toast k-sessions-toast--error">
                                <span t-esc="state.sessionDoneError"/>
                                <button class="k-sessions-toast__dismiss" t-on-click="() => this.state.sessionDoneError = null">✕</button>
                            </div>
                        </t>
                        <InstructorThreePanelLayout
                            sessions="state.sessions"
                            sessionId="state.sessionViewId"
                            sessionContext="state.sessionContext"
                            rosters="state.sessionRosters"
                            loadingRosters="state.loadingRosters"
                            onSessionChange="(id) => this.onSessionViewChange(id)"
                            onMark="(memberId, sessionId, status) => this.markAttendance(memberId, sessionId, status)"
                            onRemoveAttendance="(memberId, sessionId) => this.directRemoveAttendance(memberId, sessionId)"
                            onManage="(memberId, sessionId) => this.openProfile(memberId, sessionId, 'manage')"
                            onClose="(sessionId) => this.closeSessionById(sessionId)"
                            onReopen="(sessionId) => this.reopenSessionById(sessionId)"
                            onDelete="(sessionId) => this.deleteSessionById(sessionId)"
                            onEdit="(session) => this.openEditSession(session)"
                            onAssignRoster="(session) => this.openAssignRoster(session)"
                            onCreateSession="() => this.openCreateSession()"/>
                    </t>
                </t>

            </div>

            <!-- ── Student checkin modal ── -->
            <t t-if="state.checkinModal">
                <StudentCheckinModal
                    member="state.checkinModal.member"
                    sessions="state.checkinModal.sessions"
                    loading="state.checkinModal.loading"
                    result="state.checkinModal.result"
                    checkedInSession="state.checkinModal.checkedInSession"
                    onSelect="(session) => this.studentCheckin(session)"
                    onCheckout="(session) => this.studentCheckout(session)"
                    onClose="() => this.state.checkinModal = null"/>
            </t>

            <!-- ── Member profile modal ── -->
            <t t-if="state.profileMember">
                <MemberProfileCard
                    member="state.profileMember"
                    sessionId="state.profileSessionId"
                    instructorMode="state.instructorMode"
                    instructorKey="state.instructorKey"
                    initialTab="state.profileInitialTab"
                    onClose="() => this.closeProfile()"
                    onCheckin="(member, sessionId) => this.doCheckinFromProfile(member, sessionId)"
                    onCheckout="(member, sessionId) => this.doCheckout(member, sessionId)"
                    onMarkAttendance="(member, sessionId, status) => this.markAttendanceFromProfile(member, sessionId, status)"
                    onRosterAdd="(member, sessionId) => this.rosterAdd(member, sessionId)"
                    onRosterRemove="(member, sessionId) => this.rosterRemove(member, sessionId)"
                    onRosterRemoveBySession="(member, sessionId) => this.rosterRemoveBySession(member, sessionId)"
                    onRefreshProfile="(member, photo) => this.refreshProfile(member, photo)"/>
            </t>

            <!-- ── Remove attendance confirm ── -->
            <t t-if="state.removeAttendancePending">
                <AttendanceRemoveConfirm
                    memberName="state.removeAttendancePending.name"
                    onCancel="() => this.state.removeAttendancePending = null"
                    onConfirm="() => this.confirmRemoveAttendance()"/>
            </t>

            <!-- ── Delete session confirm ── -->
            <t t-if="state.deleteSessionPending">
                <DeleteSessionConfirm
                    onCancel="() => this.state.deleteSessionPending = null"
                    onConfirm="() => this.confirmDeleteSession()"/>
            </t>

            <!-- ── PIN modal ── -->
            <t t-if="state.showPin">
                <PinModal onClose="() => this.closePin()" onSuccess="(result) => this.onPinSuccess(result)"/>
            </t>

            <!-- ── Edit session modal ── -->
            <t t-if="state.editingSession">
                <SessionEditModal
                    session="state.editingSession"
                    onClose="() => this.closeEditSession()"
                    onSaved="() => this.onSessionSaved()"/>
            </t>

            <!-- ── Create session modal ── -->
            <t t-if="state.showCreateSession">
                <CreateSessionModal
                    date="state.filterDate"
                    onClose="() => this.state.showCreateSession = false"
                    onCreated="(session) => this.onSessionCreated(session)"/>
            </t>

            <!-- ── Assign roster modal ── -->
            <t t-if="state.assignRosterSession">
                <AssignRosterModal
                    session="state.assignRosterSession"
                    sessions="state.sessions"
                    onClose="() => this.closeAssignRoster()"
                    onAssigned="(sid) => this.onRosterAssigned(sid)"/>
            </t>

            <!-- ── Settings modal ── -->
            <t t-if="state.showSettings">
                <KioskSettingsModal
                    fontSize="state.fontSize"
                    theme="state.theme"
                    idleMinutes="state.idleMinutes"
                    showTitle="state.showTitle"
                    onClose="() => this.closeSettings()"
                    onFontSize="(s) => this.onFontSize(s)"
                    onTheme="(t) => this.onTheme(t)"
                    onIdleMinutes="(m) => this.onIdleMinutes(m)"
                    onShowTitle="(v) => this.onShowTitle(v)"/>
            </t>

            <!-- ── AI Voice Assistant ── -->
            <t t-if="!state.idle and state.instructorMode and state.aiEnabled">
                <KioskVoiceAssistant instructorMode="state.instructorMode" kioskName="state.kioskName"/>
            </t>

        </div>
    `;

    static components = {
        HomeContent,
        MemberCard,
        StudentCheckinModal,
        InstructorSessionCard,
        InstructorRosterTile,
        InstructorThreePanelLayout,
        AttendanceRemoveConfirm,
        DeleteSessionConfirm,
        AssignRosterModal,
        MemberProfileCard,
        PinModal,
        CheckinSuccessView,
        IdleScreen,
        SessionEditModal,
        KioskSettingsModal,
        CreateSessionModal,
        KioskVoiceAssistant,
    };

    setup() {
        this.state = useState({
            // Student flow
            searchQuery: "",
            searchResults: [],
            searchLoading: false,
            studentRosterCards: [],
            studentRosterLoading: false,
            studentRosterLoaded: false,
            studentRosterSessionId: null,
            studentRosterSessionTitle: "",
            studentRosterError: "",
            checkinModal: null,   // { member, sessions, loading }
            checkinResult: null,

            // Sessions (instructor)
            sessions: [],
            sessionViewId: null,
            sessionViewManual: false,
            sessionContext: null,
            filterDate: todayIso(),
            sessionRosters: {},
            loadingRosters: {},

            // Config
            showTitle: true,

            // Instructor
            instructorMode: false,
            instructorKey: null,
            showPin: false,
            sessionDoneError: null,
            reloading: false,
            profileMember: null,
            profileSessionId: null,
            profileInitialTab: "profile",
            removeAttendancePending: null,
            deleteSessionPending: null,

            // Modals
            showSettings: false,
            editingSession: null,
            assignRosterSession: null,
            showCreateSession: false,

            // Misc
            idle: false,
            announcements: [],
            marketing_cards: [],
            fontSize: "normal",
            theme: "dark",
            idleMinutes: 3,
            kioskName: "",
            aiEnabled: false,
        });

        this._searchTimer = null;
        this._searchSeq = 0;
        this._barcodeBuffer = "";
        this._barcodeTimer = null;
        this._idleTimer = null;
        this._doneErrorTimer = null;
        this._sessionPollInterval = null;
        this._interactionHandler = this._resetIdleTimer.bind(this);

        onMounted(() => {
            this._bootstrap();
            this._startBarcodeListener();
            this._startSessionPoll();
            document.addEventListener("click", this._interactionHandler, true);
            document.addEventListener("keydown", this._interactionHandler, true);
            document.addEventListener("touchstart", this._interactionHandler, true);
            this._resetIdleTimer();
        });
        onWillUnmount(() => {
            this._stopBarcodeListener();
            this._stopSessionPoll();
            document.removeEventListener("click", this._interactionHandler, true);
            document.removeEventListener("keydown", this._interactionHandler, true);
            document.removeEventListener("touchstart", this._interactionHandler, true);
            clearTimeout(this._idleTimer);
        });
    }

    formatTime(dt) { return formatTime(dt); }

    sessionContextLabel() {
        const ctx = this.state.sessionContext || {};
        if (ctx.mode === "active") return "Active: " + (ctx.selected_session_name || "Class");
        if (ctx.mode === "upcoming") return "Next: " + (ctx.selected_session_name || "Class");
        return "Standby";
    }

    // ── Idle timer ─────────────────────────────────────────────

    _resetIdleTimer() {
        if (this.state.idle) this.state.idle = false;
        clearTimeout(this._idleTimer);
        this._idleTimer = setTimeout(() => {
            this.state.idle = true;
        }, this.state.idleMinutes * 60_000);
    }

    wakeFromIdle() {
        this.state.idle = false;
        this._resetIdleTimer();
    }

    // ── Bootstrap ──────────────────────────────────────────────

    async _bootstrap() {
        if (document.body.classList.contains("kiosk-theme-light")) {
            this.state.theme = "light";
        } else {
            this.state.theme = "dark";
        }
        try {
            const data = await jsonPost("/kiosk/api/bootstrap");
            if (data && !data.error) {
                this.state.announcements = data.announcements || [];
                this.state.marketing_cards = data.marketing_cards || [];
                this._applySessionsPayload(data, {
                    applyRecommended: this.state.instructorMode && !this.state.sessionViewManual,
                });
                this.state.kioskName = data.name || "";
                this.state.showTitle = data.show_title !== false;
                this.state.aiEnabled = data.ai_enabled === true;
                if (data.theme_mode && data.theme_mode !== this.state.theme) {
                    this.onTheme(data.theme_mode);
                }
                if (!this.state.instructorMode) {
                    this._loadStudentRoster();
                }
            } else {
                await this._loadSessions(null, {
                    applyRecommended: this.state.instructorMode && !this.state.sessionViewManual,
                });
                if (!this.state.instructorMode) {
                    this._loadStudentRoster();
                }
            }
        } catch (e) {
            console.error("Kiosk: bootstrap failed", e);
            await this._loadSessions(null, {
                applyRecommended: this.state.instructorMode && !this.state.sessionViewManual,
            });
            if (!this.state.instructorMode) {
                this._loadStudentRoster();
            }
        }
    }

    // ── Sessions ───────────────────────────────────────────────

    _applySessionsPayload(payload, { applyRecommended = false } = {}) {
        if (Array.isArray(payload)) {
            this.state.sessions = payload;
            this.state.sessionContext = null;
        } else {
            this.state.sessions = (payload && payload.sessions) || [];
            this.state.sessionContext = (payload && payload.session_context) || null;
        }
        if (this.state.sessionViewId && !this.state.sessions.some(s => s.id === this.state.sessionViewId)) {
            this.state.sessionViewId = null;
            this.state.sessionViewManual = false;
        }
        if (applyRecommended) {
            this._applyRecommendedSessionContext(true);
        }
    }

    _applyRecommendedSessionContext(force = false) {
        if (!force && this.state.sessionViewManual) {
            return;
        }

        const ctx = this.state.sessionContext || {};
        const selectedId = ctx.selected_session_id || null;
        if (selectedId && this.state.sessions.some(s => s.id === selectedId)) {
            this.state.sessionViewId = selectedId;
            return;
        }

        if (ctx.mode === "standby") {
            if (force) this.state.sessionViewId = null;
            return;
        }

        if (!this.state.sessionContext) {
            const activeSession = this.state.sessions.find(s => s.time_state === "active");
            if (activeSession) {
                this.state.sessionViewId = activeSession.id;
                return;
            }

            const soonSession = this.state.sessions.find(s => s.time_state === "upcoming_soon");
            if (soonSession) {
                this.state.sessionViewId = soonSession.id;
                return;
            }
        }

        if (force) this.state.sessionViewId = null;
    }

    async _loadSessions(date = null, options = {}) {
        try {
            const params = date ? { date } : {};
            const payload = await jsonPost("/kiosk/sessions", params);
            this._applySessionsPayload(payload, options);
        } catch (e) {
            console.error("Kiosk: failed to load sessions", e);
        }
    }

    async reloadSessions() {
        this.state.reloading = true;
        try {
            await this._loadSessions(this.state.filterDate || null, {
                applyRecommended: this.state.instructorMode && !this.state.sessionViewManual,
            });
            if (this.state.instructorMode) {
                this._loadVisibleSessionRosters();
            } else {
                this._loadStudentRoster();
            }
        } finally {
            this.state.reloading = false;
        }
    }

    filteredSessions() {
        if (this.state.sessionViewId) {
            return this.state.sessions.filter(s => s.id === this.state.sessionViewId);
        }
        return this.state.sessions;
    }

    onSessionViewFilter(ev) {
        const val = ev.target.value;
        this.state.sessionViewId = val ? parseInt(val, 10) : null;
        this.state.sessionViewManual = true;
        this._loadVisibleSessionRosters();
    }

    onSessionViewChange(sessionId) {
        this.state.sessionViewId = sessionId;
        this.state.sessionViewManual = true;
        this._loadVisibleSessionRosters();
    }

    async onDateChange(ev) {
        const date = ev.target.value;
        this.state.filterDate = date;
        this.state.sessionViewId = null;
        this.state.sessionViewManual = false;
        this.state.sessionRosters = {};
        await this._loadSessions(date || null, { applyRecommended: true });
        this._loadVisibleSessionRosters();
    }

    // ── Rosters ────────────────────────────────────────────────

    _loadAllSessionRosters() {
        for (const session of this.state.sessions) {
            if (!this.state.sessionRosters[session.id] && !this.state.loadingRosters[session.id]) {
                this._loadSessionRoster(session.id);
            }
        }
    }

    _loadVisibleSessionRosters() {
        for (const session of this.filteredSessions()) {
            if (!this.state.sessionRosters[session.id] && !this.state.loadingRosters[session.id]) {
                this._loadSessionRoster(session.id);
            }
        }
    }

    async _loadSessionRoster(sessionId) {
        this.state.loadingRosters[sessionId] = true;
        try {
            const roster = await jsonPost("/kiosk/roster", { session_id: sessionId });
            this.state.sessionRosters[sessionId] = roster || [];
        } catch (e) {
            console.error("Kiosk: failed to load session roster", sessionId, e);
            this.state.sessionRosters[sessionId] = [];
        } finally {
            this.state.loadingRosters[sessionId] = false;
        }
    }

    _updateSessionRosterEntry(sessionId, memberId, changes) {
        const roster = this.state.sessionRosters[sessionId];
        const updateRoster = (entries) => {
            if (!entries) return;
            let idx;
            if (typeof memberId === "string" && memberId.startsWith("trial:")) {
                const leadId = parseInt(memberId.slice(6), 10);
                idx = entries.findIndex(r => r.is_trial && r.lead_id === leadId);
            } else {
                idx = entries.findIndex(r => r.member_id === memberId);
            }
            if (idx !== -1) Object.assign(entries[idx], changes);
        };
        updateRoster(roster);
        updateRoster(this.state.studentRosterCards);
    }

    _studentRosterSessionById(sessionId) {
        if (!sessionId) return null;
        return (this.state.sessions || []).find(session => session.id === sessionId) || null;
    }

    _studentRosterSessionTitleFromPayload(payload) {
        const session = (payload && payload.session) || null;
        if (session) {
            return session.template_name || session.name || "";
        }
        return "";
    }

    _studentRosterSessionIdFromPayload(payload) {
        const session = (payload && payload.session) || null;
        return session && session.id ? session.id : null;
    }

    _applyStudentRosterPayload(payload) {
        const members = (payload && payload.members) || [];
        const sessionId = this._studentRosterSessionIdFromPayload(payload);
        this.state.studentRosterCards = members;
        this.state.studentRosterLoaded = true;
        this.state.studentRosterSessionId = sessionId;
        this.state.studentRosterSessionTitle = this._studentRosterSessionTitleFromPayload(payload);
    }

    _studentRosterSessionIdForDisplay() {
        return this.state.studentRosterSessionId || this.studentSelectedSessionId();
    }

    _studentRosterSessionTitleForDisplay() {
        if (this.state.studentRosterSessionTitle) return this.state.studentRosterSessionTitle;
        const session = this._studentRosterSessionById(this.state.studentRosterSessionId);
        return session ? (session.template_name || session.name || "") : "";
    }

    // ── Student flow ───────────────────────────────────────────

    studentSelectedSession() {
        const sessions = this.state.sessions || [];
        if (!sessions.length) return null;

        const loadedRosterSession = this._studentRosterSessionById(this.state.studentRosterSessionId);
        if (loadedRosterSession) return loadedRosterSession;

        const ctx = this.state.sessionContext || {};
        const selectedId = ctx.selected_session_id || null;
        if (selectedId) {
            const fromContext = sessions.find(session => session.id === selectedId);
            if (fromContext) return fromContext;
        }

        return sessions.find(session => session.time_state === "active")
            || sessions.find(session => session.time_state === "upcoming_soon")
            || sessions.find(session => session.time_state === "upcoming")
            || sessions[0]
            || null;
    }

    studentSelectedSessionId() {
        const session = this.studentSelectedSession();
        return session ? session.id : null;
    }

    studentRosterSessionName() {
        const rosterTitle = this._studentRosterSessionTitleForDisplay();
        if (rosterTitle) return rosterTitle;
        const session = this.studentSelectedSession();
        if (!session) return "";
        return session.template_name || session.name || "";
    }

    studentRosterLoading() {
        const sessionId = this._studentRosterSessionIdForDisplay();
        return !!(
            this.state.studentRosterLoading
            || this.state.searchLoading
            || (sessionId && this.state.loadingRosters[sessionId])
        );
    }

    studentRoster() {
        if (this.state.studentRosterLoaded) return this.state.studentRosterCards || [];
        const sessionId = this._studentRosterSessionIdForDisplay();
        if (!sessionId) return this.state.searchResults || [];
        return this.state.sessionRosters[sessionId] || [];
    }

    visibleStudentRoster() {
        const roster = this.studentRoster();
        const terms = (this.state.searchQuery || "")
            .trim()
            .toLowerCase()
            .split(/\s+/)
            .filter(Boolean);
        if (!terms.length) return roster;
        return roster.filter(member => {
            const haystack = [
                member.name,
                member.member_number,
                member.belt_rank,
                member.program_name,
                member.trial_program,
                member.membership_label,
                member.attendance_label,
            ].filter(Boolean).join(" ").toLowerCase();
            return terms.every(term => haystack.includes(term));
        });
    }

    async _loadStudentRoster() {
        this.state.studentRosterLoading = true;
        this.state.studentRosterError = "";
        try {
            const payload = await jsonPost("/kiosk/student_roster", {
                date: this.state.filterDate || todayIso(),
            });
            this._applyStudentRosterPayload(payload || {});
        } catch (e) {
            console.error("Kiosk: failed to load student roster", e);
            const session = this.studentSelectedSession();
            const sessionId = session ? session.id : null;
            this.state.studentRosterSessionId = sessionId || null;
            this.state.studentRosterSessionTitle = session ? (session.template_name || session.name || "") : "";
            this.state.studentRosterLoaded = false;
            if (sessionId) {
                await this._loadSessionRoster(sessionId);
            } else {
                this.state.searchResults = [];
                this.state.searchLoading = false;
            }
            this.state.studentRosterError = "Could not load the class roster.";
        } finally {
            this.state.studentRosterLoading = false;
        }
    }

    onSearchInput() {
        clearTimeout(this._searchTimer);
        const searchSeq = ++this._searchSeq;
        const q = this.state.searchQuery.trim();
        if (this.state.studentRosterLoaded || this.studentSelectedSessionId()) {
            this.state.searchResults = [];
            this.state.searchLoading = false;
            return;
        }
        if (q.length < 2) { this.state.searchResults = []; this.state.searchLoading = false; return; }
        this.state.searchLoading = true;
        this._searchTimer = setTimeout(async () => {
            try {
                const results = await jsonPost("/kiosk/search", { query: q });
                if (searchSeq === this._searchSeq && this.state.searchQuery.trim() === q) {
                    this.state.searchResults = results || [];
                }
            } catch {
                if (searchSeq === this._searchSeq) this.state.searchResults = [];
            } finally {
                if (searchSeq === this._searchSeq) this.state.searchLoading = false;
            }
        }, 300);
    }

    onSearchSubmit() {
        if (this._searchTimer) clearTimeout(this._searchTimer);
        this.onSearchInput();
    }

    clearSearch() {
        this.state.searchQuery = "";
        this.state.searchResults = [];
        this._searchSeq++;
    }

    checkinMemberKey(member) {
        if (!member) return "";
        return member.is_trial
            ? `trial:${member.lead_id || ""}`
            : `member:${member.member_id || ""}`;
    }

    isCurrentCheckinMember(member) {
        return !!(
            this.state.checkinModal
            && this.state.checkinModal.memberKey === this.checkinMemberKey(member)
        );
    }

    async studentConfirm(member) {
        // Open the modal immediately with a spinner, then load the member's enrolled sessions
        const memberKey = this.checkinMemberKey(member);
        this.state.checkinModal = { member, memberKey, sessions: [], loading: true, result: null, checkedInSession: null };

        // Trial leads — show only their booked session directly, no enrolled_sessions lookup
        if (member.is_trial) {
            if (!this.isCurrentCheckinMember(member)) return;
            const session = member.trial_session;
            this.state.checkinModal.sessions = session && session.id ? [session] : [];
            this.state.checkinModal.loading = false;
            return;
        }

        try {
            const sessions = await jsonPost("/kiosk/member/enrolled_sessions", {
                member_id: member.member_id,
                date: this.state.filterDate || todayIso(),
            });
            if (!this.isCurrentCheckinMember(member)) return;
            const all = sessions || [];
            this.state.checkinModal.sessions = all;
            // Detect if already checked in to any session today
            const active = all.find(s => s.attendance_state === "present" || s.attendance_state === "late");
            this.state.checkinModal.checkedInSession = active || null;
        } catch (e) {
            console.error("Kiosk: failed to load enrolled sessions", e);
            if (this.isCurrentCheckinMember(member)) this.state.checkinModal.sessions = [];
        } finally {
            if (this.isCurrentCheckinMember(member)) this.state.checkinModal.loading = false;
        }
    }

    async studentCheckout(session) {
        const modal = this.state.checkinModal;
        if (!modal) return;
        const member = modal.member;
        try {
            const result = await jsonPost("/kiosk/checkout", {
                member_id: member.member_id,
                session_id: session.id,
            });
            if (result.success) {
                this._updateSessionRosterEntry(session.id, member.member_id, { attendance_state: "checked_out" });
            }
            modal.result = {
                success: result.success,
                type: "checkout",
                sessionName: session.template_name || session.name,
                programName: "",
                error: result.error || "",
            };
        } catch {
            modal.result = {
                success: false,
                type: "checkout",
                sessionName: "",
                programName: "",
                error: "Network error. Please try again.",
            };
        }
        setTimeout(() => {
            this.state.checkinModal = null;
            this.state.searchQuery = "";
            this.state.searchResults = [];
        }, 3000);
    }

    async studentCheckin(session) {
        const modal = this.state.checkinModal;
        if (!modal) return;
        const member = modal.member;
        modal.loading = true;
        try {
            let result;
            if (member.is_trial) {
                result = await jsonPost("/kiosk/trial/checkin", {
                    lead_id: member.lead_id,
                    session_id: session.id,
                });
            } else {
                result = await jsonPost("/kiosk/checkin", {
                    member_id: member.member_id,
                    session_id: session.id,
                });
                if (result.success) {
                    this._updateSessionRosterEntry(session.id, member.member_id, { attendance_state: result.status });
                }
            }
            const sessionName = result.session_name || session.template_name || session.name;
            const programName = result.program_name || session.program_name || "";
            if (result.success) {
                this.state.checkinResult = {
                    success: true,
                    memberName: member.name,
                    sessionName,
                    programName,
                    status: result.status || "present",
                    error: "",
                };
                this.state.checkinModal = null;
                this.state.searchQuery = "";
                this.state.searchResults = [];
                return;
            }
            modal.result = {
                success: false,
                sessionName,
                programName,
                error: result.error || "Check-in failed. Please see the front desk.",
            };
            modal.loading = false;
        } catch {
            modal.result = {
                success: false,
                sessionName: "",
                programName: "",
                error: "Network error. Please try again.",
            };
            modal.loading = false;
        }
    }

    clearCheckinResult() {
        this.state.checkinResult = null;
    }

    // ── Instructor — profile ───────────────────────────────────

    async openProfile(memberId, sessionId = null, initialTab = "profile") {
        try {
            const profile = await jsonPost("/kiosk/member/profile", {
                member_id: memberId,
                session_id: sessionId,
                instructor_key: this.state.instructorKey,
            });
            this.state.profileMember = profile;
            this.state.profileSessionId = sessionId;
            this.state.profileInitialTab = initialTab;
        } catch (e) {
            console.error("Kiosk: failed to load profile", e);
        }
    }

    closeProfile() {
        this.state.profileMember = null;
        this.state.profileSessionId = null;
        this.state.profileInitialTab = "profile";
    }

    async directRemoveAttendance(memberId, sessionId) {
        if (!memberId || !sessionId) return;
        await this.markAttendance(memberId, sessionId, "pending");
    }

    // ── Instructor — check-in from profile ────────────────────

    async doCheckinFromProfile(member, sessionId) {
        this.closeProfile();
        try {
            const result = await jsonPost("/kiosk/checkin", {
                member_id: member.member_id,
                session_id: sessionId,
            });
            if (result.success) {
                this._updateSessionRosterEntry(sessionId, member.member_id, { attendance_state: result.status });
            }
            this.state.checkinResult = {
                success: result.success,
                memberName: member.name,
                sessionName: result.session_name || "",
                programName: "",
                status: result.status || "",
                error: result.error || "",
            };
        } catch (e) {
            console.error("Kiosk: checkin from profile failed", e);
        }
    }

    // ── Instructor — checkout ─────────────────────────────────

    async doCheckout(member, sessionId) {
        this.closeProfile();
        try {
            const result = await jsonPost("/kiosk/checkout", {
                member_id: member.member_id,
                session_id: sessionId,
            });
            if (result.success) {
                // "checked_out" is a display-only state; the log record keeps present/late
                this._updateSessionRosterEntry(sessionId, member.member_id, { attendance_state: "checked_out" });
            }
        } catch (e) {
            console.error("Kiosk: checkout failed", e);
        }
    }

    // ── Instructor — attendance ───────────────────────────────

    async markAttendance(memberId, sessionId, status) {
        const validStatuses = new Set(["present", "late", "absent", "excused", "pending"]);
        if (!memberId || !sessionId || !validStatuses.has(status)) return;
        try {
            let result;
            if (typeof memberId === "string" && memberId.startsWith("trial:")) {
                if (status !== "present") return;
                const leadId = parseInt(memberId.slice(6), 10);
                result = await jsonPost("/kiosk/trial/checkin", { lead_id: leadId, session_id: sessionId });
            } else {
                result = await jsonPost("/kiosk/instructor/attendance", {
                    session_id: sessionId,
                    member_id: memberId,
                    status,
                    instructor_key: this.state.instructorKey,
                });
            }
            if (result && result.success === false) {
                console.warn("Kiosk: attendance change rejected", result);
                return;
            }
            const changes = {
                attendance_state: (result && (result.attendance_state || result.status)) || status,
            };
            if (result && result.attendance_label) changes.attendance_label = result.attendance_label;
            this._updateSessionRosterEntry(sessionId, memberId, changes);
        } catch (e) {
            console.error("Kiosk: mark attendance failed", e);
        }
    }

    async markAttendanceFromProfile(member, sessionId, status) {
        this.closeProfile();
        await this.markAttendance(member.member_id, sessionId, status);
    }

    promptRemoveAttendance(memberId, sessionId) {
        const roster = this.state.sessionRosters[sessionId] || [];
        const entry = roster.find(r => r.member_id === memberId);
        this.state.removeAttendancePending = {
            memberId,
            sessionId,
            name: entry ? entry.name : "this member",
        };
    }

    async confirmRemoveAttendance() {
        const { memberId, sessionId } = this.state.removeAttendancePending;
        this.state.removeAttendancePending = null;
        await this.markAttendance(memberId, sessionId, "pending");
    }

    // ── Instructor — roster ───────────────────────────────────

    async rosterAdd(member, sessionId) {
        try {
            const result = await jsonPost("/kiosk/instructor/roster/add", {
                session_id: sessionId,
                member_id: member.member_id,
                instructor_key: this.state.instructorKey,
            });
            if (result.success) {
                await this._loadSessionRoster(sessionId);
                return { success: true };
            } else {
                return { success: false, error: result.error || "Could not add to roster." };
            }
        } catch (e) {
            console.error("Kiosk: roster add failed", e);
            return { success: false, error: "Network error." };
        }
    }

    async rosterRemove(member, sessionId) {
        try {
            await jsonPost("/kiosk/instructor/roster/remove", {
                session_id: sessionId,
                member_id: member.member_id,
                instructor_key: this.state.instructorKey,
            });
            await this._loadSessionRoster(sessionId);
        } catch (e) {
            console.error("Kiosk: roster remove failed", e);
        }
    }

    _applyMemberPhotoUrl(memberId, imageUrl, cacheBust = null) {
        if (!memberId || !imageUrl) return;
        if (cacheBust) _photoBust[memberId] = cacheBust;
        if (this.state.profileMember && this.state.profileMember.member_id === memberId) {
            this.state.profileMember = { ...this.state.profileMember, image_url: imageUrl };
        }
        for (const entry of this.state.searchResults) {
            if (entry.member_id === memberId) Object.assign(entry, { image_url: imageUrl });
        }
        for (const entry of this.state.studentRosterCards) {
            if (entry.member_id === memberId) Object.assign(entry, { image_url: imageUrl });
        }
        if (this.state.checkinModal && this.state.checkinModal.member && this.state.checkinModal.member.member_id === memberId) {
            Object.assign(this.state.checkinModal.member, { image_url: imageUrl });
        }
        for (const roster of Object.values(this.state.sessionRosters)) {
            if (!roster) continue;
            for (const entry of roster) {
                if (entry.member_id === memberId) Object.assign(entry, { image_url: imageUrl });
            }
        }
    }

    async refreshProfile(member, photoResult = null) {
        try {
            const cacheBust = (photoResult && photoResult.cache_bust) || Date.now();
            const imageUrl = photoResult && photoResult.image_url;
            _photoBust[member.member_id] = cacheBust;
            if (imageUrl) this._applyMemberPhotoUrl(member.member_id, imageUrl, cacheBust);
            const profile = await jsonPost("/kiosk/member/profile", {
                member_id: member.member_id,
                session_id: this.state.profileSessionId,
                instructor_key: this.state.instructorKey,
            });
            if (profile && this.state.profileMember) this.state.profileMember = profile;
            if (this.state.profileSessionId) {
                await this._loadSessionRoster(this.state.profileSessionId);
            } else {
                const reloads = [];
                for (const sessionId of Object.keys(this.state.sessionRosters)) {
                    const roster = this.state.sessionRosters[sessionId];
                    if (roster && roster.some(e => e.member_id === member.member_id)) {
                        reloads.push(this._loadSessionRoster(parseInt(sessionId, 10)));
                    }
                }
                await Promise.all(reloads);
            }
            if (imageUrl) this._applyMemberPhotoUrl(member.member_id, imageUrl, cacheBust);
            return profile || null;
        } catch (e) {
            console.error("Kiosk: refresh profile failed", e);
            return null;
        }
    }

    async rosterRemoveBySession(member, sessionId) {
        try {
            await jsonPost("/kiosk/instructor/roster/remove", {
                session_id: sessionId,
                member_id: member.member_id,
                instructor_key: this.state.instructorKey,
            });
            // Reload the affected session roster
            await this._loadSessionRoster(sessionId);
            // Reload the profile to refresh appointments list
            const profile = await jsonPost("/kiosk/member/profile", {
                member_id: member.member_id,
                session_id: this.state.profileSessionId,
                instructor_key: this.state.instructorKey,
            });
            if (this.state.profileMember) this.state.profileMember = profile;
        } catch (e) {
            console.error("Kiosk: roster remove by session failed", e);
        }
    }

    openAssignRoster(session) { this.state.assignRosterSession = session; }
    closeAssignRoster() { this.state.assignRosterSession = null; }

    async onRosterAssigned(sessionId) {
        this.state.assignRosterSession = null;
        await this._loadSessionRoster(sessionId);
        await this._loadSessions(this.state.filterDate || null, {
            applyRecommended: this.state.instructorMode && !this.state.sessionViewManual,
        });
    }

    // ── Instructor — session management ──────────────────────

    async closeSessionById(sessionId) {
        try {
            const result = await jsonPost("/kiosk/instructor/session/close", { session_id: sessionId });
            if (!result.success) {
                const msg = result.error === "pending_attendance"
                    ? (result.message || `${result.count || "Some"} member(s) still have attendance pending. Record all attendance before marking done.`)
                    : (result.error || "Could not close session.");
                this.state.sessionDoneError = msg;
                clearTimeout(this._doneErrorTimer);
                this._doneErrorTimer = setTimeout(() => { this.state.sessionDoneError = null; }, 6000);
                return;
            }
            this.state.sessionDoneError = null;
            await this._loadSessions(this.state.filterDate || null, {
                applyRecommended: this.state.instructorMode && !this.state.sessionViewManual,
            });
        } catch (e) {
            console.error("Kiosk: close session failed", e);
        }
    }

    async reopenSessionById(sessionId) {
        try {
            const result = await jsonPost("/kiosk/instructor/session/reopen", { session_id: sessionId });
            if (!result.success) {
                this.state.sessionDoneError = result.error || "Could not reopen session.";
                clearTimeout(this._doneErrorTimer);
                this._doneErrorTimer = setTimeout(() => { this.state.sessionDoneError = null; }, 6000);
                return;
            }
            this.state.sessionDoneError = null;
            await this._loadSessions(this.state.filterDate || null, {
                applyRecommended: this.state.instructorMode && !this.state.sessionViewManual,
            });
            this._loadSessionRoster(sessionId);
        } catch (e) {
            console.error("Kiosk: reopen session failed", e);
        }
    }

    deleteSessionById(sessionId) {
        this.state.deleteSessionPending = sessionId;
    }

    async confirmDeleteSession() {
        const sessionId = this.state.deleteSessionPending;
        this.state.deleteSessionPending = null;
        try {
            await jsonPost("/kiosk/instructor/session/delete", { session_id: sessionId });
            delete this.state.sessionRosters[sessionId];
            if (this.state.sessionViewId === sessionId) {
                this.state.sessionViewId = null;
                this.state.sessionViewManual = false;
            }
            await this._loadSessions(this.state.filterDate || null, {
                applyRecommended: this.state.instructorMode && !this.state.sessionViewManual,
            });
        } catch (e) {
            console.error("Kiosk: delete session failed", e);
        }
    }

    openEditSession(session) { this.state.editingSession = session; }
    closeEditSession() { this.state.editingSession = null; }

    async onSessionSaved() {
        this.state.editingSession = null;
        await this._loadSessions(this.state.filterDate || null, {
            applyRecommended: this.state.instructorMode && !this.state.sessionViewManual,
        });
        this._loadVisibleSessionRosters();
    }

    openCreateSession() { this.state.showCreateSession = true; }

    async onSessionCreated(session) {
        this.state.showCreateSession = false;
        await this._loadSessions(this.state.filterDate || null, {
            applyRecommended: this.state.instructorMode && !this.state.sessionViewManual,
        });
        this._loadVisibleSessionRosters();
    }

    // ── PIN / instructor mode ─────────────────────────────────

    openPin() { this.state.showPin = true; }
    closePin() { this.state.showPin = false; }

    onPinSuccess(result) {
        this.state.showPin = false;
        this.state.instructorMode = true;
        this.state.instructorKey = result.instructor_key || null;
        this.state.sessionViewManual = false;
        this._applyRecommendedSessionContext(true);
        this._loadVisibleSessionRosters();
    }

    onInstructorToggle() {
        if (!this.state.instructorMode) {
            this.openPin();
        } else {
            this.state.instructorMode = false;
            this.state.studentView = "home";
            this.state.confirmedMember = null;
            this._loadStudentRoster();
        }
    }

    // ── Settings ──────────────────────────────────────────────

    openSettings() { this.state.showSettings = true; }
    closeSettings() { this.state.showSettings = false; }

    onFontSize(size) {
        this.state.fontSize = size;
        // Apply to <html> so all rem units scale correctly
        const sizeMap = { normal: "16px", large: "18px", xl: "21px" };
        document.documentElement.style.fontSize = sizeMap[size] || "16px";
        // Keep body classes for any em-based inheritance
        document.body.classList.remove("kiosk-font-large", "kiosk-font-xl");
        if (size === "large") document.body.classList.add("kiosk-font-large");
        if (size === "xl") document.body.classList.add("kiosk-font-xl");
    }

    onTheme(theme) {
        this.state.theme = theme;
        document.body.classList.remove("kiosk-theme-light", "kiosk-theme-dark");
        document.body.classList.add(`kiosk-theme-${theme}`);
    }

    onShowTitle(val) {
        this.state.showTitle = val;
    }

    onIdleMinutes(mins) {
        this.state.idleMinutes = mins;
        this._resetIdleTimer();
    }

    // ── Barcode scanner (HID keyboard emulation) ──────────────

    _startBarcodeListener() {
        this._barcodeHandler = this._onKeyPress.bind(this);
        document.addEventListener("keypress", this._barcodeHandler);
    }

    _stopBarcodeListener() {
        if (this._barcodeHandler) document.removeEventListener("keypress", this._barcodeHandler);
    }

    _startSessionPoll() {
        this._sessionPollInterval = setInterval(() => {
            if (this.state.instructorMode && !this.state.reloading) {
                this._loadSessions(this.state.filterDate || null, {
                    applyRecommended: !this.state.sessionViewManual,
                });
            }
        }, 60000);
    }

    _stopSessionPoll() {
        if (this._sessionPollInterval) {
            clearInterval(this._sessionPollInterval);
            this._sessionPollInterval = null;
        }
    }

    _onKeyPress(ev) {
        if (["INPUT", "SELECT", "TEXTAREA"].includes(ev.target.tagName)) return;
        clearTimeout(this._barcodeTimer);
        if (ev.key === "Enter") {
            const barcode = this._barcodeBuffer.trim();
            this._barcodeBuffer = "";
            if (barcode.length >= 3) this._handleBarcode(barcode);
            return;
        }
        if (ev.key.length === 1) this._barcodeBuffer += ev.key;
        this._barcodeTimer = setTimeout(() => {
            if (this._barcodeBuffer.length < 6) this._barcodeBuffer = "";
        }, 100);
    }

    async _handleBarcode(barcode) {
        try {
            const result = await jsonPost("/kiosk/lookup", { barcode });
            if (result.found && result.member) {
                if (!this.state.instructorMode) {
                    this.studentConfirm(result.member);
                } else {
                    await this.openProfile(result.member.member_id);
                }
            }
        } catch (e) {
            console.error("Kiosk: barcode lookup failed", e);
        }
    }
}

// ─── Mount ────────────────────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", () => {
    const root = document.getElementById("kiosk-root");
    if (!root) return;
    mount(KioskApp, root, { dev: false }).catch(e => {
        root.innerHTML =
            '<pre style="color:red;background:#111;padding:20px;font-size:13px;white-space:pre-wrap">'
            + "OWL MOUNT ERROR:\n" + (e && e.message || e)
            + (e && e.stack ? "\n\n" + e.stack : "") + "</pre>";
    });
});
