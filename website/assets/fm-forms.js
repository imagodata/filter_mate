/* The Tally forms of feedback.html and feedback.fr.html.
 *
 * Form ids come from scripts/tally_forms.py (one per form and language). A null id
 * keeps the section's fallback text (GitHub or e-mail) and embeds nothing, so the
 * page works before the forms exist. The `ref` parameter of the page URL (the
 * plugin menu, the README, a post...) is passed to the form's hidden `ref` field.
 */
(function () {
    var FORMS = {
        usage:    { en: '0V85zP', fr: 'zEMv4Z' },
        review:   { en: '5X95ov', fr: 'db0VXD' },
        feature:  { en: 'laOZXV', fr: 'RWol1v' },
        testers:  { en: 'o9RQY5', fr: 'GepyaQ' },
        services: { en: 'YjGyXz', fr: 'Dqpy9X' }
    };

    // Tally renders these forms with their dashboard theme (LIGHT): the
    // `theme` query parameter does not override it. Their background is
    // transparent, so the box always keeps a light background via CSS and the
    // answers stay readable in the site's light and dark modes alike.
    var lang = (document.documentElement.lang || 'en').slice(0, 2) === 'fr' ? 'fr' : 'en';
    var ref = 'site';
    try {
        ref = (new URLSearchParams(window.location.search).get('ref') || 'site')
            .replace(/[^A-Za-z0-9_-]/g, '').slice(0, 40) || 'site';
    } catch (e) { /* old browser: keep "site" */ }

    var embedded = false;
    var boxes = document.querySelectorAll('[data-fm-form]');
    for (var i = 0; i < boxes.length; i++) {
        var box = boxes[i];
        var id = (FORMS[box.getAttribute('data-fm-form')] || {})[lang];
        var section = box.closest('section') || box.parentNode;
        if (!id) { continue; }
        var frame = document.createElement('iframe');
        frame.setAttribute('data-tally-src', 'https://tally.so/embed/' + id +
            '?alignLeft=1&hideTitle=1&transparentBackground=1&dynamicHeight=1&ref=' +
            encodeURIComponent(ref));
        frame.setAttribute('loading', 'lazy');
        frame.setAttribute('width', '100%');
        frame.setAttribute('height', '420');
        frame.setAttribute('frameborder', '0');
        frame.setAttribute('title', box.getAttribute('data-fm-title') || 'Form');
        box.appendChild(frame);
        box.setAttribute('data-tally-theme', 'light');
        box.hidden = false;
        var soon = section.querySelector('.fm-form-soon');
        var help = section.querySelector('.fm-form-help');
        if (soon) { soon.hidden = true; }
        if (help) { help.hidden = false; }
        embedded = true;
    }
    if (!embedded) { return; }

    var script = document.createElement('script');
    script.src = 'https://tally.so/widgets/embed.js';
    script.async = true;
    script.onload = function () {
        if (window.Tally && window.Tally.loadEmbeds) { window.Tally.loadEmbeds(); }
        // The forms grow as they load: bring the section the link pointed to back into view.
        if (window.location.hash) {
            window.setTimeout(function () {
                var target = document.getElementById(window.location.hash.slice(1));
                if (target) { target.scrollIntoView(); }
            }, 800);
        }
    };
    document.body.appendChild(script);
})();
