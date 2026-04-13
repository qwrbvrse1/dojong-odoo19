/**
 * PROTOTYPE — Dojo AI Walkie-Talkie: Channel Beta (standalone SPA)
 *
 * Served at /walkie/<token> when the walkie-talkie instance is in channel_beta mode.
 * Extends the default standalone with a horizontal channel pill row.
 *
 * Authentication: PIN screen → token + PIN sent on every API call.
 * Channel: runtime UI state only — never persisted.
 */

/* global owl */

(function () {
    "use strict";

    const { Component, useState, useRef, onWillUnmount, mount, xml } = owl;

    // ── Channel definitions ───────────────────────────────────────────────────

    const CHANNELS = [
        { id: "all",        label: "All",          icon: "fa-th" },
        { id: "attendance", label: "Attendance",   icon: "fa-check-square-o" },
        { id: "members",    label: "Members",      icon: "fa-users" },
        { id: "enrollment", label: "Enrollment",   icon: "fa-calendar-plus-o" },
        { id: "belts",      label: "Belt & Ranks", icon: "fa-trophy" },
        { id: "billing",    label: "Billing",      icon: "fa-credit-card" },
        { id: "lookup",     label: "Lookup Only",  icon: "fa-search" },
    ];

    const CHANNEL_LABEL = Object.fromEntries(CHANNELS.map(c => [c.id, c.label]));

    // ── Constants ─────────────────────────────────────────────────────────────

    const YES_RE = /\b(yes|confirm|yeah|yep|sure|correct|ok|okay|affirmative|do it)\b/i;
    const NO_RE  = /\b(no|cancel|nope|stop|abort|never mind|nevermind|don'?t)\b/i;

    function nowLabel() {
        return new Date().toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
    }

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

    // ── PIN Screen (identical to default standalone) ──────────────────────────

    class PinScreen extends Component {
        static template = xml`
            <div class="wt-pin-screen">
                <div class="wt-pin-card">
                    <div class="wt-pin-card__icon"><i class="fa fa-podcast"/></div>
                    <h2 class="wt-pin-card__title" t-out="props.name"/>
                    <p class="wt-pin-card__sub">AI Walkie-Talkie — Channel Beta</p>
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

        setup() {
            this.state = useState({ pin: "", loading: false, error: "" });
        }

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

    // ── Channel Walkie component ──────────────────────────────────────────────

    class StandaloneWalkieChannel extends Component {
        static template = xml`
            <div class="dojo-wt-root">

                <!-- Header -->
                <div class="dojo-wt-header">
                    <div class="dojo-wt-header__logo"><i class="fa fa-podcast"/></div>
                    <div class="dojo-wt-header__title" t-out="props.name"/>
                    <div class="dojo-wt-header__actions">
                        <button class="dojo-wt-icon-btn" t-on-click="clearContext"
                                title="Clear conversation context">
                            <i class="fa fa-eraser"/>
                        </button>
                    </div>
                    <span t-attf-class="dojo-wt-status-pill dojo-wt-status-pill--#{state.isSpeaking ? 'speaking' : state.isHolding ? 'recording' : state.isProcessing ? 'processing' : 'idle'}">
                        ●&#160;<t t-if="state.isHolding">Listening</t><t t-elif="state.isProcessing">Processing</t><t t-elif="state.isSpeaking">Speaking</t><t t-else="">Ready</t>
                    </span>
                </div>

                <!-- Channel dial bar -->
                <div class="dojo-wt-dial">
                    <button class="dojo-wt-dial__nav" t-on-click="prevChannel" aria-label="Previous channel">
                        <i class="fa fa-chevron-left"/>
                    </button>
                    <div class="dojo-wt-dial__track">
                        <span class="dojo-wt-dial__neighbor dojo-wt-dial__neighbor--prev"
                              t-out="prevChannelLabel"/>
                        <button class="dojo-wt-dial__active" t-on-click="toggleDialOverlay"
                                title="Show all channels">
                            <i t-attf-class="fa #{activeChannelIcon} dojo-wt-dial__active-icon"/>
                            <span class="dojo-wt-dial__active-label" t-out="state.activeChannelLabel"/>
                            <i class="fa fa-chevron-down dojo-wt-dial__caret"/>
                        </button>
                        <span class="dojo-wt-dial__neighbor dojo-wt-dial__neighbor--next"
                              t-out="nextChannelLabel"/>
                    </div>
                    <button class="dojo-wt-dial__nav" t-on-click="nextChannel" aria-label="Next channel">
                        <i class="fa fa-chevron-right"/>
                    </button>
                </div>

                <!-- Channel picker overlay -->
                <div t-if="state.showDialOverlay" class="dojo-wt-dial-overlay" t-on-click="toggleDialOverlay">
                    <div class="dojo-wt-dial-overlay__panel" t-on-click.stop="">
                        <div class="dojo-wt-dial-overlay__title">Select Channel</div>
                        <div class="dojo-wt-dial-overlay__grid">
                            <t t-foreach="channels" t-as="ch" t-key="ch.id">
                                <button t-attf-class="dojo-wt-dial-tile #{state.activeChannel === ch.id ? 'active' : ''}"
                                        t-on-click="() => this.switchChannel(ch.id)">
                                    <i t-attf-class="fa #{ch.icon} dojo-wt-dial-tile__icon"/>
                                    <span class="dojo-wt-dial-tile__label" t-out="ch.label"/>
                                </button>
                            </t>
                        </div>
                    </div>
                </div>

                <!-- Error banner -->
                <div t-if="state.error" class="dojo-wt-error">
                    <i class="fa fa-exclamation-triangle me-2"/>
                    <t t-out="state.error"/>
                </div>

                <!-- Conversation thread -->
                <div class="dojo-wt-thread" t-ref="thread">

                    <div t-if="state.messages.length === 0" class="dojo-wt-empty">
                        <i class="fa fa-microphone dojo-wt-empty__icon"/>
                        <p class="dojo-wt-empty__hint">Hold the button and speak to the AI</p>
                        <p class="dojo-wt-empty__tips">Channel: <strong t-out="state.activeChannelLabel"/></p>
                    </div>

                    <t t-foreach="state.messages" t-as="msg" t-key="msg_index">
                        <div t-if="msg.role === 'divider'" class="dojo-wt-ch-divider">
                            <span t-out="msg.text"/>
                        </div>
                        <div t-elif="msg.role === 'user'" class="dojo-wt-bubble dojo-wt-bubble--user">
                            <div class="dojo-wt-bubble__body">
                                <i class="fa fa-microphone dojo-wt-bubble__icon"/>
                                <span t-out="msg.text"/>
                            </div>
                            <div class="dojo-wt-bubble__time" t-out="msg.time"/>
                        </div>
                        <div t-if="msg.role === 'ai'" class="dojo-wt-bubble dojo-wt-bubble--ai">
                            <div class="dojo-wt-bubble__body">
                                <i class="fa fa-android dojo-wt-bubble__icon"/>
                                <span t-out="msg.text"/>
                            </div>
                            <t t-if="msg.confirm and state.awaitingConfirmation and msg_index === state.messages.length - 1">
                                <div class="dojo-wt-confirm-btns">
                                    <button class="dojo-wt-btn dojo-wt-btn--confirm"
                                            t-on-click="confirmAction"
                                            t-att-disabled="state.isProcessing">
                                        <i class="fa fa-check"/> Yes, do it
                                    </button>
                                    <button class="dojo-wt-btn dojo-wt-btn--cancel"
                                            t-on-click="cancelAction"
                                            t-att-disabled="state.isProcessing">
                                        <i class="fa fa-times"/> Cancel
                                    </button>
                                </div>
                            </t>
                            <div class="dojo-wt-bubble__time" t-out="msg.time"/>
                        </div>
                    </t>

                    <div t-if="state.isProcessing" class="dojo-wt-thinking">
                        <span class="dojo-wt-thinking__dot"/>
                        <span class="dojo-wt-thinking__dot"/>
                        <span class="dojo-wt-thinking__dot"/>
                    </div>
                </div>

                <!-- PTT controls -->
                <div class="dojo-wt-controls">
                    <p class="dojo-wt-status-label" t-out="state.statusLabel"/>

                    <button
                        t-attf-class="dojo-wt-ptt
                            #{state.isHolding    ? 'dojo-wt-ptt--recording'  : ''}
                            #{state.isProcessing ? 'dojo-wt-ptt--processing' : ''}
                            #{state.isSpeaking   ? 'dojo-wt-ptt--speaking'   : ''}"
                        t-att-disabled="state.isProcessing or state.isSpeaking"
                        t-on-mousedown="onPttDown"
                        t-on-mouseup="onPttUp"
                        t-on-mouseleave="onPttLeave"
                        t-on-touchstart="onPttDown"
                        t-on-touchend="onPttUp"
                        t-on-touchcancel="onPttLeave"
                        aria-label="Push to talk">
                        <i t-attf-class="fa #{state.isSpeaking ? 'fa-volume-up' : state.isProcessing ? 'fa-spinner fa-spin' : 'fa-microphone'} dojo-wt-ptt__icon"/>
                    </button>

                    <p class="dojo-wt-hint">
                        <t t-if="state.awaitingConfirmation">
                            Say <strong>"Yes"</strong> or <strong>"No"</strong>, or use the buttons above
                        </t>
                        <t t-else="">Hold to speak · Release to send</t>
                    </p>
                </div>

            </div>`;

        setup() {
            this.threadRef = useRef("thread");
            this.channels  = CHANNELS;

            this.state = useState({
                isHolding: false,
                isProcessing: false,
                isSpeaking: false,
                messages: [],
                contextWindow: [],
                activeChannel: "all",
                activeChannelLabel: CHANNEL_LABEL["all"],
                showDialOverlay: false,
                awaitingConfirmation: false,
                confirmationPrompt: "",
                sessionKey: null,
                statusLabel: "Hold to talk",
                error: null,
            });

            this._contextWindowMax = (window.WT_CONFIG && window.WT_CONFIG.context_window_turns) || 10;
            this._mediaRecorder = null;
            this._audioChunks    = [];
            this._stream         = null;
            this._currentAudio   = null;
            this._lastTranscribed = "";

            onWillUnmount(() => {
                this._cleanupRecording();
                if (this._currentAudio) { this._currentAudio.pause(); this._currentAudio = null; }
            });
        }

        // ── Dial computed props ───────────────────────────────────────────────

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

        // ── Channel switching ─────────────────────────────────────────────────

        switchChannel(channelId) {
            if (channelId === this.state.activeChannel) return;
            this.state.activeChannel = channelId;
            this.state.activeChannelLabel = CHANNEL_LABEL[channelId] || channelId;
            this.state.contextWindow = [];
            this.state.awaitingConfirmation = false;
            this.state.sessionKey = null;
            this.state.showDialOverlay = false;
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
                ? "audio/webm;codecs=opus" : "audio/webm";
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
            if (this._mediaRecorder && this._mediaRecorder.state !== "inactive") this._mediaRecorder.stop();
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
            if (this._stream) { this._stream.getTracks().forEach(t => t.stop()); this._stream = null; }
        }

        // ── Audio → STT → AI ─────────────────────────────────────────────────

        async _processRecording(mimeType) {
            if (!this._audioChunks.length) { this.state.statusLabel = "Hold to talk"; return; }

            const blob = new Blob(this._audioChunks, { type: mimeType || "audio/webm" });
            this._audioChunks = [];
            this.state.isProcessing = true;
            this.state.statusLabel = "Thinking…";

            try {
                const formData = new FormData();
                formData.append("audio", blob, "walkie.webm");
                formData.append("pin", this.props.pin);
                formData.append("conversation_history", JSON.stringify(this.state.contextWindow));
                formData.append("channel", this.state.activeChannel);

                const resp = await fetch(`/walkie/${window.WT_TOKEN}/voice`, {
                    method: "POST", body: formData, credentials: "same-origin",
                });
                let result;
                try { result = await resp.json(); } catch (_) {}
                if (!resp.ok || !result) throw new Error((result && result.error) || `Server error ${resp.status}`);
                this._handleResult(result);
            } catch (e) {
                this._pushError(e.message || "Failed to process audio — please try again.");
            } finally {
                this.state.isProcessing = false;
            }
        }

        // ── Text input (channel-aware) ────────────────────────────────────────

        async sendText(text) {
            text = (text || "").trim();
            if (!text || this.state.isProcessing) return;
            this.state.isProcessing = true;
            this.state.statusLabel = "Thinking…";
            this._pushMsg("user", text);

            try {
                const result = await jsonRpc(`/walkie/${window.WT_TOKEN}/text`, {
                    pin: this.props.pin,
                    text,
                    conversation_history: this.state.contextWindow,
                    channel: this.state.activeChannel,
                });
                this._handleResult(result);
            } catch (e) {
                this._pushError(e.message || "Request failed.");
            } finally {
                this.state.isProcessing = false;
            }
        }

        // ── Result handling ───────────────────────────────────────────────────

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

        // ── Confirmation ──────────────────────────────────────────────────────

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
                const result = await jsonRpc(`/walkie/${window.WT_TOKEN}/confirm`, {
                    pin: this.props.pin, session_key: key, confirmed,
                });
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

        // ── TTS ───────────────────────────────────────────────────────────────

        async _speakResponse(text) {
            if (!text) return;
            this.state.isSpeaking = true;
            this.state.statusLabel = "Speaking…";
            try {
                const result = await jsonRpc(`/walkie/${window.WT_TOKEN}/speak`, {
                    pin: this.props.pin, text,
                });
                if (!result || !result.success) {
                    this.state.isSpeaking = false; this.state.statusLabel = "Hold to talk"; return;
                }
                const audio = new Audio("data:" + result.mime + ";base64," + result.audio_b64);
                if (this._currentAudio) this._currentAudio.pause();
                this._currentAudio = audio;
                const done = () => {
                    this.state.isSpeaking = false;
                    this.state.statusLabel = "Hold to talk";
                    this._currentAudio = null;
                };
                audio.onended = done; audio.onerror = done;
                await audio.play().catch(done);
            } catch (_) {
                this.state.isSpeaking = false; this.state.statusLabel = "Hold to talk";
            }
        }

        // ── Helpers ───────────────────────────────────────────────────────────

        _pushMsg(role, text, meta) {
            this.state.messages.push(Object.assign({ role, text, time: nowLabel() }, meta || {}));
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
            const maxItems = this._contextWindowMax * 2;
            if (cw.length > maxItems) cw.splice(0, cw.length - maxItems);
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

    StandaloneWalkieChannel.props = ["name", "pin"];

    // ── Root App ─────────────────────────────────────────────────────────────

    class WalkieChannelApp extends Component {
        static template = xml`
            <div class="wt-app">
                <PinScreen t-if="!state.authed"
                           name="state.name"
                           onAuth.bind="onAuth"/>
                <StandaloneWalkieChannel t-else=""
                                         name="state.name"
                                         pin="state.pin"/>
            </div>`;

        static components = { PinScreen, StandaloneWalkieChannel };

        setup() {
            this.state = useState({
                authed: false,
                pin: "",
                name: window.WT_NAME || "AI Walkie-Talkie",
            });
        }

        onAuth(pin) { this.state.pin = pin; this.state.authed = true; }
    }

    // ── Mount ─────────────────────────────────────────────────────────────────

    mount(WalkieChannelApp, document.getElementById("wt-root"));

})();
