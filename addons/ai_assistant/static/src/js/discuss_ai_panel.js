/** @odoo-module **/
/**
 * Dojo AI Assistant — Discuss side panel.
 *
 * Adds a slide-in AI chat panel to the Odoo Discuss view.
 * Users click the 🤖 tab to open the panel, type queries, and each AI
 * response is followed by a collapsible "agent log" showing:
 *   - Which agent handled the request
 *   - Intent type detected
 *   - Confidence score
 *   - Execution time
 *
 * Injects itself into mail.Discuss via template inheritance (discuss_ai_panel.xml).
 * No dedicated channel, no action log writes — purely a frontend chat layer.
 */

import { Component, useState, useRef, onPatched } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";
import { patch } from "@web/core/utils/patch";
import { Discuss } from "@mail/core/public_web/discuss_app/discuss_app";

// ── helpers ──────────────────────────────────────────────────────────────────

function formatConfidence(val) {
    if (val === null || val === undefined) return null;
    return Math.round(val * 100) + "%";
}

function formatMs(ms) {
    if (!ms) return null;
    return ms < 1000 ? ms + "ms" : (ms / 1000).toFixed(1) + "s";
}

let _msgIdCounter = 0;
function newMsg(fields) {
    return { id: ++_msgIdCounter, logOpen: false, ...fields };
}

// ── Agent step sequences ─────────────────────────────────────────────────────
// Minimal fallback shown while waiting when n8n has no step nodes configured.
const FALLBACK_STEPS = [
    { name: "Analyzing request",  detail: "Understanding what you're asking for..." },
    { name: "Routing to agent",   detail: "Finding the right specialist to handle this..." },
    { name: "Querying database",  detail: "Looking up the relevant records..." },
    { name: "Formatting results", detail: "Putting together your response..." },
];

// ── DiscussAiPanel ────────────────────────────────────────────────────────────

export class DiscussAiPanel extends Component {
    static template = "ai_assistant.DiscussAiPanel";

