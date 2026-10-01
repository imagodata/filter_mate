// FilterMate website — navigation, background footage, watch mode, table of contents.
(function () {
    'use strict';

    // ---------------------------------------------------------------- navigation
    const nav = document.querySelector('.nav');
    const toggle = document.querySelector('.nav-toggle');
    const links = document.getElementById('navLinks');
    if (toggle && links) {
        toggle.addEventListener('click', () => {
            const open = links.classList.toggle('open');
            toggle.setAttribute('aria-expanded', String(open));
            toggle.setAttribute('aria-label', open
                ? (document.documentElement.lang === 'fr' ? 'Fermer le menu' : 'Close menu')
                : (document.documentElement.lang === 'fr' ? 'Ouvrir le menu' : 'Open menu'));
        });
        links.addEventListener('click', (e) => {
            if (e.target.closest('a') && links.classList.contains('open')) {
                links.classList.remove('open');
                toggle.setAttribute('aria-expanded', 'false');
                toggle.setAttribute('aria-label', document.documentElement.lang === 'fr' ? 'Ouvrir le menu' : 'Open menu');
            }
        });
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && links.classList.contains('open')) {
                links.classList.remove('open');
                toggle.setAttribute('aria-expanded', 'false');
                toggle.setAttribute('aria-label', document.documentElement.lang === 'fr' ? 'Ouvrir le menu' : 'Open menu');
                toggle.focus();
            }
        });
    }
    if (nav && nav.classList.contains('on-video')) {
        const onScroll = () => nav.classList.toggle('scrolled', window.scrollY > 40);
        window.addEventListener('scroll', onScroll, { passive: true });
        onScroll();
    }
    // the language switch keeps the current section
    document.querySelectorAll('[data-lang-link]').forEach((a) => {
        a.addEventListener('click', () => { a.href = a.getAttribute('href').split('#')[0] + location.hash; });
    });

    // ---------------------------------------------------------------- background footage
    // Videos load only when their sheet comes into view and pause when it leaves.
    // Reduced motion or a data-saving connection keeps the poster; "Watch" still plays.
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const conn = navigator.connection || {};
    const frugal = conn.saveData || /(^|-)2g$/.test(conn.effectiveType || '');
    const autoplay = !reduce && !frugal;
    const videos = Array.from(document.querySelectorAll('video[data-src]'));

    // ---------------------------------------------------------------- home scroll aids
    // Keep scrolling native: add orientation and shortcuts without intercepting
    // the wheel, trackpad, Page Down or keyboard navigation.
    if (document.body.classList.contains('home')) {
        const french = document.documentElement.lang === 'fr';
        const sectionData = french
            ? [
                ['top', 'Accueil'],
                ['workflow', 'Méthode'],
                ['examples', 'Exemples'],
                ['capabilities', 'Fonctions'],
                ['performance', 'Mesures'],
                ['install', 'Installer'],
            ]
            : [
                ['top', 'Top'],
                ['workflow', 'Workflow'],
                ['examples', 'Examples'],
                ['capabilities', 'Features'],
                ['performance', 'Performance'],
                ['install', 'Install'],
            ];
        const sections = sectionData
            .map(([id, label]) => ({ id, label, node: document.getElementById(id) }))
            .filter((item) => item.node);

        const progress = document.createElement('div');
        progress.className = 'scroll-progress';
        progress.setAttribute('role', 'progressbar');
        progress.setAttribute('aria-label', french ? 'Progression dans la page' : 'Page progress');
        progress.setAttribute('aria-valuemin', '0');
        progress.setAttribute('aria-valuemax', '100');
        progress.setAttribute('aria-valuenow', '0');
        document.body.appendChild(progress);

        const rail = document.createElement('nav');
        rail.className = 'scroll-rail';
        rail.setAttribute('aria-label', french ? 'Sections de la page' : 'Page sections');
        const railLinks = sections.map(({ id, label }) => {
            const a = document.createElement('a');
            a.href = '#' + id;
            a.setAttribute('aria-label', label);
            const tooltip = document.createElement('span');
            tooltip.setAttribute('aria-hidden', 'true');
            tooltip.textContent = label;
            a.appendChild(tooltip);
            rail.appendChild(a);
            return a;
        });
        document.body.appendChild(rail);

        const backToTop = document.createElement('button');
        backToTop.className = 'back-to-top';
        backToTop.type = 'button';
        backToTop.setAttribute('aria-label', french ? 'Revenir en haut' : 'Back to top');
        backToTop.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m6 15 6-6 6 6"/></svg>';
        backToTop.addEventListener('click', () => {
            window.scrollTo({ top: 0, behavior: reduce ? 'auto' : 'smooth' });
        });
        document.body.appendChild(backToTop);

        // Reveal content once as it enters the viewport. Content remains fully
        // visible without JavaScript and when reduced motion is requested.
        if (!reduce && 'IntersectionObserver' in window) {
            const revealNodes = Array.from(document.querySelectorAll([
                '.home-section .section-heading',
                '.workflow-grid > li',
                '.example-card',
                '.product-shot',
                '.capability-list > li',
                '.performance-stats > div',
                '.install-steps > li',
                '.install-bottom',
            ].join(',')));
            revealNodes.forEach((node, index) => {
                node.classList.add('scroll-reveal');
                node.style.setProperty('--reveal-delay', String((index % 3) * 55) + 'ms');
            });
            document.body.classList.add('scroll-reveal-ready');
            const revealObserver = new IntersectionObserver((entries) => {
                entries.forEach((entry) => {
                    if (entry.isIntersecting) {
                        entry.target.classList.add('is-visible');
                        revealObserver.unobserve(entry.target);
                    }
                });
            }, { rootMargin: '0px 0px -8% 0px', threshold: 0.08 });
            revealNodes.forEach((node) => revealObserver.observe(node));
        }

        let scrollTicking = false;
        function updateScrollAids() {
            const root = document.documentElement;
            const maximum = Math.max(1, root.scrollHeight - window.innerHeight);
            const ratio = Math.min(1, Math.max(0, window.scrollY / maximum));
            const percent = Math.round(ratio * 100);
            progress.style.transform = 'scaleX(' + ratio + ')';
            progress.setAttribute('aria-valuenow', String(percent));
            backToTop.classList.toggle('visible', window.scrollY > window.innerHeight * 0.8);

            const marker = window.scrollY + window.innerHeight * 0.42;
            let activeIndex = 0;
            sections.forEach((section, index) => {
                if (section.node.offsetTop <= marker) activeIndex = index;
            });
            railLinks.forEach((a, index) => {
                const active = index === activeIndex;
                a.classList.toggle('active', active);
                if (active) a.setAttribute('aria-current', 'location');
                else a.removeAttribute('aria-current');
            });
            scrollTicking = false;
        }
        function requestScrollUpdate() {
            if (!scrollTicking) {
                scrollTicking = true;
                window.requestAnimationFrame(updateScrollAids);
            }
        }
        window.addEventListener('scroll', requestScrollUpdate, { passive: true });
        window.addEventListener('resize', requestScrollUpdate, { passive: true });
        window.addEventListener('load', requestScrollUpdate, { once: true });
        updateScrollAids();
    }

    function load(v) {
        if (!v.src) {
            v.src = v.dataset.src;
        }
    }
    function play(v) {
        load(v);
        const p = v.play();
        if (p && p.catch) p.catch(() => {});
    }

    if ('IntersectionObserver' in window) {
        const io = new IntersectionObserver((entries) => {
            entries.forEach((e) => {
                const v = e.target;
                const watching = v.closest('.is-watching');
                if (e.isIntersecting && (autoplay || watching)) {
                    play(v);
                } else if (!e.isIntersecting) {
                    v.pause();
                }
            });
        }, { threshold: 0.25 });
        videos.forEach((v) => io.observe(v));
    } else if (autoplay) {
        videos.forEach(play);
    }

    // ---------------------------------------------------------------- watch mode
    const lightbox = document.getElementById('lightbox');
    const lbVideo = lightbox ? lightbox.querySelector('video') : null;

    function exitWatch(sheet) {
        sheet.classList.remove('is-watching');
        const btn = sheet.querySelector('[data-watch]');
        if (btn) btn.focus();
        const v = sheet.querySelector('video');
        if (v && !autoplay) v.pause();
    }

    document.querySelectorAll('[data-watch]').forEach((btn) => {
        btn.addEventListener('click', () => {
            const holder = btn.closest('.sheet, .band');
            const v = holder && holder.querySelector('video');
            const directSrc = btn.dataset.video;
            if (directSrc && lightbox && lbVideo) {
                lbVideo.src = directSrc;
                lbVideo.poster = btn.dataset.poster || '';
                lightbox.showModal();
                const p = lbVideo.play();
                if (p && p.catch) p.catch(() => {});
                return;
            }
            if (!v) return;
            if (holder.classList.contains('band') && lightbox && lbVideo) {
                // documentation: a larger player with controls
                lbVideo.src = v.dataset.src;
                lbVideo.poster = v.poster;
                lightbox.showModal();
                const p = lbVideo.play();
                if (p && p.catch) p.catch(() => {});
                return;
            }
            holder.classList.add('is-watching');
            v.currentTime = 0;
            play(v);
            const close = holder.querySelector('.close-watch');
            if (close) close.focus();
        });
    });
    document.querySelectorAll('.close-watch').forEach((btn) => {
        btn.addEventListener('click', () => exitWatch(btn.closest('.sheet')));
    });
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            document.querySelectorAll('.sheet.is-watching').forEach(exitWatch);
        }
    });
    if (lightbox && lbVideo) {
        lightbox.addEventListener('close', () => { lbVideo.pause(); lbVideo.removeAttribute('src'); lbVideo.load(); });
        lightbox.addEventListener('click', (e) => { if (e.target === lightbox) lightbox.close(); });
    }

    // ---------------------------------------------------------------- table of contents
    const tocLinks = Array.from(document.querySelectorAll('.toc a[href^="#"]'));
    if (tocLinks.length && 'IntersectionObserver' in window) {
        const sections = tocLinks.map((a) => document.querySelector(a.getAttribute('href'))).filter(Boolean);
        const spy = new IntersectionObserver((entries) => {
            entries.forEach((e) => {
                if (e.isIntersecting) {
                    const id = '#' + e.target.id;
                    tocLinks.forEach((a) => a.classList.toggle('active', a.getAttribute('href') === id));
                }
            });
        }, { rootMargin: '-20% 0px -70% 0px', threshold: 0 });
        sections.forEach((s) => spy.observe(s));
    }
})();
