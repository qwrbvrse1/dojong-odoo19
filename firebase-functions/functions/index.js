/**
 * Dojang Firebase Cloud Functions — Gen 2 (Node 22)
 *
 * Two HTTPS endpoints:
 *   POST /sendEmail  — send transactional email via Gmail + Nodemailer
 *   POST /sendPush   — send FCM push notification multicast
 *
 * Secrets setup (run once):
 *   firebase functions:secrets:set GMAIL_EMAIL
 *   firebase functions:secrets:set GMAIL_PASSWORD
 *   firebase functions:secrets:set APP_SECRET
 *
 * Deploy:
 *   firebase deploy --only functions
 */

"use strict";

const { onRequest } = require("firebase-functions/v2/https");
const { defineSecret } = require("firebase-functions/params");
const { logger } = require("firebase-functions");
const admin = require("firebase-admin");
const nodemailer = require("nodemailer");

admin.initializeApp();

// ── Secrets (Cloud Secret Manager) ────────────────────────────────────────
const GMAIL_EMAIL = defineSecret("GMAIL_EMAIL");
const GMAIL_PASSWORD = defineSecret("GMAIL_PASSWORD");
const APP_SECRET = defineSecret("APP_SECRET");

// ── Helpers ────────────────────────────────────────────────────────────────

function checkAuth(req, res, expectedSecret) {
    if (!expectedSecret) {
        logger.error("APP_SECRET not configured.");
        res.status(500).json({ error: "Server misconfiguration: APP_SECRET missing." });
        return false;
    }
    const authHeader = req.headers.authorization || "";
    const token = authHeader.startsWith("Bearer ") ? authHeader.slice(7) : null;
    if (!token || token !== expectedSecret) {
        res.status(403).json({ error: "Forbidden: invalid or missing Bearer token." });
        return false;
    }
    return true;
}

// ── sendEmail ──────────────────────────────────────────────────────────────

exports.sendEmail = onRequest(
    { secrets: [GMAIL_EMAIL, GMAIL_PASSWORD, APP_SECRET] },
    async (req, res) => {
        if (req.method !== "POST") {
            return res.status(405).json({ error: "Method not allowed." });
        }
        if (!checkAuth(req, res, APP_SECRET.value())) return;

        const { to, subject, html, from_name } = req.body;
        if (!to || !subject || !html) {
            return res.status(400).json({ error: "Missing required fields: to, subject, html." });
        }

        const gmailEmail = GMAIL_EMAIL.value();
        const gmailPassword = GMAIL_PASSWORD.value();

        const transporter = nodemailer.createTransport({
            service: "gmail",
            auth: { user: gmailEmail, pass: gmailPassword },
        });

        const recipients = Array.isArray(to) ? to.join(", ") : to;
        const fromAddress = from_name
            ? `"${from_name.replace(/"/g, "'")}" <${gmailEmail}>`
            : gmailEmail;

        try {
            const info = await transporter.sendMail({
                from: fromAddress, to: recipients, subject, html,
            });
            logger.info("Email sent:", info.messageId, "→", recipients);
            return res.status(200).json({ success: true, messageId: info.messageId });
        } catch (err) {
            logger.error("Failed to send email:", err.message);
            return res.status(500).json({ error: err.message });
        }
    }
);

// ── sendPush ───────────────────────────────────────────────────────────────

exports.sendPush = onRequest(
    { secrets: [APP_SECRET] },
    async (req, res) => {
        if (req.method !== "POST") {
            return res.status(405).json({ error: "Method not allowed." });
        }
        if (!checkAuth(req, res, APP_SECRET.value())) return;

        const { tokens, title, body, data } = req.body;
        if (!tokens || !Array.isArray(tokens) || tokens.length === 0) {
            return res.status(400).json({ error: "Missing or empty tokens array." });
        }
        if (!title || !body) {
            return res.status(400).json({ error: "Missing required fields: title, body." });
        }

        const BATCH_SIZE = 500;
        const unregisteredTokens = [];
        let successCount = 0;

        for (let i = 0; i < tokens.length; i += BATCH_SIZE) {
            const batch = tokens.slice(i, i + BATCH_SIZE);
            const message = {
                tokens,
                notification: { title, body },
                data: data
                    ? Object.fromEntries(Object.entries(data).map(([k, v]) => [k, String(v)]))
                    : {},
                webpush: {
                    notification: {
                        icon: "/dojo_base/static/src/img/dojo_logo.png",
                        requireInteraction: false,
                    },
                },
            };
            try {
                const response = await admin.messaging().sendEachForMulticast(message);
                successCount += response.successCount;
                response.responses.forEach((r, idx) => {
                    if (!r.success) {
                        const code = r.error && r.error.code;
                        if (
                            code === "messaging/registration-token-not-registered" ||
                            code === "messaging/invalid-registration-token"
                        ) {
                            unregisteredTokens.push(batch[idx]);
                        }
                        logger.warn("FCM send failed for token:", batch[idx], code);
                    }
                });
            } catch (err) {
                logger.error("FCM multicast error:", err.message);
                return res.status(500).json({ error: err.message });
            }
        }

        logger.info(`FCM push sent: ${successCount} success, ${unregisteredTokens.length} invalid tokens.`);
        return res.status(200).json({
            success: true,
            sent: successCount,
            unregistered_tokens: unregisteredTokens,
        });
    }
);
