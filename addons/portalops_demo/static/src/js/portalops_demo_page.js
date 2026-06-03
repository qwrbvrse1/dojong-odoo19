/** @odoo-module **/

function requestJson(url, { method = "GET", payload } = {}) {
    return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.open(method, url, true);
        xhr.responseType = "json";
        xhr.withCredentials = true;
        xhr.setRequestHeader("Content-Type", "application/json");
        xhr.onload = () => {
            const response = xhr.response ?? JSON.parse(xhr.responseText || "{}");
            const body =
                response && typeof response === "object" && "result" in response ? response.result : response;
            if (xhr.status >= 200 && xhr.status < 300) {
                resolve(body);
                return;
            }
            reject(new Error(body?.error || `Request failed with status ${xhr.status}.`));
        };
        xhr.onerror = () => reject(new Error("Network request failed."));
        xhr.send(payload ? JSON.stringify(payload) : null);
    });
}

function postJson(url, payload) {
    return requestJson(url, { method: "POST", payload: payload || {} });
}

function escapeHtml(text) {
    return (text || "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;");
}

const ROLE_DEMOS = {
    doctor: {
        label: "Doctor",
        greeting: "Doctor, how may I be of service?",
        hint: "Ask: “How many patients do I have left today?”",
        fallback: "For this demo, I can help with today's remaining patient schedule.",
        intents: [
            {
                patterns: [
                    "how many patients do i have left today",
                    "how many patients do i have left",
                    "how many patients are left today",
                    "how many patients are left",
                    "patients left today",
                    "patients left",
                    "how many appointments do i have left today",
                    "how many appointments do i have left",
                    "how many appointments are left today",
                    "how many appointments are left",
                    "what appointments do i have left today",
                    "what appointments do i have left",
                    "what do i have left today",
                    "how many do i have left today",
                ],
                answer: "5 appointments are scheduled for this afternoon.",
            },
        ],
    },
    nurse: {
        label: "Nurse",
        greeting: "Nurse, how may I be of service?",
        hint: "Ask: “When is the next patient appointment?”",
        fallback: "For this demo, I can help with the next patient appointment time.",
        intents: [
            {
                patterns: ["when is the next patient appointment", "next patient appointment", "what time is the next patient appointment"],
                answer: "3:00 PM.",
            },
        ],
    },
    patient: {
        label: "Patient",
        greeting: "Atlanta Midtown, how may I be of service?",
        hint: "Ask: “What time is my appointment?” then “Do I need to fast before my blood test?”",
        fallback: "For this demo, I can help with appointment timing and blood test preparation.",
        intents: [
            {
                patterns: ["what time is my appointment", "when is my appointment", "appointment time"],
                answer: "3:00 PM.",
            },
            {
                patterns: ["do i need to fast before my blood test", "do i need to fast", "fast before my blood test"],
                answer: "Yes.",
            },
        ],
    },
};

const SpeechRecognitionClass = window.SpeechRecognition || window.webkitSpeechRecognition;

class PortalOpsVoicePanel {
    constructor(root) {
        this.root = root;
        this.slug = root.dataset.slug;
        this.sessionKey = null;
        this.currentRole = "doctor";
        this.latestAgentTranscript = "";
        this.latestCallerTranscript = "";
        this.history = [];
        this.recognition = null;
        this.demoActive = false;

        this.statusNode = document.getElementById("portalops-voice-status");
        this.statusDetailNode = document.getElementById("portalops-voice-status-detail");
        this.stateChipNode = document.getElementById("portalops-voice-state-chip");
        this.previewNode = document.getElementById("portalops-voice-transcript-preview");
        this.completionNode = document.getElementById("portalops-voice-completion");
        this.selectedRoleNode = document.getElementById("portalops-selected-role");
        this.hintNode = document.getElementById("portalops-voice-hint");
        this.hintButtonNode = document.getElementById("portalops-voice-hint-button");
        this.topHintButtonNode = document.getElementById("portalops-voice-hint-button-top");
        this.stopButtonNode = this.root.querySelector('[data-portalops-action="stop"]');
        this.compactPanelNode = root;

        this.stopButtonNode?.addEventListener("click", () => this.stop());
        this.hintButtonNode?.addEventListener("click", () => {
            this.hintNode?.classList.toggle("is-hidden");
        });
        this.topHintButtonNode?.addEventListener("click", () => {
            document.getElementById("portalops-voice-hint-top")?.classList.toggle("is-hidden");
        });

        this.updateRoleUi();
    }

