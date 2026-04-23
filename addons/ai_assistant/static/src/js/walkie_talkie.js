/** @odoo-module **/
/**
 * Dojo AI Walkie-Talkie — push-to-talk voice conversation UI.
 *
 * Instructor / Admin only client action.
 * Registered as: ai_assistant.walkie_talkie
 *
 * Flow:
 *   Hold PTT button → MediaRecorder starts
 *   Release         → audio POSTed to /dojo/ai/voice (ElevenLabs STT → intent AI)
 *   AI responds     → /dojo/ai/speak (ElevenLabs TTS) auto-plays
 *   Confirmation    → voice "yes/no" OR on-screen buttons in-thread
 */

import { Component, useState, useRef, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

// ─── helpers ────────────────────────────────────────────────────────────────

function nowLabel() {
    return new Date().toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
}

function formatConfidence(val) {
    if (val === null || val === undefined) return null;
    return Math.round(val * 100) + "%";
}

function formatMs(ms) {
    if (!ms) return null;
    return ms < 1000 ? ms + "ms" : (ms / 1000).toFixed(1) + "s";
}

const YES_RE = /\b(yes|confirm|yeah|yep|sure|correct|ok|okay|affirmative|do it)\b/i;
const NO_RE  = /\b(no|cancel|nope|stop|abort|never mind|nevermind|don'?t)\b/i;

// Minimal fallback steps shown while waiting when n8n has no step nodes configured.
const FALLBACK_STEPS = [
    { name: "Analyzing request",  detail: "Understanding what you're asking for..." },
    { name: "Routing to agent",   detail: "Finding the right specialist to handle this..." },
    { name: "Querying database",  detail: "Looking up the relevant records..." },
    { name: "Formatting results", detail: "Putting together your response..." },
];

// ─── component ──────────────────────────────────────────────────────────────

class DojoWalkieTalkie extends Component {
    static template = "ai_assistant.WalkieTalkie";

    setup() {
        this.threadRef = useRef("thread");

        // Read per-instance metadata injected by action_launch()
        const ctx = this.props.action?.context || {};
        this.walkieId   = ctx.walkie_id   || null;
        this.walkieName = ctx.walkie_name || "AI Walkie-Talkie";

        this.state = useState({
            // PTT / recording
            isHolding: false,
            isProcessing: false,
            isSpeaking: false,
            // Conversation
            messages: [],
            // Rolling LLM context window; reset on clearContext()
            contextWindow: [],
            // Walkie-Talkie name (reactive copy for template)
            walkieName: this.walkieName,
            // Confirmation flow
            awaitingConfirmation: false,
            confirmationPrompt: "",
            sessionKey: null,
            // Status label shown under button
            statusLabel: "Hold to talk",
            error: null,
            // User name for personalized empty state
            userName: "",
            // n8n pipeline steps
            liveSteps: [],
            liveStepIdx: 0,
        });

        this._mediaRecorder = null;
        this._audioChunks   = [];
        this._stream        = null;
        this._currentAudio  = null;
        this._lastTranscribed = "";
        this._pollInterval    = null;
        this._fallbackInterval = null;
        this._fallbackTimer   = null;
        this._pollHadResults  = false;

        // Fetch user name for personalized greeting
        rpc("/dojo/ai/config", {}).then((cfg) => {
            if (cfg && cfg.user_first_name) {
                this.state.userName = cfg.user_first_name;
            }
        }).catch(() => { /* keep default */ });

        onWillUnmount(() => {
            this._cleanupRecording();
            if (this._currentAudio) { this._currentAudio.pause(); this._currentAudio = null; }
            this._stopPoll();
            this._stopFallback();
        });
    }

    // ── PTT: hold to record ──────────────────────────────────────────────────

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
        // Cancel if finger/cursor leaves button while still holding
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
        // User dragged off the button — discard audio
        this._cleanupRecording();
        this.state.isHolding = false;
        this.state.statusLabel = "Hold to talk";
    }

    _cleanupRecording() {
        if (this._mediaRecorder && this._mediaRecorder.state !== "inactive") {
            // Overwrite onstop so we don't process the cancelled chunk
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

    // ── Audio processing → STT → AI ──────────────────────────────────────────

    async _processRecording(mimeType) {
        if (!this._audioChunks.length) {
            this.state.statusLabel = "Hold to talk";
            return;
        }
        const blob = new Blob(this._audioChunks, { type: mimeType || "audio/webm" });
        this._audioChunks = [];

        this.state.isProcessing = true;
        this.state.statusLabel = "Thinking…";
        this.state.liveSteps = [];
        this.state.liveStepIdx = 0;

        const pipelineKey = crypto.randomUUID().replace(/-/g, "").slice(0, 12);

        // Show placeholder step immediately; fall back to fake animation if n8n
        // doesn't push real steps within 12.5s.
        this.state.liveSteps = [{ name: "Processing your request...", detail: "Connecting to AI pipeline..." }];
        this.state.liveStepIdx = 0;
        this._scrollThread();
        this._startPoll(pipelineKey);
        this._fallbackTimer = setTimeout(() => {
            if (!this._pollHadResults) this._startFallback();
        }, 12500);

        try {
            const formData = new FormData();
            formData.append("audio", blob, "walkie.webm");
            formData.append("conversation_history", JSON.stringify(this.state.contextWindow));
            formData.append("pipeline_key", pipelineKey);

            const resp = await fetch("/dojo/ai/voice", {
                method: "POST",
                body: formData,
                credentials: "same-origin",
            });
            let result;
            try { result = await resp.json(); } catch (_) {}
            if (!resp.ok || !result) {
                const msg = result && result.error ? result.error : `Server error ${resp.status}`;
                throw new Error(msg);
            }

            // Use accumulated pipeline steps from n8n response if available
            if (result.pipeline_steps && result.pipeline_steps.length > 0) {
                this.state.liveSteps = result.pipeline_steps;
                this.state.liveStepIdx = result.pipeline_steps.length - 1;
            }

            this._handleResult(result);
        } catch (e) {
            this._pushError(e.message || "Failed to process audio — please try again.");
            console.error("[walkie-talkie]", e);
        } finally {
            this._stopPoll();
            this._stopFallback();
            this.state.isProcessing = false;
            this.state.liveSteps = [];
        }
    }

    // ── Result handling ───────────────────────────────────────────────────────

    _handleResult(result) {
        if (!result || !result.success) {
            this._pushError((result && result.error) || "An unexpected error occurred.");
            this.state.statusLabel = "Hold to talk";
            return;
        }

        // Show what user said
        const said = (result.transcribed || "").trim();
        this._lastTranscribed = said;
        if (said) this._pushMsg("user", said);

        // --- Awaiting confirmation mode: check for voice yes/no first ---
        if (this.state.awaitingConfirmation && said) {
            if (YES_RE.test(said)) {
                this._doConfirm(true);
                return;
            }
            if (NO_RE.test(said)) {
                this._doConfirm(false);
                return;
            }
            // Not a yes/no — treat as new query (override the confirmation)
            this.state.awaitingConfirmation = false;
            this.state.sessionKey = null;
        }

        const agentMeta = {
            agent_name: result.agent_name || null,
            intent_type: (result.intent || {}).intent_type || null,
            confidence: formatConfidence((result.intent || {}).confidence),
            execution_time_ms: formatMs(result.execution_time_ms),
            logOpen: false,
        };

        if (result.state === "pending_confirmation") {
            const prompt = result.confirmation_prompt || result.response || "Please confirm.";
            this.state.awaitingConfirmation = true;
            this.state.sessionKey = result.session_key || null;
            this.state.confirmationPrompt = prompt;
            this._pushMsg("ai", prompt, { confirm: true, ...agentMeta });
            this._speakResponse(prompt);
            this.state.statusLabel = "Say Yes or No";
        } else if (result.state === "needs_clarification") {
            const response = result.response || "Could you clarify?";
            this._pushMsg("ai", response, agentMeta);
            this._speakResponse(response);
            this._updateContextWindow(this._lastTranscribed, response);
            this.state.statusLabel = "Hold to talk";
        } else if (result.state === "executed") {
            this.state.awaitingConfirmation = false;
            this.state.sessionKey = null;
            const response = result.response || "Done!";
            this._pushMsg("ai", response, agentMeta);
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

    // ── Confirmation (button or auto-voice) ───────────────────────────────────

    async confirmAction() {
        await this._doConfirm(true);
    }

    async cancelAction() {
        await this._doConfirm(false);
    }

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
                const err = (result && result.error) || "Action failed.";
                this._pushMsg("ai", "⚠️ " + err);
                this._speakResponse("Something went wrong. " + err);
            } else if (!confirmed) {
                this._pushMsg("ai", "Action cancelled.");
                this._speakResponse("Action cancelled.");
            } else {
                const r = result.result || {};
                const msg = result.response || r.response || r.message || "Done!";
                this._pushMsg("ai", msg, {
                    agent_name: result.agent_name || null,
                    intent_type: (result.intent || {}).intent_type || null,
                    confidence: formatConfidence((result.intent || {}).confidence),
                    execution_time_ms: formatMs(result.execution_time_ms),
                    logOpen: false,
                });
                this._speakResponse(msg);
                this._updateContextWindow("(confirmed action)", msg);
            }
        } catch (e) {
            this._pushError("Confirm request failed.");
        } finally {
            this.state.isProcessing = false;
            this.state.statusLabel = "Hold to talk";
        }
    }

    // ── Agent log ─────────────────────────────────────────────────────────────

    toggleLog(msg) {
        msg.logOpen = !msg.logOpen;
    }

    // ── n8n pipeline step polling ─────────────────────────────────────────────

    stepClass(idx) {
        if (idx < this.state.liveStepIdx) return "o-done";
        if (idx === this.state.liveStepIdx) return "o-active";
        return "o-pending";
    }

    _startPoll(pipelineKey) {
        this._stopPoll();
        this._pollHadResults = false;
        this._pollInterval = setInterval(async () => {
            try {
                const r = await rpc("/dojo/ai/steps", { pipeline_key: pipelineKey });
                if (r && r.steps && r.steps.length > 0) {
                    this._pollHadResults = true;
                    this.state.liveSteps = r.steps;
                    this.state.liveStepIdx = r.steps.length - 1;
                    this._stopFallback();
                    this._scrollThread();
                }
                if (r && r.done) this._stopPoll();
            } catch (_e) { /* ignore poll errors */ }
        }, 400);
    }

    _startFallback() {
        if (this._fallbackInterval) return;
        this._stopFallbackTimer();
        this.state.liveSteps = [...FALLBACK_STEPS];
        this.state.liveStepIdx = 0;
        let idx = 0;
        const max = FALLBACK_STEPS.length - 1;
        this._fallbackInterval = setInterval(() => {
            if (idx < max) { idx++; this.state.liveStepIdx = idx; }
        }, 900);
    }

    _stopPoll() {
        if (this._pollInterval) { clearInterval(this._pollInterval); this._pollInterval = null; }
    }

    _stopFallback() {
        this._stopFallbackTimer();
        if (this._fallbackInterval) { clearInterval(this._fallbackInterval); this._fallbackInterval = null; }
    }

    _stopFallbackTimer() {
        if (this._fallbackTimer) { clearTimeout(this._fallbackTimer); this._fallbackTimer = null; }
    }

    // ── ElevenLabs TTS ───────────────────────────────────────────────────────

    skipSpeaking() {
        if (this._currentAudio) {
            this._currentAudio.pause();
            this._currentAudio = null;
        }
        this.state.isSpeaking = false;
        this.state.statusLabel = "Hold to talk";
    }

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
        if (aiText) cw.push({ role: "assistant", text: aiText });
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

registry.category("actions").add("ai_assistant.walkie_talkie", DojoWalkieTalkie);
