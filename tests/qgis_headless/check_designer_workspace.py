"""Native Designer drafts/preferences and read-only design inventory; theme operations use real QGIS state."""
import json
import os
import sys
import types
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('FILTERMATE_LOG_DIR', '/tmp/fm-designer-logs')
from qgis.core import QgsApplication, QgsProject, QgsVectorLayer, QgsPrintLayout, QgsSettings, Qgis
from qgis.gui import QgsMapCanvas
from qgis.PyQt.QtCore import QTranslator
from qgis.PyQt.QtWidgets import QMainWindow

app = QgsApplication([], False)
app.initQgis()
root = Path(os.environ.get('FM_REPO', '/src'))
translator = QTranslator()
assert translator.load(str(root / 'i18n/FilterMate_fr.qm'))
app.installTranslator(translator)
package = types.ModuleType('filter_mate')
package.__path__ = [str(root)]
sys.modules['filter_mate'] = package
from filter_mate.adapters.agent.settings import read_designer_mode, write_designer_mode
from filter_mate.adapters.public_api.qgis_interface import qgis_capabilities
from filter_mate.adapters.public_api.layer_tree import map_theme, themes_xml
from filter_mate.ui.widgets.agent_panel import AgentPanel

project = QgsProject.instance()
layer = QgsVectorLayer('Point?crs=EPSG:2154&field=value:integer', 'Communes', 'memory')
project.addMapLayer(layer)
node = project.layerTreeRoot().findLayer(layer.id())
map_theme('save', 'Vue générale')
node.setItemVisibilityChecked(False)
map_theme('save', 'Sans points')
map_theme('apply', 'Vue générale')
assert node.isVisible()
map_theme('apply', 'Sans points')
assert not node.isVisible()
map_theme('apply', 'Vue générale')
layout = QgsPrintLayout(project)
layout.initializeDefaults()
layout.setName('Rapport A4')
project.layoutManager().addLayout(layout)
before_xml = themes_xml()
project.setDirty(False)
window = QMainWindow()
canvas = QgsMapCanvas(window)
face = types.SimpleNamespace(mainWindow=lambda: window, mapCanvas=lambda: canvas)
inventory = qgis_capabilities(face)['project_assets']
assert inventory['map_themes'] == ['Sans points', 'Vue générale']
assert inventory['layouts'] == ['Rapport A4']
assert not project.isDirty() and themes_xml() == before_xml and node.isVisible()
print('PASS real theme save/apply and print layout inventory, observational discovery', flush=True)

settings = QgsSettings()
settings.remove('filter_mate/agent/designer_mode')
assert not read_designer_mode()
settings.setValue('filter_mate/agent/mode', 'respond')
write_designer_mode(True)
assert read_designer_mode() and settings.value('filter_mate/agent/mode') == 'respond'
panel = AgentPanel()
panel.set_ready(True, 'Test')
panel.set_designer_mode(read_designer_mode())
panel.set_mode('respond')
assert panel.designer_action.text() == 'Atelier Designer avancé'
sent = []
panel.send_requested.connect(sent.append)
panel.show()
for dark in (False, True):
    panel._dark = lambda: dark
    panel._refresh_look()
    for width in (280, 360):
        panel.resize(width, 640)
        app.processEvents()
        assert panel.width() == width and panel.designer_frame.isVisible()
        assert all(button.width() > 0 for button in panel.designer_buttons.values())
        panel.input.setText('Mon brouillon')
        panel.designer_buttons['brainstorm'].click()
        assert panel.input.text().startswith('Mon brouillon\n\nAide-moi')
        before = panel.input.text()
        panel.designer_buttons['brainstorm'].click()
        assert panel.input.text() == before
        panel.input.clear()
        panel.designer_buttons['themes'].click()
        assert 'thèmes cartographiques' in panel.input.text()
    panel.input.clear()
    panel.add_text('Atelier Designer : styles, mises en page et thèmes cartographiques.\nChoisissez une piste à affiner.')
    panel.resize(420, 640)
    app.processEvents()
    panel.grab().save(f'/audit/fm-designer-{"dark" if dark else "light"}.png')
assert not sent and panel._posture == 'respond'
assert not project.isDirty() and themes_xml() == before_xml
panel.set_working(True)
assert not panel.designer_action.isEnabled()
panel.set_working(False)
write_designer_mode(False)
panel.set_designer_mode(read_designer_mode())
assert not panel.designer_frame.isVisible()
print('PASS French Designer, editable drafts, persistent independent preference, narrow light/dark dock', flush=True)
out = os.environ.get('FM_DESIGNER_OUTPUT', '/audit/fm-designer.json')
Path(out).write_text(json.dumps({'qgis': Qgis.QGIS_VERSION, 'checks_passed': True,
                                'project_assets': inventory}, ensure_ascii=False, indent=2))
panel.close()
os._exit(0)
