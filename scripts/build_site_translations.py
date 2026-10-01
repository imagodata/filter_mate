"""Generate translated landing pages from the English HTML and reviewed messages.

Run after updating website/index.html or website/i18n/home.json. Missing messages
fail the build; guides and use cases deliberately remain linked in English.
"""
import argparse
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / 'website'
LANGUAGES = {
    'en': ('English', 'index.html'), 'fr': ('Français', 'index.fr.html'),
    'de': ('Deutsch', 'index.de.html'), 'es': ('Español', 'index.es.html'),
    'it': ('Italiano', 'index.it.html'), 'ja': ('日本語', 'index.ja.html'),
    'nl': ('Nederlands', 'index.nl.html'), 'pl': ('Polski', 'index.pl.html'),
    'pt-BR': ('Português (Brasil)', 'index.pt-br.html'), 'ru': ('Русский', 'index.ru.html'),
    'sv': ('Svenska', 'index.sv.html'),
    'zh-Hant': ('繁體中文', 'index.zh-hant.html'),
    'zh-Hans': ('简体中文', 'index.zh-hans.html'),
}


def switcher(lang):
    links = ''.join(
        f'<li><a href="{filename}{"?lang=en" if code == "en" else ""}" lang="{code}" hreflang="{code}" data-lang-link'
        + (' aria-current="true"' if code == lang else '')
        + f'>{label}</a></li>' for code, (label, filename) in LANGUAGES.items()
    )
    return f'<details class="language-menu"><summary>{LANGUAGES[lang][0]}</summary><ul>{links}</ul></details>'


def alternates():
    return '\n'.join(
        f'    <link rel="alternate" hreflang="{lang}" href="https://imagodata.github.io/filter_mate/{filename if lang != "en" else ""}">'
        for lang, (_, filename) in LANGUAGES.items()
    ) + '\n    <link rel="alternate" hreflang="x-default" href="https://imagodata.github.io/filter_mate/">'


def insert_alternates(source):
    marker = '    <script src="assets/fm-language.js"' if 'src="assets/fm-language.js"' in source else '    <link rel="icon"'
    return source.replace(marker, alternates() + '\n' + marker, 1)


def update_languages(source, lang):
    source = re.sub(r'    <link rel="alternate"[^>]+>\n?', '', source)
    source = insert_alternates(source)
    source = re.sub(r'<span class="lang"[^>]*>.*?</span>', switcher(lang), source)
    source = re.sub(r'<details class="language-menu">.*?</details>', switcher(lang), source)
    return source