    setup() {
        this.state = useState({
            open: false,
            messages: [],
            input: "",
            loading: false,
            liveSteps: [],      // steps received from n8n via polling
            liveStepIdx: 0,     // index of the currently-active step
        });
        this._pollInterval = null;  // polling timer for /dojo/ai/steps
        this._fallbackInterval = null;  // fallback fake-advance timer
        this._chatSessionId = crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).slice(2);
        this.msgEndRef = useRef("msgEnd");
        onPatched(() => this._scrollToBottom());
    }

    toggle() {
        this.state.open = !this.state.open;
    }

    _scrollToBottom() {
        const el = this.msgEndRef.el;
        if (el) {
            el.scrollIntoView({ block: "end", behavior: "smooth" });
        }
    }

    _push(fields) {
        this.state.messages.push(newMsg(fields));
    }

    onInput(ev) {
        this.state.input = ev.target.value;
    }

    onKeydown(ev) {
        if (ev.key === "Enter" && !ev.shiftKey) {
            ev.preventDefault();
            this.sendMessage();
        }
    }

    toggleLog(msg) {
        msg.logOpen = !msg.logOpen;
    }

    /**
     * Returns the CSS class for a live step by its index.
     * Steps before liveStepIdx are "done"; liveStepIdx is "active" (spinner);
     * steps after are "pending".
     */
    stepClass(idx) {
        if (idx < this.state.liveStepIdx) return "o-done";
        if (idx === this.state.liveStepIdx) return "o-active";
        return "o-pending";
    }

    /** Start polling /dojo/ai/steps every 400ms while loading. */
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
                    // Cancel the delayed fallback and stop fake animation
                    this._stopFallback();
                }
                if (r && r.done) this._stopPoll();
            } catch (_e) {
                // ignore poll errors — fallback steps continue showing
            }
        }, 400);
    }

    /** Start a slow fallback step advance if n8n has no step nodes yet. */
    _startFallback() {
        if (this._fallbackInterval) return; // already running
        this._stopFallbackTimer();
        this.state.liveSteps = [...FALLBACK_STEPS];
        this.state.liveStepIdx = 0;
        let idx = 0;
        const max = FALLBACK_STEPS.length - 1;
        this._fallbackInterval = setInterval(() => {
            if (idx < max) {
                idx++;
                this.state.liveStepIdx = idx;
            }
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

    clearChat() {
        this.state.messages = [];
        this._chatSessionId = crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).slice(2);
    }

    async sendMessage() {
        const text = (this.state.input || "").trim();
        if (!text || this.state.loading) return;

        this.state.input = "";
        this.state.liveSteps = [];
        this.state.liveStepIdx = 0;
        this.state.loading = true;

        this._push({ type: "user", text });

        // Generate a short pipeline key the browser will use for polling
        // and Odoo will forward to n8n so it can push step callbacks.
        const pipelineKey = crypto.randomUUID().replace(/-/g, "").slice(0, 12);

        // Show a single placeholder while waiting for real n8n steps.
        // Only fall back to the generic animation if nothing arrives within 2.5s.
        this.state.liveSteps = [{ name: "Processing your request...", detail: "Connecting to AI pipeline..." }];
        this.state.liveStepIdx = 0;
        this._startPoll(pipelineKey);
        this._fallbackTimer = setTimeout(() => {
            if (!this._pollHadResults) this._startFallback();
        }, 12500);

        // Build conversation history for context window
        const history = this.state.messages
            .filter((m) => m.type === "user" || m.type === "ai")
            .slice(-20)
            .map((m) => ({ role: m.type === "user" ? "user" : "assistant", text: m.text }));

        try {
            const result = await rpc("/dojo/ai/text", {
                text,
                role: "instructor",
                conversation_history: history,
                chat_session_id: this._chatSessionId,
                pipeline_key: pipelineKey,
            });

            if (!result.success && result.state === "error") {
                this._push({ type: "system", text: "Error: " + (result.error || "Request failed.") });
                return;
            }

            // If n8n returned accumulated steps, use those as the final step list
            if (result.pipeline_steps && result.pipeline_steps.length > 0) {
                this.state.liveSteps = result.pipeline_steps;
                this.state.liveStepIdx = result.pipeline_steps.length - 1;
            }

            if (result.state === "pending_confirmation") {
                this._push({
                    type: "ai",
                    text: result.confirmation_prompt || "Please confirm this action.",
                    agent_name: result.agent_name || null,
                    intent_type: (result.intent || {}).intent_type || null,
                    confidence: formatConfidence((result.intent || {}).confidence),
                    execution_time_ms: null,
                    state: "pending_confirmation",
                    session_key: result.session_key,
                });
            } else if (result.state === "needs_clarification") {
                this._push({
                    type: "ai",
                    text: result.response || "Could you clarify?",
                    agent_name: result.agent_name || null,
                    intent_type: null,
                    confidence: null,
                    execution_time_ms: null,
                    state: "clarification",
                    session_key: null,
                });
            } else {
                this._push({
                    type: "ai",
                    text: result.response || (result.result || {}).message || "Done.",
                    agent_name: result.agent_name || null,
                    intent_type: (result.intent || {}).intent_type || null,
                    confidence: formatConfidence((result.intent || {}).confidence),
                    execution_time_ms: formatMs(result.execution_time_ms),
                    state: result.state,
                    session_key: null,
                });
            }
        } catch (e) {
            this._push({ type: "system", text: "Error: " + (e.message || "Request failed.") });
        } finally {
            this._stopPoll();
            this._stopFallback();
            this._stopFallbackTimer();
            this.state.loading = false;
        }
    }

    async confirmAction(msg, confirmed) {
        if (!msg.session_key || msg.state !== "pending_confirmation") return;
        this.state.loading = true;
        msg.state = confirmed ? "confirming" : "rejecting";

        try {
            if (!confirmed) {
                msg.state = "rejected";
                this._push({ type: "system", text: "Action cancelled." });
                return;
            }

            const result = await rpc("/dojo/ai/confirm", {
                session_key: msg.session_key,
                confirmed: true,
            });

            msg.state = "executed";

            const responseText =
                result.response ||
                (result.result || {}).message ||
                (result.success ? "Done." : result.error || "Failed.");

            this._push({
                type: "ai",
                text: responseText,
                agent_name: result.agent_name || msg.agent_name || null,
                intent_type: msg.intent_type,
                confidence: msg.confidence,
                execution_time_ms: formatMs(result.execution_time_ms),
                state: result.state || "executed",
                session_key: null,
            });
        } catch (e) {
            msg.state = "error";
            this._push({ type: "system", text: "Error: " + (e.message || "Execution failed.") });
        } finally {
            this._stopPoll();
            this._stopFallback();
            this.state.loading = false;
        }
    }
}

// ── Inject DiscussAiPanel into the Discuss component tree ─────────────────────
// Template injection is handled via t-inherit in discuss_ai_panel.xml.
// Here we register the component so Discuss's template can reference it.
Discuss.components = { ...Discuss.components, DiscussAiPanel };
