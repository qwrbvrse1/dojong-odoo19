# Dojang Firebase Cloud Functions

Handles email delivery (Gmail/Nodemailer) and FCM push notifications for the Odoo `dojo_firebase` module.

## Setup

### 1. Prerequisites
- Node.js 22+
- Firebase CLI: `npm install -g firebase-tools`
- Firebase project created at [console.firebase.google.com](https://console.firebase.google.com)
- Gmail account with **2-Step Verification enabled** and an **App Password** generated

### 2. Set credentials
```bash
cd firebase-functions

# Replace with your values
firebase functions:config:set \
  gmail.email="your@gmail.com" \
  gmail.password="YOUR_APP_PASSWORD" \
  app.secret="STRONG_RANDOM_SECRET_32_CHARS_MIN"
```

> `app.secret` is a shared secret between Firebase CF and Odoo. Generate with:
> `openssl rand -base64 32`

### 3. Update project ID
Edit `.firebaserc` and replace `YOUR_FIREBASE_PROJECT_ID` with your actual Firebase project ID.

### 4. Install deps and deploy
```bash
cd functions
npm install
cd ..
firebase deploy --only functions
```

### 5. Copy the base URL into Odoo
After deploying, Firebase shows the function URLs, e.g.:
```
https://us-central1-YOUR_PROJECT_ID.cloudfunctions.net/sendEmail
https://us-central1-YOUR_PROJECT_ID.cloudfunctions.net/sendPush
```

In Odoo: **Settings → Firebase Integration → Cloud Functions Base URL**
Paste: `https://us-central1-YOUR_PROJECT_ID.cloudfunctions.net`
(without a trailing slash — Odoo appends `/sendEmail` and `/sendPush`)

## Endpoints

### `POST /sendEmail`
```json
{
  "to": "member@example.com",
  "subject": "Your invoice is ready",
  "html": "<p>Hello...</p>",
  "from_name": "Dojang"
}
```
Bearer token required: `Authorization: Bearer <app.secret>`

### `POST /sendPush`
```json
{
  "tokens": ["FCM_TOKEN_1", "FCM_TOKEN_2"],
  "title": "Class tomorrow!",
  "body": "Brazilian Jiu-Jitsu — 6:00 PM",
  "data": {"type": "class_reminder", "session_id": "42"}
}
```
Returns `unregistered_tokens` array — Odoo automatically deactivates those tokens.

## Local testing
```bash
firebase emulators:start --only functions
# Then hit http://localhost:5001/YOUR_PROJECT_ID/us-central1/sendEmail
```