def build(check=False):
    data = json.loads((ROOT / 'i18n/home.json').read_text(encoding='utf-8'))
    if len(set(data['languages'])) != len(data['languages']):
        raise ValueError('Duplicate translation languages')
    if set(data['languages']) != set(LANGUAGES) - {'en', 'fr'}:
        raise ValueError('Translations must cover every language in the switcher except English and French')
    required_ui = {'openMenu', 'closeMenu', 'progress', 'pageSections', 'backTop', 'sections'}
    section_ids = ['top', 'workflow', 'examples', 'capabilities', 'performance', 'install']
    for lang in data['languages']:
        ui = data['ui'].get(lang, {})
        if not required_ui <= ui.keys() or not all(ui.values()):
            raise ValueError(f'Missing navigation translations: {lang}')
        if [item[0] for item in ui['sections']] != section_ids or not all(item[1] for item in ui['sections']):
            raise ValueError(f'Invalid section navigation: {lang}')
    keys = [row[0] for row in data['messages']]
    if len(set(keys)) != len(keys):
        raise ValueError('Duplicate source messages')
    if any(len(row) != len(data['languages']) + 1 or not all(row) for row in data['messages']):
        raise ValueError('Every message needs one non-empty translation per language')
    stale = []

    def write(file, content):
        if check:
            if not file.exists() or file.read_text(encoding='utf-8') != content:
                stale.append(str(file.relative_to(ROOT)))
        else:
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text(content, encoding='utf-8')

    english = (ROOT / 'index.html').read_text(encoding='utf-8')
    # Translate before injecting the autonyms, which stay unchanged in every locale.
    template = re.sub(r'<(?:span class="lang"[^>]*|details class="language-menu")>.*?</(?:span|details)>', '__LANGUAGE_MENU__', english)
    template = re.sub(r'    <link rel="alternate"[^>]+>\n?', '', template)
    keep = {'FilterMate', 'GitHub', 'Discord', 'PostgreSQL', 'SpatiaLite', 'OGR', 'GPL-3.0', 'EN', 'FR', '< 1 s', '→'}
    for index, lang in enumerate(data['languages']):
        messages = {row[0]: row[index + 1] for row in data['messages']}
        missing = set()

        def translate(value):
            raw = html.unescape(value.strip())
            if not raw or raw in keep or not any(c.isalpha() for c in raw):
                return value
            if raw not in messages:
                missing.add(raw)
                return value
            return value.replace(value.strip(), html.escape(messages[raw], quote=True))

        tokens = re.split(r'(<!--.*?-->|<[^>]+>)', template, flags=re.S)
        for i, token in enumerate(tokens):
            if token.startswith('<!--'):
                continue
            if token.startswith('<'):
                token = re.sub(r'((?:alt|aria-label)=")([^"]*)(")', lambda m: m[1] + translate(m[2]) + m[3], token)
                if re.match(r'<meta\s+(?:name="description"|property="og:(?:title|description)")', token):
                    token = re.sub(r'(content=")([^"]*)(")', lambda m: m[1] + translate(m[2]) + m[3], token)
                tokens[i] = token
            elif '__LANGUAGE_MENU__' not in token:
                tokens[i] = translate(token)
        if missing:
            raise ValueError(f'Missing {lang} translations: {sorted(missing)}')
        page = ''.join(tokens).replace('__LANGUAGE_MENU__', switcher(lang))
        filename = LANGUAGES[lang][1]
        page = page.replace('<html lang="en">', f'<html lang="{lang}">')
        page = page.replace('href="index.html"', f'href="{filename}"', 1)
        # Brand/footer home links, but not the English item in the language menu.
        page = page.replace('href="index.html" class="nav-brand"', f'href="{filename}" class="nav-brand"')
        page = page.replace('content="https://imagodata.github.io/filter_mate/"', f'content="https://imagodata.github.io/filter_mate/{filename}"')
        page = page.replace('rel="canonical" href="https://imagodata.github.io/filter_mate/"', f'rel="canonical" href="https://imagodata.github.io/filter_mate/{filename}"')
        page = insert_alternates(page)
        for target in ('guide.html', 'stories.html', 'roadmap.html'):
            page = re.sub(r'(<a\b[^>]*href="' + re.escape(target) + r'(?:#[^"]*)?"[^>]*>)(.*?)(</a>)',
                          lambda m: m[1].replace('>', ' hreflang="en">', 1) + m[2] + ' <small lang="en">(EN)</small>' + m[3], page)
        page = page.replace('<script src="assets/fm.js">', f'<script src="assets/i18n/{lang.lower()}.js"></script>\n<script src="assets/fm.js">')
        write(ROOT / filename, page)
        ui = data['ui'][lang]
        directory = ROOT / 'assets/i18n'
        write(directory / f'{lang.lower()}.js', 'window.FM_I18N = ' + json.dumps(ui, ensure_ascii=False) + ';\n')
    for lang in ('en', 'fr'):
        file = ROOT / LANGUAGES[lang][1]
        write(file, update_languages(file.read_text(encoding='utf-8'), lang))
    urls = [filename for _, filename in LANGUAGES.values()] + ['guide.html', 'guide.fr.html', 'stories.html', 'stories.fr.html', 'roadmap.html']
    sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    sitemap += ''.join(f'  <url><loc>https://imagodata.github.io/filter_mate/{name if name != "index.html" else ""}</loc></url>\n' for name in urls)
    write(ROOT / 'sitemap.xml', sitemap + '</urlset>\n')
    if stale:
        raise ValueError('Run python3 scripts/build_site_translations.py to update: ' + ', '.join(stale))
    print(f'{"Checked" if check else "Generated"} {len(data["languages"])} landing pages and sitemap.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Fail if generated files are missing or stale; do not write files')
    build(check=parser.parse_args().check)