    setStatus(state, detail) {
        if (this.statusNode) this.statusNode.textContent = state;
        if (this.stateChipNode) this.stateChipNode.textContent = state;
        if (this.statusDetailNode) this.statusDetailNode.textContent = detail;
    }

    setRole(role) {
        if (!ROLE_DEMOS[role]) return;
        this.currentRole = role;
        this.compactPanelNode?.classList.remove("is-hidden");
        this.updateRoleUi();
        this.latestAgentTranscript = "";
        this.latestCallerTranscript = "";
        this.history = [];
        if (this.completionNode) {
            this.completionNode.textContent = "Waiting for session start.";
        }
        this.hintNode?.classList.add("is-hidden");
        this.setStatus("ready", `${ROLE_DEMOS[role].label} role selected.`);
    }

    async activateRole(role) {
        if (!ROLE_DEMOS[role]) return;
        const roleChanged = this.currentRole !== role;
        if (this.demoActive) {
            await this.stop();
        }
        if (roleChanged || !this.sessionKey) {
            this.setRole(role);
        }
        await this.start();
    }

    updateRoleUi() {
        const roleConfig = ROLE_DEMOS[this.currentRole];
        if (this.selectedRoleNode) {
            this.selectedRoleNode.textContent = roleConfig.label;
        }
        if (this.hintNode) {
            this.hintNode.textContent = roleConfig.hint;
        }
    }

    async start() {
        if (this.demoActive) {
            return;
        }
        this.setStatus("connecting", `Connecting ${ROLE_DEMOS[this.currentRole].label.toLowerCase()} voice demo...`);
        if (!SpeechRecognitionClass) {
            this.setStatus("failed", "This browser does not support microphone speech recognition for the demo.");
            return;
        }
        const data = await postJson(`/portalops/api/location/${this.slug}/voice-session/start`, {
            perspective: this.currentRole,
            is_low_vision_mode: false,
        });
        if (!data.success) {
            this.setStatus("failed", data.error || "Could not start voice session.");
            return;
        }
        this.sessionKey = data.session.session_key;
        this.demoActive = true;
        this.latestAgentTranscript = "";
        this.latestCallerTranscript = "";
        this.history = [];
        this.stopButtonNode?.classList.remove("is-hidden");
        this.setStatus("active", `${ROLE_DEMOS[this.currentRole].label} demo is starting.`);
        if (this.completionNode) {
            this.completionNode.textContent = "Speaking greeting and preparing microphone...";
        }
        await this.speakAgent(ROLE_DEMOS[this.currentRole].greeting, true);
    }

    async stop() {
        this.demoActive = false;
        if (this.recognition) {
            this.recognition.onend = null;
            this.recognition.onerror = null;
            this.recognition.onresult = null;
            this.recognition.stop();
            this.recognition = null;
        }
        window.speechSynthesis.cancel();
        if (!this.sessionKey) {
            this.stopButtonNode?.classList.add("is-hidden");
            this.setStatus("stopped", "Voice demo stopped.");
            return;
        }
        const transcriptText = this.history.map((turn) => `${turn.speaker}: ${turn.text}`).join("\n");
        if (transcriptText) {
            await postJson(`/portalops/api/location/${this.slug}/voice-session/${this.sessionKey}/demo-complete`, {
                transcript: transcriptText,
                summary: `${ROLE_DEMOS[this.currentRole].label} scripted demo completed.`,
            });
        } else {
            await postJson(`/portalops/api/location/${this.slug}/voice-session/stop`, {
                session_key: this.sessionKey,
            });
        }
        this.setStatus("stopped", "Voice demo stopped.");
        this.stopButtonNode?.classList.add("is-hidden");
        if (this.completionNode) {
            this.completionNode.textContent = "Demo stopped. You can restart the selected role at any time.";
        }
        this.sessionKey = null;
    }

    async speakAgent(text, listenAfter = false) {
        this.latestAgentTranscript = text;
        this.appendHistory("Agent", text);
        await this.syncPreviewToServer();
        this.setStatus("active", "Agent is speaking.");
        await new Promise((resolve) => {
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.rate = 1;
            utterance.pitch = 1;
            utterance.onend = () => resolve();
            utterance.onerror = () => resolve();
            window.speechSynthesis.cancel();
            window.speechSynthesis.speak(utterance);
        });
        if (listenAfter && this.demoActive) {
            this.startListening();
        }
    }

