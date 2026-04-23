/**
 * PROTOTYPE — Dojo AI Walkie-Talkie: Elder Beta (standalone SPA)
 *
 * Served at /walkie/<token> when the instance is in elder_beta mode.
 *
 * Design goals:
 *   - One giant PTT button (~50% screen height)
 *   - Last AI response only — no scroll history
 *   - Verbal-only confirmations (no Yes/Cancel buttons)
 *   - "Say that again" replay after every successful TTS
 *   - Empty STT → verbal "I didn't catch that"
 *   - Elder system prompt via channel="elder" on every request
 *   - Auto-play TTS always on
 */

/* global owl */

(function () {
    "use strict";

    const { Component, useState, onWillUnmount, mount, xml } = owl;

    const YES_RE = /\b(yes|confirm|yeah|yep|sure|correct|ok|okay|affirmative|do it)\b/i;
    const NO_RE  = /\b(no|cancel|nope|stop|abort|never mind|nevermind|don'?t)\b/i;
    const DIDNT_CATCH = "I didn't catch that. Please try again.";

    const FALLBACK_STEPS = [
        { name: "Analyzing request",  detail: "Understanding what you're asking for..." },
        { name: "Routing to agent",   detail: "Finding the right specialist to handle this..." },
        { name: "Querying database",  detail: "Looking up the relevant records..." },
        { name: "Formatting results", detail: "Putting together your response..." },
    ];

    // ── JSON-RPC helper ───────────────────────────────────────────────────────

    async function jsonRpc(url, params) {
        const resp = await fetch(url, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ jsonrpc: "2.0", id: 1, method: "call", params: params || {} }),
            credentials: "same-origin",
        });
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();
        if (data.error) {
            const msg = (data.error.data && data.error.data.message) || data.error.message || "RPC error";
            throw new Error(msg);
        }
        return data.result;
    }

    // ── PIN Screen — oversized for elder users ────────────────────────────────

    class PinScreen extends Component {
        static template = xml`
            <div class="wt-pin-screen">
                <div class="wt-pin-card">
                    <div class="wt-pin-card__icon"><i class="fa fa-podcast"/></div>
                    <h2 class="wt-pin-card__title" t-out="props.name"/>
                    <p class="wt-pin-card__sub">AI Assistant</p>
                    <p class="wt-pin-card__label">Enter your PIN to continue</p>
                    <div class="wt-pin-card__input-row">
                        <input type="password" inputmode="numeric" maxlength="12"
                               placeholder="PIN" class="wt-pin-input"
                               t-att-value="state.pin"
                               t-on-input="onInput"
                               t-on-keydown="onKeydown"
                               t-att-disabled="state.loading"
                               autofocus="1"/>
                        <button class="wt-pin-btn"
                                t-att-disabled="state.loading or !state.pin"
                                t-on-click="submit">
                            <t t-if="state.loading"><i class="fa fa-spinner fa-spin"/></t>
                            <t t-else=""><i class="fa fa-arrow-right"/></t>
                        </button>
                    </div>
                    <p t-if="state.error" class="wt-pin-error" t-out="state.error"/>
                </div>
            </div>`;

        setup() { this.state = useState({ pin: "", loading: false, error: "" }); }

        onInput(ev) { this.state.pin = ev.target.value; this.state.error = ""; }
        onKeydown(ev) { if (ev.key === "Enter") this.submit(); }

        async submit() {
            if (!this.state.pin || this.state.loading) return;
            this.state.loading = true;
            this.state.error = "";
            try {
                const result = await jsonRpc(`/walkie/${window.WT_TOKEN}/auth`, { pin: this.state.pin });
                if (result && result.success) {
                    this.props.onAuth(this.state.pin);
                } else {
                    this.state.error = (result && result.error) || "Incorrect PIN.";
                }
            } catch (_) {
                this.state.error = "Could not connect. Please try again.";
            } finally {
                this.state.loading = false;
            }
        }
    }

    PinScreen.props = ["name", "onAuth"];

    // ── Elder Walkie component ────────────────────────────────────────────────

    class StandaloneWalkieElder extends Component {
        static template = xml`
            <div class="wt-elder-root">

                <!-- Minimal header -->
                <div class="wt-elder-header">
                    <i class="fa fa-podcast wt-elder-header__icon"/>
                    <span class="wt-elder-header__name" t-out="props.name"/>
                </div>

                <!-- Error banner -->
                <div t-if="state.error" class="wt-elder-error">
                    <i class="fa fa-exclamation-triangle"/> <t t-out="state.error"/>
                </div>

                <!-- Response area -->
                <div class="wt-elder-response">

                    <!-- Large status text -->
                    <p t-attf-class="wt-elder-status
                        #{state.isHolding    ? 'wt-elder-status--listening' : ''}
                        #{state.isSpeaking   ? 'wt-elder-status--speaking'  : ''}
                        #{state.isProcessing ? 'wt-elder-status--thinking'  : ''}">
                        <t t-if="state.isHolding">Listening…</t>
                        <t t-elif="state.isProcessing">Thinking…</t>
                        <t t-elif="state.isSpeaking">Speaking…</t>
                        <t t-elif="state.awaitingConfirmation">Waiting for your answer…</t>
                        <t t-else="">Ready</t>
                    </p>

                    <!-- Pipeline steps (shown while processing) -->
                    <div t-if="state.isProcessing" class="wt-elder-steps">
                        <t t-foreach="state.liveSteps" t-as="step" t-key="step_index">
                            <div class="wt-elder-step" t-att-class="stepClass(step_index)">
                                <span class="wt-elder-step__icon">
                                    <i t-if="stepClass(step_index) === 'o-done'" class="fa fa-check-circle"/>
                                    <i t-elif="stepClass(step_index) === 'o-active'" class="fa fa-circle-o-notch fa-spin"/>
                                    <i t-else="" class="fa fa-circle-o"/>
                                </span>
                                <span class="wt-elder-step__name" t-out="step.name or step"/>
                            </div>
                        </t>
                    </div>

                    <!-- Last AI response -->
                    <div t-if="state.lastResponse and !state.isProcessing"
                         class="wt-elder-last-response"
                         t-out="state.lastResponse"/>
                    <div t-elif="!state.isProcessing"
                         class="wt-elder-last-response wt-elder-last-response--empty">
                        Hold the big button below and speak
                    </div>

                    <!-- Verbal confirmation hint only — no buttons -->
                    <p t-if="state.awaitingConfirmation" class="wt-elder-confirm-hint">
                        Say "Yes" to confirm or "No" to cancel
                    </p>

                    <!-- Say that again -->
                    <button t-if="state.lastAudioB64 and !state.isSpeaking and !state.isHolding and !state.isProcessing"
                            class="wt-elder-replay"
                            t-on-click="replayLastAudio">
                        <i class="fa fa-repeat wt-elder-replay__icon"/>
                        Say that again
                    </button>

                </div>

                <!-- Giant PTT area -->
                <div class="wt-elder-ptt-area">

                    <button
                        t-attf-class="wt-elder-ptt
                            #{state.isHolding    ? 'wt-elder-ptt--recording'  : ''}
                            #{state.isProcessing ? 'wt-elder-ptt--processing' : ''}
                            #{state.isSpeaking   ? 'wt-elder-ptt--speaking'   : ''}"
                        t-att-disabled="state.isProcessing or state.isSpeaking"
                        t-on-mousedown="onPttDown"
                        t-on-mouseup="onPttUp"
                        t-on-mouseleave="onPttLeave"
                        t-on-touchstart="onPttDown"
                        t-on-touchend="onPttUp"
                        t-on-touchcancel="onPttLeave"
                        aria-label="Hold to talk">
                        <i t-attf-class="fa #{state.isSpeaking ? 'fa-volume-up' : state.isProcessing ? 'fa-spinner fa-spin' : 'fa-microphone'} wt-elder-ptt__icon"/>
                    </button>

                    <p class="wt-elder-ptt-label">
                        <t t-if="state.awaitingConfirmation">Say Yes or No</t>
                        <t t-else="">Hold to talk</t>
                    </p>

                </div>

            </div>`;

        setup() {
            this.state = useState({
                isHolding:    false,
                isProcessing: false,
                isSpeaking:   false,
                lastResponse:  "",
                lastAudioB64:  null,
                lastAudioMime: "audio/mpeg",
                awaitingConfirmation: false,
                sessionKey:           null,
                error:                null,
                liveSteps: [],
                liveStepIdx: 0,
            });

            this._mediaRecorder   = null;
            this._audioChunks     = [];
            this._stream          = null;
            this._currentAudio    = null;
            this._lastTranscribed = "";
            this._pollInterval    = null;
            this._fallbackInterval = null;
            this._fallbackTimer   = null;
            this._pollHadResults  = false;

            onWillUnmount(() => {
                this._cleanupRecording();
                if (this._currentAudio) { this._currentAudio.pause(); this._currentAudio = null; }
                this._stopPoll();
                this._stopFallback();
            });
        }

        // ── PTT ──────────────────────────────────────────────────────────────

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

        onPttLeave() { if (this.state.isHolding) this._stopRecordingCancel(); }

        async _startRecording() {
            if (!navigator.mediaDevices?.getUserMedia) {
                await this._speakAndShow("Sorry, microphone is not supported in this browser.");
                return;
            }
            try {
                this._stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            } catch (_) {
                await this._speakAndShow("Microphone access was denied. Please allow it in your browser.");
                return;
            }

            this._audioChunks = [];
            const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
                ? "audio/webm;codecs=opus" : "audio/webm";
            this._mediaRecorder = new MediaRecorder(this._stream, { mimeType });
            this._mediaRecorder.ondataavailable = (e) => {
                if (e.data && e.data.size > 0) this._audioChunks.push(e.data);
            };
            this._mediaRecorder.onstop = () => this._processRecording(mimeType);
            this._mediaRecorder.start(100);

            this.state.isHolding = true;
            this.state.error = null;
        }

        _stopRecording() {
            if (this._mediaRecorder && this._mediaRecorder.state !== "inactive") this._mediaRecorder.stop();
            this._releaseStream();
            this.state.isHolding = false;
        }

        _stopRecordingCancel() {
            this._cleanupRecording();
            this.state.isHolding = false;
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
            if (this._stream) { this._stream.getTracks().forEach(t => t.stop()); this._stream = null; }
        }

        // ── Pipeline step helpers ─────────────────────────────────────────────

        stepClass(idx) {
            if (idx < this.state.liveStepIdx) return "o-done";
            if (idx === this.state.liveStepIdx) return "o-active";
            return "o-pending";
        }

        _startPoll(pipelineKey) {
            this._pollHadResults = false;
            this._pollInterval = setInterval(async () => {
                try {
                    const data = await jsonRpc(`/walkie/${window.WT_TOKEN}/steps`, {
                        pin: this.props.pin,
                        pipeline_key: pipelineKey,
                    });
                    if (!data || !data.steps || !data.steps.length) return;
                    this._pollHadResults = true;
                    this._stopFallback();
                    this.state.liveSteps = data.steps;
                    this.state.liveStepIdx = data.done ? data.steps.length : Math.max(0, data.steps.length - 1);
                } catch (_) {}
            }, 400);
        }

        _startFallback() {
            let idx = 0;
            this.state.liveSteps = [FALLBACK_STEPS[0]];
            this.state.liveStepIdx = 0;
            this._fallbackInterval = setInterval(() => {
                if (idx < FALLBACK_STEPS.length - 1) {
                    idx++;
                    this.state.liveSteps = FALLBACK_STEPS.slice(0, idx + 1);
                    this.state.liveStepIdx = idx;
                }
            }, 2500);
        }

        _stopPoll() {
            if (this._pollInterval) { clearInterval(this._pollInterval); this._pollInterval = null; }
        }

        _stopFallback() {
            if (this._fallbackTimer) { clearTimeout(this._fallbackTimer); this._fallbackTimer = null; }
            if (this._fallbackInterval) { clearInterval(this._fallbackInterval); this._fallbackInterval = null; }
        }

        // ── Audio processing ──────────────────────────────────────────────────

        async _processRecording(mimeType) {
            if (!this._audioChunks.length) return;

            const blob = new Blob(this._audioChunks, { type: mimeType || "audio/webm" });
            this._audioChunks = [];
            const pipelineKey = crypto.randomUUID().replace(/-/g, "").slice(0, 12);
            this.state.isProcessing = true;
            this.state.liveSteps = [];
            this.state.liveStepIdx = 0;
            this._startPoll(pipelineKey);
            this._fallbackTimer = setTimeout(() => {
                if (!this._pollHadResults) this._startFallback();
            }, 12500);

            try {
                const formData = new FormData();
                formData.append("audio", blob, "walkie.webm");
                formData.append("pin", this.props.pin);
                formData.append("pipeline_key", pipelineKey);
                formData.append("channel", "elder");

                const resp = await fetch(`/walkie/${window.WT_TOKEN}/voice`, {
                    method: "POST", body: formData, credentials: "same-origin",
                });
                let result;
                try { result = await resp.json(); } catch (_) {}
                if (!resp.ok || !result) throw new Error((result && result.error) || `Server error ${resp.status}`);

                this._stopPoll();
                this._stopFallback();
                this.state.liveSteps = [];

                // Empty STT → verbal "didn't catch that"
                if (!result.transcribed || !result.transcribed.trim()) {
                    this.state.isProcessing = false;
                    await this._speakAndShow(DIDNT_CATCH);
                    return;
                }

                this._lastTranscribed = result.transcribed.trim();
                this.state.isProcessing = false;
                await this._handleResult(result);
            } catch (_) {
                this._stopPoll();
                this._stopFallback();
                this.state.liveSteps = [];
                this.state.isProcessing = false;
                await this._speakAndShow("Something went wrong. Please try again.");
            }
        }

        // ── Result handling ───────────────────────────────────────────────────

        async _handleResult(result) {
            if (!result || !result.success) {
                await this._speakAndShow((result && result.error) || "Something went wrong. Please try again.");
                return;
            }

            // Verbal yes/no when awaiting confirmation
            if (this.state.awaitingConfirmation && this._lastTranscribed) {
                if (YES_RE.test(this._lastTranscribed)) { await this._doConfirm(true);  return; }
                if (NO_RE.test(this._lastTranscribed))  { await this._doConfirm(false); return; }
                this.state.awaitingConfirmation = false;
                this.state.sessionKey = null;
            }

            if (result.state === "pending_confirmation") {
                const prompt = result.confirmation_prompt || result.response || "Please confirm.";
                this.state.awaitingConfirmation = true;
                this.state.sessionKey = result.session_key || null;
                await this._speakAndShow(prompt);
            } else if (result.state === "executed") {
                this.state.awaitingConfirmation = false;
                this.state.sessionKey = null;
                await this._speakAndShow(result.response || "Done!");
            } else if (result.state === "error") {
                await this._speakAndShow(result.error || "An error occurred. Please try again.");
            }
        }

        // ── Verbal confirmation ───────────────────────────────────────────────

        async _doConfirm(confirmed) {
            if (!this.state.sessionKey) return;
            this.state.isProcessing = true;
            const key = this.state.sessionKey;
            this.state.awaitingConfirmation = false;
            this.state.sessionKey = null;

            try {
                const result = await jsonRpc(`/walkie/${window.WT_TOKEN}/confirm`, {
                    pin: this.props.pin, session_key: key, confirmed,
                });
                this.state.isProcessing = false;
                if (!result || !result.success) {
                    await this._speakAndShow("Something went wrong. Please try again.");
                } else if (!confirmed) {
                    await this._speakAndShow("Got it, cancelled.");
                } else {
                    const r = result.result || {};
                    await this._speakAndShow(result.response || r.response || r.message || "Done!");
                }
            } catch (_) {
                this.state.isProcessing = false;
                await this._speakAndShow("Could not connect. Please try again.");
            }
        }

        // ── TTS + display ─────────────────────────────────────────────────────

        async _speakAndShow(text) {
            if (!text) return;
            this.state.lastResponse = text;
            this.state.lastAudioB64 = null;
            this.state.isSpeaking   = true;

            try {
                const result = await jsonRpc(`/walkie/${window.WT_TOKEN}/speak`, {
                    pin: this.props.pin, text,
                });
                if (!result || !result.success || !result.audio_b64) {
                    this.state.isSpeaking = false;
                    return;
                }
                this.state.lastAudioB64  = result.audio_b64;
                this.state.lastAudioMime = result.mime || "audio/mpeg";
                await this._playAudio(result.audio_b64, result.mime);
            } catch (_) {
                this.state.isSpeaking = false;
            }
        }

        async _playAudio(b64, mime) {
            if (this._currentAudio) { this._currentAudio.pause(); this._currentAudio = null; }
            const audio = new Audio(`data:${mime || "audio/mpeg"};base64,${b64}`);
            this._currentAudio = audio;
            const done = () => { this.state.isSpeaking = false; this._currentAudio = null; };
            audio.onended = done;
            audio.onerror = done;
            this.state.isSpeaking = true;
            await audio.play().catch(done);
        }

        async replayLastAudio() {
            if (!this.state.lastAudioB64 || this.state.isSpeaking) return;
            await this._playAudio(this.state.lastAudioB64, this.state.lastAudioMime);
        }
    }

    StandaloneWalkieElder.props = ["name", "pin"];

    // ── Root App ─────────────────────────────────────────────────────────────

    class WalkieElderApp extends Component {
        static template = xml`
            <div class="wt-app">
                <PinScreen t-if="!state.authed"
                           name="state.name"
                           onAuth.bind="onAuth"/>
                <StandaloneWalkieElder t-else=""
                                       name="state.name"
                                       pin="state.pin"/>
            </div>`;

        static components = { PinScreen, StandaloneWalkieElder };

        setup() {
            this.state = useState({
                authed: false,
                pin: "",
                name: window.WT_NAME || "AI Assistant",
            });
        }

        onAuth(pin) { this.state.pin = pin; this.state.authed = true; }
    }

    // ── Mount ─────────────────────────────────────────────────────────────────

    mount(WalkieElderApp, document.getElementById("wt-root"));

})();
