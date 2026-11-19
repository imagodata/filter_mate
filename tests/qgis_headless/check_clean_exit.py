# -*- coding: utf-8 -*-
"""QGIS quits cleanly after FilterMate was used: exit code 0, no abort while the application is torn down.

The GUI smoke leaves with os._exit(): nothing in the bench went through the real end of QGIS. On 2026-11-18 the
recordings of the site videos (scripts/site_videos.py) ended with "pure virtual method called" (exit 134) or a
segmentation fault (139) when EXPLORING was in its own panel and Identify or Tracking had been used.

One case per run, chosen by FM_EXIT_CASE:

    plain      the dock opened, nothing else
    detached   EXPLORING in its own panel
    identify   a feature picked, Identify clicked (the feature flashes), EXPLORING in the dock
    identify_detached, tracking, tracking_detached   the same with EXPLORING apart, or Tracking and three "next"

and the way out by FM_EXIT_HOW: ``quit`` (QgsApplication.quit(), as the recordings do) or ``close`` (the main
window closed, as a user does). The caller reads the exit code of QGIS: 0 is a clean end, 4 means QGIS was still
running 45 s after the way out (the check says which question kept it open), 134 / 139 an abort.

    docker run --rm -v "$PWD:/src:ro" -e FM_EXIT_CASE=tracking_detached qgis/qgis:stable bash -c \
      "python3 /src/tests/qgis_headless/make_fixtures.py /srv/fm >/dev/null 2>&1; FM_FIXTURES=/srv/fm \
       dbus-run-session -- xvfb-run -a qgis --nologo --noversioncheck --profiles-path /tmp/profiles \
       --code /src/tests/qgis_headless/check_clean_exit.py; echo EXIT=\\$?"

The fixtures must not be under /tmp: QGIS takes a layer read from the temporary folder for a temporary layer and
asks before closing the project ("one or more temporary layers"), which nobody answers here.

2026-11-19: 24 runs out of 24 ended with 0 on qgis/qgis:stable (the six cases by ``quit``, the three with
EXPLORING apart three more times by ``quit`` and by ``close``): the aborts of the recordings were not reproduced
without the recorder.
"""
import json
import os
import shutil
import sys
import tempfile

from qgis.core import QgsApplication, QgsProject, QgsVectorLayer
from qgis.PyQt.QtCore import QSettings, QTimer
from qgis.PyQt.QtWidgets import QToolButton
from qgis.utils import iface

REPO = os.environ.get('FM_REPO') or (os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                                     if '__file__' in globals() else '/src')
PACKAGE = os.environ.get('FM_PACKAGE') or 'filter_mate'
EXCLUDED = ('.git', '.github', '.claude', '.serena', '_bmad', '_bmad-output', 'dist', 'build', 'scripts',
            'knowledge', 'website', 'tests', 'docs', 'logs', '__pycache__', '*.pyc', 'test_*.py')
FIXTURES = os.environ.get('FM_FIXTURES', '/tmp/fm')
CASE = os.environ.get('FM_EXIT_CASE', 'tracking_detached')
HOW = os.environ.get('FM_EXIT_HOW', 'quit')


def say(text):
    print(f'EXITCHECK {text}', flush=True)


def _watchdog():
    say('FAIL watchdog: the steps did not reach the end')
    os._exit(2)


QTimer.singleShot(150 * 1000, _watchdog)


def dock():
    import qgis.utils
    plugin = qgis.utils.plugins.get(PACKAGE)
    return getattr(getattr(plugin, 'app', None), 'dockwidget', None)


