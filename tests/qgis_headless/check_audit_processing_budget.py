"""R02: native Processing outputs obey the managed file budget before publication."""
import os
import sys
import types
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('FILTERMATE_LOG_DIR', '/tmp/fm-processing-budget-logs')
from qgis.core import QgsApplication, QgsProject, QgsVectorLayer, QgsFeature, QgsGeometry, Qgis
from osgeo import gdal

app = QgsApplication([], False)
app.initQgis()
sys.path.append('/usr/share/qgis/python/plugins')
from processing.core.Processing import Processing
Processing.initialize()
package = types.ModuleType('filter_mate')
package.__path__ = [os.environ.get('FM_REPO', '/src')]
sys.modules['filter_mate'] = package
from filter_mate.adapters.agent import data_store
from filter_mate.adapters.public_api import processing_tools as tools

project = QgsProject.instance()
layer = QgsVectorLayer('Point?crs=EPSG:2154', 'points', 'memory')
features = []
for number in range(5000):
    feature = QgsFeature()
    feature.setGeometry(QgsGeometry.fromWkt(f'POINT({number} {number})'))
    features.append(feature)
layer.dataProvider().addFeatures(features)
project.addMapLayer(layer)
store = data_store.store_for()
before = set(project.mapLayers())

def refused():
    try:
        tools.run_algorithm('native:buffer', {'INPUT': layer.id(), 'DISTANCE': 10, 'SEGMENTS': 20})
    except ValueError as exc:
        assert 'memory budget' in str(exc), str(exc)
        assert set(project.mapLayers()) == before
        assert not tools._RUNNING
        assert not [name for name in (gdal.ReadDirRecursive(store.root) or []) if not name.endswith('/')]
        return
    raise AssertionError('over-budget native Processing result was published')

store.limit = 1
with patch.object(tools, '_run', side_effect=AssertionError('preflight must prevent execution')):
    refused()
print('PASS native writer cannot bypass a one-byte budget', flush=True)

store.limit = data_store.NATIVE_OUTPUT_RESERVE
refused()
print('PASS native overrun is canceled/rejected and its files are discarded before layer publication', flush=True)

store.limit = data_store.MAX_MEMORY_BYTES
result = tools.run_algorithm('native:centroids', {'INPUT': layer.id()})
output = project.mapLayer(result['layers'][0]['layer_id'])
assert output.isValid() and output.featureCount() == 5000 and data_store.is_memory(output.source())
assert data_store.size(data_store.memory_path(output.source())) > 0
print(f'PASS QGIS {Qgis.QGIS_VERSION}: adequate native budget still produces a readable result', flush=True)
project.clear()
os._exit(0)
