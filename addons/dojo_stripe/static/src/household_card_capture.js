/** @odoo-module **/
/**
 * household_card_capture.js  (dojo_stripe)
 * ─────────────────────────────────────────
 * Odoo client action that provides an inline card-capture modal for adding or
 * replacing the saved Stripe payment method on a Household record.
 *
 * Registered action tag: "dojo_stripe.HouseholdCardCapture"
 *
 * Opened by res.partner.action_add_update_card() which passes:
 *   params.household_id       – res.partner ID (is_household = True)
 *   params.guardian_name      – display name for the UI
 *   params.has_existing_card  – true = "Update Card", false = "Add Card"
 *
 * Flow:
 *   1. onMounted → POST /dojo/stripe/household/setup
 *      Returns {client_secret, publishable_key, stripe_customer_id}
 *   2. Load Stripe.js → stripe.elements({clientSecret}) → mount PaymentElement
 *   3. Admin clicks "Save Card"
 *      a. elements.submit()
 *      b. stripe.confirmSetup({redirect: 'if_required'})
 *      c. POST /dojo/stripe/household/confirm
 *   4. Success → notification + historyBack() to household form
 */

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, xml, useState, onMounted, useRef, useEffect } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";

class HouseholdCardCapture extends Component {
    static template = xml`
        <div style="width: 100%; padding: 4px 0;">

            <!-- ── Billing contact banner ────────────────────────────────── -->
            <div t-if="props.action.params.guardian_name"
                 class="d-flex align-items-center gap-3 mb-4 p-3 rounded-3"
                 style="background: #f8f5fc; border: 1px solid #e8dff0;">
                <div class="d-flex align-items-center justify-content-center rounded-circle"
                     style="width:40px;height:40px;background:#714b67;flex-shrink:0;">
                    <i class="fa fa-user text-white"/>
                </div>
                <div>
                    <div class="text-muted" style="font-size:11px;text-transform:uppercase;letter-spacing:.5px;">Billing Contact</div>
                    <div class="fw-semibold" style="font-size:15px;" t-esc="props.action.params.guardian_name"/>
                </div>
            </div>

            <!-- ── Loading ───────────────────────────────────────────────── -->
            <div t-if="state.status === 'loading'"
                 class="text-center py-5">
                <div class="spinner-border text-primary mb-3"
                     role="status" style="width:2.5rem;height:2.5rem;"/>
                <p class="text-muted mb-0">Loading secure payment form…</p>
                <p class="text-muted small mt-1">Powered by Stripe</p>
            </div>

            <!-- ── Stripe PaymentElement mount target ────────────────────── -->
            <div t-if="state.status === 'ready' or state.status === 'processing'"
                 t-ref="stripeMountRef"
                 id="stripe-household-payment-element"/>

            <!-- ── Processing overlay ────────────────────────────────────── -->
            <div t-if="state.status === 'processing'"
                 class="d-flex align-items-center justify-content-center gap-2 mt-3 p-2">
                <div class="spinner-border spinner-border-sm text-primary" role="status"/>
                <span class="text-muted small">Saving securely…</span>
            </div>

            <!-- ── Error ─────────────────────────────────────────────────── -->
            <div t-if="state.errorMessage and state.status !== 'processing'"
                 class="rounded-3 p-3 d-flex gap-3 align-items-start"
                 style="background:#fff5f5;border:1px solid #f5c2c7;">
                <i class="fa fa-exclamation-circle text-danger mt-1" style="font-size:18px;flex-shrink:0;"/>
                <div class="flex-grow-1">
                    <div class="fw-semibold text-danger mb-1" style="font-size:13px;">Unable to load payment form</div>
                    <div class="text-muted small" t-esc="state.errorMessage"/>
                    <div t-if="state.status === 'error'" class="mt-2">
                        <button class="btn btn-sm btn-outline-danger" t-on-click="onRetry">
                            <i class="fa fa-refresh me-1"/>Try again
                        </button>
                    </div>
                </div>
            </div>

            <!-- ── Success ───────────────────────────────────────────────── -->
            <div t-if="state.status === 'done'" class="text-center py-4">
                <div class="d-flex align-items-center justify-content-center rounded-circle mx-auto mb-3"
                     style="width:64px;height:64px;background:#d1fae5;">
                    <i class="fa fa-check text-success" style="font-size:28px;"/>
                </div>
                <h6 class="mb-1">Card Saved Successfully</h6>
                <p class="text-muted small mb-0" t-esc="state.cardDisplay"/>
            </div>

            <!-- ── Footer ────────────────────────────────────────────────── -->
            <div t-if="state.status !== 'done'"
                 class="d-flex justify-content-end gap-2 mt-4 pt-3"
                 style="border-top: 1px solid #e9ecef;">
                <button class="btn btn-outline-secondary"
                        t-att-disabled="state.status === 'processing'"
                        t-on-click="goBack">
                    Cancel
                </button>
                <button class="btn btn-primary"
                        t-if="state.status === 'ready' or state.status === 'processing'"
                        t-att-disabled="state.status === 'processing'"
                        t-on-click="onSaveCard">
                    <t t-if="state.status === 'processing'">
                        <span class="spinner-border spinner-border-sm me-1" role="status"/>Saving…
                    </t>
                    <t t-else="">
                        <i class="fa fa-lock me-1"/>Save Card
                    </t>
                </button>
            </div>

        </div>
    `;

