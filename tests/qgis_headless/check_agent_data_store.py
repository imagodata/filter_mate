"""Agent geodata: no disk before a chosen save, durable/portable data afterwards.

docker run --rm -v "$PWD":/src:ro -e QT_QPA_PLATFORM=offscreen qgis/qgis:ltr \
    python3 /src/tests/qgis_headless/check_agent_data_store.py
"""
import io
import json
import os
import shutil
import sys
import tempfile
import traceback
import types
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.dont_write_bytecode = True
package = types.ModuleType("filter_mate")
package.__path__ = [os.environ.get("FM_REPO", "/src")]
sys.modules["filter_mate"] = package

from qgis.core import (QgsApplication, QgsProject, QgsRasterLayer, QgsVectorLayer, QgsGeometry,
                       QgsCoordinateReferenceSystem, QgsProcessingUtils)
from osgeo import gdal

app = QgsApplication([], False)
app.initQgis()
work = tempfile.mkdtemp(prefix="fm-data-store-check-")
os.environ["FILTERMATE_LOG_DIR"] = os.path.join(work, "logs")


def check(label, condition):
    assert condition, label
    print("PASS " + label, flush=True)


def main():
    from filter_mate.adapters.agent import data_store
    from filter_mate.adapters.agent.turn_effects import EffectsRecorder, apply_effects
    from filter_mate.adapters.public_api import project_control, processing_tools
    from filter_mate.core.agent.messages import ToolCallPart
    from filter_mate.core.agent.open_data import RemoteFile

    sys.path.append("/usr/share/qgis/python/plugins")
    from processing.core.Processing import Processing
    Processing.initialize()
    project = QgsProject.instance()
    profile = Path(QgsApplication.qgisSettingsDirPath()) / "filtermate" / "open_data"
    old_profile = set(profile.rglob("*")) if profile.exists() else set()
    cache_folder = Path(QgsApplication.qgisSettingsDirPath()) / 'filtermate' / 'cache'
    processing_folder = Path(QgsProcessingUtils.tempFolder())
    cache_before, processing_before = set(cache_folder.rglob('*')), set(processing_folder.rglob('*'))
    data = json.dumps({"type": "FeatureCollection", "features": [
        {"type": "Feature", "geometry": {"type": "Point", "coordinates": [i, i]},
         "properties": {"value": i}} for i in (1, 2, 3)]}).encode()

    def fetch(url, **kwargs):
        kwargs["sink"](data[:40])
        kwargs["sink"](data[40:])
        return SimpleNamespace(status=200, headers={"content-type": "application/geo+json"})

    recorder = EffectsRecorder()
    recorder.before_call(ToolCallPart("add", "add_layer", {}))
    with patch.object(project_control, "_probe", return_value=("https://example.org/data.geojson",
                      RemoteFile("data.geojson", False, len(data)))), \
            patch.object(project_control, "resolved_problem", return_value=""), \
            patch.object(project_control, "fetch", side_effect=fetch), \
            patch("tempfile.mkdtemp", side_effect=AssertionError("no temporary directory for agent data")):
        answer = project_control.add_layer("https://example.org/data.geojson", "Downloaded")
    recorder.after_call()
    effects = recorder.finish()
    layer = project.mapLayer(answer["layer_id"])
    virtual_source = layer.source()
    layer_id = layer.id()
    check("whole-file downloads are readable in memory, without a profile or temp copy",
          data_store.is_memory(virtual_source) and layer.featureCount() == 3 and not os.path.exists(virtual_source)
          and (set(profile.rglob("*")) if profile.exists() else set()) == old_profile)
    apply_effects(effects, undo=True)
    check("undo removes the layer while its data remain available", project.mapLayer(layer_id) is None
          and data_store.exists(virtual_source))
    apply_effects(effects, undo=False)
    layer = project.mapLayer(layer_id)
    check("redo restores all features from memory", layer is not None and layer.featureCount() == 3)
    layer.setSubsetString('"value" > 1')
    layer.selectByIds([next(layer.getFeatures()).id()])
    layer.renderer().symbol().setColor(__import__('qgis.PyQt.QtGui', fromlist=['QColor']).QColor('#e34234'))
    layer.setCustomProperty("test-property", "kept")
    selected, color = layer.selectedFeatureIds(), layer.renderer().symbol().color().name()
    buffered = processing_tools.run_algorithm("native:buffer", {"INPUT": layer_id, "DISTANCE": 0.1})
    buffer_layer = project.mapLayer(buffered["layers"][0]["layer_id"])
    check("native Processing outputs use an in-memory GeoPackage", buffer_layer.isValid()
          and data_store.is_memory(buffer_layer.source()) and buffer_layer.featureCount() == 2)
    buffer_layer.setSubsetString('"value" = 3')
    check("filtered in-memory GeoPackages report exact counts", project_control._summary(buffer_layer)["feature_count"] == 1)

    path = data_store.new_path("raster.tif", expected_bytes=400)
    dataset = gdal.GetDriverByName("GTiff").Create(path, 10, 10, 1, gdal.GDT_Float32)
    dataset.SetGeoTransform([0, 1, 0, 10, 0, -1])
    dataset.SetProjection("EPSG:4326")
    dataset.GetRasterBand(1).Fill(42)
    dataset = None
    raster = QgsRasterLayer(path, "Raster", "gdal")
    project.addMapLayer(raster)
    check("raster providers read raw values directly from memory", raster.isValid()
          and raster.dataProvider().bandStatistics(1).mean == 42)
    from filter_mate.adapters.public_api import operations
    from filter_mate.adapters.qgis.coverage_layers.snapshots import registry
    clipped = operations.cross_filter_by_geometry(
        QgsGeometry.fromWkt('POLYGON((0 0, 5 0, 5 10, 0 10, 0 0))'),
        QgsCoordinateReferenceSystem('EPSG:4326'), [raster.id()])
    check("spatial filters of downloaded rasters also stay in memory", not clipped.error
          and data_store.is_memory(raster.source()) and raster.source().endswith('.vrt')
          and registry().is_derived(raster.id()))
    check("agent data create no profile cache or Processing temporary files",
          set(cache_folder.rglob('*')) == cache_before and set(processing_folder.rglob('*')) == processing_before)

    zipped = io.BytesIO()
    with zipfile.ZipFile(zipped, "w") as archive:
        archive.writestr("inside.geojson", data)
    zip_path = data_store.new_path("archive.zip")
    with data_store.store_for().writer(zip_path) as write:
        write(zipped.getvalue())
    source = project_control._local_source(zip_path, "vector")
    zip_layer = QgsVectorLayer(source, "Archive", "ogr")
    project.addMapLayer(zip_layer)
    check("zip archives are read in memory without extraction", zip_layer.isValid() and zip_layer.featureCount() == 3)

    store = data_store.store_for(project)
    project_path = os.path.join(work, "chosen", "analysis.qgz")
    os.makedirs(os.path.dirname(project_path))
    existing = Path(project_path).parent / Path(virtual_source).name
    existing.write_text("User data must stay untouched", encoding="utf-8")
    folder = data_store.persist(project, project_path)
    check("explicit save keeps layer objects, ids, styles, filters and properties", project.mapLayer(layer_id) is layer
          and layer.isValid() and layer.featureCount() == 2 and layer.subsetString() == '"value" > 1'
          and layer.renderer().symbol().color().name() == color and layer.customProperty("test-property") == "kept"
          and layer.selectedFeatureIds() == selected
          and os.path.isfile(project_path) and not data_store.pending_layers(project))
    layer.setSubsetString("")
    check("saving preserves the complete source, not only filtered features", layer.featureCount() == 3)
    layer.setSubsetString('"value" > 1')
    check("the project and all saved datasets are directly in the same chosen folder",
          Path(folder) == Path(project_path).parent
          and all(Path(value).parent == Path(project_path).parent for value in store.persisted.values())
          and store.destination == str(Path(project_path).parent))
    check("a conflicting dataset name gets a suffix without overwriting user data",
          existing.read_text(encoding="utf-8") == "User data must stay untouched"
          and Path(layer.source()) != existing and Path(layer.source()).stem.endswith("_2"))
    original_raster = registry().get(raster.id()).pristine_source
    check("saving a spatially filtered raster also keeps its original full dataset", os.path.isfile(original_raster)
          and gdal.Open(original_raster).RasterXSize == 10
          and not data_store.memory_path(raster.customProperty('filtermate/derived')))
    with open(raster.source(), encoding='utf-8') as stream:
        check("a saved VRT references portable data, with no session-memory dependency", data_store.PREFIX not in stream.read())

    apply_effects(effects, undo=True)
    apply_effects(effects, undo=False)
    check("redo after saving uses the durable data source", not data_store.memory_path(project.mapLayer(layer_id).source()))
    project.clear()
    check("closing the project releases its virtual datasets", not gdal.ReadDirRecursive(store.root))
    destination = os.path.join(work, "moved")
    shutil.copytree(os.path.dirname(project_path), destination)
    check("the saved project reopens after moving its whole folder", project.read(os.path.join(destination, "analysis.qgz"))
          and all(found.isValid() for found in project.mapLayers().values()) and len(project.mapLayers()) == 4)
    restored = project.mapLayer(layer_id)
    check("reopening restores the filter and style", restored.subsetString() == '"value" > 1'
          and restored.featureCount() == 2 and restored.renderer().symbol().color().name() == color)

    from filter_mate.adapters.agent.save_location import suggested_project_path
    check("a saved project's exact location is proposed again", suggested_project_path(project) == project.fileName())

    from filter_mate.ui.controllers.agent_data import AgentDataController
    from qgis.PyQt.QtWidgets import QWidget, QMessageBox
    project.clear()
    path = data_store.new_path("native.geojson")
    with data_store.store_for().writer(path) as write:
        write(data)
    layer = QgsVectorLayer(path, "Native Save", "ogr")
    project.addMapLayer(layer)
    native_id = layer.id()
    panel = QWidget()
    ui = AgentDataController(SimpleNamespace(panel=panel, chat_busy=lambda: False))
    native_project = os.path.join(work, "native.qgz")
    native_raster = data_store.new_path('native.tif')
    dataset = gdal.GetDriverByName('GTiff').Create(native_raster, 10, 10, 1, gdal.GDT_Float32)
    dataset.SetGeoTransform([0, 1, 0, 10, 0, -1])
    dataset.SetProjection('EPSG:4326')
    dataset.GetRasterBand(1).Fill(42)
    dataset = None
    clipped_raster = QgsRasterLayer(native_raster, 'Native raster', 'gdal')
    project.addMapLayer(clipped_raster)
    operations.cross_filter_by_geometry(QgsGeometry.fromWkt('POLYGON((0 0, 5 0, 5 10, 0 10, 0 0))'),
                                       clipped_raster.crs(), [clipped_raster.id()])
    with patch.object(ui, '_ask_to_save', return_value=QMessageBox.StandardButton.Yes):
        check("native QGIS Save offers to keep the downloaded data", project.write(native_project)
              and not data_store.pending_layers(project))
    ui.close()
    project.clear()
    check("native QGIS Save writes the updated data sources into the project XML", project.read(native_project)
          and project.mapLayer(native_id).isValid() and project.mapLayer(native_id).featureCount() == 3
          and os.path.isfile(project.mapLayer(native_id).source()))
    from filter_mate.adapters.qgis.coverage_layers.snapshots import pending_replays
    check("native Save keeps the full raster and a portable spatial filter for replay", len(pending_replays(project)) == 1
          and all(found.isValid() for found in project.mapLayers().values()))

    # A failed export must leave a live memory layer, its original source, and no partial dataset directory.
    project.clear()
    path = data_store.new_path("failure.geojson")
    with data_store.store_for().writer(path) as write:
        write(data)
    layer = QgsVectorLayer(path, "Keep in memory", "ogr")
    project.addMapLayer(layer)
    another_path = data_store.new_path("another.geojson")
    with data_store.store_for().writer(another_path) as write:
        write(data)
    another = QgsVectorLayer(another_path, "Another layer", "ogr")
    project.addMapLayer(another)
    before = set(Path(work).rglob("*"))
    copy_file = data_store._copy_file
    copied = []

    def fail_second_copy(source, destination):
        if copied:
            raise OSError("disk full")
        copy_file(source, destination)
        copied.append(destination)

    with patch.object(data_store, "_copy_file", side_effect=fail_second_copy):
        try:
            data_store.persist(project, os.path.join(work, "failure.qgz"))
        except OSError:
            pass
        else:
            raise AssertionError("the failed copy was reported as saved")
    check("a disk failure leaves data in memory and removes only newly copied files",
          layer.source() == path and layer.featureCount() == 3 and another.source() == another_path
          and another.featureCount() == 3 and copied and set(Path(work).rglob("*")) == before)
    with patch.object(project, "write", return_value=False):
        try:
            data_store.persist(project, os.path.join(work, "failed-project.qgz"))
        except ValueError as exc:
            check("a failed project write is reported", "project could not be saved" in str(exc))
        else:
            raise AssertionError("a failed project write was reported as saved")
    check("a failed project write restores live layer sources and leaves the chosen folder untouched",
          layer.source() == path and layer.featureCount() == 3 and another.source() == another_path
          and another.featureCount() == 3 and set(Path(work).rglob("*")) == before)
    project.clear()
    project.setPresetHomePath(os.path.dirname(project_path))
    project.setTitle("Urumea slope")
    check("a new project proposes its working folder and title without creating anything",
          suggested_project_path(project) == str(Path(project_path).parent / "Urumea slope.qgz")
          and not (Path(project_path).parent / "Urumea slope.qgz").exists())
    print("All agent data storage checks passed", flush=True)


try:
    main()
except Exception:
    traceback.print_exc()
    os._exit(1)
os._exit(0)