def s_open():
    import qgis.utils
    with open(os.path.join(FIXTURES, 'manifest.json'), encoding='utf-8') as stream:
        manifest = json.load(stream)
    iface.mainWindow().resize(1600, 1000)
    zones = QgsVectorLayer(manifest['zones'] + '|layername=zones', 'zones', 'ogr')
    QgsProject.instance().addMapLayer(zones)
    iface.mapCanvas().setExtent(zones.extent())
    settings = QSettings()
    settings.setValue('FilterMate/discord_welcome_dismissed', True)
    settings.setValue('FilterMate/whats_new_seen', 99)
    settings.setValue('qgis/digitizing/validate_geometries', 0)
    plugins = os.path.join(tempfile.mkdtemp(prefix='fm_exit_'), 'plugins')
    shutil.copytree(REPO, os.path.join(plugins, PACKAGE), ignore=shutil.ignore_patterns(*EXCLUDED))
    sys.path.insert(0, plugins)
    qgis.utils.plugin_paths.insert(0, plugins)
    qgis.utils.updateAvailablePlugins()
    started = qgis.utils.loadPlugin(PACKAGE) and qgis.utils.startPlugin(PACKAGE)
    qgis.utils.plugins[PACKAGE].run()
    say(f'plugin started {bool(started)} case={CASE} how={HOW}')


def s_use():
    d = dock()
    zones = QgsProject.instance().mapLayersByName('zones')[0]
    iface.setActiveLayer(zones)
    if CASE.endswith('detached'):
        say(f"detach exploring: {d._fm_panels.detach('exploring')}")


def s_pick():
    if CASE in ('plain', 'detached'):
        return
    d = dock()
    zones = QgsProject.instance().mapLayersByName('zones')[0]
    d.mGroupBox_exploring_single_selection.setChecked(True)
    if CASE.startswith('tracking'):
        d.pushButton_checkable_exploring_tracking.setChecked(True)
    fid = next(zones.getFeatures()).id()
    d.mFeaturePickerWidget_exploring_single_selection.setFeature(fid)
    say(f'picked {fid}')


def s_act():
    if CASE in ('plain', 'detached'):
        return
    d = dock()
    if CASE.startswith('identify'):
        d.pushButton_exploring_identify.click()
        say('identify clicked')
    else:
        buttons = [b for b in d.mFeaturePickerWidget_exploring_single_selection.findChildren(QToolButton)
                   if b.isVisible()]
        for delay in (0, 700, 1400):
            QTimer.singleShot(delay, buttons[-1].click)
        say(f'three "next" with tracking on ({len(buttons)} browser buttons)')


def _what_blocks():
    """A question asked on the way out keeps QGIS open: say which one."""
    from qgis.PyQt.QtWidgets import QApplication, QLabel
    widget = QApplication.activeModalWidget() or QApplication.activePopupWidget()
    if widget is None:
        say('no modal widget 4 s after the way out')
        return
    texts = [label.text()[:160] for label in widget.findChildren(QLabel) if label.text()]
    say(f'BLOCKED by {type(widget).__name__} "{widget.windowTitle()}": {texts}')


def s_leave(tries=0):
    import faulthandler
    # QGIS asks before closing while a task runs: a question nobody answers here. Wait for the tasks first, as the
    # recordings do (quit_when_idle).
    active = [task.description() for task in QgsApplication.taskManager().activeTasks()]
    if active and tries < 80:
        if tries % 10 == 0:
            say(f'waiting for {active}')
        QTimer.singleShot(500, lambda: s_leave(tries + 1))
        return
    layers = [(layer.name(), layer.providerType(), layer.customPropertyKeys()[:4]) for layer in QgsProject.instance().mapLayers().values()]
    say(f'layers of the project: {layers}')
    QgsProject.instance().setDirty(False)
    say(f'REACHED the way out (tasks still active: {active})')
    # still alive 40 s later: say where (every thread), then leave with a code of its own
    faulthandler.dump_traceback_later(40, exit=False, file=sys.stderr)
    QTimer.singleShot(45 * 1000, lambda: (say('FAIL still running 45 s after the way out'), os._exit(4)))
    QTimer.singleShot(4000, _what_blocks)
    if HOW == 'close':
        iface.mainWindow().close()
    else:
        QgsApplication.instance().quit()


for delay, step in ((2000, s_open), (14000, s_use), (17000, s_pick), (20000, s_act), (26000, s_leave)):
    QTimer.singleShot(delay, step)
