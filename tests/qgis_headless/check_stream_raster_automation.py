"""Real automation of raw HTTP rasters, without public network or a dock.

docker run --rm --network none -v "$PWD:/src:ro" \
  -e QT_QPA_PLATFORM=offscreen -e PYTHONDONTWRITEBYTECODE=1 \
  qgis/qgis:ltr python3 /src/tests/qgis_headless/check_stream_raster_automation.py

Repeat with qgis/qgis:stable. Reuses the local byte-range COG fixture.
"""
import ast
import logging
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
import types

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from osgeo import gdal
from qgis.core import (
    Qgis, QgsApplication, QgsFeature, QgsGeometry, QgsProcessingFeedback,
    QgsProject, QgsRasterLayer, QgsVectorLayer,
)
from qgis.PyQt.QtCore import QCoreApplication, QTimer

from check_stream_raster import RangeServer, make_cog


def main():
    app = QgsApplication([], False)
    app.initQgis()
    main_thread = threading.get_ident()
    root = Path(__file__).resolve().parents[2]
    with tempfile.TemporaryDirectory(prefix='fm_automation_') as directory:
        folder = Path(directory)
        os.environ['FILTERMATE_LOG_DIR'] = str(folder / 'logs')
        plugins = folder / 'plugins'
        plugins.mkdir()
        (plugins / 'filter_mate').symlink_to(root, target_is_directory=True)
        sys.path.insert(0, str(plugins))
        sys.path.append(os.path.join(QgsApplication.pkgDataPath(), 'python', 'plugins'))
        from filter_mate.adapters.public_api import operations
        from filter_mate.adapters.qgis.coverage_layers import cache, raster_materialization
        from filter_mate.adapters.qgis.coverage_layers.cross_filter_task import CrossFilterTask
        from filter_mate.adapters.qgis.coverage_layers.snapshots import registry
        from filter_mate.core.domain.raster_filter_criteria import RasterSelection

        gdal.UseExceptions()
        gdal.SetConfigOption('GDAL_DISABLE_READDIR_ON_OPEN', 'EMPTY_DIR')
        gdal.SetConfigOption('GDAL_HTTP_TIMEOUT', '10')
        gdal.SetConfigOption('GDAL_PAM_ENABLED', 'NO')
        cache.set_cache_root(str(folder / 'cache'))
        server = RangeServer(make_cog(folder))
        serving = threading.Thread(target=server.serve_forever, daemon=True)
        serving.start()
        project = QgsProject.instance()
        threads = {'compute': [], 'apply': [], 'capture': [], 'progress': []}
        original_run, original_apply = CrossFilterTask.run, CrossFilterTask.apply_results
        original_capture = raster_materialization.materialize_raster
        unload_requested = threading.Event()
        unload_capturing = threading.Event()
        gui_reentry = threading.Event()
        app_tree = ast.parse((root / 'filter_mate_app.py').read_text())
        app_class = next(node for node in app_tree.body if isinstance(node, ast.ClassDef)
                         and node.name == 'FilterMateApp')
        app_methods = [node for node in app_tree.body if isinstance(node, ast.FunctionDef)
                       and node.name == '_api_operation_running']
        app_methods += [node for node in app_class.body if isinstance(node, ast.FunctionDef)
                        and node.name in ('manage_task', '_execute_filter_task')]
        warnings, gui_errors = [], []
        gui_namespace = {'__package__': 'filter_mate', '__name__': 'filter_mate.filter_mate_app', 'sys': sys,
                         'QCoreApplication': QCoreApplication,
                         'logger': logging.getLogger('fm_automation'),
                         'iface': types.SimpleNamespace(messageBar=lambda: types.SimpleNamespace(
                             pushWarning=lambda *args: warnings.append(args)))}
        exec(compile(ast.Module(body=app_methods, type_ignores=[]), str(root / 'filter_mate_app.py'), 'exec'),
             gui_namespace)

        def attempt_gui_filter():
            try:
                assert operations._RUNNING, 'GUI callback did not reenter active API operation'
                gui_namespace['manage_task'](types.SimpleNamespace(), 'filter')
                gui_namespace['_execute_filter_task'](types.SimpleNamespace(), 'filter', {})
            except Exception as exc:
                gui_errors.append(str(exc))

        def compute(task):
            threads['compute'].append(threading.get_ident())
            if gui_reentry.is_set():
                time.sleep(0.35)  # deterministic reviewer reproducer: GUI callback at 100 ms
            return original_run(task)

        def apply(task, result):
            threads['apply'].append(threading.get_ident())
            return original_apply(task, result)

        def capture(*args, **kwargs):
            threads['capture'].append(threading.get_ident())
            if unload_requested.is_set():
                unload_capturing.set()
                deadline = time.monotonic() + 5
                while not kwargs['is_canceled']() and time.monotonic() < deadline:
                    time.sleep(0.001)
                assert kwargs['is_canceled'](), 'service cancellation did not reach capture worker'
            return original_capture(*args, **kwargs)

        CrossFilterTask.run, CrossFilterTask.apply_results = compute, apply
        raster_materialization.materialize_raster = capture

        def remote(name):
            uri = '/vsicurl/http://127.0.0.1:{}/{}.tif'.format(server.server_port, name)
            layer = QgsRasterLayer(uri, name, 'gdal')
            assert layer.isValid(), name
            project.addMapLayer(layer)
            return layer

        def polygon(name, boxes):
            layer = QgsVectorLayer('Polygon?crs=EPSG:3857', name, 'memory')
            for x1, y1, x2, y2 in boxes:
                feature = QgsFeature()
                feature.setGeometry(QgsGeometry.fromWkt(
                    'POLYGON (({} {}, {} {}, {} {}, {} {}, {} {}))'.format(
                        x1, y1, x2, y1, x2, y2, x1, y2, x1, y1)))
                assert layer.dataProvider().addFeatures([feature])[0]
            layer.updateExtents()
            project.addMapLayer(layer)
            return layer

        ticks = []
        timer = QTimer()
        timer.timeout.connect(lambda: ticks.append(True))
        timer.start(1)
        try:
            source = remote('source')
            target = polygon('features', [(600, 200, 700, 300), (1400, 200, 1500, 300)])
            original_uri = source.source()
            gui_reentry.set()
            QTimer.singleShot(100, attempt_gui_filter)
            report = operations.cross_filter(source, [target], selected_only=False,
                                             raster_selection=RasterSelection(minimum=64, maximum=127),
                                             max_pixels=65536, project=project)
            gui_reentry.clear()
            assert not gui_errors and len(warnings) == 2, str((gui_errors, warnings))
            print('PASS nested Qt GUI vector launches at 100 ms refused during 350 ms API worker', flush=True)
            assert report.ok and target.id() in report.done, str(report)
            assert target.featureCount() == 1, target.subsetString()
            assert source.source() == original_uri
            print('PASS raw remote source without feedback filters expected vector', flush=True)

            mask = polygon('mask', [(256, 256, 1024, 1024)])
            remote_target = remote('target')
            feedback = QgsProcessingFeedback()
            feedback.progressChanged.connect(lambda value: threads['progress'].append(threading.get_ident()))
            report = operations.cross_filter(mask, [remote_target], selected_only=False,
                                             project=project, feedback=feedback)
            assert report.ok and remote_target.id() in report.done, str(report)
            assert remote_target.isValid() and cache.in_session(remote_target.source())
            dataset = gdal.Open(remote_target.source())
            assert dataset.RasterCount == 2, 'integer raster clip must preserve values plus alpha'
            transform = dataset.GetGeoTransform()
            def cell(band, x, y):
                column = int((x - transform[0]) / transform[1])
                row = int((y - transform[3]) / transform[5])
                if not (0 <= column < dataset.RasterXSize and 0 <= row < dataset.RasterYSize):
                    return None
                return dataset.GetRasterBand(band).ReadAsArray(column, row, 1, 1)[0, 0]
            # 2026-10-20: a remote target is captured around the area kept only (one cell of margin):
            # far outside the mask there is no pixel at all, just inside its edge the alpha masks.
            assert cell(2, 640, 512) > 0 and cell(2, 1500, 1500) is None and cell(2, 1030, 1030) in (0, None)
            assert 76 <= cell(1, 640, 512) <= 84, 'raw values were not preserved'
            dataset = None
            print('PASS raw remote target with feedback preserves values and masks outside selection', flush=True)

            alone = remote('source_only')
            report = operations.cross_filter(alone, [], filter_source=True,
                                             raster_selection=RasterSelection(minimum=64, maximum=127),
                                             max_pixels=65536, project=project)
            assert report.ok and alone.id() in report.done, str(report)
            assert alone.isValid() and cache.in_session(alone.source())
            print('PASS raw remote source without targets computed in worker', flush=True)

            alternate = QgsProject()
            alternate_source = QgsRasterLayer(
                '/vsicurl/http://127.0.0.1:{}/alternate.tif'.format(server.server_port), 'alternate', 'gdal')
            assert alternate_source.isValid()
            alternate.addMapLayer(alternate_source)
            try:
                report = operations.cross_filter(alternate_source, [], filter_source=True,
                                                 raster_selection=RasterSelection(minimum=64, maximum=127),
                                                 max_pixels=65536, project=alternate)
                assert report.ok and alternate_source.id() in report.done, str(report)
                assert alternate_source.isValid() and cache.in_session(alternate_source.source())
                assert project.mapLayer(alternate_source.id()) is None
                print('PASS raw source-only filter honors explicit project distinct from singleton', flush=True)
            finally:
                alternate.removeAllMapLayers()
                # Destroy the independent project while QGIS and Python signal
                # receivers are alive, rather than during interpreter teardown.
                registry().uninstall()
                alternate_source = None
                alternate = None
                operations._install_registry(project)

            unload_target = remote('unload_target')
            unload_uri = unload_target.source()
            api_service = operations._api_service()
            canceled = []
            cancel_timer = QTimer()
            def unload_when_capturing():
                if not unload_capturing.is_set() or canceled:
                    return
                assert api_service._running, 'API task missing from service registry'
                assert operations._background_tasks_running(), 'private API worker not reported busy'
                api_service.cancel_all()
                canceled.append(True)
            cancel_timer.timeout.connect(unload_when_capturing)
            cancel_timer.start(1)
            unload_requested.set()
            try:
                report = operations.cross_filter(mask, [unload_target], selected_only=False,
                                                 project=project, service=api_service)
            finally:
                cancel_timer.stop()
                unload_requested.clear()
            assert canceled and report.error and not report.done, str(report)
            assert unload_target.source() == unload_uri, 'canceled worker mutated project layer'
            assert not api_service._running, 'API task lease leaked'
            assert not operations.busy_reason(), 'API remained busy after canceled worker drained'
            print('PASS service unload cancels API capture with no mutation or stale busy lease', flush=True)

            assert ticks, 'Qt event loop did not advance'
            assert threads['compute'] and all(t != main_thread for t in threads['compute'])
            assert threads['capture'] and all(t != main_thread for t in threads['capture'])
            assert threads['apply'] and set(threads['apply']) == {main_thread}
            assert threads['progress'] and set(threads['progress']) == {main_thread}
            assert server.snapshot()[1] > 0
            print('PASS worker captures, main application/progress, Qt heartbeat; QGIS ' + Qgis.QGIS_VERSION,
                  flush=True)
        finally:
            timer.stop()
            CrossFilterTask.run, CrossFilterTask.apply_results = original_run, original_apply
            raster_materialization.materialize_raster = original_capture
            project.removeAllMapLayers()
            registry().uninstall()
            cache.purge_session()
            server.shutdown()
            server.server_close()
            serving.join(timeout=2)
    return 0


if __name__ == '__main__':
    sys.exit(main())
