// Run with: node --test scripts/tests/site_language.test.cjs
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const root = path.resolve(__dirname, '../../website');
const source = fs.readFileSync(path.join(root, 'assets/fm-language.js'), 'utf8');
const english = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
const links = [...english.matchAll(/<link rel="alternate" hreflang="([^"]+)" href="([^"]+)">/g)]
    .map((match) => ({ hreflang: match[1], href: match[2] }));

function run({ languages = ['en-US'], saved = null, current = 'en', url = 'https://example.test/filter_mate/', denied = false } = {}) {
    const redirects = [];
    const events = {};
    const stored = [];
    const location = new URL(url);
    location.replace = (value) => redirects.push(value);
    vm.runInNewContext(source, {
        URL, URLSearchParams, location,
        navigator: { languages, language: languages[0] },
        localStorage: {
            getItem() { if (denied) throw new Error('Storage blocked'); return saved; },
            setItem(key, value) { if (denied) throw new Error('Storage blocked'); stored.push([key, value]); },
        },
        document: {
            documentElement: { lang: current },
            querySelectorAll: () => links,
            addEventListener: (name, callback) => { events[name] = callback; },
        },
    });
    return { redirects, stored, events };
}

const regional = {
    'es-MX': 'es', 'es-AR': 'es', 'pl-PL': 'pl', 'ja-JP': 'ja', 'it-CH': 'it',
    'ru-RU': 'ru', 'sv-SE': 'sv', 'fr-CA': 'fr', 'de-CH': 'de', 'nl-BE': 'nl',
    'pt-PT': 'pt-br', 'pt-BR': 'pt-br', 'zh-TW': 'zh-hant', 'zh-HK': 'zh-hant',
    'zh-MO': 'zh-hant', 'zh-CN': 'zh-hans', 'zh-SG': 'zh-hans', 'zh': 'zh-hans',
    'zh-Hans-HK': 'zh-hans', 'zh-Hant-CN': 'zh-hant',
};
for (const [language, expected] of Object.entries(regional)) {
    test(`browser variant ${language} resolves to ${expected}`, () => {
        assert.deepEqual(run({ languages: [language] }).redirects, [`https://example.test/filter_mate/index.${expected}.html`]);
    });
}

test('uses the first supported browser language, not necessarily the first language', () => {
    assert.deepEqual(run({ languages: ['xx-XX', 'pl-PL', 'es-ES'] }).redirects, ['https://example.test/filter_mate/index.pl.html']);
});
test('English, unknown languages and an empty language list keep the fallback', () => {
    for (const languages of [['en-GB', 'fr'], ['xx'], []]) assert.deepEqual(run({ languages }).redirects, []);
});
test('keeps fragments, query strings, origin and Pages subdirectory', () => {
    assert.deepEqual(run({ languages: ['es'], url: 'http://localhost:8123/filter_mate/index.html?source=demo#examples' }).redirects,
        ['http://localhost:8123/filter_mate/index.es.html?source=demo#examples']);
});
test('manual preference wins over browser language, including English', () => {
    assert.deepEqual(run({ languages: ['ru'], saved: 'pl' }).redirects, ['https://example.test/filter_mate/index.pl.html']);
    assert.deepEqual(run({ languages: ['ru'], saved: 'en' }).redirects, []);
});
test('an explicit English link stays English even when shared', () => {
    assert.deepEqual(run({ languages: ['ru'], saved: 'pl', url: 'https://example.test/index.html?lang=en#install' }).redirects, []);
});
test('invalid or blocked stored preferences fall back to the browser', () => {
    for (const options of [{ saved: 'unknown' }, { denied: true }]) {
        assert.deepEqual(run({ languages: ['it'], ...options }).redirects, ['https://example.test/filter_mate/index.it.html']);
    }
});
test('explicit translated links are never redirected or saved automatically', () => {
    for (const current of ['fr', 'es', 'pl', 'ja', 'it', 'ru', 'sv']) {
        const result = run({ languages: ['ja'], saved: 'ru', current });
        assert.deepEqual(result.redirects, []);
        assert.deepEqual(result.stored, []);
    }
});
test('only clicks on a language link save a preference; blocked storage is harmless', () => {
    const result = run({ current: 'pl' });
    result.events.click({ target: { closest: () => null } });
    assert.deepEqual(result.stored, []);
    const click = { target: { closest: () => ({ getAttribute: () => 'en' }) } };
    result.events.click(click);
    assert.deepEqual(result.stored, [['filtermate-language', 'en']]);
    assert.doesNotThrow(() => run({ current: 'pl', denied: true }).events.click(click));
});
test('every homepage declares its alternates before detection; docs do not auto-redirect', () => {
    for (const name of fs.readdirSync(root).filter((name) => /^index(?:\.[a-z-]+)?\.html$/.test(name))) {
        const html = fs.readFileSync(path.join(root, name), 'utf8');
        assert.ok(html.lastIndexOf('<link rel="alternate"') < html.indexOf('<script src="assets/fm-language.js"'), name);
        assert.equal((html.match(/data-lang-link/g) || []).length, 13, name);
    }
    for (const name of ['guide.html', 'guide.fr.html', 'stories.html', 'stories.fr.html', 'roadmap.html']) {
        assert.ok(!fs.readFileSync(path.join(root, name), 'utf8').includes('assets/fm-language.js'), name);
    }
});
