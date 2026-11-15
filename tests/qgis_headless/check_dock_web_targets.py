# -*- coding: utf-8 -*-
"""Web services as targets of the dock, in a real QGIS with its GUI (Xvfb), with no network.

    docker run --rm --network none -v "$PWD:/src:ro" qgis/qgis:ltr bash -c \\
        'dbus-run-session -- xvfb-run -a -s "-screen 0 1600x1000x24" qgis --nologo --noversioncheck --lang en \\
         --profiles-path /tmp/profiles --code /src/tests/qgis_headless/check_dock_web_targets.py'

2026-11-15. ``check_stream_extent_clip.py`` goes through the public API; this script goes through the widgets of
the dock, the way a user does: a vector source is chosen, a tile basemap and a WFS layer are ticked among the layers
to filter, Filter is pressed, then Unfilter. The tiles were listed greyed and the WFS was refused past 500 features.
The two local servers are those of ``check_stream_extent_clip.py``.

Prints one PASS / FAIL line per check; QGIS exits with 1 when one failed.
"""
import faulthandler
import importlib
import logging
import os
import shutil
import sys
import tempfile
import threading
import time
import traceback
from http.server import ThreadingHTTPServer

from qgis.core import Qgis, QgsApplication, QgsFeature, QgsGeometry, QgsProject, QgsRasterLayer, QgsVectorLayer
from qgis.PyQt.QtCore import QSettings, Qt, QTimer
from qgis.utils import iface
import qgis.utils

faulthandler.enable(all_threads=True)
logging.raiseExceptions = False
REPO = os.environ.get('FM_REPO') or (os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                                     if '__file__' in globals() else '/src')
PACKAGE = 'filter_mate'
EXCLUDED = ('.git', '.github', '.claude', '.serena', '_bmad', '_bmad-output', 'dist', 'build', 'scripts',
            'knowledge', 'website', 'tests', 'docs', 'logs', '__pycache__', '*.pyc', 'test_*.py')
STEP_TIMEOUT = float(os.environ.get('FM_STEP_TIMEOUT', '90'))
STATE = {'results': [], 'errors': [], 'started': time.time()}
sys.path.insert(0, os.path.join(REPO, 'tests', 'qgis_headless'))
import check_stream_extent_clip as bench  # noqa: E402 - the two local servers
project = QgsProject.instance()


def _show_exception(type_, value, tb, msg=None, messagebar=False, level=None):
    """qgis.utils.showException opens a modal dialog that would block the run: record and print instead."""
    text = ''.join(traceback.format_exception(type_, value, tb)).strip()
    STATE['errors'].append(f"{msg or ''} {text.splitlines()[-1] if text else value}".strip())
    print(f"   [Python exception] {msg or ''}\n{text}", flush=True)


qgis.utils.showException = _show_exception
QTimer.singleShot(6 * 60 * 1000, lambda: (print('FAIL   watchdog: not finished in 6 minutes', flush=True), os._exit(2)))


def check(name, condition, detail=''):
    STATE['results'].append(bool(condition))
    print(f"{'PASS' if condition else 'FAIL'}   {name}" + (f"  -- {str(detail)[:500]}" if not condition else ''), flush=True)
    return bool(condition)


def app():
    return qgis.utils.plugins[PACKAGE].app


def dock():
    return app().dockwidget


def layer(name):
    found = project.mapLayersByName(name)
    return found[0] if found else None


def tasks_idle():
    try:
        own = set(app().tasks_descriptions.values())
    except Exception:
        own = set()
    return not [task for task in QgsApplication.taskManager().activeTasks()
                if task.description().startswith('FilterMate') or task.description() in own]


def registered(*names):
    ids = [layer(name).id() for name in names if layer(name) is not None]
    return len(ids) == len(names) and all(layer_id in app().PROJECT_LAYERS for layer_id in ids)


def target_rows():
    model = dock().checkableComboBoxLayer_filtering_layers_to_filter.model()
    return [model.item(row) for row in range(model.rowCount())]


