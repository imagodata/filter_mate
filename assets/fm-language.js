// Homepage only. Alternate links are the single source of supported languages.
(function () {
    'use strict';
    const storageKey = 'filtermate-language';
    const languages = new Map();
    document.querySelectorAll('link[rel="alternate"][hreflang]').forEach((link) => {
        if (link.hreflang !== 'x-default') languages.set(link.hreflang.toLowerCase(), link.href);
    });

    function resolve(language) {
        const tag = String(language || '').toLowerCase().replace(/_/g, '-');
        if (languages.has(tag)) return tag;
        const base = tag.split('-')[0];
        if (base === 'zh') {
            // An explicit script takes precedence over the regional default.
            if (tag.includes('-hans')) return 'zh-hans';
            if (tag.includes('-hant')) return 'zh-hant';
            return /-(tw|hk|mo)(-|$)/.test(tag) ? 'zh-hant' : 'zh-hans';
        }
        if (base === 'pt' && languages.has('pt-br')) return 'pt-br';
        return languages.has(base) ? base : null;
    }

    // Explicit translated URLs are shareable and must never be redirected.
    // Only the default English entry point negotiates the browser preference.
    if (document.documentElement.lang === 'en') {
        // The English menu link also stays English when shared in another browser.
        let preferred = new URLSearchParams(location.search).get('lang') === 'en' ? 'en' : null;
        if (!preferred) {
            try { preferred = resolve(localStorage.getItem(storageKey)); } catch (_) { /* Storage may be disabled. */ }
        }
        if (!preferred) {
            const requested = navigator.languages?.length ? navigator.languages : [navigator.language];
            preferred = requested.map(resolve).find(Boolean) || 'en';
        }
        if (preferred !== 'en' && languages.has(preferred)) {
            const destination = new URL(languages.get(preferred));
            // Resolve locally as well as on GitHub Pages; never change origin.
            const filename = destination.pathname.split('/').pop();
            const target = new URL(filename, location.href);
            target.search = location.search;
            target.hash = location.hash;
            location.replace(target.href);
            return;
        }
    }

    // Store only explicit choices. Browser detection is not a permanent choice.
    document.addEventListener('click', (event) => {
        const link = event.target.closest?.('[data-lang-link]');
        if (!link) return;
        const language = resolve(link.getAttribute('hreflang'));
        if (language) {
            try { localStorage.setItem(storageKey, language); } catch (_) { /* Navigation still works. */ }
        }
    });
})();
