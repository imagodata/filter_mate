"""Check the article's local assets and rebuild its publication/project ZIPs.

Run with Python 3 and pypdf after write_english.py, render_assets.py and PDF printing.
The source datasets and the portable QGIS project are not changed.
"""
from pathlib import Path
from datetime import datetime
from html.parser import HTMLParser
import hashlib
import json
import re
import subprocess
import zipfile

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent.parent
STEMS = ['00_sarlat_overview', '01_roads_buildings', '02_church_dtm_lidar',
         '03_slope_parcels', '04_ndvi_parcels', '05_high_vegetation_roads']


def digest(path):
    with path.open('rb') as file:
        return hashlib.file_digest(file, 'sha256').hexdigest()


def asset(path):
    return {'file': path.relative_to(ROOT).as_posix(),
            'bytes': path.stat().st_size, 'sha256': digest(path)}


class AssetLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.images = []
        self.local_links = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'img':
            assert attrs.get('alt'), 'Missing image alt text'
            self.images.append(attrs['src'])
        if tag == 'a' and 'href' in attrs and '://' not in attrs['href']:
            self.local_links.append(attrs['href'])


html = AssetLinks()
html.feed((ROOT / 'linkedin-article.html').read_text())
assert len(html.images) == 12
for name in html.images + html.local_links:
    assert (ROOT / name).is_file(), name

exports = json.loads((ROOT / 'image-exports.json').read_text())
dimensions = {item['file']: [item['width'], item['height']] for item in exports}
for stem in STEMS:
    assert dimensions[f'screenshots/{stem}.jpg'] == [3030, 2070]
    assert dimensions[f'screenshots/{stem}-settings.jpg'][0] == 900

capture = json.loads((ROOT / 'capture-validation.json').read_text())
widgets = capture['widget_checks']
assert len(widgets) in (6, 7)
preparatory = len(widgets) == 7
saved_checks = widgets[int(preparatory):]
assert all(value == 1.0 for item in saved_checks for value in item['widgets'].values())
assert not capture['python_errors']
failed = [name for status, name in capture['checks'] if status == 'FAIL']
assert failed == (['vector: critical widgets fully visible'] if preparatory else [])

pdf = PdfReader(ROOT / 'linkedin-article.pdf')
pdf_text = '\n'.join(page.extract_text() for page in pdf.pages)
for text in ['113 buildings', '106 parcels', '321 parcels', '12 parcels', '6 of 9']:
    assert text in pdf_text, text
assert sum(len(page.images) for page in pdf.pages) == 12
assert len(pdf.pages) == 12

manifest = json.loads((ROOT / 'manifest.json').read_text())
for name, previous in manifest['datasets'].items():
    path = ROOT / 'data' / name
    assert digest(path) == previous['sha256'], 'Dataset changed: ' + name
assert json.loads((ROOT / 'project-validation.json').read_text())['ok']
with zipfile.ZipFile(ROOT / 'sarlat-verified-layers.qgz') as project:
    xml = project.read(next(name for name in project.namelist() if name.endswith('.qgs'))).decode()
    assert xml.count('<maplayer ') == 7
    assert './data/' in xml

summary = {
    'language': 'en', 'site': 'Sarlat-la-Canéda, France',
    'full_window_dimensions_px': [3030, 2070],
    'qgis_context': ['Layers', 'Browser', 'menus', 'toolbars', 'status bar'],
    'saved_widget_checks': dict(zip(STEMS, saved_checks)),
    'all_saved_critical_widgets_fully_visible': True,
    'preparatory_check': {
        'present': preparatory,
        'note': 'The first pre-capture layout check ran before the dock settled. '
                'The subsequent overview check and all five scenario checks passed. '
                'The original log and recorded failure are retained.',
    },
    'python_errors': capture['python_errors'],
    'scenario_results': capture['scenario_results'],
    'terrain_display': json.loads((ROOT / 'terrain-display.json').read_text()),
    'html_images': len(html.images), 'local_links_resolve': True,
    'pdf_pages': len(pdf.pages), 'pdf_images': 12,
    'native_project_validation_retained': True, 'source_dataset_hashes_unchanged': True,
    'visual_review': 'Reviewed the six-window overview, full street-corridor capture, '
                     'slope/NDVI/LiDAR control details and PDF terrain/NDVI pages.',
}
(ROOT / 'verification-summary.json').write_text(json.dumps(summary, indent=2, ensure_ascii=False) + '\n')

manifest['updated'] = datetime.now().astimezone().isoformat()
manifest['article_word_count'] = len((ROOT / 'linkedin-article.txt').read_text().split())
manifest['post_characters'] = len((ROOT / 'linkedin-post.txt').read_text())
manifest.setdefault('original_publication_checkout', manifest.get('source_checkout'))
manifest.pop('source_checkout', None)
manifest['source_checkout_at_packaging'] = subprocess.check_output(
    ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
manifest['source_checkout_note'] = (
    'Captured from a local working copy copied to an isolated QGIS profile. '
    'The repository was updated independently after capture; the packaging commit '
    'is recorded for context and does not identify the exact captured source tree.')
manifest['screenshots'] = [asset(ROOT / 'screenshots' / (stem + '.jpg')) for stem in STEMS]
manifest['widget_details'] = [asset(ROOT / 'screenshots' / (stem + '-settings.jpg')) for stem in STEMS[1:]]
manifest['pdf'] = {**asset(ROOT / 'linkedin-article.pdf'), 'pages': len(pdf.pages)}
manifest['image_exports'] = exports
(ROOT / 'manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n')


def archive(destination, prefix, paths):
    temporary = destination.with_suffix('.tmp.zip')
    with zipfile.ZipFile(temporary, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=3) as zipped:
        for path in sorted(paths):
            zipped.write(path, prefix + '/' + path.relative_to(ROOT).as_posix(),
                         compress_type=zipfile.ZIP_STORED if path.suffix == '.laz' else zipfile.ZIP_DEFLATED)
    with zipfile.ZipFile(temporary) as zipped:
        assert zipped.testzip() is None
    temporary.replace(destination)
    print(destination.name, round(destination.stat().st_size / 2**20, 1), 'MiB')


publication_files = [path for path in ROOT.rglob('*') if path.is_file()
                     and path.relative_to(ROOT).parts[0] != 'data'
                     and path.suffix != '.qgz' and '__pycache__' not in path.parts]
archive(ROOT.parent / 'filtermate-v5-linkedin-english.zip', ROOT.name, publication_files)
project_files = [ROOT / name for name in (
    'sarlat-verified-layers.qgz', 'data-validation.txt', 'data-audit.json', 'sources.json',
    'manifest.json', 'project-validation.json', 'verification-summary.json',
    'capture-validation.json', 'terrain-display.json',
)] + list((ROOT / 'data').iterdir())
archive(ROOT.parent / 'filtermate-v5-sarlat-qgis.zip', 'filtermate-v5-sarlat', project_files)
print('Verified: six full QGIS windows, all saved key widgets, 12 illustrated PDF pages, unchanged GIS data.')