    startListening() {
        if (!this.demoActive || !SpeechRecognitionClass) {
            return;
        }
        this.setStatus("listening", `Listening for the ${ROLE_DEMOS[this.currentRole].label.toLowerCase()} question.`);
        if (this.completionNode) {
            this.completionNode.textContent = "Microphone live. Ask the role question now.";
        }
        const recognition = new SpeechRecognitionClass();
        this.recognition = recognition;
        recognition.lang = "en-US";
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.maxAlternatives = 1;
        recognition.onresult = async (event) => {
            const transcript = Array.from(event.results)
                .map((result) => result[0]?.transcript || "")
                .join(" ")
                .trim();
            this.recognition = null;
            if (!transcript) {
                this.setStatus("active", "No speech detected. Please try the role question again.");
                return;
            }
            await this.handleCallerSpeech(transcript);
        };
        recognition.onerror = () => {
            this.recognition = null;
            if (this.demoActive) {
                this.setStatus("failed", "Microphone recognition failed. Please try Start Voice again.");
            }
        };
        recognition.onend = () => {
            this.recognition = null;
        };
        recognition.start();
    }

    async handleCallerSpeech(text) {
        const normalizedText = this.normalizeText(text);
        this.latestCallerTranscript = text;
        this.appendHistory("Caller", text);
        await this.syncPreviewToServer();
        const response = this.resolveScriptedAnswer(normalizedText);
        if (this.completionNode) {
            this.completionNode.textContent = `Answered for ${ROLE_DEMOS[this.currentRole].label}. You can ask another supported question or press Stop Voice.`;
        }
        await this.speakAgent(response, true);
    }

    resolveScriptedAnswer(normalizedText) {
        const roleConfig = ROLE_DEMOS[this.currentRole];
        for (const intent of roleConfig.intents) {
            const matched = intent.patterns.some((pattern) => normalizedText.includes(pattern));
            if (matched) {
                return intent.answer;
            }
        }
        return roleConfig.fallback;
    }

    normalizeText(text) {
        return String(text || "")
            .toLowerCase()
            .replace(/[^a-z0-9\s]/g, " ")
            .replace(/\s+/g, " ")
            .trim();
    }

    appendHistory(speaker, text) {
        if (!text) return;
        this.history.push({ speaker, text });
    }

    async syncPreviewToServer() {
        if (!this.sessionKey) return;
        const transcriptText = this.history.map((turn) => `${turn.speaker}: ${turn.text}`).join("\n");
        await postJson(`/portalops/api/location/${this.slug}/voice-session/${this.sessionKey}/preview`, {
            preview_transcript: transcriptText,
        });
    }
}

class PortalOpsMapRoleSelector {
    constructor(root, voicePanel) {
        this.root = root;
        this.voicePanel = voicePanel;
        this.markerButton = document.querySelector('[data-portalops-map-marker="1"]');
        this.placeCard = document.querySelector('[data-portalops-place-card="1"]');
        this.closeButton = document.querySelector('[data-portalops-close-card="1"]');

        root.querySelectorAll("[data-portalops-role]").forEach((button) => {
            button.addEventListener("click", () => this.activateRole(button.dataset.portalopsRole));
        });
        this.markerButton?.addEventListener("click", () => this.openPlaceCard());
        this.closeButton?.addEventListener("click", () => this.closePlaceCard());
    }

    openPlaceCard() {
        this.placeCard?.classList.remove("is-hidden");
        this.placeCard?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }

    closePlaceCard() {
        this.placeCard?.classList.add("is-hidden");
    }

    async activateRole(role) {
        this.root.querySelectorAll("[data-portalops-role]").forEach((button) => {
            button.classList.toggle("is-active", button.dataset.portalopsRole === role);
        });
        this.openPlaceCard();
        await this.voicePanel.activateRole(role);
    }
}

function initPortalOpsDemoPage() {
    const root = document.querySelector('[data-portalops-voice-root="1"]');
    if (!root || root.dataset.portalopsInitialized === "1") {
        return;
    }
    root.dataset.portalopsInitialized = "1";
    const voicePanel = new PortalOpsVoicePanel(root);
    document.querySelectorAll('[data-portalops-role-root="1"]').forEach((roleRoot) => {
        new PortalOpsMapRoleSelector(roleRoot, voicePanel);
    });
}

if (document.readyState === "loading") {
    window.addEventListener("DOMContentLoaded", initPortalOpsDemoPage, { once: true });
} else {
    initPortalOpsDemoPage();
}
