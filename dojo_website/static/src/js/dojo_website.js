/** @odoo-module **/

import { onMounted } from "@odoo/owl";
import publicWidget from "@web/legacy/js/public/public_widget";

// ── Sticky Header ────────────────────────────────────────────────
publicWidget.registry.DjStickyHeader = publicWidget.Widget.extend({
    selector: '.o_website .o_header_standard, .o_website header',
    events: {},

    start() {
        this._onScroll = this._handleScroll.bind(this);
        window.addEventListener('scroll', this._onScroll, { passive: true });
        return this._super(...arguments);
    },

    destroy() {
        window.removeEventListener('scroll', this._onScroll);
        this._super(...arguments);
    },

    _handleScroll() {
        const header = document.querySelector('#wrapwrap > header');
        if (header) {
            header.classList.toggle('dj-scrolled', window.scrollY > 60);
        }
    },
});

// ── Counter Animation ─────────────────────────────────────────────
publicWidget.registry.DjCounters = publicWidget.Widget.extend({
    selector: '.dj-stats-grid',

    start() {
        this._observed = false;
        this._observer = new IntersectionObserver(
            ([entry]) => {
                if (entry.isIntersecting && !this._observed) {
                    this._observed = true;
                    this._runCounters();
                }
            },
            { threshold: 0.4 }
        );
        this._observer.observe(this.el);
        return this._super(...arguments);
    },

    destroy() {
        this._observer.disconnect();
        this._super(...arguments);
    },

    _runCounters() {
        const nums = this.el.querySelectorAll('.dj-stat-num');
        nums.forEach(el => {
            const target = parseInt(el.dataset.target || el.textContent, 10);
            if (isNaN(target)) return;
            const duration = 2000;
            const start = performance.now();

            const step = (now) => {
                const progress = Math.min((now - start) / duration, 1);
                const eased = 1 - Math.pow(1 - progress, 3); // ease-out cubic
                el.textContent = Math.round(eased * target);
                if (progress < 1) requestAnimationFrame(step);
                else el.textContent = target;
            };
            requestAnimationFrame(step);
        });
    },
});

// ── Testimonial Slider ────────────────────────────────────────────
publicWidget.registry.DjTestiSlider = publicWidget.Widget.extend({
    selector: '.dj-testi-slider',
    events: {
        'click .dj-slider-btn[data-dir="-1"]': '_prev',
        'click .dj-slider-btn[data-dir="1"]': '_next',
    },

    start() {
        this._track = this.el.querySelector('.dj-testi-track');
        this._cards = Array.from(this.el.querySelectorAll('.dj-testi-card'));
        if (!this._track || this._cards.length === 0) return this._super(...arguments);

        this._index = 0;
        this._perView = this._getPerView();
        this._dots = Array.from(document.querySelectorAll('.dj-dot'));

        this._autoTimer = setInterval(() => this._next(), 5500);

        // Touch / swipe
        let touchX = null;
        this._track.addEventListener('touchstart', e => { touchX = e.touches[0].clientX; }, { passive: true });
        this._track.addEventListener('touchend', e => {
            if (touchX === null) return;
            const diff = touchX - e.changedTouches[0].clientX;
            if (Math.abs(diff) > 40) diff > 0 ? this._next() : this._prev();
            touchX = null;
        });

        this._dots.forEach((dot, i) => dot.addEventListener('click', () => this._goTo(i)));
        this._render();
        return this._super(...arguments);
    },

    destroy() {
        clearInterval(this._autoTimer);
        this._super(...arguments);
    },

    _getPerView() {
        return window.innerWidth < 769 ? 1 : window.innerWidth < 1025 ? 2 : 3;
    },

    _maxIndex() {
        const pv = this._getPerView();
        return Math.max(0, Math.ceil(this._cards.length / pv) - 1);
    },

    _prev() { this._goTo(this._index - 1); },
    _next() { this._goTo(this._index + 1); },

    _goTo(i) {
        const max = this._maxIndex();
        this._index = ((i % (max + 1)) + (max + 1)) % (max + 1);
        this._render();
    },

    _render() {
        const pv = this._getPerView();
        const cardWidth = this._cards[0].offsetWidth;
        const gap = 24; // 1.5rem
        this._track.style.transform = `translateX(-${this._index * (cardWidth + gap)}px)`;
        this._dots.forEach((d, i) => d.classList.toggle('active', i === this._index));
    },
});

// ── Scroll Reveal ─────────────────────────────────────────────────
publicWidget.registry.DjScrollReveal = publicWidget.Widget.extend({
    selector: '.dojo-page',

    start() {
        const items = this.el.querySelectorAll(
            '.dj-why-card, .dj-program-card, .dj-instructor-card, ' +
            '.dj-stat-item, .dj-info-card, .dj-section-header'
        );
        items.forEach(el => {
            el.style.cssText += 'opacity:0; transform:translateY(24px); transition:opacity .6s ease,transform .6s ease;';
        });

        const observer = new IntersectionObserver(
            entries => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        entry.target.style.opacity = '1';
                        entry.target.style.transform = 'none';
                        observer.unobserve(entry.target);
                    }
                });
            },
            { threshold: 0.15 }
        );
        items.forEach(el => observer.observe(el));
        this._observer = observer;
        return this._super(...arguments);
    },

    destroy() {
        if (this._observer) this._observer.disconnect();
        this._super(...arguments);
    },
});
