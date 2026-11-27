import json
import os
import sys
import tempfile
import types
from unittest.mock import patch

sys.dont_write_bytecode = True
os.environ['FILTERMATE_LOG_DIR'] = '/tmp/fm-audit-logs'
package = types.ModuleType('filter_mate')
package.__path__ = [os.environ.get('FM_REPO', '/src')]
sys.modules['filter_mate'] = package
from qgis.core import QgsApplication, QgsProject, QgsVectorLayer, QgsFeature, QgsGeometry, QgsRectangle, QgsCoordinateReferenceSystem, QgsRasterLayer
from qgis.gui import QgsMapCanvas
from osgeo import gdal

app = QgsApplication([], False)
app.initQgis()
project = QgsProject.instance()
canvas = QgsMapCanvas()
canvas.resize(800, 600)
canvas.setDestinationCrs(QgsCoordinateReferenceSystem('EPSG:4326'))
canvas.setExtent(QgsRectangle(-2, 42, 2, 46))

from filter_mate.adapters.public_api import project_control
from filter_mate.adapters import auto_zoom
from filter_mate.adapters.qgis import async_query
from filter_mate.adapters.agent import data_store

def emit(name, value):
    print('AUDIT ' + json.dumps({'case': name, **value}, ensure_ascii=False), flush=True)

def point(name, x, y):
    layer = QgsVectorLayer('Point?crs=EPSG:4326', name, 'memory')
    feature = QgsFeature()
    feature.setGeometry(QgsGeometry.fromWkt(f'POINT({x} {y})'))
    layer.dataProvider().addFeatures([feature])
    layer.updateExtents()
    project.addMapLayer(layer)
    return layer

for name, x, y in [('greenwich', 0, 45), ('france', 1, 45), ('origin', 0, 0)]:
    layer = point(name, x, y)
    feature = next(layer.getFeatures())
    layer.selectByIds([feature.id()])
    canvas.setExtent(QgsRectangle(-2, 42, 2, 46))
    before = canvas.extent().width()
    with patch.object(project_control, '_canvas', return_value=canvas):
        try:
            result = project_control.zoom_to(layer.id(), selected_only=True)
            emit('zoom_point_' + name, {'accepted': True, 'width_before': before, 'width_after': canvas.extent().width(), 'result': result})
        except ValueError as exc:
            emit('zoom_point_' + name, {'accepted': False, 'error': str(exc)})

layer = point('async-source', 1, 45)
delivered = {}
def submit(*args, **kwargs):
    delivered['callback'] = args[5]
    return object()
canvas.setExtent(QgsRectangle(0, 44, 2, 46))
with patch.object(async_query, 'submit_query', side_effect=submit):
    async_query.queue_union_zoom([layer], canvas, auto_zoom.current_subset_change_token())
canvas.setExtent(QgsRectangle(10, 10, 20, 20))
manual = canvas.extent().toString()
delivered['callback'](QgsRectangle(0, 44, 2, 46))
emit('late_autozoom_overwrites_manual_pan', {'manual_view': manual, 'after_delivery': canvas.extent().toString(), 'overwritten': manual != canvas.extent().toString()})

path = '/vsimem/fm-audit-raster.tif'
dataset = gdal.GetDriverByName('GTiff').Create(path, 10, 10, 1, gdal.GDT_Byte)
dataset.SetGeoTransform([20, 1, 0, 30, 0, -1])
dataset.SetProjection('EPSG:4326')
dataset.GetRasterBand(1).Fill(1)
dataset = None
raster = QgsRasterLayer(path, 'raster-target', 'gdal')
seen = []
with patch.object(auto_zoom, '_read_global_auto_zoom_flag', return_value=True), patch('filter_mate.adapters.qgis.source_capability_probe.counts_cheaply', return_value=False), patch.object(async_query, 'queue_union_zoom', side_effect=lambda layers, *_: seen.extend(item.name() for item in layers)):
    auto_zoom.auto_zoom_to_filtered([layer, raster], iface_obj=types.SimpleNamespace(mapCanvas=lambda: canvas))
