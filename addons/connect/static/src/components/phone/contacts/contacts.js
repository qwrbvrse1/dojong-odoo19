/** @odoo-module **/

import { useService } from "@web/core/utils/hooks"
import { setFocus } from "@connect/js/utils"
import { Component, useState, useRef, onWillStart, onWillDestroy } from "@odoo/owl"

const searching = {
    all: 'all',
    extensions: 'extensions',
    partners: 'partners',
}

export class Contacts extends Component {
    static template = 'connect.contacts'
    static props = {
        bus: Object,
        isTransfer: { type: Boolean, optional: true },
        isContact: { type: Boolean, optional: true },
        isForward: { type: Boolean, optional: true },
        contactSearch: { type: String, optional: true },
    }

    constructor() {
        super(...arguments)
        const { bus, isTransfer = false, isForward = false, isContact = false, contactSearch = 'all' } = this.props
        this.bus = bus
        this.isTransfer = isTransfer
        this.isForward = isForward
        this.isContact = isContact
        this.contactSearch = contactSearch
        this.searchQuery = ''
        this.users = []
        this.isFavoritesMode = contactSearch === 'favorites'
    }

    setup(props) {
        super.setup()
        this.orm = useService('orm')
        this.action = useService('action')
        this.contactInput = useRef('contact-input')
        this.state = useState({
            isContactMode: !this.isFavoritesMode,
            partners: [],
            users: this.users,
            hasSearched: false,
        })

        onWillStart(async () => {
            this._isAlive = true
            this._onBusContactSetState = ({ detail }) => this._busContactSetState(detail)
            this._onBusContactSearchQuery = ({ detail }) => this._busContactSearchQuery(detail)
            this.bus.addEventListener('busContactSetState', this._onBusContactSetState)
            this.bus.addEventListener('busContactSearchQuery', this._onBusContactSearchQuery)
            if (this.isFavoritesMode) {
                await this._loadFavorites()
            }
        })

        onWillDestroy(() => {
            this._isAlive = false
            this.bus.removeEventListener('busContactSetState', this._onBusContactSetState)
            this.bus.removeEventListener('busContactSearchQuery', this._onBusContactSearchQuery)
        })
    }

    _busContactSetState({ isTransfer = false, isForward = false, isContact = false, isContactMode = false }) {
        this.state.isContactMode = isContactMode
        this.isTransfer = isTransfer
        this.isContact = isContact
        this.isForward = isForward
        this.state.partners = []
        this.state.users = []
        this.state.hasSearched = false
        this.searchQuery = ''
        if (this.contactInput.el) {
            this.contactInput.el.value = ''
            setFocus(this.contactInput.el)
        }
    }

    _busContactSearchQuery({ searchQuery = '' }) {
        this.searchQuery = searchQuery
        this.searchUser()
        this.searchPartner()
    }

    _onSearchContact(ev) {
        if (ev.key === "Enter") {
            this._contactCall()
        } else {
            this._contactSearchQuery({ searchQuery: ev.target.value })
        }
    }

    _onClickClearSearchContact(ev) {
        this._contactSearchQuery({ searchQuery: '' })
        this.state.hasSearched = false
        this.contactInput.el.value = ''
        setFocus(this.contactInput.el)
    }

    _contactSearchQuery({ searchQuery = '' }) {
        this.searchQuery = searchQuery
        this.searchUser()
        this.searchPartner()
    }

    _contactCall() {
        let phoneNumber
        if (this.state.partners.length + this.state.users.length === 1) {
            if (this.state.partners.length) {
                const contact = this.state.partners[0]
                phoneNumber = contact.phone ? contact.phone : contact.mobile
            } else {
                phoneNumber = this.state.users[0].exten
            }
        } else {
            phoneNumber = this.searchQuery
        }

        if (this.isTransfer) {
            this._onClickMakeTransfer(phoneNumber)
        } else if (this.isContact) {
            this._onClickMakeCall(phoneNumber)
        } else if (this.isForward) {
            this._onClickMakeForward(phoneNumber)
        }
    }

    searchPartner() {
        if (this.contactSearch !== searching.all && this.contactSearch !== searching.partners) return
        const self = this
        if (self.searchQuery) {
            self.orm.searchRead(
                "res.partner",
                [
                    '|', ['connect_phone_normalized', '=ilike', `%${self.searchQuery}%`],
                    '|', ['connect_mobile_normalized', '=ilike', `%${self.searchQuery}%`],
                    ['name', '=ilike', `%${self.searchQuery}%`],
                    '|', ['phone', '!=', null],
                    ['mobile', '!=', null]
                ],
                ['id', 'name', 'email', 'connect_phone_normalized', 'connect_mobile_normalized'],
                { order: 'name asc', limit: 10 }
            ).then((records) => {
                if (!self._isAlive) return
                self.state.partners = records
                self.state.hasSearched = true
            })
        } else {
            self.state.partners = []
        }
    }

    searchUser() {
        if (this.contactSearch !== searching.all && this.contactSearch !== searching.extensions) return
        const self = this
        if (self.searchQuery) {
            self.orm.searchRead(
                "connect.user",
                [
                    '|', ['exten_number', '=ilike', `%${self.searchQuery}%`],
                    ['user', '=ilike', `%${self.searchQuery}%`]
                ],
                ['id', 'name', 'exten_number', 'user'],
                { order: 'exten_number asc', limit: 10 }
            ).then((records) => {
                if (!self._isAlive) return
                self.state.users = records
                self.state.hasSearched = true
            })
        } else {
            self.state.users = []
        }
    }

    _onClickMakeCall(phoneNumber) {
        this.bus.trigger('busPhoneMakeCall', { phone: phoneNumber })
    }

    _onClickMakeTransfer(phoneNumber) {
        this.bus.trigger('busPhoneMakeTransfer', phoneNumber)
    }

    _onClickMakeForward(phoneNumber) {
        this.bus.trigger('busPhoneMakeForward', phoneNumber.replace('+', ''))
    }

    _openPartner(id) {
        this.action.doAction({
            res_id: id,
            res_model: "res.partner",
            target: 'new',
            type: 'ir.actions.act_window',
            views: [[false, 'form']],
        })
    }

    async _loadFavorites() {
        const favorites = await this.orm.searchRead('connect.favorite', [], ['phone_number', 'partner', 'user', 'name'])
        if (!this._isAlive) return

        const partnerIds = favorites.filter(f => f.partner).map(f => f.partner[0])
        const userIds = favorites.filter(f => f.user).map(f => f.user[0])

        if (partnerIds.length > 0) {
            this.state.partners = await this.orm.searchRead(
                'res.partner',
                [['id', 'in', partnerIds]],
                ['id', 'name', 'email', 'connect_phone_normalized', 'connect_mobile_normalized'],
                { order: 'name asc' }
            )
        }
        if (userIds.length > 0) {
            this.state.users = await this.orm.searchRead(
                'connect.user',
                [['id', 'in', userIds]],
                ['id', 'name', 'exten_number', 'user'],
                { order: 'exten_number asc' }
            )
        }

        // For favorites that have neither partner nor user, show as plain entries
        const plainFavs = favorites.filter(f => !f.partner && !f.user)
        for (const fav of plainFavs) {
            this.state.partners.push({
                id: -fav.id,
                name: fav.name || fav.phone_number,
                connect_phone_normalized: fav.phone_number,
                connect_mobile_normalized: false,
            })
        }

        this.state.hasSearched = true
    }
}