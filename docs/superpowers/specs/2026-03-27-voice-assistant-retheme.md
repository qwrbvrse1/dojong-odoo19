# Voice Assistant Retheme — Design Spec
**Date:** 2026-03-27
**Module:** `dojo_instructor_dashboard`
**Files in scope:** `static/src/xml/voice_assistant.xml`, `static/src/css/instructor_dashboard.css`

---

## Goal

Align the floating AI voice assistant bubble and panel header with the admin dashboard design language: swap Google Blue for the warm red primary (`#b41e16`) and replace the generic robot icon with the dojo logo image.

## Constraints

1. Panel body (white background, message bubbles, input bar structure) — unchanged
2. No changes to `voice_assistant.js` logic
3. Assistant message bubbles stay gray (`#f1f3f4`) — only user bubbles + interactive elements get the red primary
4. Logo image must sit cleanly inside the existing circular avatar container

---

## Changes

### `voice_assistant.xml`

Replace `<i class="fa fa-robot"/>` with the logo image in **3 places**:

| Location | Old | New |
|---|---|---|
| Panel header `.dojo-va-avatar` | `<i class="fa fa-robot"/>` | `<img src="/dojo_instructor_dashboard/static/src/img/uft-logo.png" alt="AI"/>` |
| Message thread `.dojo-va-msg-avatar` (messages loop) | `<i class="fa fa-robot"/>` | `<img src="/dojo_instructor_dashboard/static/src/img/uft-logo.png" alt="AI"/>` |
| Typing indicator `.dojo-va-msg-avatar` | `<i class="fa fa-robot"/>` | `<img src="/dojo_instructor_dashboard/static/src/img/uft-logo.png" alt="AI"/>` |

### `instructor_dashboard.css` — `dojo-va-*` section

| Selector | Property | Old value | New value |
|---|---|---|---|
| `.dojo-va-fab` | `background` | `#1a73e8` | `#b41e16` |
| `.dojo-va-fab` | `box-shadow` | `rgba(26,115,232,0.45)` | `rgba(180,30,22,0.45)` |
| `.dojo-va-fab:hover` | `background` | `#1558b0` | `#8a1510` |
| `.dojo-va-fab:hover` | `box-shadow` | `rgba(26,115,232,0.55)` | `rgba(180,30,22,0.55)` |
| `.dojo-va-header` | `background` | `#1a73e8` | `#b41e16` |
| `.dojo-va-avatar` | add `overflow: hidden; padding: 3px; background: rgba(255,255,255,0.15)` | — | logo sits cleanly in circle |
| `.dojo-va-msg-avatar` | add `overflow: hidden` | — | logo image fits the circle |
| `.dojo-va-msg--user .dojo-va-msg-bubble` | `background` | `#1a73e8` | `#b41e16` |
| `.dojo-va-send-btn` | `background` | `#1a73e8` | `#b41e16` |
| `.dojo-va-send-btn:hover` | `background` | `#1558b0` | `#8a1510` |
| `.dojo-va-chat-input:focus` | `border-color` | `#1a73e8` | `#b41e16` |
| `.dojo-va-icon-btn--active` | `background` | blue tint | `rgba(180,30,22,0.12)` |
| `.dojo-va-icon-btn--active` | `color` | `#1a73e8` | `#b41e16` |

Logo image CSS (add to `.dojo-va-avatar img` and `.dojo-va-msg-avatar img`):
```
width: 100%; height: 100%; object-fit: cover; border-radius: 50%;
```

---

## Files NOT Changed

- `voice_assistant.js` — zero changes
- Panel white background, assistant bubbles, input bar, recording strip colors
- Any other dashboard CSS (`.o_di_*`, `.o_ad_*`) — untouched