    static props = {
        action: { type: Object },
    };

    setup() {
        this.actionService = useService("action");
        this.notificationService = useService("notification");

        this.state = useState({
            /** idle | loading | ready | processing | done | error */
            status: "idle",
            errorMessage: "",
            cardDisplay: "",
        });

        this.stripeMountRef = useRef("stripeMountRef");
        this.stripe = null;
        this.elements = null;
        this._pendingPaymentEl = null;
        /** Stripe Customer ID (cus_...) returned by setup endpoint — needed by confirm. */
        this._stripeCustomerId = null;

        // Mount the PaymentElement after the t-ref div appears in the DOM.
        // The div is only rendered when status changes to 'ready', so useEffect
        // fires on the render cycle after that state change.
        useEffect(
            (status) => {
                if (status === "ready" && this._pendingPaymentEl && this.stripeMountRef.el) {
                    this._pendingPaymentEl.mount(this.stripeMountRef.el);
                    this._pendingPaymentEl = null;
                }
            },
            () => [this.state.status],
        );

        onMounted(() => {
            this._initStripe();
        });
    }

    // ── Stripe initialisation ──────────────────────────────────────────────

    async _initStripe() {
        this.state.status = "loading";
        this.state.errorMessage = "";
        const householdId = this.props.action.params.household_id;

        let result;
        try {
            result = await rpc("/dojo/stripe/household/setup", { household_id: householdId });
        } catch (e) {
            this.state.status = "error";
            this.state.errorMessage = e.message || "Network error — could not reach the server.";
            return;
        }

        if (result.error) {
            this.state.status = "error";
            this.state.errorMessage = result.error;
            return;
        }

        this._stripeCustomerId = result.stripe_customer_id;

        try {
            const stripeJs = await this._loadStripeJs(result.publishable_key);
            this.stripe = stripeJs;
            this.elements = stripeJs.elements({
                clientSecret: result.client_secret,
                appearance: {
                    theme: "stripe",
                    variables: { colorPrimary: "#714b67" },
                },
            });

            const paymentEl = this.elements.create("payment", {
                layout: "tabs",
                // Disable wallet shortcuts — this is an admin-facing form
                wallets: { applePay: "never", googlePay: "never", link: "never" },
            });

            // Store reference; useEffect will .mount() after status → 'ready' re-render
            this._pendingPaymentEl = paymentEl;
            this.state.status = "ready";
        } catch (e) {
            this.state.status = "error";
            this.state.errorMessage = e.message || "Failed to initialise payment form.";
        }
    }

    async _loadStripeJs(publishableKey) {
        if (window.Stripe) {
            return window.Stripe(publishableKey);
        }
        return new Promise((resolve, reject) => {
            const script = document.createElement("script");
            script.src = "https://js.stripe.com/v3/";
            script.async = true;
            script.onload = () => resolve(window.Stripe(publishableKey));
            script.onerror = () => reject(new Error("Failed to load Stripe.js"));
            document.head.appendChild(script);
        });
    }

    // ── Save card ──────────────────────────────────────────────────────────

    async onSaveCard() {
        if (!this.stripe || !this.elements) return;

        this.state.status = "processing";
        this.state.errorMessage = "";

        // Step 1: validate element inputs
        const { error: submitError } = await this.elements.submit();
        if (submitError) {
            this.state.errorMessage = submitError.message;
            this.state.status = "ready";
            return;
        }

        // Step 2: confirm the SetupIntent (no redirect for cards)
        const { error, setupIntent } = await this.stripe.confirmSetup({
            elements: this.elements,
            redirect: "if_required",
        });
        if (error) {
            this.state.errorMessage = error.message;
            this.state.status = "ready";
            return;
        }

        const pmId =
            typeof setupIntent.payment_method === "string"
                ? setupIntent.payment_method
                : setupIntent.payment_method.id;

        // Step 3: tell the server to record the PM and replace old tokens
        const householdId = this.props.action.params.household_id;
        let result;
        try {
            result = await rpc("/dojo/stripe/household/confirm", {
                household_id: householdId,
                payment_method_id: pmId,
                stripe_customer_id: this._stripeCustomerId,
            });
        } catch (e) {
            this.state.errorMessage = e.message || "Network error saving card.";
            this.state.status = "ready";
            return;
        }

        if (result.error) {
            this.state.errorMessage = result.error;
            this.state.status = "ready";
            return;
        }

        this.state.status = "done";
        this.state.cardDisplay = result.display || "Card saved";

        // Notify and return to household form after a short pause
        this.notificationService.add(
            `Payment method saved: ${result.display}`,
            { type: "success", title: "Card Saved" },
        );
        // Short pause to show the success state, then close the dialog
        setTimeout(() => {
            this.actionService.doAction({ type: "ir.actions.act_window_close" });
        }, 1400);
    }

    // ── Retry ──────────────────────────────────────────────────────────────

    async onRetry() {
        this.stripe = null;
        this.elements = null;
        this._pendingPaymentEl = null;
        this._stripeCustomerId = null;
        await this._initStripe();
    }

    // ── Cancel / close ─────────────────────────────────────────────────────

    goBack() {
        this.actionService.doAction({ type: "ir.actions.act_window_close" });
    }
}

registry.category("actions").add("dojo_stripe.HouseholdCardCapture", HouseholdCardCapture);