SAID = []  # every message seen in the bar, in order: a later one may hide or replace an earlier one
LOGGED = []  # what the plugin logged at WARNING and above


def _watch_bar():
    for item in iface.messageBar().items():
        try:
            text = f"{item.title()}: {item.text()}"
        except Exception:
            continue
        if text not in SAID:
            SAID.append(text)


_BAR_TIMER = QTimer()
_BAR_TIMER.timeout.connect(_watch_bar)
_BAR_TIMER.start(100)


class _Records(logging.Handler):
    def emit(self, record):
        LOGGED.append(f"{record.levelname[0]} {record.name.split('.')[-1]}: {record.getMessage()[:300]}")


_RECORDS = _Records(level=logging.WARNING)


def watch_loggers():
    """Each logger of the plugin has its own handlers and does not propagate."""
    for name, logger in list(logging.root.manager.loggerDict.items()):
        if isinstance(logger, logging.Logger) and name.split('.')[0] in ('FilterMate', PACKAGE) \
                and _RECORDS not in logger.handlers:
            logger.addHandler(_RECORDS)


def message_bar_texts():
    _watch_bar()
    return list(SAID)


def after(seconds, condition=lambda: True):
    since = time.time()
    return lambda: time.time() - since > seconds and tasks_idle() and condition()


# --- steps: each returns None, or a condition polled until true (or STEP_TIMEOUT) ---

def s_setup():
    window = iface.mainWindow()
    window.resize(1600, 1000)
    window.show()
    services = ThreadingHTTPServer(('127.0.0.1', 0), bench.WfsHandler)
    maps = ThreadingHTTPServer(('127.0.0.1', 0), bench.MapHandler)
    for server in (services, maps):
        threading.Thread(target=server.serve_forever, daemon=True).start()
    STATE['servers'] = (services, maps)
    zones = QgsVectorLayer('Polygon?crs=EPSG:3857&field=name:string', 'zones', 'memory')
    feature = QgsFeature(zones.fields())
    feature.setAttributes(['big'])
    # More than 500 of the points of the WFS layer lie in it (61 x 31 in its rectangle).
    feature.setGeometry(QgsGeometry.fromWkt('POLYGON((95 95, 705 95, 505 405, 95 405, 95 95))'))
    medium = QgsFeature(zones.fields())
    medium.setAttributes(['medium'])
    # Twenty of the points lie in it: a list of keys short enough for most servers (7 KB of address), and too long
    # for the WFS type ``strict``, which reads 3,000 bytes.
    medium.setGeometry(QgsGeometry.fromWkt('POLYGON((95 95, 145 95, 145 135, 95 135, 95 95))'))
    zones.dataProvider().addFeatures([feature, medium])
    zones.updateExtents()
    project.addMapLayer(zones)
    bench.wfs_layer(services.server_port, 'keyed')
    bench.wfs_layer(services.server_port, 'strict')
    uri = f"type=xyz&url=http://127.0.0.1:{maps.server_port}/tiles/{{z}}/{{x}}/{{y}}.png&zmin=0&zmax=14&crs=EPSG:3857"
    tiles = QgsRasterLayer(uri, 'tuiles', 'wms')
    project.addMapLayer(tiles)
    STATE['tiles_source'] = tiles.source()
    iface.mapCanvas().setExtent(zones.extent())
    check('the source, the WFS layers and the tiles load', zones.isValid() and layer('keyed').isValid()
          and layer('strict').isValid() and tiles.isValid())


