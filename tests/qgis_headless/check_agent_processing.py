"""Registered providers, native/nested models, controlled disk storage and the native model designer.

docker run --rm -v "$PWD":/src:ro -e QT_QPA_PLATFORM=offscreen qgis/qgis:ltr \
    python3 /src/tests/qgis_headless/check_agent_processing.py
"""
import os
import sys
import tempfile
import traceback
import types
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.dont_write_bytecode = True
package = types.ModuleType('filter_mate')
package.__path__ = [os.environ.get('FM_REPO', '/src')]
sys.modules['filter_mate'] = package
work = Path(tempfile.mkdtemp(prefix='fm-processing-check-'))
os.environ['FILTERMATE_LOG_DIR'] = str(work / 'logs')

from qgis.core import (Qgis, QgsApplication, QgsFeature, QgsFeatureSink, QgsGeometry, QgsPointXY,
                       QgsProcessingAlgorithm, QgsProcessingParameterFeatureSink, QgsProcessingParameterFeatureSource, QgsProcessingProvider,
                       QgsProcessingUtils, QgsProject, QgsRasterLayer, QgsVectorLayer)
from qgis.PyQt.QtWidgets import QMainWindow
from osgeo import gdal

app = QgsApplication([], False)
app.initQgis()
sys.path.append('/usr/share/qgis/python/plugins')
from processing.core.Processing import Processing
Processing.initialize()


def check(label, condition):
    assert condition, label
    print('PASS ' + label, flush=True)


def refuses(function, *args, **kwargs):
    try:
        function(*args, **kwargs)
    except ValueError as exc:
        return str(exc)
    raise AssertionError('call should have been refused')


