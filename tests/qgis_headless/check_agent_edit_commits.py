"""A real agent edit reaches a GeoPackage only after an explicit native Qt confirmation click."""
import os
import sqlite3
import sys
import tempfile
import types
from unittest.mock import MagicMock, patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('FILTERMATE_LOG_DIR', '/tmp/fm-edit-commit-logs')
from qgis.core import QgsApplication, QgsProject, QgsVectorLayer, QgsFeature, QgsGeometry, QgsVectorFileWriter, Qgis
from qgis.PyQt.QtCore import QTranslator

app = QgsApplication([], False)
app.initQgis()
translation = QTranslator()
assert translation.load(os.path.join(os.environ.get('FM_REPO', '/src'), 'i18n', 'FilterMate_fr.qm'))
app.installTranslator(translation)
package = types.ModuleType('filter_mate')
package.__path__ = [os.environ.get('FM_REPO', '/src')]
sys.modules['filter_mate'] = package
from filter_mate.ui.widgets.agent_panel import AgentPanel
from filter_mate.ui.widgets.agent_thread import ConfirmCard
from filter_mate.ui.controllers.agent_edit_commits import LayerEditCommits, _scope
from filter_mate.adapters.public_api import feature_edits
from filter_mate.adapters.agent.turn_effects import EffectsRecorder, apply_effects
from filter_mate.core.agent.messages import ToolCallPart

project = QgsProject.instance()
panel = AgentPanel()
panel.resize(600, 700)
panel.show()
host = types.SimpleNamespace(panel=panel, _memory_generation=0, _refresh_history=MagicMock())
ui = LayerEditCommits(host, project, lambda: False)


def make_layer(name, folder):
    memory = QgsVectorLayer('Point?crs=EPSG:2154&field=value:integer', name, 'memory')
    feature = QgsFeature(memory.fields())
    feature.setGeometry(QgsGeometry.fromWkt('POINT(650000 6860000)'))
    feature.setAttributes([1])
    memory.dataProvider().addFeatures([feature])
    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName, options.layerName = 'GPKG', name
    path = os.path.join(folder, name + '.gpkg')
    result = QgsVectorFileWriter.writeAsVectorFormatV3(memory, path, project.transformContext(), options)
    assert result[0] == QgsVectorFileWriter.WriterError.NoError, result
    layer = QgsVectorLayer(path + '|layername=' + name, name, 'ogr')
    assert layer.isValid()
    project.addMapLayer(layer)
    return layer, path


def disk(path, name):
    connection = sqlite3.connect(path)
    try:
        return connection.execute('SELECT value FROM "' + name + '"').fetchone()[0]
    finally:
        connection.close()


def change(layer, value):
    with patch.object(feature_edits, 'busy_reason', return_value=''):
        result = feature_edits.update_features(layer.id(), values={'value': value}, expression='true')
    assert result['changed'] == 1 and result['unsaved']


def offer(layer):
    ui.offer([(layer.id(), layer.undoStack().index())])
    return panel.findChildren(ConfirmCard)[-1]


with tempfile.TemporaryDirectory(prefix='fm-edit-commit-') as folder:
    layer, path = make_layer('agent_edits', folder)
    recorder = EffectsRecorder()
    recorder.before_call(ToolCallPart('edit', 'update_features', {'layer': layer.id()}))
    change(layer, 2)
    effects = recorder.finish()
    card = offer(layer)
    assert card.yes_button.text() == 'Enregistrer les modifications'
    assert card.always_button is None and disk(path, 'agent_edits') == 1
    card.no_button.click()
    assert layer.isEditable() and layer.isModified() and disk(path, 'agent_edits') == 1
    done, left = apply_effects(effects, undo=True)
    assert done and not left and disk(path, 'agent_edits') == 1
    print('PASS edit stays buffered, refusal preserves pending edits and agent Undo still works', flush=True)

    change(layer, 3)
    card = offer(layer)
    card.yes_button.click()
    assert disk(path, 'agent_edits') == 3 and not layer.isEditable()
    assert host._refresh_history.call_count == 1
    print('PASS explicit user click commits the real GeoPackage and closes editing', flush=True)

    change(layer, 4)
    card = offer(layer)
    change(layer, 5)
    assert card.done and not card.yes_button.isEnabled()
    card.yes_button.click()
    assert disk(path, 'agent_edits') == 3
    # A later explicit confirmation clearly covers manual edits as well.
    card = offer(layer)
    card.yes_button.click()
    assert disk(path, 'agent_edits') == 5
    print('PASS further edits expire the old confirmation; a fresh click saves reviewed pending edits', flush=True)

    ui.close()
    project.clear()
    project.setTransactionMode(Qgis.TransactionMode.BufferedGroups)
    first, first_path = make_layer('group_agent', folder)
    second, second_path = make_layer('group_manual', folder)
    assert project.startEditing(first)
    assert second.isEditable()
    change(first, 10)
    change(second, 20)
    assert {item.id() for item in _scope(project, first)} == {first.id(), second.id()}
    card = offer(first)
    assert {label.text() for label in card._layer_chips} == {'group_agent', 'group_manual'}
    assert disk(first_path, 'group_agent') == disk(second_path, 'group_manual') == 1
    card.yes_button.click()
    assert disk(first_path, 'group_agent') == 10 and disk(second_path, 'group_manual') == 20
    assert not first.isEditable() and not second.isEditable()
    print('PASS real buffered transaction group lists and saves companion manual edits together', flush=True)
    ui.close()
    project.clear()
print(f'PASS QGIS {Qgis.QGIS_VERSION}: separate confirmation for durable agent edits', flush=True)
os._exit(0)
