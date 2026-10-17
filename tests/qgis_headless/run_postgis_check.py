# -*- coding: utf-8 -*-
"""
FilterMate on PostGIS: canceled tasks, materialized views and connections (QGIS GUI under Xvfb).

A PostgreSQL / PostGIS server is needed (``FM_PG``, a libpq connection string), e.g. on a dedicated
Docker network:

    docker network create fm_pg_net
    docker run -d --name fm_pg --network fm_pg_net -e POSTGRES_PASSWORD=fm postgis/postgis:16-3.4
    docker run --rm --network fm_pg_net -v "$PWD:/src:ro" -e FM_FIXTURES=/tmp/fm \\
        -e FM_PG="host=fm_pg port=5432 dbname=postgres user=postgres password=fm" qgis/qgis:stable bash -c \\
        'python3 /src/tests/qgis_headless/make_fixtures.py /tmp/fm > /dev/null && xvfb-run -a qgis --nologo \\
         --noversioncheck --profiles-path /tmp/p --code /src/tests/qgis_headless/run_postgis_check.py'

Checks (2026-10-17 review of the thread / lifecycle fixes): a PostgreSQL filter whose source selection
is large enough for a materialized view; an unfilter canceled by a filter launched at once; a second
click on Filter. After each: no target left empty or unreadable, no materialized view that no subset
reads, no connection "idle in transaction (aborted)" or left open by a task, no subset set from a
worker thread, no Python error or critical message. ``FM_PG_DEBUG=1`` prints the views of the canceled
task and the stack of every subset change of the target.
"""
import faulthandler
import logging
import os
import re
import shutil
import sys
import tempfile
import time
import traceback

from qgis.core import Qgis, QgsApplication, QgsDataSourceUri, QgsProject, QgsVectorLayer
from qgis.PyQt.QtCore import QSettings, Qt, QThread, QTimer
from qgis.utils import iface
import qgis.utils

STATE = {'results': [], 'errors': [], 'started': time.time()}
faulthandler.enable(all_threads=True)
PG = os.environ.get('FM_PG', 'host=fm_pg port=5432 dbname=postgres user=postgres password=fm')
REPO = os.environ.get('FM_REPO') or (os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                                     if '__file__' in globals() else '/src')
PACKAGE = 'filter_mate'
EXCLUDED = ('.git', '.github', '.claude', '.serena', '_bmad', '_bmad-output', 'dist', 'build', 'scripts',
            'knowledge', 'website', 'tests', 'docs', 'logs', '__pycache__', '*.pyc', 'test_*.py')
TEMP_SCHEMA = 'filter_mate_temp'
# A source of more than 100,000 features: the PostgreSQL backend filters it through a materialized view
ZONES_SIDE = int(os.environ.get('FM_PG_ZONES_SIDE', '330'))
POINTS = int(os.environ.get('FM_PG_POINTS', '20000'))
project = QgsProject.instance()


def _show_exception(type_, value, tb, msg=None, messagebar=False, level=None):
    text = ''.join(traceback.format_exception(type_, value, tb)).strip()
    STATE['errors'].append(f"{msg or ''} {text.splitlines()[-1] if text else value}".strip())
    print(f"   [Python exception] {msg or ''}\n{text}", flush=True)


qgis.utils.showException = _show_exception
QTimer.singleShot(10 * 60 * 1000, lambda: (print('FAIL   watchdog', flush=True), os._exit(2)))


def _on_log(message, tag, level):
    if tag == 'Python error' or (tag == 'FilterMate' and level == Qgis.MessageLevel.Critical):
        STATE['errors'].append(f"[{tag}] {message[:300]}")


QgsApplication.messageLog().messageReceived.connect(_on_log)


class _ErrorRecords(logging.Handler):
    def emit(self, record):
        STATE['errors'].append(f"[{record.name}] {record.getMessage()[:300]}")


_ERRORS = _ErrorRecords(level=logging.ERROR)


class _ViewRecords(logging.Handler):
    """FilterMate's lines about materialized views (printed: what a canceled task dropped)."""

    def emit(self, record):
        message = record.getMessage()
        if 'view' in message.lower() and ('anceled' in message or 'dropped' in message.lower()):
            print(f"   | {record.name}: {message[:200]}", flush=True)


_VIEWS = _ViewRecords(level=logging.INFO)