emit('mixed_autozoom_drops_raster', {'requested': [layer.name(), raster.name()], 'queued': seen})

project.clear()
store = data_store.store_for(project)
memory = store.new_path('sample.geojson')
data = b'{"type":"FeatureCollection","features":[{"type":"Feature","geometry":{"type":"Point","coordinates":[1,45]},"properties":{}}]}'
with store.writer(memory) as write:
    write(data)
saved_layer = QgsVectorLayer(memory, 'saved-data', 'ogr')
project.addMapLayer(saved_layer)
store.limit = len(data)
data_store.persist(project, os.path.join(tempfile.mkdtemp(prefix='fm-audit-save-'), 'saved.qgz'))
try:
    store.check_capacity(1)
    error = ''
except ValueError as exc:
    error = str(exc)
emit('save_does_not_release_memory_budget', {'durable': not data_store.is_memory(saved_layer.source()), 'memory_bytes_retained': data_store.size(memory), 'budget': store.limit, 'next_byte_error': error})

from filter_mate.ui.widgets.agent_panel import AgentPanel
panel = AgentPanel()
panel.set_ready(True, 'Audit')
panel.set_mode('act')
panel.set_working(True)
panel.set_mode('respond')
pushes, sends = [], []
panel.push_requested.connect(pushes.append)
panel.send_requested.connect(sends.append)
panel.input.setText('Donne seulement ton avis')
panel._on_send()
emit('respond_selected_but_push_emitted', {'displayed_posture': panel.posture(), 'mode_selector_enabled': panel.mode_button.isEnabled(), 'pushes': pushes, 'new_requests': sends})

from filter_mate.ui.controllers.agent_chat_controller import AgentChatController
from filter_mate.core.agent.permissions import PermissionPolicy
from filter_mate.core.agent.tool_catalog import chat_tools
policy = PermissionPolicy()
policy.set_posture('act')
host = types.SimpleNamespace(_abandoned=False, _replaying=False, _building=False,
    _engine=types.SimpleNamespace(busy=True, push=lambda text: True),
    _posture='respond', _request_posture='act', _last_request='Original request',
    _checkpoint=types.SimpleNamespace(label='Original request'), panel=panel,
    _flush_answer=lambda: None, _record=lambda *args: None, _policy=policy)
AgentChatController._on_push(host, 'Donne seulement ton avis')
spec = next(tool for tool in chat_tools() if tool.name == 'apply_filter')
emit('push_policy_keeps_act_when_respond_displayed', {'displayed': panel.posture(),
    'effective_request': host._request_posture, 'filter_verdict': policy.verdict(spec, {'layer_name': saved_layer.id(), 'expression':'1=1'})})

from filter_mate.adapters.agent import transcript_store, session_store
project.setFileName('/tmp/audit-history.qgz')
key = session_store.project_key()
session_store.save(key, 'conversation A')
session_store.save(key, '')
emit('session_single_slot_clear', {'after_new_conversation': session_store.load(key), 'project_key': key})

project.clear()
store = data_store.store_for(project)
store.limit = 1
layer = point('processing-input', 1, 45)
sys.path.append('/usr/share/qgis/python/plugins')
from processing.core.Processing import Processing
Processing.initialize()
from filter_mate.adapters.public_api import processing_tools
result = processing_tools.run_algorithm('native:buffer', {'INPUT':layer.id(), 'DISTANCE':0.1})
made = project.mapLayer(result['layers'][0]['layer_id'])
emit('native_processing_exceeds_memory_budget', {'budget':store.limit,
    'output_size':data_store.size(data_store.memory_path(made.source())), 'output_valid': made.isValid()})

project.clear()
panel.deleteLater()
canvas.setLayers([])
canvas.deleteLater()
print('AUDIT complete', flush=True)
