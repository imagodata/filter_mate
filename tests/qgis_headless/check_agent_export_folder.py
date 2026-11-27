"""Real QGIS export writer with a simulated user folder choice; no export may enter a QGIS profile."""
import os
import sys
import tempfile
import types
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import MagicMock, patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('FILTERMATE_LOG_DIR', '/tmp/fm-export-folder-logs')
from qgis.core import QgsApplication, QgsSettings, QgsProject, QgsVectorLayer, QgsFeature, QgsGeometry, Qgis
from qgis.PyQt.QtWidgets import QFileDialog

app = QgsApplication([], False)
app.initQgis()
package = types.ModuleType('filter_mate')
package.__path__ = [os.environ.get('FM_REPO', '/src')]
sys.modules['filter_mate'] = package
from filter_mate.filtermate_api.config import EXPORT_FOLDER_KEY, configured_export_root, _default_export_root
from filter_mate.filtermate_api.export_root import ExportRootError, prepare_export_root, resolve_export_folder
from filter_mate.filtermate_api.agent_tools import build_handlers
from filter_mate.filtermate_api.qgis_accessor import QGISFilterMateAccessor
from filter_mate.core.agent.tool_executor import ToolFailure
from filter_mate.ui.controllers.agent_chat_controller import AgentChatController
from filter_mate.ui.widgets.agent_panel import AgentPanel
from filter_mate.adapters.agent import data_store

settings = QgsSettings()
settings.remove(EXPORT_FOLDER_KEY)
profile = Path(QgsApplication.qgisSettingsDirPath()).resolve()
assert profile not in _default_export_root().resolve().parents
panel = AgentPanel()
panel.show()
host = types.SimpleNamespace(panel=panel, _memory_generation=0, _abandoned=False, _activity=lambda phase: nullcontext())
host._agent_export_root = types.MethodType(AgentChatController._agent_export_root, host)
accessor = QGISFilterMateAccessor(None, None)

with tempfile.TemporaryDirectory(prefix='fm-user-export-') as temporary:
    chosen = Path(temporary)
    with patch.object(QFileDialog, 'getExistingDirectory', return_value=str(chosen)) as picker:
        handlers = build_handlers(accessor, host._agent_export_root)
        picker.assert_not_called()
        layer = QgsVectorLayer('Point?crs=EPSG:2154&field=value:integer', 'points', 'memory')
        feature = QgsFeature(layer.fields())
        feature.setAttributes([3])
        feature.setGeometry(QgsGeometry.fromWkt('POINT(650000 6860000)'))
        layer.dataProvider().addFeatures([feature])
        QgsProject.instance().addMapLayer(layer)
        arguments = {'layers': [layer.id()], 'subfolder': 'deliverable', 'vector_format': 'GPKG',
                     'raster_format': 'COG', 'point_cloud_format': 'LAZ'}
        answer = handlers['export_layers'](arguments)
        assert picker.call_count == 1 and configured_export_root() == chosen
        assert all(not os.path.isabs(path) for path in answer['outputs'].values())
        exported = chosen / 'deliverable' / next(iter(answer['outputs'].values()))
        check = QgsVectorLayer(str(exported), 'read back', 'ogr')
        assert check.isValid() and check.featureCount() == 1 and next(check.getFeatures())['value'] == 3
        handlers['export_layers'](arguments)
        assert picker.call_count == 1
        print('PASS lazy explicit choice, remembered default, real GeoPackage exports and relative model results', flush=True)

    forbidden = profile / 'agent-export-must-not-exist'
    assert not forbidden.exists()
    try:
        prepare_export_root(forbidden)
    except ExportRootError:
        pass
    else:
        raise AssertionError('profile export accepted')
    assert not forbidden.exists()
    try:
        resolve_export_folder(profile.parent.parent, profile.parent.name + '/' + profile.name + '/forbidden')
    except ExportRootError:
        pass
    else:
        raise AssertionError('profile reentered through an export subfolder')
    with patch.object(QFileDialog, 'getExistingDirectory', return_value=str(profile)), patch(
            'qgis.PyQt.QtWidgets.QMessageBox.warning') as warning:
        settings.remove(EXPORT_FOLDER_KEY)
        try:
            host._agent_export_root()
        except ToolFailure:
            pass
        else:
            raise AssertionError('profile picker choice accepted')
        warning.assert_called_once()
    assert configured_export_root() is None
    print('PASS forbidden profile destination, nested subfolder and invalid picker choice write no output', flush=True)

    with patch.object(QFileDialog, 'getExistingDirectory', return_value=''):
        try:
            handlers['export_layers'](arguments)
        except ToolFailure:
            pass
        else:
            raise AssertionError('cancelled folder choice exported data')
    try:
        data_store.persist(QgsProject.instance(), str(forbidden.with_suffix('.qgz')))
    except ExportRootError:
        pass
    else:
        raise AssertionError('project-and-layer persistence accepted a QGIS profile')
    print('PASS cancellation has no default fallback; project-and-layer saves also refuse QGIS profiles', flush=True)
settings.remove(EXPORT_FOLDER_KEY)
print(f'PASS QGIS {Qgis.QGIS_VERSION}: exports use the user-selected directory', flush=True)
os._exit(0)
