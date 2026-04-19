/** @odoo-module **/
/**
 * PROTOTYPE — Dojo AI Walkie-Talkie: Elder Beta (backend OWL component)
 *
 * Design goals:
 *   - One giant PTT button (~50% screen height) — impossible to miss
 *   - Last AI response displayed large — no scroll history
 *   - Verbal-only confirmations — no Yes/Cancel buttons rendered
 *   - "Say that again" replay button after every successful TTS
 *   - Empty STT → AI verbal "didn't catch that" instead of error banner
 *   - Elder system prompt always injected via channel="elder"
 *   - Auto-play TTS always on
 *
 * Registered as: ai_assistant.walkie_elder
 */

import { Component, useState, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

const YES_RE = /\b(yes|confirm|yeah|yep|sure|correct|ok|okay|affirmative|do it)\b/i;
const NO_RE  = /\b(no|cancel|nope|stop|abort|never mind|nevermind|don'?t)\b/i;

const DIDNT_CATCH = "I didn't catch that. Please try again.";

class DojoWalkieElder extends Component {
    static template = "ai_assistant.WalkieElder";

    setup() {
        const ctx = this.props.action?.context || {};
        this.walkieId   = ctx.walkie_id   || null;
        this.walkieName = ctx.walkie_name || "AI Walkie-Talkie";

        this.state = useState({
            isHolding:    false,
            isProcessing: false,
            isSpeaking:   false,
            walkieName:   this.walkieName,
            // Elder mode shows only the last response, not a full history
            lastResponse:  "",
            // Replay support
            lastAudioB64:  null,
            lastAudioMime: "audio/mpeg",
            // Confirmation
            awaitingConfirmation: false,
            sessionKey:           null,
            error:                null,
        });

        this._mediaRecorder    = null;
        this._audioChunks      = [];
        this._stream           = null;
        this._currentAudio     = null;
        this._lastTranscribed  = "";

        onWillUnmount(() => {
            this._cleanupRecording();
            if (this._currentAudio) { this._currentAudio.pause(); this._currentAudio = null; }
        });
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

    onPttLeave() {
        if (this.state.isHolding) this._stopRecordingCancel();
    }

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
        if (this._mediaRecorder && this._mediaRecorder.state !== "inactive") {
            this._mediaRecorder.stop();
        }
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

    // ── Audio processing ─────────────────────────────────────────────────────

    async _processRecording(mimeType) {
        if (!this._audioChunks.length) return;

        const blob = new Blob(this._audioChunks, { type: mimeType || "audio/webm" });
        this._audioChunks = [];
        this.state.isProcessing = true;

        try {
            const formData = new FormData();
            formData.append("audio", blob, "walkie.webm");
            // Elder mode: always inject elder system prompt via channel param
            formData.append("channel", "elder");
            if (this.walkieId) formData.append("walkie_id", this.walkieId);

            const resp = await fetch("/dojo/ai/voice", {
                method: "POST", body: formData, credentials: "same-origin",
            });
            let result;
            try { result = await resp.json(); } catch (_) {}
            if (!resp.ok || !result) throw new Error((result?.error) || `Server error ${resp.status}`);

            // Empty STT → verbal "didn't catch that" instead of error banner
            if (!result.transcribed || !result.transcribed.trim()) {
                this.state.isProcessing = false;
                await this._speakAndShow(DIDNT_CATCH);
                return;
            }

            this._lastTranscribed = result.transcribed.trim();
            await this._handleResult(result);
        } catch (e) {
            this.state.isProcessing = false;
            await this._speakAndShow("Something went wrong. Please try again.");
        }
    }

    // ── Result handling ───────────────────────────────────────────────────────

    async _handleResult(result) {
        this.state.isProcessing = false;

        if (!result?.success) {
            await this._speakAndShow((result?.error) || "Something went wrong. Please try again.");
            return;
        }

        // Voice yes/no detection when awaiting confirmation
        if (this.state.awaitingConfirmation && this._lastTranscribed) {
            if (YES_RE.test(this._lastTranscribed)) { await this._doConfirm(true);  return; }
            if (NO_RE.test(this._lastTranscribed))  { await this._doConfirm(false); return; }
            // Not yes/no — override the pending confirmation with new query
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

    // ── Verbal confirmation ───────────────────────────────────────────────────

    async _doConfirm(confirmed) {
        if (!this.state.sessionKey) return;
        this.state.isProcessing = true;
        const key = this.state.sessionKey;
        this.state.awaitingConfirmation = false;
        this.state.sessionKey = null;

        try {
            const result = await rpc("/dojo/ai/confirm", { session_key: key, confirmed });
            this.state.isProcessing = false;
            if (!result?.success) {
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

    // ── TTS + display ─────────────────────────────────────────────────────────

    /**
     * Set the last response text AND auto-play TTS.
     * Stores audio b64 for the "Say that again" replay button.
     */
    async _speakAndShow(text) {
        if (!text) return;
        this.state.lastResponse  = text;
        this.state.lastAudioB64  = null;   // clear while fetching
        this.state.isSpeaking    = true;

        try {
            const result = await rpc("/dojo/ai/speak", { text });
            if (!result?.success || !result.audio_b64) {
                this.state.isSpeaking = false;
                return;
            }
            // Store for replay
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
        const done = () => {
            this.state.isSpeaking = false;
            this._currentAudio = null;
        };
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

registry.category("actions").add("ai_assistant.walkie_elder", DojoWalkieElder);
