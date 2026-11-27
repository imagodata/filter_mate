"""A01: worker reads, live UI, and no partial selection after cancellation."""
import os
import sys
import time
import threading
import types
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('FILTERMATE_LOG_DIR', '/tmp/fm-feature-id-logs')
from qgis.core import QgsApplication, QgsProject, QgsVectorLayer, QgsFeature, QgsGeometry, Qgis
from qgis.PyQt.QtCore import QEventLoop, QTimer

app = QgsApplication([], False)
app.initQgis()
package = types.ModuleType('filter_mate')
package.__path__ = [os.environ.get('FM_REPO', '/src')]
sys.modules['filter_mate'] = package
from filter_mate.adapters.qgis import async_query, feature_ids
from filter_mate.adapters.public_api import gui_control, project_control
from filter_mate.adapters.agent.turn_effects import EffectsRecorder
from filter_mate.core.agent.messages import ToolCallPart

layer = QgsVectorLayer('Point?crs=EPSG:2154&field=value:integer', 'points', 'memory')
features = []
for number in range(3):
    feature = QgsFeature(layer.fields())
    feature.setAttributes([number])
    feature.setGeometry(QgsGeometry.fromWkt(f'POINT({number} {number})'))
    features.append(feature)
layer.dataProvider().addFeatures(features)
QgsProject.instance().addMapLayer(layer)
main_thread = threading.get_ident()
original = async_query.SnapshotQueryTask.features
threads = []

def slow(self, request, source=None):
    threads.append(threading.get_ident())
    time.sleep(.08)
    yield from original(self, request, source)

def wait():
    loop = QEventLoop()
    QTimer.singleShot(180, loop.quit)
    loop.exec()

ticks = []
timer = QTimer()
timer.timeout.connect(lambda: ticks.append(True))
timer.start(5)
with patch.object(async_query.SnapshotQueryTask, 'features', slow), patch.object(
        layer, 'getFeatures', side_effect=AssertionError('no GUI-thread iteration of the live layer')):
    answer = project_control.select_features(layer.id(), '"value" > 0')
    assert answer['selected_count'] == 2 and len(ticks) >= 3
    assert threads and all(thread != main_thread for thread in threads)
    print('PASS selection reads a snapshot in a worker while GUI events continue', flush=True)

    manual = [features[0].id()]
    effects = EffectsRecorder()
    call = ToolCallPart('selection', 'select_features', {'layer': layer.id(), 'expression': '"value" > 0'})
    effects.before_call(call)
    QTimer.singleShot(10, lambda: layer.selectByIds(manual))
    try:
        project_control.select_features(layer.id(), '"value" > 0')
    except ValueError as exc:
        assert 'changed' in str(exc), str(exc)
    else:
        raise AssertionError('manual selection was overwritten')
    assert set(layer.selectedFeatureIds()) == set(manual)
    effects.cancel_failed_selection()
    effects.after_call()
    assert not any(effect[0] == 'selection' for effect in effects.finish()), 'manual selection is not an agent effect'
    wait()
    assert set(layer.selectedFeatureIds()) == set(manual)
    print('PASS manual selection wins; a late result cannot overwrite it', flush=True)

    try:
        feature_ids.read_feature_ids(layer, '"value" > 0', 10, timeout_ms=10)
    except ValueError as exc:
        assert 'timed out' in str(exc), str(exc)
    else:
        raise AssertionError('slow read did not time out')
    wait()
    assert set(layer.selectedFeatureIds()) == set(manual)
    flashed = []
    canvas = types.SimpleNamespace(flashGeometries=lambda geometries, crs: flashed.extend(geometries))
    face = types.SimpleNamespace(mapCanvas=lambda: canvas)
    answer = gui_control.flash_features(layer.id(), '"value" > 0', iface_obj=face)
    assert answer['flashed'] == 2 and len(flashed) == 2
    assert set(layer.selectedFeatureIds()) == set(manual)
    print('PASS bounded flash and timeouts leave selection intact', flush=True)
timer.stop()
with patch.object(layer, 'selectedFeatureCount', return_value=100001):
    try:
        EffectsRecorder().before_call(call)
    except ValueError as exc:
        assert 'too large to capture' in str(exc), str(exc)
    else:
        raise AssertionError('a selection without Undo coverage must be refused')
print('PASS failed selections exclude manual changes from Undo; oversized originals require Undo coverage', flush=True)
QgsProject.instance().clear()
print(f'PASS QGIS {Qgis.QGIS_VERSION}: all feature ID regression checks', flush=True)
os._exit(0)
