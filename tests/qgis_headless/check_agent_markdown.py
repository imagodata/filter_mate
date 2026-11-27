"""Rich Markdown and responsive tables with real Qt text layout, links and clipboard.

QT_QPA_PLATFORM=offscreen python3 tests/qgis_headless/check_agent_markdown.py
Set FM_REPO to the checkout and FM_MARKDOWN_SHOTS to a writable screenshot folder when desired.
"""
import os
from pathlib import Path
import sys
import tempfile
import time
import traceback
import types

sys.dont_write_bytecode = True
package = types.ModuleType('filter_mate')
package.__path__ = [os.environ.get('FM_REPO', '/src')]
sys.modules['filter_mate'] = package
os.environ['FILTERMATE_LOG_DIR'] = tempfile.mkdtemp(prefix='fm-markdown-logs-')

from qgis.core import QgsApplication  # noqa: E402 - environment and package set before QGIS imports
from qgis.PyQt.QtCore import Qt  # noqa: E402
from qgis.PyQt.QtGui import QTextDocument  # noqa: E402
from qgis.PyQt.QtTest import QTest  # noqa: E402

app = QgsApplication([], False)
app.initQgis()


def check(label, condition):
    assert condition, label
    print('PASS ' + label, flush=True)


def settle():
    until = time.monotonic() + 0.15
    while time.monotonic() < until:
        app.processEvents()
        time.sleep(0.002)


def document(label):
    result = QTextDocument()
    result.setDefaultFont(label.font())
    result.setDocumentMargin(0)
    result.setHtml(label.text())
    result.setTextWidth(label.width())
    return result


def main():
    from filter_mate.ui.styles.mockup_design import tokens
    from filter_mate.ui.widgets.agent_markdown import LayerReference, FileReference, output_href
    from filter_mate.ui.widgets.agent_thread import AgentThread, ZWSP

    dark = [False]
    thread = AgentThread(lambda: tokens(dark[0]), lambda: dark[0], lambda: None)
    thread.layer_references = lambda: (LayerReference('communes', 'Communes', 'Données'),)
    file = FileReference('/chosen/cartes/bilan.pdf', 'bilan.pdf')
    thread.file_references = lambda: (file,)
    selected, opened = [], []
    thread.on_layer = selected.append
    thread.on_file = opened.append
    thread.resize(760, 760)
    thread.show()
    source = (
        '# Bilan territorial\n'
        'Les **résultats** sont disponibles pour Communes. ~~Ancienne version~~\n\n'
        '> **Lecture**\n> Les valeurs restent comparables entre les territoires.\n\n'
        '| Couche | Type | Objets | Résultat |\n|:---|:---:|---:|:---|\n'
        '| Communes | Vecteur | 125 | [**Bilan PDF**](bilan.pdf) |\n'
        '| Routes | Vecteur | 1 842 | Intersection |\n'
        '| Terrain | Raster | 42 | Altitude |\n\n'
        '## Étapes\n1. Préparer les données\n   - Vérifier le SCR\n   - Examiner les champs\n'
        '2. Exporter\n\n- [x] Vérifié\n- [ ] À partager\n\n'
        '```sql\nSELECT "nom", "population"\nFROM communes\nWHERE "population" > 1000;\n```'
    )
    # A header split over streaming fragments becomes a complete table when the separator arrives.
    for offset in range(0, len(source), 27):
        thread.add_text(source[offset:offset + 27])
    thread.end_answer()
    settle()
    item = next(item for item in thread._items if item.kind == 'text')
    label = item.widget
    check('Markdown streaming retains the exact original text', thread.toPlainText() == source)
    check('a wide conversation renders a real four-column table', label.text().count('<table') == 1
          and label.text().count('<th') == 4)
    check('Qt draws lists, checkboxes, quotes and code without Markdown delimiters',
          all(text in document(label).toPlainText() for text in ('Bilan territorial', 'Préparer', '☑', 'SELECT'))
          and '|:---' not in document(label).toPlainText())
    label.linkActivated.emit('layer:id/communes')
    label.linkActivated.emit(output_href(file.path))
    check('formatted table links retain the registered layer and output targets',
          selected == ['communes'] and opened == [file.path])
    folder = os.environ.get('FM_MARKDOWN_SHOTS')
    if folder:
        Path(folder).mkdir(parents=True, exist_ok=True)
        thread.grab().save(str(Path(folder) / 'wide-light.png'))

    for width in (340, 760, 300, 760):
        thread.resize(width, 760)
        settle()
        expected = 3 if width < 500 else 1
        check(f'tables adapt after resizing to {width} px', label.text().count('<table') == expected)
        doc = document(label)
        check(f'all table values remain present at {width} px',
              all(text in doc.toPlainText() for text in ('1 842', '125', '42', 'Altitude', 'Bilan PDF')))
        check(f'Qt content fits within the conversation at {width} px',
              doc.idealWidth() <= label.width() + 2 and label.geometry().right() <= thread.widget().width())
        if folder and width == 340:
            thread.verticalScrollBar().setValue(0)
            app.processEvents()
            thread.grab().save(str(Path(folder) / 'narrow-light.png'))

    dark[0] = True
    thread.refresh_look()
    settle()
    check('tables and code take the dark theme when it changes', tokens(True)['fm_group'] in label.text()
          and tokens(False)['fm_group'] not in label.text())
    if folder:
        thread.grab().save(str(Path(folder) / 'wide-dark.png'))

    path = '/chosen/' + 'dossier_tres_long/' * 8 + 'carte.gpkg'
    thread.clear()
    thread.add_text('Chemin | Objets\n---|---:\n`' + path + '` | 1')
    thread.end_answer()
    settle()
    label = next(item.widget for item in thread._items if item.kind == 'text')
    rendered = document(label).toPlainText()
    label.setFocus()
    label.setSelection(0, len(rendered))
    QTest.keyClick(label, Qt.Key.Key_C, Qt.KeyboardModifier.ControlModifier)
    settle()
    check('copying a table keeps its path without invisible wrap characters',
          path in app.clipboard().text() and ZWSP not in app.clipboard().text())

    thread.clear()
    thread.add_text('```text\n' + path + '\n```')
    thread.end_answer()
    settle()
    label = next(item.widget for item in thread._items if item.kind == 'text')
    rendered = document(label).toPlainText()
    check('long code paths wrap without widening the conversation', ZWSP in rendered
          and document(label).idealWidth() <= label.width() + 2)
    label.setFocus()
    label.setSelection(0, len(rendered))
    QTest.keyClick(label, Qt.Key.Key_C, Qt.KeyboardModifier.ControlModifier)
    settle()
    check('copying code removes invisible wrap characters and keeps the path',
          path in app.clipboard().text() and ZWSP not in app.clipboard().text())
    thread.clear()
    settle()
    thread.close()
    print('All native Markdown checks passed', flush=True)


try:
    main()
except Exception:
    traceback.print_exc()
    os._exit(1)
os._exit(0)
