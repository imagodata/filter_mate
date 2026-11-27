"""Welcome discovery and project requests on real QGIS/Qt, without network or an AI provider.

    docker run --rm --network none -e QT_QPA_PLATFORM=offscreen -v "$PWD:/src:ro" \
        qgis/qgis:ltr python3 /src/tests/qgis_headless/check_welcome_examples.py

FM_WELCOME_SCREENSHOTS optionally names a writable folder for the two French UI previews.
"""
import os
from pathlib import Path
import sys
import tempfile

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ['QGIS_CUSTOM_CONFIG_PATH'] = tempfile.mkdtemp()

from qgis.core import QgsApplication, QgsCoordinateReferenceSystem, QgsProject, QgsRectangle, QgsVectorLayer  # noqa: E402
from qgis.gui import QgsMapCanvas  # noqa: E402
from qgis.PyQt.QtCore import QSettings, QTranslator, QT_VERSION_STR  # noqa: E402


def main():
    app = QgsApplication([], True)
    app.initQgis()
    package_root = tempfile.mkdtemp()
    root = Path(__file__).resolve().parents[2]
    os.symlink(root, Path(package_root) / 'filter_mate')
    sys.path.insert(0, package_root)
    from filter_mate.adapters.qgis.project_facts import read_facts
    from filter_mate.core.agent.example_prompts import CATALOG, DATA, PROJECT
    from filter_mate.ui.widgets.agent_panel import AgentPanel

    translator = QTranslator()
    assert translator.load(str(root / 'i18n/FilterMate_fr.qm'))
    app.installTranslator(translator)
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, tempfile.mkdtemp())
    QSettings().setValue('locale/userLocale', 'fr_FR')
    catalog = {example.key: example for example in CATALOG}
    project = QgsProject()
    canvas = QgsMapCanvas()
    canvas.resize(500, 500)
    canvas.setDestinationCrs(QgsCoordinateReferenceSystem('EPSG:4326'))
    canvas.setExtent(QgsRectangle(135.76, 35.00, 135.78, 35.02))
    active = [None]
    panel = AgentPanel()
    panel.facts_provider = lambda: read_facts(project, active[0], canvas)
    panel.set_ready(True, 'Modèle local')
    panel.resize(420, 800)
    panel.show()
    panel.refresh_examples()
    app.processEvents()
    assert panel.more_examples_button.text() == 'Autres idées'
    assert all(catalog[key].group == DATA for key in panel.example_keys)
    assert all(panel.example_places[key].name in button.request() and 'km' in button.request()
               for key, button in zip(panel.example_keys, panel.example_buttons))
    before = {p.id for p in panel.example_places.values()}
    panel.more_examples_button.click()
    app.processEvents()
    assert not before & {p.id for p in panel.example_places.values()}
    button = panel.example_buttons[0]
    button.click()
    assert panel.input.text() == button.request()
    assert canvas.extent().xMinimum() > 135  # drawing/clicking a suggestion never moves the map
    screenshots = os.environ.get('FM_WELCOME_SCREENSHOTS')
    if screenshots:
        Path(screenshots).mkdir(parents=True, exist_ok=True)
        panel.grab().save(str(Path(screenshots) / f'welcome-empty-qt{QT_VERSION_STR[0]}.png'))
    print(f'PASS Qt {QT_VERSION_STR}: French discovery, other ideas, exact editable request, no map mutation', flush=True)

    layer = QgsVectorLayer('Point?crs=EPSG:4326&field=fid:integer&field=usage:string&field=height_m:double', 'Bâtiments', 'memory')
    project.addMapLayer(layer)
    active[:] = [layer]
    panel.refresh_examples()
    facts = panel._examples_facts
    assert facts.known and facts.active_name == 'Bâtiments'
    assert facts.field('numeric') == 'height_m' and facts.field('text') == 'usage'
    assert facts.focus.country == 'jp'  # France is only the UI language
    assert sum(catalog[key].group == PROJECT for key in panel.example_keys) == 3
    panel._set_examples(('color_by', 'numeric_summary', 'labels', 'osm_cycle'), facts)
    texts = [b.request() for b in panel.example_buttons]
    assert 'Bâtiments' in texts[0] and 'usage' in texts[0] and 'height_m' in texts[1]
    assert 'Kyoto' in texts[3] and 'IGN' not in texts[3]
    layer.setName('Parcelles')
    panel.refresh_examples()
    assert 'Parcelles' in panel.example_buttons[0].request() and 'Bâtiments' not in panel.example_buttons[0].request()
    app.processEvents()
    if screenshots:
        panel.grab().save(str(Path(screenshots) / f'welcome-project-qt{QT_VERSION_STR[0]}.png'))
    # Preserve a valid schema, then remove the fields that the examples depend on.
    layer.dataProvider().deleteAttributes([layer.fields().indexFromName(name) for name in ('usage', 'height_m')])
    layer.updateFields()
    panel.refresh_examples()
    assert not {'color_by', 'numeric_summary', 'labels', 'slider_histogram'} & set(panel.example_keys)
    panel.stop_following()
    panel.close()
    print(f'PASS Qt {QT_VERSION_STR}: cached schema, project relevance, real layer/field names, map geography, invalidation', flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        os._exit(1)
    os._exit(0)
