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