def s_open_plugin():
    settings = QSettings()
    settings.setValue('FilterMate/discord_welcome_dismissed', True)  # modal dialogs would block the run
    settings.setValue('FilterMate/whats_new_seen', 99)
    settings.setValue('qgis/digitizing/validate_geometries', 0)
    plugins = os.path.join(tempfile.mkdtemp(prefix='fm_gui_'), 'plugins')
    shutil.copytree(REPO, os.path.join(plugins, PACKAGE), ignore=shutil.ignore_patterns(*EXCLUDED))
    sys.path.insert(0, plugins)
    qgis.utils.plugin_paths.insert(0, plugins)
    qgis.utils.updateAvailablePlugins()
    started = qgis.utils.loadPlugin(PACKAGE) and qgis.utils.startPlugin(PACKAGE)
    check('plugin starts with iface', started and PACKAGE in qgis.utils.plugins)
    cache = importlib.import_module(f'{PACKAGE}.adapters.qgis.coverage_layers.cache')
    cache.set_cache_root(os.path.join(os.path.dirname(plugins), 'cache'))
    qgis.utils.plugins[PACKAGE].run()
    return lambda: dock() is not None and registered('zones', 'keyed', 'strict', 'tuiles') and tasks_idle()


def s_source():
    check('dock open, the four layers registered', dock() is not None
          and registered('zones', 'keyed', 'strict', 'tuiles'))
    dock().comboBox_filtering_current_layer.setLayer(layer('zones'))
    return after(3.0, lambda: dock().current_layer is not None and dock().current_layer.name() == 'zones')


def s_select():
    d = dock()
    rows = {item.text().split(' [')[0]: item for item in target_rows()}
    tiles = rows.get('tuiles')
    check('the tiles are listed among the layers to filter, and can be ticked (they were greyed)',
          tiles is not None and bool(tiles.flags() & Qt.ItemFlag.ItemIsEnabled), sorted(rows))
    check('the WFS layer is listed among the layers to filter', 'keyed' in rows, sorted(rows))
    d.mGroupBox_exploring_single_selection.setChecked(True)
    return choose('big', ('keyed', 'tuiles'))


def choose(zone, targets):
    """The feature ``zone`` of the source in EXPLORING, ``targets`` ticked among the layers to filter, Intersect."""
    d = dock()
    chosen = next(feature for feature in layer('zones').getFeatures() if feature['name'] == zone)
    d.mFeaturePickerWidget_exploring_single_selection.setFeature(chosen.id())
    for item in target_rows():
        if item.flags() & Qt.ItemFlag.ItemIsEnabled:
            name = item.text().split(' [')[0]
            item.setCheckState(Qt.CheckState.Checked if name in targets else Qt.CheckState.Unchecked)
    if not d.pushButton_checkable_filtering_layers_to_filter.isChecked():
        d.pushButton_checkable_filtering_layers_to_filter.setChecked(True)
    if not d.pushButton_checkable_filtering_geometric_predicates.isChecked():
        d.pushButton_checkable_filtering_geometric_predicates.setChecked(True)
    d.comboBox_filtering_geometric_predicates.setCheckedItems(['Intersect'])
    wanted = {layer(name).id() for name in targets}

    def ready():
        features = d.get_current_features()[0]
        return bool(features) and features[0]['name'] == zone and wanted == set(d.get_layers_to_filter() or [])
    return ready


def wfs_filters():
    """Whether this QGIS sets the filter of a WFS at all (from 3.24: its setter crashes before)."""
    transfer = importlib.import_module(f'{PACKAGE}.adapters.qgis.server_subset_job')
    policy = importlib.import_module(f'{PACKAGE}.core.filter.server_transfer_policy')
    mode = transfer.transfer_mode_for_layer(layer('keyed'))
    # Prepared and checked off the main thread before it is set (from 3.32): a filter the service refuses is seen.
    STATE['prepared'] = mode == policy.ASYNC
    return mode != policy.REFUSE


def s_filter():
    del bench.ASKED[:], bench.TILES[:], SAID[:], LOGGED[:]
    iface.messageBar().clearWidgets()
    STATE['filter_started'] = time.time()
    STATE['wfs'] = wfs_filters()
    dock().launchTaskEvent(False, 'filter')
    return lambda: (layer('tuiles').providerType() == 'gdal'
                    and (not STATE['wfs'] or layer('keyed').subsetString() != '') and tasks_idle())


def s_filter_said():
    """The messages of a filter come after its layers changed: wait for them."""
    return after(3.0)


