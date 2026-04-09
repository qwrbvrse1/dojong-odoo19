/** @odoo-module **/

import { useService } from "@web/core/utils/hooks"
import { Component, useState, onWillStart, onWillDestroy } from "@odoo/owl"
import { user } from "@web/core/user"

const uid = user.userId

export class Favorites extends Component {
    static template = 'connect.favorites'
    static props = {
        bus: Object,
    }

    constructor() {
        super(...arguments)
        this.bus = this.props.bus
    }

    setup() {
        super.setup()
        this.orm = useService('orm')
        this.action = useService('action')
        this._isAlive = true
        this.state = useState({
            activities: [],
            loading: true,
        })

        onWillStart(async () => {
            await this._loadActivities()
        })

        onWillDestroy(() => {
            this._isAlive = false
        })
    }

    async _loadActivities() {
        const today = new Date()
        const yyyy = today.getFullYear()
        const mm = String(today.getMonth() + 1).padStart(2, '0')
        const dd = String(today.getDate()).padStart(2, '0')
        const todayStr = `${yyyy}-${mm}-${dd}`

        const records = await this.orm.searchRead(
            'mail.activity',
            [
                ['user_id', '=', uid],
                ['date_deadline', '<=', todayStr],
            ],
            ['id', 'res_name', 'res_model', 'res_id', 'summary', 'date_deadline', 'activity_type_id', 'note'],
            { order: 'date_deadline asc', limit: 50 }
        )

        if (!this._isAlive) return

        const today0 = new Date()
        today0.setHours(0, 0, 0, 0)

        // Deduplicate: keep earliest-deadline activity per res_id+res_model
        const seen = new Map()
        for (const r of records) {
            const key = `${r.res_model}:${r.res_id}`
            if (!seen.has(key)) {
                seen.set(key, r)
            }
        }

        this.state.activities = [...seen.values()].map((r) => {
            const deadline = new Date(r.date_deadline)
            deadline.setHours(0, 0, 0, 0)
            const diffDays = Math.round((today0 - deadline) / 86400000)
            let badge = 'today'
            if (diffDays > 0) badge = `${diffDays}d overdue`
            return { ...r, badge, isOverdue: diffDays > 0 }
        })
        this.state.loading = false
    }

    _onClickActivity(activity) {
        this.action.doAction({
            res_id: activity.res_id,
            res_model: activity.res_model,
            target: 'new',
            type: 'ir.actions.act_window',
            views: [[false, 'form']],
        })
    }

    async _onClickCallActivity(ev, activity) {
        ev.stopPropagation()
        let phone = null
        // Try each field individually so a missing field on the model doesn't
        // abort the entire read (e.g. crm.lead has no 'mobile' field).
        for (const field of ['phone', 'partner_phone', 'mobile']) {
            try {
                const records = await this.orm.read(
                    activity.res_model,
                    [activity.res_id],
                    [field]
                )
                if (records && records.length && records[0][field]) {
                    phone = records[0][field]
                    break
                }
            } catch (e) {
                // field doesn't exist on this model, try next
            }
        }
        // Fall back to the linked partner's phone if still not found
        if (!phone) {
            try {
                const records = await this.orm.read(
                    activity.res_model,
                    [activity.res_id],
                    ['partner_id']
                )
                if (records && records.length && records[0].partner_id) {
                    const partnerId = records[0].partner_id[0]
                    const partners = await this.orm.read(
                        'res.partner',
                        [partnerId],
                        ['phone', 'mobile']
                    )
                    if (partners && partners.length) {
                        phone = partners[0].phone || partners[0].mobile
                    }
                }
            } catch (e2) {
                // give up silently
            }
        }
        if (phone) {
            this.bus.trigger('busPhoneMakeCall', { phone })
        }
    }

    _getActivityIcon(activity) {
        if (!activity.activity_type_id) return 'fa-clock-o'
        const name = (activity.activity_type_id[1] || '').toLowerCase()
        if (name.includes('call') || name.includes('phone')) return 'fa-phone'
        if (name.includes('email') || name.includes('mail')) return 'fa-envelope'
        if (name.includes('meet')) return 'fa-users'
        if (name.includes('todo') || name.includes('to-do') || name.includes('to do')) return 'fa-check-square-o'
        return 'fa-clock-o'
    }
}
