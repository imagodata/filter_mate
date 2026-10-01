// FilterMate website — navigation, background footage, watch mode, table of contents.
(function () {
    'use strict';
    const french = document.documentElement.lang === 'fr';
    const messages = window.FM_I18N || {};
    const tr = (key, fallback) => messages[key] || fallback;

    // ---------------------------------------------------------------- navigation
    const nav = document.querySelector('.nav');
    const toggle = document.querySelector('.nav-toggle');
    const links = document.getElementById('navLinks');
    if (toggle && links) {
        toggle.addEventListener('click', () => {
            const open = links.classList.toggle('open');
            toggle.setAttribute('aria-expanded', String(open));
            toggle.setAttribute('aria-label', open
                ? tr('closeMenu', french ? 'Fermer le menu' : 'Close menu')
                : tr('openMenu', french ? 'Ouvrir le menu' : 'Open menu'));
        });
        links.addEventListener('click', (e) => {
            if (e.target.closest('a') && links.classList.contains('open')) {
                links.classList.remove('open');
                toggle.setAttribute('aria-expanded', 'false');
                toggle.setAttribute('aria-label', tr('openMenu', french ? 'Ouvrir le menu' : 'Open menu'));
            }
        });
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && links.classList.contains('open')) {
                links.classList.remove('open');
                toggle.setAttribute('aria-expanded', 'false');
                toggle.setAttribute('aria-label', tr('openMenu', french ? 'Ouvrir le menu' : 'Open menu'));
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
    document.querySelectorAll('.language-menu').forEach((menu) => {
        document.addEventListener('click', (e) => {
            if (!menu.contains(e.target)) menu.open = false;
        });
        menu.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && menu.open) {
                e.stopPropagation();
                menu.open = false;
                menu.querySelector('summary').focus();
            }
        });
    });

    // Pick one existing demonstration per home visit, not a rotating carousel.
    // Keep the chosen poster and the manual player in sync, including on mobile.
    const heroVideo = document.querySelector('.home-hero video[data-src]');
    if (heroVideo) {
        const choices = ['hero', 'export', 'noise', 'buffer', 'bridges', 'brush', 'hamlets', 'favorites', 'processing'];
        let previous;
        try { previous = sessionStorage.getItem('filtermate-home-video'); } catch (_) { /* Storage is optional. */ }
        const candidates = choices.filter((name) => name !== previous);
        const chosen = candidates[Math.floor(Math.random() * candidates.length)];
        heroVideo.dataset.src = 'video/' + chosen + '.mp4';
        heroVideo.poster = 'video/' + chosen + '.webp';
        const watch = document.querySelector('.home-actions [data-watch]');
        if (watch) {
            watch.dataset.video = heroVideo.dataset.src;
            watch.dataset.poster = heroVideo.getAttribute('poster');
        }
        try { sessionStorage.setItem('filtermate-home-video', chosen); } catch (_) { /* Storage is optional. */ }
    }

    // ---------------------------------------------------------------- background footage
    // Videos load only when their sheet comes into view and pause when it leaves.
    // Reduced motion or a data-saving connection keeps the poster; "Watch" still plays.
    const motionPreference = window.matchMedia('(prefers-reduced-motion: reduce)');
    const smallScreen = window.matchMedia('(max-width: 760px)');
    const reduce = motionPreference.matches;
    const conn = navigator.connection || {};
    const frugal = conn.saveData || /(^|-)2g$/.test(conn.effectiveType || '');
    const canAutoplay = () => !motionPreference.matches && !smallScreen.matches && !frugal;
    const videos = Array.from(document.querySelectorAll('video[data-src]'));
    const visibleVideos = new Set();
    let modalOpen = false;

    // ---------------------------------------------------------------- home scroll aids
    // Keep scrolling native: add orientation and shortcuts without intercepting
    // the wheel, trackpad, Page Down or keyboard navigation.
    if (document.body.classList.contains('home')) {
        const french = document.documentElement.lang === 'fr';
        const sectionData = messages.sections || (french
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
            ]);
        const sections = sectionData
            .map(([id, label]) => ({ id, label, node: document.getElementById(id) }))
            .filter((item) => item.node);

        const progress = document.createElement('div');
        progress.className = 'scroll-progress';
        progress.setAttribute('role', 'progressbar');
        progress.setAttribute('aria-label', tr('progress', french ? 'Progression dans la page' : 'Page progress'));
        progress.setAttribute('aria-valuemin', '0');
        progress.setAttribute('aria-valuemax', '100');
        progress.setAttribute('aria-valuenow', '0');
        document.body.appendChild(progress);

        const rail = document.createElement('nav');
        rail.className = 'scroll-rail';
        rail.setAttribute('aria-label', tr('pageSections', french ? 'Sections de la page' : 'Page sections'));
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
        backToTop.setAttribute('aria-label', tr('backTop', french ? 'Revenir en haut' : 'Back to top'));
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

    function syncVideos() {
        videos.forEach((v) => {
            if (!modalOpen && !document.hidden && visibleVideos.has(v)
                && (canAutoplay() || v.closest('.is-watching'))) play(v);
            else v.pause();
        });
    }
    motionPreference.addEventListener('change', syncVideos);
    smallScreen.addEventListener('change', syncVideos);
    document.addEventListener('visibilitychange', syncVideos);

    if ('IntersectionObserver' in window) {
        const io = new IntersectionObserver((entries) => {
            entries.forEach((e) => {
                const v = e.target;
                if (e.isIntersecting) visibleVideos.add(v);
                else visibleVideos.delete(v);
            });
            syncVideos();
        }, { threshold: 0.25 });
        videos.forEach((v) => io.observe(v));
    }

    // ---------------------------------------------------------------- watch mode
    const lightbox = document.getElementById('lightbox');
    const lbVideo = lightbox ? lightbox.querySelector('video') : null;

    function exitWatch(sheet) {
        sheet.classList.remove('is-watching');
        const btn = sheet.querySelector('[data-watch]');
        if (btn) btn.focus();
        const v = sheet.querySelector('video');
        if (v && !canAutoplay()) v.pause();
    }

    function watchVideo(src, poster) {
        modalOpen = true;
        syncVideos();
        lbVideo.src = src;
        lbVideo.poster = poster || '';
        lightbox.showModal();
        const p = lbVideo.play();
        if (p && p.catch) p.catch(() => {});
    }

    document.querySelectorAll('[data-watch]').forEach((btn) => {
        btn.addEventListener('click', () => {
            const holder = btn.closest('.sheet, .band');
            const v = holder && holder.querySelector('video');
            const directSrc = btn.dataset.video;
            if (directSrc && lightbox && lbVideo) {
                watchVideo(directSrc, btn.dataset.poster);
                return;
            }
            if (!v) return;
            if (holder.classList.contains('band') && lightbox && lbVideo) {
                // documentation: a larger player with controls
                watchVideo(v.dataset.src, v.poster);
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
        lightbox.addEventListener('close', () => {
            lbVideo.pause(); lbVideo.removeAttribute('src'); lbVideo.load();
            modalOpen = false;
            syncVideos();
        });
        lightbox.addEventListener('click', (e) => {
            const r = lightbox.getBoundingClientRect();
            if (e.target === lightbox && (e.clientX < r.left || e.clientX > r.right
                || e.clientY < r.top || e.clientY > r.bottom)) lightbox.close();
        });
    }

    // Screenshots remain readable at their native size; the dialog scrolls on
    // narrow screens and a separate link opens the original file.
    const screenshots = Array.from(document.querySelectorAll('figure img'));
    if (screenshots.length) {
        const dialog = document.createElement('dialog');
        dialog.className = 'image-viewer';
        dialog.setAttribute('aria-label', french ? 'Capture agrandie' : 'Enlarged screenshot');
        const close = document.createElement('button');
        close.type = 'button';
        close.textContent = french ? 'Fermer' : 'Close';
        const original = document.createElement('a');
        original.textContent = french ? 'Ouvrir l’image originale' : 'Open original image';
        original.target = '_blank';
        original.rel = 'noopener';
        const toolbar = document.createElement('div');
        toolbar.className = 'image-viewer-toolbar';
        toolbar.append(original, close);
        const viewport = document.createElement('div');
        viewport.className = 'image-viewer-viewport';
        viewport.tabIndex = 0;
        viewport.setAttribute('aria-label', french ? 'Image : faites défiler pour explorer' : 'Image: scroll to explore');
        const full = document.createElement('img');
        const caption = document.createElement('p');
        viewport.append(full);
        dialog.append(toolbar, viewport, caption);
        document.body.append(dialog);
        close.addEventListener('click', () => dialog.close());
        dialog.addEventListener('close', () => { modalOpen = false; syncVideos(); });
        screenshots.forEach((img) => {
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'screenshot-zoom';
            button.setAttribute('aria-label', (french ? 'Agrandir : ' : 'Enlarge: ') + img.alt);
            img.replaceWith(button);
            button.append(img);
            const hint = document.createElement('span');
            hint.textContent = french ? 'Agrandir' : 'Enlarge';
            hint.className = 'zoom-hint';
            button.append(hint);
            button.addEventListener('click', () => {
                full.src = img.currentSrc || img.src;
                full.alt = img.alt;
                original.href = full.src;
                caption.textContent = img.closest('figure').querySelector('figcaption')?.textContent || img.alt;
                modalOpen = true;
                syncVideos();
                dialog.showModal();
                viewport.scrollTo(0, 0);
                close.focus();
            });
        });
    }

    document.querySelectorAll('pre > code').forEach((code) => {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'copy-code';
        button.textContent = french ? 'Copier' : 'Copy';
        code.parentNode.before(button);
        button.addEventListener('click', async () => {
            try {
                await navigator.clipboard.writeText(code.textContent);
                button.textContent = french ? 'Copié !' : 'Copied!';
            } catch (_) {
                const range = document.createRange();
                range.selectNodeContents(code);
                const selection = window.getSelection();
                selection.removeAllRanges(); selection.addRange(range);
                button.textContent = french ? 'Texte sélectionné : copiez-le' : 'Text selected: copy it';
            }
        });
    });

    // ---------------------------------------------------------------- table of contents
    const toc = document.querySelector('.toc');
    if (toc) {
        const compact = window.matchMedia('(max-width: 960px)');
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'toc-toggle';
        button.textContent = french ? 'Sommaire' : 'On this page';
        const list = toc.querySelector('ol');
        list.id = 'toc-sections';
        button.setAttribute('aria-controls', list.id);
        const setOpen = (open) => {
            toc.classList.toggle('toc-collapsed', !open);
            button.setAttribute('aria-expanded', String(open));
        };
        toc.prepend(button);
        toc.classList.add('toc-enhanced');
        setOpen(!compact.matches);
        compact.addEventListener('change', () => setOpen(!compact.matches));
        button.addEventListener('click', () => setOpen(button.getAttribute('aria-expanded') !== 'true'));
        list.addEventListener('click', (e) => {
            if (compact.matches && e.target.closest('a')) {
                setOpen(false);
                button.focus({ preventScroll: true });
            }
        });
    }
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