def s_filter_check():
    tiles, keyed = layer('tuiles'), layer('keyed')
    print(f"   said: {message_bar_texts()}\n   logged: {LOGGED[:12]}", flush=True)
    check('dock: the tiles are cut by the source, from a capture', tiles.isValid() and tiles.providerType() == 'gdal'
          and tiles.source().endswith('.vrt'), (tiles.providerType(), tiles.source()[-50:]))
    inside, outside = bench.pixel(tiles, 300, 250), bench.pixel(tiles, 680, 380)
    check('dock: inside the source the image of the tiles, outside it nothing',
          inside is not None and inside[3] == 255 and (outside or (0, 0, 0, 0))[3] == 0, (inside, outside))
    # (None at all when the canvas had already drawn them: QGIS keeps the tiles it fetched.)
    check('dock: no tile beyond the source was asked', len(bench.TILES) <= 9, len(bench.TILES))
    said = ' | '.join(message_bar_texts())
    check('dock: the message says the tiles are a still image, and its resolution', 'still image' in said, said[:600])
    if STATE['wfs']:
        check('dock: past 500 features the WFS layer is cut by the extent of the source',
              keyed.subsetString().startswith("intersects_bbox($geometry, geom_from_wkt('POLYGON((95 95, 705 95, "
                                              "705 405, 95 405, 95 95))'))"), keyed.subsetString()[:140])
        given = bench.shown(keyed)
        check('dock: the WFS layer gives what meets that extent', given == bench.inside(95, 95, 705, 405),
              (len(given), len(bench.inside(95, 95, 705, 405))))
        check('dock: the message says the WFS layer is cut by the extent of the source', 'extent of the source' in said,
              said[:600])
    else:
        check('dock, a QGIS that sets no WFS filter: the WFS layer is left as it was', keyed.subsetString() == '',
              keyed.subsetString()[:140])
    check('dock: the server refused no request', not bench.REFUSED, bench.REFUSED)
    return after(3.0)


def s_unfilter():
    dock().launchTaskEvent(False, 'unfilter')
    return lambda: layer('tuiles').providerType() == 'wms' and layer('keyed').subsetString() == '' and tasks_idle()


def s_unfilter_check():
    tiles, keyed = layer('tuiles'), layer('keyed')
    check('dock: Unfilter gives the live tiles back', tiles.isValid() and tiles.providerType() == 'wms'
          and tiles.source() == STATE['tiles_source'], (tiles.providerType(), tiles.source()[:80]))
    check('dock: Unfilter gives the whole WFS layer back', keyed.subsetString() == '', keyed.subsetString()[:80])


def s_settled():
    """For a few seconds after a filter or an unfilter the dock puts back what it had: wait before choosing again."""
    return after(3.0)


def s_refused_select():
    """A source of twenty features and a WFS that refuses the address their keys make, as a real one did."""
    STATE['exact'] = importlib.import_module(f'{PACKAGE}.adapters.qgis.remote_materializer').supports_reply_validation()
    transfer = importlib.import_module(f'{PACKAGE}.adapters.qgis.server_subset_job')
    # From QGIS 3.32 a WFS filter is tried on a copy of the provider before it is set: the refusal is seen there.
    STATE['asks'] = transfer.transfer_mode_for_layer(layer('strict')) == transfer.ASYNC
    return choose('medium', ('strict',))


def s_refused_filter():
    del bench.TOO_LONG[:], SAID[:], LOGGED[:]
    iface.messageBar().clearWidgets()
    dock().launchTaskEvent(False, 'filter')
    return lambda: (not STATE['wfs'] or layer('strict').subsetString() != '') and tasks_idle()


