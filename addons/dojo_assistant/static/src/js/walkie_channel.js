/** @odoo-module **/
/**
 * PROTOTYPE — Dojo AI Walkie-Talkie: Channel Beta (backend OWL component)
 *
 * Extends the default walkie-talkie with a runtime channel switcher.
 * Channels narrow the AI's focus via system prompt prefix injection on the server.
 * No hard filtering — purely prompt-level context steering.
 *
 * Channel is runtime UI state only — never persisted to the database.
 *
 * Registered as: dojo_assistant.walkie_channel
 */

import { Component, useState, useRef, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

// ─── Channel definitions ─────────────────────────────────────────────────────

const CHANNELS = [
    { id: "all",        label: "All",         icon: "fa-th" },
    { id: "attendance", label: "Attendance",  icon: "fa-check-square-o" },
    { id: "members",    label: "Members",     icon: "fa-users" },
    { id: "enrollment", label: "Enrollment",  icon: "fa-calendar-plus-o" },
    { id: "belts",      label: "Belt & Ranks",icon: "fa-trophy" },
    { id: "billing",    label: "Billing",     icon: "fa-credit-card" },
    { id: "lookup",     label: "Lookup Only", icon: "fa-search" },
];

const CHANNEL_LABEL = Object.fromEntries(CHANNELS.map(c => [c.id, c.label]));

// ─── Helpers ─────────────────────────────────────────────────────────────────

function nowLabel() {
    return new Date().toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
}

const YES_RE = /\b(yes|confirm|yeah|yep|sure|correct|ok|okay|affirmative|do it)\b/i;
const NO_RE  = /\b(no|cancel|nope|stop|abort|never mind|nevermind|don'?t)\b/i;

// ─── Component ───────────────────────────────────────────────────────────────

class DojoWalkieChannel extends Component {
    static template = "dojo_assistant.WalkieChannel";

    setup() {
        this.threadRef = useRef("thread");

        const ctx = this.props.action?.context || {};
        this.walkieId   = ctx.walkie_id   || null;
        this.walkieName = ctx.walkie_name || "AI Walkie-Talkie";

        this.channels = CHANNELS;

        this.state = useState({
            // PTT / recording
            isHolding: false,
            isProcessing: false,
            isSpeaking: false,
            // Conversation
            messages: [],
            contextWindow: [],
            walkieName: this.walkieName,
            // Channel
            activeChannel: "all",
            activeChannelLabel: CHANNEL_LABEL["all"],
            showDialOverlay: false,
            // Confirmation flow
            awaitingConfirmation: false,
            confirmationPrompt: "",
            sessionKey: null,
            // Status
            statusLabel: "Hold to talk",
            error: null,
        });

        this._mediaRecorder = null;
        this._audioChunks   = [];
        this._stream        = null;
        this._currentAudio  = null;
        this._lastTranscribed = "";

        onWillUnmount(() => {
            this._cleanupRecording();
            if (this._currentAudio) { this._currentAudio.pause(); this._currentAudio = null; }
        });
    }

    // ── Dial computed props ───────────────────────────────────────────────────

    get activeChannelIcon() {
        const ch = CHANNELS.find(c => c.id === this.state.activeChannel);
        return ch ? ch.icon : "fa-th";
    }

    get prevChannelLabel() {
        const idx = CHANNELS.findIndex(c => c.id === this.state.activeChannel);
        return CHANNELS[(idx - 1 + CHANNELS.length) % CHANNELS.length].label;
    }

    get nextChannelLabel() {
        const idx = CHANNELS.findIndex(c => c.id === this.state.activeChannel);
        return CHANNELS[(idx + 1) % CHANNELS.length].label;
    }

    // ── Channel switching ────────────────────────────────────────────────────

    switchChannel(channelId) {
        if (channelId === this.state.activeChannel) return;
        this.state.activeChannel = channelId;
        this.state.activeChannelLabel = CHANNEL_LABEL[channelId] || channelId;
        // Clear context on channel switch to prevent cross-channel bleed
        this.state.contextWindow = [];
        this.state.awaitingConfirmation = false;
        this.state.sessionKey = null;
        // Only add divider when there is existing conversation to separate
        if (this.state.messages.length > 0) {
            this._pushDivider(`── Channel: ${CHANNEL_LABEL[channelId] || channelId} ──`);
        }
    }

    prevChannel() {
        const idx = CHANNELS.findIndex(c => c.id === this.state.activeChannel);
        const prev = CHANNELS[(idx - 1 + CHANNELS.length) % CHANNELS.length];
        this.switchChannel(prev.id);
    }

    nextChannel() {
        const idx = CHANNELS.findIndex(c => c.id === this.state.activeChannel);
        const next = CHANNELS[(idx + 1) % CHANNELS.length];
        this.switchChannel(next.id);
    }

    toggleDialOverlay() {
        this.state.showDialOverlay = !this.state.showDialOverlay;
    }

    // ── PTT ──────────────────────────────────────────────────────────────────

    async onPttDown(ev) {
        ev.preventDefault();
        if (this.state.isHolding || this.state.isProcessing || this.state.isSpeaking) return;
        await this._startRecording();
    }

    onPttUp(ev) {
        ev.preventDefault();
        if (!this.state.isHolding) return;
        this._stopRecording();
    }

    onPttLeave(ev) {
        if (this.state.isHolding) this._stopRecordingCancel();
    }

    async _startRecording() {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            this._pushError("Microphone not supported in this browser.");
            return;
        }
        try {
            this._stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        } catch (_) {
            this._pushError("Microphone access denied — please allow it in your browser.");
            return;
        }

        this._audioChunks = [];
        const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
            ? "audio/webm;codecs=opus"
            : "audio/webm";
        this._mediaRecorder = new MediaRecorder(this._stream, { mimeType });
        this._mediaRecorder.ondataavailable = (e) => {
            if (e.data && e.data.size > 0) this._audioChunks.push(e.data);
        };
        this._mediaRecorder.onstop = () => this._processRecording(mimeType);
        this._mediaRecorder.start(100);

        this.state.isHolding = true;
        this.state.statusLabel = "Listening…";
        this.state.error = null;
    }

    _stopRecording() {
        if (this._mediaRecorder && this._mediaRecorder.state !== "inactive") {
            this._mediaRecorder.stop();
        }
        this._releaseStream();
        this.state.isHolding = false;
        this.state.statusLabel = "Processing…";
    }

    _stopRecordingCancel() {
        this._cleanupRecording();
        this.state.isHolding = false;
        this.state.statusLabel = "Hold to talk";
    }

    _cleanupRecording() {
        if (this._mediaRecorder && this._mediaRecorder.state !== "inactive") {
            this._mediaRecorder.onstop = () => {};
            this._mediaRecorder.stop();
        }
        this._releaseStream();
        this._audioChunks = [];
    }

    _releaseStream() {
        if (this._stream) {
            this._stream.getTracks().forEach(t => t.stop());
            this._stream = null;
        }
    }

    // ── Audio processing ─────────────────────────────────────────────────────

    async _processRecording(mimeType) {
        if (!this._audioChunks.length) {
            this.state.statusLabel = "Hold to talk";
            return;
        }
        const blob = new Blob(this._audioChunks, { type: mimeType || "audio/webm" });
        this._audioChunks = [];

        this.state.isProcessing = true;
        this.state.statusLabel = "Thinking…";

        try {
            const formData = new FormData();
            formData.append("audio", blob, "walkie.webm");
            formData.append("conversation_history", JSON.stringify(this.state.contextWindow));
            formData.append("channel", this.state.activeChannel);
            if (this.walkieId) formData.append("walkie_id", this.walkieId);

            const resp = await fetch("/dojo/ai/voice", {
                method: "POST",
                body: formData,
                credentials: "same-origin",
            });
            let result;
            try { result = await resp.json(); } catch (_) {}
            if (!resp.ok || !result) {
                throw new Error((result && result.error) || `Server error ${resp.status}`);
            }
            this._handleResult(result);
        } catch (e) {
            this._pushError(e.message || "Failed to process audio — please try again.");
            console.error("[walkie-channel]", e);
        } finally {
            this.state.isProcessing = false;
        }
    }

    // ── Result handling ───────────────────────────────────────────────────────

    _handleResult(result) {
        if (!result || !result.success) {
            this._pushError((result && result.error) || "An unexpected error occurred.");
            this.state.statusLabel = "Hold to talk";
            return;
        }

        const said = (result.transcribed || "").trim();
        this._lastTranscribed = said;
        if (said) this._pushMsg("user", said);

        if (this.state.awaitingConfirmation && said) {
            if (YES_RE.test(said)) { this._doConfirm(true); return; }
            if (NO_RE.test(said))  { this._doConfirm(false); return; }
            this.state.awaitingConfirmation = false;
            this.state.sessionKey = null;
        }

        if (result.state === "pending_confirmation") {
            const prompt = result.confirmation_prompt || result.response || "Please confirm.";
            this.state.awaitingConfirmation = true;
            this.state.sessionKey = result.session_key || null;
            this.state.confirmationPrompt = prompt;
            this._pushMsg("ai", prompt, { confirm: true });
            this._speakResponse(prompt);
            this.state.statusLabel = "Say Yes or No";
        } else if (result.state === "executed") {
            this.state.awaitingConfirmation = false;
            this.state.sessionKey = null;
            const response = result.response || "Done!";
            this._pushMsg("ai", response);
            this._speakResponse(response);
            this._updateContextWindow(this._lastTranscribed, response);
            this.state.statusLabel = "Hold to talk";
        } else if (result.state === "error") {
            this._pushError(result.error || "An error occurred.");
            this.state.statusLabel = "Hold to talk";
        } else {
            this.state.statusLabel = "Hold to talk";
        }
    }

    // ── Confirmation ─────────────────────────────────────────────────────────

    async confirmAction() { await this._doConfirm(true); }
    async cancelAction()  { await this._doConfirm(false); }

    async _doConfirm(confirmed) {
        if (!this.state.sessionKey || this.state.isProcessing) return;
        this.state.isProcessing = true;
        this.state.statusLabel = "Processing…";
        const key = this.state.sessionKey;
        this.state.awaitingConfirmation = false;
        this.state.sessionKey = null;

        try {
            const result = await rpc("/dojo/ai/confirm", { session_key: key, confirmed });
            if (!result || !result.success) {
                this._pushMsg("ai", "⚠️ " + ((result && result.error) || "Action failed."));
            } else if (!confirmed) {
                this._pushMsg("ai", "Action cancelled.");
                this._speakResponse("Action cancelled.");
            } else {
                const r = result.result || {};
                const msg = result.response || r.response || r.message || "Done!";
                this._pushMsg("ai", msg);
                this._speakResponse(msg);
                this._updateContextWindow("(confirmed action)", msg);
            }
        } catch (_) {
            this._pushError("Confirm request failed.");
        } finally {
            this.state.isProcessing = false;
            this.state.statusLabel = "Hold to talk";
        }
    }

    // ── TTS ──────────────────────────────────────────────────────────────────

    async _speakResponse(text) {
        if (!text) return;
        this.state.isSpeaking = true;
        this.state.statusLabel = "Speaking…";
        try {
            const result = await rpc("/dojo/ai/speak", { text });
            if (!result || !result.success) {
                this.state.isSpeaking = false;
                this.state.statusLabel = "Hold to talk";
                return;
            }
            const audio = new Audio("data:" + result.mime + ";base64," + result.audio_b64);
            if (this._currentAudio) this._currentAudio.pause();
            this._currentAudio = audio;
            audio.onended = () => {
                this.state.isSpeaking = false;
                this.state.statusLabel = "Hold to talk";
                this._currentAudio = null;
            };
            audio.onerror = () => {
                this.state.isSpeaking = false;
                this.state.statusLabel = "Hold to talk";
                this._currentAudio = null;
            };
            await audio.play().catch(() => {
                this.state.isSpeaking = false;
                this.state.statusLabel = "Hold to talk";
                this._currentAudio = null;
            });
        } catch (_) {
            this.state.isSpeaking = false;
            this.state.statusLabel = "Hold to talk";
        }
    }

    // ── Message helpers ───────────────────────────────────────────────────────

    _pushMsg(role, text, meta = {}) {
        this.state.messages.push({ role, text, time: nowLabel(), ...meta });
        this._scrollThread();
    }

    _pushDivider(text) {
        this.state.messages.push({ role: "divider", text, time: "" });
        this._scrollThread();
    }

    clearContext() {
        this.state.contextWindow = [];
        this._pushDivider("── Context Cleared ──");
    }

    _updateContextWindow(userText, aiText) {
        const cw = this.state.contextWindow;
        if (userText) cw.push({ role: "user", text: userText });
        if (aiText)   cw.push({ role: "assistant", text: aiText });
        if (cw.length > 20) cw.splice(0, cw.length - 20);
    }

    _pushError(msg) {
        this.state.error = msg;
        setTimeout(() => { if (this.state.error === msg) this.state.error = null; }, 6000);
    }

    _scrollThread() {
        setTimeout(() => {
            const el = this.threadRef.el;
            if (el) el.scrollTop = el.scrollHeight;
        }, 30);
    }
}

registry.category("actions").add("dojo_assistant.walkie_channel", DojoWalkieChannel);
