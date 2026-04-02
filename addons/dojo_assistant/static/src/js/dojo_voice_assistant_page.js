/** @odoo-module **/
/**
 * Dojo AI Voice Assistant — Full-page client action widget.
 *
 * Uses elevenlabs_connector for STT (via /dojo/ai/voice endpoint which
 * internally calls elevenlabs.service.transcribe_audio), but routes all
 * AI processing through the dojo_assistant intent engine.
 *
 * Endpoints:
 *   POST /dojo/ai/voice   — multipart audio → elevenlabs STT → dojo AI
 *   POST /dojo/ai/text    — jsonrpc text → dojo AI
 *   POST /dojo/ai/confirm — jsonrpc confirm/reject pending action
 *   POST /dojo/ai/history — jsonrpc recent action log
 */

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

class DojoVoiceAssistantPage extends Component {
    static template = "dojo_assistant.VoiceAssistantPage";

    setup() {
        this.state = useState({
            mode: "voice",              // "voice" | "text"
            isRecording: false,
            isProcessing: false,
            textInput: "",
            transcribedText: "",
            aiResponse: "",
            // Confirmation flow
            awaitingConfirmation: false,
            confirmationPrompt: "",
            sessionKey: null,
            undoAvailable: false,
            error: null,
            history: [],
            historyPage: 0,
            historyTotal: 0,
            historyPerPage: 10,
        });

        this._mediaRecorder = null;
        this._audioChunks = [];

        onWillStart(async () => {
            await this.loadHistory();
        });
    }

    // ── History (dojo_assistant action log) ───────────────────────────────

    async loadHistory() {
        const offset = this.state.historyPage * this.state.historyPerPage;
        try {
            const result = await rpc("/dojo/ai/history", {
                limit: this.state.historyPerPage,
                offset,
                user_only: true,
            });
            if (result && result.success) {
                this.state.history = (result.records || []).map(r => ({
                    ...r,
                    _badge: this._statusBadge(r),
                    _intent: this._formatIntent(r.intent_type),
                    _time: this._formatTime(r.timestamp),
                }));
                this.state.historyTotal = result.total || 0;
            }
        } catch (e) {
            console.warn("[DojoAI] Failed to load history:", e);
        }
    }

    get historyTotalPages() {
        return Math.max(1, Math.ceil(this.state.historyTotal / this.state.historyPerPage));
    }

    get hasNextPage() {
        return this.state.historyPage < this.historyTotalPages - 1;
    }

    get hasPrevPage() {
        return this.state.historyPage > 0;
    }

    async prevPage() {
        if (this.hasPrevPage) {
            this.state.historyPage--;
            await this.loadHistory();
        }
    }

    async nextPage() {
        if (this.hasNextPage) {
            this.state.historyPage++;
            await this.loadHistory();
        }
    }

    // ── Recording (same MediaRecorder approach) ──────────────────────────

    async toggleRecording() {
        if (this.state.isRecording) {
            this._stopRecording();
        } else {
            await this._startRecording();
        }
    }

    async _startRecording() {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            this.state.error = "Microphone is not supported in this browser.";
            return;
        }
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            this._audioChunks = [];

            const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
                ? "audio/webm;codecs=opus"
                : MediaRecorder.isTypeSupported("audio/webm")
                    ? "audio/webm"
                    : "";

            this._mediaRecorder = new MediaRecorder(stream, mimeType ? { mimeType } : {});

            this._mediaRecorder.ondataavailable = (e) => {
                if (e.data && e.data.size > 0) this._audioChunks.push(e.data);
            };

            this._mediaRecorder.onstop = () => {
                const blob = new Blob(this._audioChunks, { type: mimeType || "audio/webm" });
                stream.getTracks().forEach(t => t.stop());
                this._processAudio(blob);
            };