def s_refused_check():
    strict = layer('strict')
    said = ' | '.join(message_bar_texts())
    print(f"   said: {message_bar_texts()}", flush=True)
    if not STATE['wfs']:
        check('dock, a QGIS that sets no WFS filter: the WFS layer is left as it was', strict.subsetString() == '',
              strict.subsetString()[:140])
        return None
    if STATE['exact'] and not STATE['asks']:
        # QGIS 3.24 to 3.31 sets the filter without asking the service: the refusal only shows when the layer is
        # read, in the words of QGIS. As before this change.
        check('dock, a QGIS that sets a WFS filter without asking: the list of keys is set',
              '"id" IN' in strict.subsetString(), strict.subsetString()[:140])
        return after(3.0)
    check('dock: the keys the service refused give way to a cut by the extent of the source',
          strict.subsetString().startswith("intersects_bbox($geometry, geom_from_wkt('POLYGON((95 95, 145 95, "
                                           "145 135, 95 135, 95 95))'))"), strict.subsetString()[:140])
    given = bench.shown(strict)
    check('dock: the layer gives what meets that extent', given == bench.inside(95, 95, 145, 135), len(given))
    if STATE['exact']:
        check('dock: the service did refuse the list of keys, and the message says so',
              bool(bench.TOO_LONG) and 'refused the list' in said, (bench.TOO_LONG[:2], said[:600]))
    else:
        check('dock, a QGIS that cannot check a service: cut by extent at once, and the message says why',
              not bench.TOO_LONG and 'this version of QGIS' in said, (bench.TOO_LONG[:2], said[:600]))
    return after(3.0)


def s_refused_unfilter():
    dock().launchTaskEvent(False, 'unfilter')
    return lambda: layer('strict').subsetString() == '' and tasks_idle()


def s_refused_unfilter_check():
    check('dock: Unfilter gives the whole WFS layer back', layer('strict').subsetString() == '',
          layer('strict').subsetString()[:80])


def s_refused_or_not():
    """The keys a service refuses: where QGIS prepares a WFS filter before setting it (from 3.32).

    From 3.24 to 3.31 it sets the filter without asking the service anything: the refusal is not seen then, only as
    an empty layer when the layer is read, as before 2026-11-15.
    """
    if STATE.get('prepared'):
        at = STEPS.index(s_refused_or_not) + 1
        STEPS[at:at] = REFUSED_KEYS
    else:
        print('SKIP   dock: the keys the service refused (this QGIS sets a WFS filter without preparing it)', flush=True)


def s_finish():
    check('no Python error', not STATE['errors'], '; '.join(STATE['errors'][:3]))
    failed = STATE['results'].count(False)
    print(f"\n{len(STATE['results']) - failed} passed, {failed} failed in {time.time() - STATE['started']:.1f}s "
          f"(QGIS {Qgis.QGIS_VERSION}, dock)", flush=True)
    os._exit(1 if failed else 0)  # the exit code of QGIS is the result


REFUSED_KEYS = [s_settled, s_refused_select, s_refused_filter, s_filter_said, s_refused_check, s_refused_unfilter,
                s_refused_unfilter_check]
STEPS = [s_setup, s_open_plugin, s_source, s_select, s_filter, s_filter_said, s_filter_check, s_unfilter,
         s_unfilter_check, s_refused_or_not, s_finish]


def run_step(index=0):
    watch_loggers()
    step = STEPS[index]
    try:
        until = step()
    except Exception:
        check(f"{step.__name__} raised", False, traceback.format_exc().strip().splitlines()[-1])
        print(traceback.format_exc(), flush=True)
        until = None
        if step in (s_setup, s_open_plugin):
            QTimer.singleShot(0, lambda: run_step(STEPS.index(s_finish)))
            return
    wait(index, until, time.time())


def wait(index, until, since):
    """Poll ``until`` every 250 ms, then move on (a timeout is reported, the next check tells what failed)."""
    if until is not None:
        try:
            done = until()
        except Exception:
            done = False
        if not done and time.time() - since < STEP_TIMEOUT:
            QTimer.singleShot(250, lambda: wait(index, until, since))
            return
        if not done:
            print(f"   (timeout after {STEP_TIMEOUT:.0f}s waiting at the end of {STEPS[index].__name__})", flush=True)
    QTimer.singleShot(300, lambda: run_step(index + 1))


QTimer.singleShot(2000, run_step)
