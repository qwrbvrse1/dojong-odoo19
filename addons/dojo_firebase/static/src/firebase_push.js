/**
 * Dojang Firebase Push — Portal Client
 *
 * Loaded in the member portal head when firebase.push_enabled = True.
 * Reads window.__FIREBASE_CONFIG__ injected by portal_push_inject.xml.
 *
 * Flow:
 *   1. Init Firebase app from server-injected config
 *   2. Register /firebase-messaging-sw.js as service worker
 *   3. Request Notification permission (if not already granted/denied)
 *   4. Get FCM token using VAPID key
 *   5. POST token to /dojo/firebase/register-token (JSON-RPC, auth=user)
 */
(function () {
    'use strict';

    var config = window.__FIREBASE_CONFIG__;
    if (!config || !config.apiKey || !config.projectId) {
        // Push is disabled or partially configured — bail silently
        return;
    }

    // Firebase compat SDK is loaded via CDN <script> tags in portal_push_inject.xml
    // before this file, so `firebase` is available as a global.
    if (typeof firebase === 'undefined') {
        console.warn('Dojang Firebase: firebase SDK not loaded.');
        return;
    }

    // Avoid double-init if page is revisited (SPA-style navigation)
    if (!firebase.apps.length) {
        firebase.initializeApp({
            apiKey: config.apiKey,
            authDomain: config.authDomain || (config.projectId + '.firebaseapp.com'),
            projectId: config.projectId,
            messagingSenderId: config.messagingSenderId,
            appId: config.appId,
        });
    }

    // Notification API must be available (not available in Firefox in private mode)
    if (!('Notification' in window) || !('serviceWorker' in navigator)) {
        return;
    }

    // If the user has explicitly blocked notifications, don't prompt again
    if (Notification.permission === 'denied') {
        return;
    }

    var messaging = firebase.messaging();

    navigator.serviceWorker
        .register('/firebase-messaging-sw.js', { scope: '/' })
        .then(function (registration) {
            return Notification.requestPermission().then(function (permission) {
                if (permission !== 'granted') {
                    return null;
                }
                return messaging.getToken({
                    vapidKey: config.vapidKey,
                    serviceWorkerRegistration: registration,
                });
            });
        })
        .then(function (token) {
            if (!token) return;
            return fetch('/dojo/firebase/register-token', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest',
                },
                credentials: 'same-origin',
                body: JSON.stringify({
                    jsonrpc: '2.0',
                    method: 'call',
                    id: Math.floor(Math.random() * 100000),
                    params: { token: token, device_type: 'pwa' },
                }),
            });
        })
        .then(function (response) {
            return response && response.json();
        })
        .then(function (data) {
            if (data && data.result && data.result.success) {
                console.info('Dojang: FCM push notifications enabled.');
            }
        })
        .catch(function (err) {
            // Non-fatal — push is a convenience feature
            console.warn('Dojang Firebase: push setup failed:', err);
        });
})();