def watch_plugin_loggers():
    for name, logger in list(logging.root.manager.loggerDict.items()):
        if isinstance(logger, logging.Logger) and name.split('.')[0] in ('FilterMate', 'filter_mate') \
                and _ERRORS not in logger.handlers:
            logger.addHandler(_ERRORS)
            logger.addHandler(_VIEWS)
            if logger.level > logging.INFO or logger.level == logging.NOTSET:
                logger.setLevel(logging.INFO)


def report(status, name, detail=''):
    STATE['results'].append((status, name))
    print(f"{status:<5}  {name}  {detail}".rstrip(), flush=True)


def check(name, condition, detail=''):
    report('PASS' if condition else 'FAIL', name, detail)


def sql(query, fetch=True):
    import psycopg2
    conn = psycopg2.connect(PG)
    try:
        with conn.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall() if fetch and cur.description else []
        conn.commit()
        return rows
    finally:
        conn.close()


def app():
    return qgis.utils.plugins[PACKAGE].app


def dock():
    return app().dockwidget


def layer(name):
    found = project.mapLayersByName(name)
    return found[0] if found else None


def tasks_idle():
    own = set(app().tasks_descriptions.values())
    return not [task for task in QgsApplication.taskManager().activeTasks()
                if task.description().startswith('FilterMate') or task.description() in own]


def settled(seconds=3.0):
    state = {'since': None}

    def done():
        if not tasks_idle():
            state['since'] = None
            return False
        state['since'] = state['since'] or time.time()
        return time.time() - state['since'] > seconds
    return done


def pg_layer(table, name):
    uri = QgsDataSourceUri(PG)
    uri.setDataSource('public', table, 'geom', '', 'id')
    return QgsVectorLayer(uri.uri(False), name, 'postgres')


def matviews():
    return {row[0] for row in sql(f"SELECT matviewname FROM pg_matviews WHERE schemaname = '{TEMP_SCHEMA}'")}


def aborted_connections():
    return sql("SELECT pid, application_name, left(query, 80) FROM pg_stat_activity "
               "WHERE state = 'idle in transaction (aborted)'")


def state_check(label, expect_filtered):
    """No unreadable / unexpectedly empty layer, no view nothing reads, no aborted transaction."""
    counts, unreadable = {}, []
    for name in ('zones', 'pts'):
        target = layer(name)
        try:
            counts[name] = sum(1 for _ in target.getFeatures())
        except Exception as exc:
            unreadable.append(f"{name}: {exc}")
        if target.dataProvider().hasErrors():
            unreadable.append(f"{name}: {target.dataProvider().errors()[-1:]}")
            target.dataProvider().clearErrors()
    subsets = ' '.join(layer(name).subsetString() for name in ('zones', 'pts'))
    views = matviews()
    read = {view for view in views if view in subsets}
    # a view read by another view (the *_dump of a source view) counts as read with it
    read |= {view for view in views if any(view.startswith(other) for other in read)}
    # The views of the filters a later one replaced stay for the undo history (by design, as on
    # main): a leak is a view created during this step that nothing reads.
    orphans = sorted((views - STATE.get('views_before', set())) - read)
    if expect_filtered:
        ok = counts.get('pts', 0) > 0 and counts['pts'] < STATE['pts_total'] and not unreadable
    else:
        ok = counts.get('pts') == STATE['pts_total'] and not unreadable
    check(f"{label}: layers readable, {'filtered' if expect_filtered else 'unfiltered'}", ok,
          f"counts={counts} unreadable={unreadable} subset(pts)={layer('pts').subsetString()[:100]!r}")
    check(f"{label}: no view created then left unread", not orphans,
          f"views={sorted(views)} new and unread={orphans}")
    aborted = aborted_connections()
    check(f"{label}: no connection idle in an aborted transaction", not aborted, str(aborted))
    # psycopg2 connections (no application_name, unlike QGIS's own) left open by the tasks
    left = sql("SELECT count(*) FROM pg_stat_activity WHERE backend_type = 'client backend' "
               "AND application_name = '' AND pid <> pg_backend_pid()")[0][0]
    check(f"{label}: no task connection left open", left == 0, f"{left} open")
    from_worker, STATE['subsets_from_worker'] = STATE.get('subsets_from_worker', []), []
    check(f"{label}: every subset set on the main thread", not from_worker, '; '.join(from_worker[:2]))


# --- steps ---------------------------------------------------------------------------------------