def main():
    from filter_mate.adapters.public_api import processing_models as models, processing_tools as tools
    from filter_mate.adapters.agent import data_store
    from filter_mate.adapters.agent.turn_effects import EffectsRecorder, apply_effects
    from filter_mate.core.agent.messages import ToolCallPart
    spec = {
        'name': 'buffer_centroids',
        'inputs': [{'name': 'INPUT', 'step': 'buffer', 'parameter': 'INPUT'},
                   {'name': 'DISTANCE', 'step': 'buffer', 'parameter': 'DISTANCE', 'default': 10}],
        'steps': [{'id': 'buffer', 'algorithm_id': 'native:buffer', 'parameters': {
            'INPUT': {'input': 'INPUT'}, 'DISTANCE': {'input': 'DISTANCE'}, 'SEGMENTS': 5}},
            {'id': 'centroids', 'algorithm_id': 'native:centroids', 'parameters': {
                'INPUT': {'step': 'buffer', 'output': 'OUTPUT'}, 'ALL_PARTS': False}}],
        'outputs': [{'name': 'RESULT', 'step': 'centroids', 'output': 'OUTPUT'}],
    }
    model = models.build_model(spec)
    check('a declarative chain builds a validated native model without files', model.validate()[0]
          and len(model.childAlgorithms()) == 2 and not model.sourceFilePath())
    bad = dict(spec, steps=[dict(spec['steps'][0], parameters={'INPUT': '/etc/passwd'})])
    check('a draft cannot embed a path as a layer input', 'wire' in refuses(models.build_model, bad))
    bad = dict(spec, steps=[dict(spec['steps'][0], parameters={'INPUT': {'step': 'centroids', 'output': 'OUTPUT'}}),
                           spec['steps'][1]])
    check('a draft cannot connect a future step or create a cycle', 'earlier' in refuses(models.build_model, bad))
    bad = dict(spec, inputs=[dict(spec['inputs'][0], parameter='DISTANCE'), spec['inputs'][1]])
    check('a scalar input cannot masquerade as a layer connection', 'checked type' in refuses(models.build_model, bad))

    class Models(QgsProcessingProvider):
        def id(self):
            return 'fmcheck'

        def name(self):
            return 'Test models'

        def supportsNonFileBasedOutput(self):
            return False

        def loadAlgorithms(self):
            self.addAlgorithm(model.create())
            self.addAlgorithm(CopyFeatures())

    class CopyFeatures(QgsProcessingAlgorithm):
        """An installed-provider algorithm which also uses Python scratch files."""
        def name(self):
            return 'copy_features'

        def displayName(self):
            return 'Copy features'

        def createInstance(self):
            return CopyFeatures()

        def initAlgorithm(self, config=None):
            self.addParameter(QgsProcessingParameterFeatureSource('INPUT', 'Features'))
            self.addParameter(QgsProcessingParameterFeatureSink('OUTPUT', 'Copy'))

        def processAlgorithm(self, parameters, context, feedback):
            if self.provider().id() != 'fmram':
                with tempfile.NamedTemporaryFile(prefix='provider-scratch-', delete=False) as scratch:
                    assert Path(scratch.name).is_relative_to(context.temporaryFolder())
            source = self.parameterAsSource(parameters, 'INPUT', context)
            sink, destination = self.parameterAsSink(parameters, 'OUTPUT', context, source.fields(),
                                                     source.wkbType(), source.sourceCrs())
            for feature in source.getFeatures():
                sink.addFeature(feature, QgsFeatureSink.FastInsert)
            return {'OUTPUT': destination}
    provider = Models()
    registry = QgsApplication.processingRegistry()
    registry.addProvider(provider)
    found = tools.find_algorithms('model')
    row = next(row for row in found['algorithms'] if row['id'] == 'fmcheck:buffer_centroids')
    check('model discovery includes provider, type and memory capability', row['is_model'] and
          row['provider'] == 'fmcheck' and not row['requires_disk'])
    info = tools.describe_algorithm(row['id'])
    check('model description gives its actual steps and output parameters',
          {step['algorithm_id'] for step in info['steps']} == {'native:buffer', 'native:centroids'}
          and info['is_model'])
    project = QgsProject.instance()
    layer = QgsVectorLayer('Point?crs=EPSG:2154&field=value:integer', 'Points', 'memory')
    features = []
    for index in range(3):
        feature = QgsFeature(layer.fields())
        feature.setAttributes([index])
        feature.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(100 + index * 100, 200)))
        features.append(feature)
    layer.dataProvider().addFeatures(features)
    project.addMapLayer(layer)
    temp = Path(QgsProcessingUtils.tempFolder())
    before = set(temp.rglob('*'))
    class RamProvider(Models):
        def id(self):
            return 'fmram'

        def supportsNonFileBasedOutput(self):
            return True

        def loadAlgorithms(self):
            self.addAlgorithm(CopyFeatures())
    ram_provider = RamProvider()
    registry.addProvider(ram_provider)
    result = tools.run_algorithm('fmram:copy_features', {'INPUT': layer.id()})
    ram_output = project.mapLayer(result['layers'][0]['layer_id'])
    check('a provider declaring vector memory support runs without choosing a disk folder',
          result['layers'][0]['feature_count'] == 3 and data_store.is_memory(ram_output.source())
          and not tools.describe_algorithm('fmram:copy_features')['requires_disk'])
    recorder = EffectsRecorder()
    recorder.before_call(ToolCallPart('model', 'run_algorithm', {}))
    result = tools.run_algorithm(row['id'], {'INPUT': layer.id()})
    recorder.after_call()
    effect = recorder.finish()
    output = project.mapLayer(result['layers'][0]['layer_id'])
    check('a native model and its intermediate outputs stay in memory', output.featureCount() == 3
          and data_store.is_memory(output.source()) and set(temp.rglob('*')) == before)
    output_id = output.id()
    apply_effects(effect, undo=True)
    check('model outputs participate in turn undo', project.mapLayer(output_id) is None)
    apply_effects(effect, undo=False)
    check('redo restores all model output features', project.mapLayer(output_id).featureCount() == 3)

    nested_spec = {'name': 'nested', 'inputs': [{'name': 'INPUT', 'step': 'first', 'parameter': 'INPUT'}],
                   'steps': [{'id': 'first', 'algorithm_id': row['id'], 'parameters': {'INPUT': {'input': 'INPUT'}}}],
                   'outputs': [{'name': 'FINAL', 'step': 'first', 'output': model.destinationParameterDefinitions()[0].name()}]}
    nested = models.build_model(nested_spec)
    provider.addAlgorithm(nested)
    result = tools.run_algorithm('fmcheck:nested', {'INPUT': layer.id()})
    check('nested model dependencies and destinations work', len(result['layers']) == 1 and
          result['layers'][0]['feature_count'] == 3 and set(temp.rglob('*')) == before)

    # A model cannot hide a step which edits the project or runs code.
    from qgis.core import QgsProcessingModelChildAlgorithm
    unsafe = model.create()
    unsafe.setName('unsafe')
    child = QgsProcessingModelChildAlgorithm('native:selectbyexpression')
    child.setChildId('in_place')
    unsafe.addChildAlgorithm(child)
    provider.addAlgorithm(unsafe)
    check('a model cannot bypass the in-place algorithm rules',
          'step' in refuses(tools.describe_algorithm, 'fmcheck:unsafe'))
    missing = model.create()
    missing.setName('missing')
    child = QgsProcessingModelChildAlgorithm('uninstalled:no_algorithm')
    child.setChildId('missing')
    missing.addChildAlgorithm(child)
    provider.addAlgorithm(missing)
    check('a missing model dependency is reported before running',
          'missing algorithm' in refuses(tools.describe_algorithm, 'fmcheck:missing'))

    chosen = work / 'chosen'
    chosen.mkdir()
    from qgis.core import QgsProcessingContext
    if hasattr(QgsProcessingContext, 'setTemporaryFolder'):
        gdal_row = tools.find_algorithms('gdal translate')['algorithms']
        check('GDAL algorithms are discoverable and declare file-only storage',
              any(row['id'] == 'gdal:translate' and row['requires_disk'] for row in gdal_row))
        check('file-only algorithms ask for a chosen project folder before writing',
              'Save project and layers' in refuses(tools.run_algorithm, 'gdal:translate', {'INPUT': layer.id()})
              and set(temp.rglob('*')) == before)
        raster_path = data_store.new_path('input.tif')
        dataset = gdal.GetDriverByName('GTiff').Create(raster_path, 5, 5, 1, gdal.GDT_Float32)
        dataset.SetGeoTransform([0, 1, 0, 5, 0, -1])
        dataset.GetRasterBand(1).Fill(12)
        dataset = None
        raster = QgsRasterLayer(raster_path, 'Raster in RAM', 'gdal')
        project.addMapLayer(raster)
        data_store.persist(project, str(chosen / 'project.qgz'))
        # Make a fresh memory raster after saving: an external process must get a durable input snapshot.
        fresh = data_store.new_path('fresh.tif')
        gdal.Translate(fresh, raster.source())
        raster = QgsRasterLayer(fresh, 'Fresh raster in RAM', 'gdal')
        project.addMapLayer(raster)
        result = tools.run_algorithm('gdal:translate', {'INPUT': raster.id()})
        output = project.mapLayer(result['layers'][0]['layer_id'])
        check('the real GDAL executable reads a RAM raster through a controlled snapshot', output.isValid()
              and output.dataProvider().identify(output.extent().center(), Qgis.RasterIdentifyFormat.Value).results()[1] == 12)
        check('external output and working files use the chosen data folder',
              Path(output.source()).is_relative_to(chosen) and set(temp.rglob('*')) == before
              and raster.source() == fresh)
        check('extra command-line options cannot be supplied', 'command-line' in refuses(
            tools.run_algorithm, 'gdal:translate', {'INPUT': raster.id(), 'EXTRA': '-of evil'}))
        layer.setSubsetString('"value" >= 1')
        layer.selectByExpression('"value" = 2')
        selected = layer.selectedFeatureIds()
        previous_temp = tempfile.tempdir
        result = tools.run_algorithm('fmcheck:copy_features', {'INPUT': {'layer': layer.id(), 'selected_only': True}})
        check('another registered provider receives a snapshot of just the requested selection',
              result['layers'][0]['feature_count'] == 1 and layer.featureCount() == 2
              and layer.selectedFeatureIds() == selected)
        check('provider Python scratch uses the chosen folder and process settings are restored',
              list(chosen.rglob('provider-scratch-*')) and tempfile.tempdir == previous_temp
              and set(temp.rglob('*')) == before)
        mixed = dict(spec, name='mixed', steps=[spec['steps'][0], {'id': 'centroids',
                     'algorithm_id': 'fmcheck:copy_features', 'parameters': {'INPUT': {'step': 'buffer', 'output': 'OUTPUT'}}}])
        provider.addAlgorithm(models.build_model(mixed))
        result = tools.run_algorithm('fmcheck:mixed', {'INPUT': {'layer': layer.id(), 'selected_only': True}})
        check('models can combine providers with controlled intermediate storage',
              result['layers'][0]['feature_count'] == 1
              and tools.describe_algorithm('fmcheck:mixed')['requires_disk']
              and set(temp.rglob('*')) == before)

    else:
        check('older QGIS refuses file-only providers without a per-context working folder',
              '3.32' in refuses(tools.run_algorithm, 'gdal:translate', {'INPUT': layer.id()}))

    window = QMainWindow()
    face = SimpleNamespace(mainWindow=lambda: window)
    saved_paths = []
    result = models.open_model(definition=spec, iface_obj=face, on_saved=saved_paths.append)
    editor = models._EDITORS[-1]
    app.processEvents()
    check('the native graphical designer opens the built chain without saving or executing',
          result['opened'] and not result['saved'] and editor.model().validate()[0]
          and not editor.model().sourceFilePath())
    with patch('qgis.PyQt.QtWidgets.QFileDialog.getSaveFileName', return_value=('', '')):
        check('cancelling Save writes no model', not editor.saveModel(False) and not saved_paths)
    path = chosen / 'my_chain.model3'
    with patch('qgis.PyQt.QtWidgets.QFileDialog.getSaveFileName', return_value=(str(path), '')):
        check('Save uses the selected model file and reports a clickable output',
              editor.saveModel(False) and path.is_file() and saved_paths == [str(path)])
    check('a model saved outside the profile is available for this project session',
          any(row['id'] == 'filtermate_models:buffer_centroids'
              for row in tools.find_algorithms('model')['algorithms']))
    editor.close()
    models.open_model('fmcheck:buffer_centroids', iface_obj=face)
    copy_editor = models._EDITORS[-1]
    check('opening a registered model edits a draft without overwriting its source',
          copy_editor.model().validate()[0] and not copy_editor.model().sourceFilePath())
    copy_editor.close()
    models.open_model(iface_obj=face)
    blank = models._EDITORS[-1]
    check('a blank model editor is available directly without a definition or expert mode',
          blank.model() is not None and not blank.model().sourceFilePath())
    blank.close()
    window.close()
    project.clear()
    check('closing the project releases saved-model session registration',
          registry.providerById('filtermate_models') is None)
    print('All agent Processing checks passed', flush=True)


try:
    main()
except Exception:
    traceback.print_exc()
    os._exit(1)
os._exit(0)