            this._mediaRecorder.start();
            this.state.isRecording = true;
            this.state.error = null;
            this._clearResult();
        } catch (e) {
            this.state.error = "Could not access microphone. Please check permissions.";
        }
    }

    _stopRecording() {
        if (this._mediaRecorder && this.state.isRecording) {
            this._mediaRecorder.stop();
            this.state.isRecording = false;
        }
    }

    // ── Audio → /dojo/ai/voice (multipart, elevenlabs STT → dojo AI) ────

    async _processAudio(blob) {
        this.state.isProcessing = true;
        this.state.error = null;
        this.state.transcribedText = "";
        this.state.aiResponse = "";

        try {
            const formData = new FormData();
            formData.append("audio", blob, "voice.webm");

            const resp = await fetch("/dojo/ai/voice", {
                method: "POST",
                body: formData,
                credentials: "same-origin",
            });

            if (!resp.ok) throw new Error("Server error " + resp.status);
            const result = await resp.json();
            this._handleResult(result, null);
        } catch (e) {
            this.state.error = "Failed to process audio. Please try again.";
            console.error("[DojoAI] Audio error:", e);
        } finally {
            this.state.isProcessing = false;
        }
    }

    // ── Text mode ────────────────────────────────────────────────────────

    async submitText() {
        const text = (this.state.textInput || "").trim();
        if (!text || this.state.isProcessing) return;

        this.state.isProcessing = true;
        this.state.error = null;
        this.state.aiResponse = "";
        this.state.awaitingConfirmation = false;
        const entered = text;
        this.state.textInput = "";

        try {
            const result = await rpc("/dojo/ai/text", { text: entered });
            this._handleResult(result, entered);
        } catch (e) {
            this.state.error = "Failed to process command. Please try again.";
            console.error("[DojoAI] Text error:", e);
        } finally {
            this.state.isProcessing = false;
        }
    }

    onTextKeydown(ev) {
        if (ev.key === "Enter" && !ev.shiftKey) {
            ev.preventDefault();
            this.submitText();
        }
    }

    // ── Result handling (supports two-phase confirmation) ────────────────

    _handleResult(result, fallbackText) {
        if (!result || !result.success) {
            this.state.error = (result && result.error) || "An unexpected error occurred.";
            return;
        }

        this.state.transcribedText = result.transcribed || fallbackText || "";

        if (result.state === "pending_confirmation") {
            this.state.awaitingConfirmation = true;
            this.state.sessionKey = result.session_key || null;
            this.state.confirmationPrompt = result.confirmation_prompt || result.response || "Please confirm this action.";
            this.state.aiResponse = "";
        } else if (result.state === "executed") {
            this.state.awaitingConfirmation = false;
            this.state.sessionKey = null;
            this.state.aiResponse = result.response || "Done!";
            this.state.undoAvailable = !!result.undo_available;
            this.loadHistory();
        } else if (result.state === "error") {
            this.state.error = result.error || "An error occurred.";
        }
    }

    // ── Confirm / Cancel ─────────────────────────────────────────────────

    async confirmAction() {
        await this._doConfirm(true);
    }

    async cancelAction() {
        await this._doConfirm(false);
    }

    async _doConfirm(confirmed) {
        if (!this.state.sessionKey || this.state.isProcessing) return;
        this.state.isProcessing = true;

        try {
            const result = await rpc("/dojo/ai/confirm", {
                session_key: this.state.sessionKey,
                confirmed,
            });

            this.state.awaitingConfirmation = false;
            this.state.sessionKey = null;

            if (!result || !result.success) {
                this.state.error = (result && result.error) || "Failed to process action.";
                return;
            }

            if (!confirmed) {
                this.state.aiResponse = "Action cancelled.";
            } else {
                const r = result.result || {};
                this.state.aiResponse = result.response || r.response || r.message || "Action completed!";
                this.state.undoAvailable = !!result.undo_available;
            }
            this.loadHistory();
        } catch (e) {
            this.state.error = "Failed to confirm action. Please try again.";
        } finally {
            this.state.isProcessing = false;
        }
    }

    // ── Undo ─────────────────────────────────────────────────────────────

    async requestUndo() {
        this.state.isProcessing = true;
        try {
            const result = await rpc("/dojo/ai/undo", {});
            if (result && result.success) {
                this.state.awaitingConfirmation = true;
                this.state.sessionKey = result.session_key;
                this.state.confirmationPrompt = result.confirmation_prompt || "Undo the last action?";
                this.state.aiResponse = "";
                this.state.undoAvailable = false;
            } else {
                this.state.error = (result && result.error) || "Nothing to undo.";
            }
        } catch (e) {
            this.state.error = "Undo request failed.";
        } finally {
            this.state.isProcessing = false;
        }
    }

    // ── Helpers ──────────────────────────────────────────────────────────

    _clearResult() {
        this.state.aiResponse = "";
        this.state.transcribedText = "";
        this.state.awaitingConfirmation = false;
        this.state.sessionKey = null;
        this.state.error = null;
        this.state.undoAvailable = false;
        this.state.confirmationPrompt = "";
    }

    clearConversation() {
        this._clearResult();
    }

    setMode(mode) {
        if (mode !== this.state.mode) {
            if (this.state.isRecording) this._stopRecording();
            this._clearResult();
            this.state.mode = mode;
        }
    }

    _statusBadge(rec) {
        if (rec.undone) return { text: "Undone", cls: "badge text-bg-secondary" };
        if (rec.execution_status === "error") return { text: "Error", cls: "badge text-bg-danger" };
        if (rec.confirmation_status === "rejected") return { text: "Cancelled", cls: "badge text-bg-warning" };
        if (rec.execution_status === "success") return { text: "Done", cls: "badge text-bg-success" };
        if (rec.confirmation_status === "pending") return { text: "Pending", cls: "badge text-bg-info" };
        return { text: rec.confirmation_status || "—", cls: "badge text-bg-secondary" };
    }

    _formatIntent(type) {
        if (!type) return "";
        return type.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
    }

    _formatTime(iso) {
        if (!iso) return "";
        try {
            return new Date(iso).toLocaleString([], {
                month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
            });
        } catch { return iso; }
    }
}

registry.category("actions").add("dojo_assistant.voice_assistant_page", DojoVoiceAssistantPage);