def s_setup():
    iface.mainWindow().resize(1600, 1000)
    iface.mainWindow().show()
    sql("CREATE EXTENSION IF NOT EXISTS postgis", fetch=False)
    sql(f"DROP SCHEMA IF EXISTS {TEMP_SCHEMA} CASCADE", fetch=False)
    sql("DROP TABLE IF EXISTS public.fm_zones, public.fm_pts CASCADE", fetch=False)
    sql("CREATE TABLE public.fm_zones AS SELECT row_number() OVER ()::int AS id, "
        "ST_SetSRID(ST_MakeEnvelope(700000 + x * 3, 6599000 + y * 3, 700002 + x * 3, 6599002 + y * 3), 2154)"
        f"::geometry(Polygon, 2154) AS geom FROM generate_series(0, {ZONES_SIDE - 1}) x, "
        f"generate_series(0, {ZONES_SIDE - 1}) y", fetch=False)
    sql("ALTER TABLE public.fm_zones ADD PRIMARY KEY (id)", fetch=False)
    sql("CREATE TABLE public.fm_pts AS SELECT row_number() OVER ()::int AS id, "
        "ST_SetSRID(ST_MakePoint(700000 + random() * 990, 6599000 + random() * 990), 2154)::geometry(Point, 2154) "
        f"AS geom FROM generate_series(1, {POINTS})", fetch=False)
    sql("ALTER TABLE public.fm_pts ADD PRIMARY KEY (id)", fetch=False)
    sql("CREATE INDEX ON public.fm_zones USING GIST (geom); CREATE INDEX ON public.fm_pts USING GIST (geom)",
        fetch=False)
    zones, pts = pg_layer('fm_zones', 'zones'), pg_layer('fm_pts', 'pts')
    project.addMapLayers([zones, pts])
    STATE['pts_total'] = POINTS
    check('PostGIS layers load', zones.isValid() and pts.isValid(), f"zones={zones.featureCount()}")


def s_open_plugin():
    settings = QSettings()
    settings.setValue('FilterMate/discord_welcome_dismissed', True)
    settings.setValue('FilterMate/whats_new_seen', 99)
    settings.setValue('qgis/digitizing/validate_geometries', 0)
    plugins = os.path.join(tempfile.mkdtemp(prefix='fm_pg_'), 'plugins')
    shutil.copytree(REPO, os.path.join(plugins, PACKAGE), ignore=shutil.ignore_patterns(*EXCLUDED))
    sys.path.insert(0, plugins)
    qgis.utils.plugin_paths.insert(0, plugins)
    qgis.utils.updateAvailablePlugins()
    check('plugin starts', qgis.utils.loadPlugin(PACKAGE) and qgis.utils.startPlugin(PACKAGE))
    qgis.utils.plugins[PACKAGE].run()
    ids = {layer('zones').id(), layer('pts').id()}
    return lambda: dock() is not None and ids <= set(app().PROJECT_LAYERS) and tasks_idle()


def s_prepare():
    d = dock()
    d.comboBox_filtering_current_layer.setLayer(layer('zones'))

    def configure():
        d.mGroupBox_exploring_custom_selection.setChecked(True)
        d.mFieldExpressionWidget_exploring_custom_selection.setExpression('"id" <= 20000')
        combo = d.checkableComboBoxLayer_filtering_layers_to_filter
        for row in range(combo.model().rowCount()):
            item = combo.model().item(row)
            item.setCheckState(Qt.CheckState.Checked if item.text().startswith('pts [') else Qt.CheckState.Unchecked)
        d.pushButton_checkable_filtering_layers_to_filter.setChecked(True)
        d.pushButton_checkable_filtering_geometric_predicates.setChecked(True)
        d.comboBox_filtering_geometric_predicates.setCheckedItems(['Intersect'])

    QTimer.singleShot(2500, configure)
    since = time.time()
    return lambda: time.time() - since > 3.0 and bool(dock().get_current_features()[0]) \
        and layer('pts').id() in (dock().get_layers_to_filter() or [])


def run_task(name):
    dock().launchTaskEvent(False, name)


def mark_views():
    STATE['views_before'] = matviews()


def s_filter():
    watch_subset_threads()
    mark_views()
    run_task('filter')
    return settled()


def s_filter_check():
    STATE['views_after_filter'] = sorted(matviews())
    print(f"   views after the filter: {STATE['views_after_filter']}", flush=True)
    state_check('PostgreSQL filter', expect_filtered=True)


def s_unfilter_canceled_by_a_filter():
    mark_views()
    run_task('unfilter')
    run_task('filter')  # cancels the unfilter at once
    return settled()


