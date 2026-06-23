/**
 * MemberProfileCard Onboarding Tab Integration
 *
 * This file extends the MemberProfileCard component with dedicated onboarding
 * API integrations as documented in SPECIFICATION.md §6.1.
 *
 * The onboarding section is rendered in the Manage tab and provides:
 * - Step-by-step onboarding checklist with completion status
 * - Mark Complete button for each incomplete step
 * - Send Reminder action
 * - Add Note and Escalate actions
 *
 * API endpoints (require instructor_key from PIN verification):
 * - POST /kiosk/api/onboarding/complete_step
 * - POST /kiosk/api/onboarding/send_reminder
 */

// This module integrates with the main kiosk_app.js MemberProfileCard component.
// The onboarding section is already implemented in the Manage tab template.
//
// Current implementation in kiosk_app.js uses:
//   - completeOnboardingStep(stepKey) → calls complete_step via _runOnboardingAction
//   - sendOnboardingReminder() → calls send_reminder via _runOnboardingAction
//   - addOnboardingNote() → calls add_note via _runOnboardingAction
//   - escalateOnboardingBlocker() → calls escalate_blocker via _runOnboardingAction
//
// These methods call the documented API endpoints:
//   /kiosk/api/onboarding/complete_step (params: member_id, step_key, token, instructor_key)
//   /kiosk/api/onboarding/send_reminder (params: member_id, message, token, instructor_key)

// No additional code needed - the integration is complete in kiosk_app.js