def s_unfilter_canceled_check():
    state_check('unfilter canceled by a filter', expect_filtered=True)


def watch_subset_threads():
    """Record the target's subset changes made outside the main thread (direct connection: the slot
    runs in the thread that called setSubsetString; queued, it would always run on the main thread)."""
    def changed():
        on_main = QThread.currentThread() == QgsApplication.instance().thread()
        if not on_main:
            stack = traceback.format_stack()[:-1]
            STATE.setdefault('subsets_from_worker', []).append(
                ' <- '.join(frame.strip().splitlines()[0] for frame in reversed(stack[-2:])) or '?')
        if os.environ.get('FM_PG_DEBUG'):
            found = re.findall(r'fm_temp_mv_[0-9a-z_]+', layer('pts').subsetString())
            print(f"   debug: pts subset changed (main thread={on_main}) -> {found[:1]}\n"
                  + ''.join(traceback.format_stack()[:-1]), flush=True)
    layer('pts').subsetStringChanged.connect(changed, Qt.ConnectionType.DirectConnection)


def s_double_click():
    mark_views()
    run_task('filter')
    first = app().appTasks.get('filter')
    STATE['first'] = first
    STATE['first_canceled'] = None

    def second():
        try:  # the first task: canceled by the second click (False: it was over already)
            first.taskTerminated.connect(lambda: STATE.__setitem__('first_canceled', True))
            first.taskCompleted.connect(lambda: STATE.__setitem__('first_canceled', first.isCanceled()))
        except RuntimeError:
            STATE['first_canceled'] = False
        run_task('filter')
    QTimer.singleShot(30, second)
    return settled()


def s_double_click_check():
    print(f"   first task canceled by the second click: {STATE['first_canceled']}", flush=True)
    if os.environ.get('FM_PG_DEBUG'):
        task_module = sys.modules[f'{PACKAGE}.core.tasks.filter_task']
        print(f"   debug: first created={STATE['first'].__dict__.get('_created_mv_names')} "
              f"deferred={task_module._DEFERRED_VIEW_DROPS}", flush=True)
        for name in ('zones', 'pts'):
            print(f"   debug: subset {name}: {re.findall(r'fm_temp_mv_[0-9a-z_]+', layer(name).subsetString())}",
                  flush=True)
    if STATE['first_canceled'] is False:
        # it completed before the second click: its view is in the undo history, not a leak
        STATE['views_before'] = STATE['views_before'] | (matviews() - set(
            view for view in matviews() if view in layer('pts').subsetString() + layer('zones').subsetString()))
    state_check('second click on Filter', expect_filtered=True)


def s_reset():
    mark_views()
    run_task('reset')
    return settled()


def s_reset_check():
    state_check('reset', expect_filtered=False)


def s_finish():
    check('no Python error and no FilterMate critical message', not STATE['errors'], '; '.join(STATE['errors'][:3]))
    failed = [name for status, name in STATE['results'] if status == 'FAIL']
    print(f"\n{len(STATE['results']) - len(failed)} passed, {len(failed)} failed in "
          f"{time.time() - STATE['started']:.1f}s (QGIS {Qgis.QGIS_VERSION}, PostGIS)", flush=True)
    os._exit(1 if failed else 0)


STEPS = [s_setup, s_open_plugin, s_prepare, s_filter, s_filter_check, s_unfilter_canceled_by_a_filter,
         s_unfilter_canceled_check, s_double_click, s_double_click_check, s_reset, s_reset_check, s_finish]


def run_step(index=0):
    watch_plugin_loggers()
    step = STEPS[index]
    print(f"-- {step.__name__} ({time.time() - STATE['started']:.1f}s)", flush=True)
    try:
        until = step()
    except Exception:
        report('FAIL', f"{step.__name__} raised", traceback.format_exc().strip().splitlines()[-1])
        print(traceback.format_exc(), flush=True)
        until = None
        if step in (s_setup, s_open_plugin):
            QTimer.singleShot(0, lambda: run_step(STEPS.index(s_finish)))
            return
    wait(index, until, time.time())


def wait(index, until, since):
    if until is not None:
        try:
            done = until()
        except Exception:
            done = False
        if not done and time.time() - since < 90:
            QTimer.singleShot(250, lambda: wait(index, until, since))
            return
        if not done:
            print(f"   (timeout at the end of {STEPS[index].__name__})", flush=True)
    QTimer.singleShot(300, lambda: run_step(index + 1))


QTimer.singleShot(2000, run_step)
