# -*- coding: utf-8 -*-
"""
FilterMate on PostGIS: a buffer given by an expression on the source (QGIS GUI under Xvfb).

Up to 2026-11-12 the PostgreSQL backend applied a buffer expression to the source rows up to 10,000
source features, and above named a materialized view that was never created (every distant
PostgreSQL layer failed). ``FM_PG_SRC_COUNT`` sets the size of the source table (8000 and 12000:
both sides of that former threshold). The source selection is the same 100 points whatever the
size, so the expected result is the same: the target points within the radius of one of them,
counted in SQL with the 5 segments per quarter circle FilterMate's buffers use.

    docker network create fm_pg_net
    docker run -d --name fm_pg --network fm_pg_net -e POSTGRES_PASSWORD=fm postgis/postgis:16-3.4
    docker run --rm --network fm_pg_net -v "$PWD:/src:ro" -e FM_PG_SRC_COUNT=12000 \\
        -e FM_PG="host=fm_pg port=5432 dbname=postgres user=postgres password=fm" qgis/qgis:stable \\
        xvfb-run -a qgis --nologo --noversioncheck --profiles-path /tmp/p \\
        --code /src/tests/qgis_headless/check_pg_buffer_expression.py
"""
import faulthandler
import logging
import os
import shutil
import sys
import tempfile
import time
import traceback

from qgis.core import Qgis, QgsApplication, QgsDataSourceUri, QgsProject, QgsProperty, QgsVectorLayer
from qgis.PyQt.QtCore import QSettings, Qt, QTimer
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
SRC_COUNT = int(os.environ.get('FM_PG_SRC_COUNT', '12000'))
SELECTION = '"id" <= 100'
BUFFER_EXPRESSION = '"radius"'
project = QgsProject.instance()


def _show_exception(type_, value, tb, msg=None, messagebar=False, level=None):
    text = ''.join(traceback.format_exception(type_, value, tb)).strip()
    STATE['errors'].append(f"{msg or ''} {text.splitlines()[-1] if text else value}".strip())
    print(f"   [Python exception] {msg or ''}\n{text}", flush=True)


qgis.utils.showException = _show_exception
QTimer.singleShot(6 * 60 * 1000, lambda: (print('FAIL   watchdog', flush=True), os._exit(2)))


def _on_log(message, tag, level):
    if tag == 'Python error' or (tag == 'FilterMate' and level == Qgis.MessageLevel.Critical):
        STATE['errors'].append(f"[{tag}] {message[:300]}")
    if tag == 'FilterMate' and level >= Qgis.MessageLevel.Warning:
        print(f"   | QGIS log [{tag}] {message[:240]}", flush=True)


QgsApplication.messageLog().messageReceived.connect(_on_log)


class _Records(logging.Handler):
    """FilterMate's errors, and its lines about the buffer expression and the views."""

    def emit(self, record):
        message = record.getMessage()
        if record.levelno >= logging.ERROR:
            STATE['errors'].append(f"[{record.name}] {message[:300]}")
        lowered = message.lower()
        if record.levelno >= logging.WARNING or 'buffer expr' in lowered or 'buffer_expr' in lowered \
                or 'inline buffer' in lowered or 'materialized view' in lowered:
            print(f"   | {record.levelname} {record.name}: {message[:260]}", flush=True)


_RECORDS = _Records(level=logging.INFO)


def watch_plugin_loggers():
    for name, logger in list(logging.root.manager.loggerDict.items()):
        if isinstance(logger, logging.Logger) and name.split('.')[0] in ('FilterMate', 'filter_mate') \
                and _RECORDS not in logger.handlers:
            logger.addHandler(_RECORDS)
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


# --- steps ---------------------------------------------------------------------------------------

def s_setup():
    iface.mainWindow().resize(1600, 1000)
    iface.mainWindow().show()
    sql("CREATE EXTENSION IF NOT EXISTS postgis", fetch=False)
    sql("DROP SCHEMA IF EXISTS filter_mate_temp CASCADE", fetch=False)
    sql("DROP TABLE IF EXISTS public.fm_src, public.fm_tgt CASCADE", fetch=False)
    # Source points at positions and radii given by their id: the 100 selected ones are the same
    # whatever FM_PG_SRC_COUNT
    sql("CREATE TABLE public.fm_src AS SELECT id::int AS id, (5 + (id % 3) * 10)::double precision AS radius, "
        "ST_SetSRID(ST_MakePoint(700000 + (id * 37) % 1000, 6599000 + (id * 91) % 1000), 2154)"
        f"::geometry(Point, 2154) AS geom FROM generate_series(1, {SRC_COUNT}) id", fetch=False)
    sql("ALTER TABLE public.fm_src ADD PRIMARY KEY (id)", fetch=False)
    sql("CREATE TABLE public.fm_tgt AS SELECT row_number() OVER ()::int AS id, "
        "ST_SetSRID(ST_MakePoint(700000 + x * 5, 6599000 + y * 5), 2154)::geometry(Point, 2154) AS geom "
        "FROM generate_series(0, 199) x, generate_series(0, 199) y", fetch=False)
    sql("ALTER TABLE public.fm_tgt ADD PRIMARY KEY (id)", fetch=False)
    sql("CREATE INDEX ON public.fm_src USING GIST (geom); CREATE INDEX ON public.fm_tgt USING GIST (geom); "
        "ANALYZE public.fm_src; ANALYZE public.fm_tgt", fetch=False)
    STATE['tgt_total'] = sql("SELECT count(*) FROM public.fm_tgt")[0][0]
    STATE['expected'] = sql(
        "SELECT count(*) FROM public.fm_tgt t WHERE EXISTS (SELECT 1 FROM public.fm_src s "
        "WHERE s.id <= 100 AND ST_Intersects(t.geom, ST_Buffer(s.geom, s.radius, 'quad_segs=5')))")[0][0]
    src, tgt = pg_layer('fm_src', 'src'), pg_layer('fm_tgt', 'tgt')
    project.addMapLayers([src, tgt])
    check('PostGIS layers load', src.isValid() and tgt.isValid(),
          f"src={src.featureCount()} tgt={tgt.featureCount()} expected={STATE['expected']}")


def s_open_plugin():
    settings = QSettings()
    settings.setValue('FilterMate/discord_welcome_dismissed', True)
    settings.setValue('FilterMate/whats_new_seen', 99)
    plugins = os.path.join(tempfile.mkdtemp(prefix='fm_pgbuf_'), 'plugins')
    shutil.copytree(REPO, os.path.join(plugins, PACKAGE), ignore=shutil.ignore_patterns(*EXCLUDED))
    sys.path.insert(0, plugins)
    qgis.utils.plugin_paths.insert(0, plugins)
    qgis.utils.updateAvailablePlugins()
    check('plugin starts', qgis.utils.loadPlugin(PACKAGE) and qgis.utils.startPlugin(PACKAGE))
    qgis.utils.plugins[PACKAGE].run()
    ids = {layer('src').id(), layer('tgt').id()}
    return lambda: dock() is not None and ids <= set(app().PROJECT_LAYERS) and tasks_idle()


def s_prepare():
    d = dock()
    d.comboBox_filtering_current_layer.setLayer(layer('src'))

    def configure():
        d.mGroupBox_exploring_custom_selection.setChecked(True)
        d.mFieldExpressionWidget_exploring_custom_selection.setExpression(SELECTION)
        combo = d.checkableComboBoxLayer_filtering_layers_to_filter
        for row in range(combo.model().rowCount()):
            item = combo.model().item(row)
            item.setCheckState(Qt.CheckState.Checked if item.text().startswith('tgt [') else Qt.CheckState.Unchecked)
        d.pushButton_checkable_filtering_layers_to_filter.setChecked(True)
        d.pushButton_checkable_filtering_geometric_predicates.setChecked(True)
        d.comboBox_filtering_geometric_predicates.setCheckedItems(['Intersect'])
        widgets = d.widgets["FILTERING"]
        widgets["HAS_BUFFER_VALUE"]["WIDGET"].setChecked(True)
        button = widgets["BUFFER_VALUE_PROPERTY"]["WIDGET"]
        button.setToProperty(QgsProperty.fromExpression(BUFFER_EXPRESSION))
        button.setActive(True)
        d.filtering_buffer_property_changed()

    QTimer.singleShot(2500, configure)
    since = time.time()

    def ready():
        if time.time() - since < 3.0:
            return False
        filtering = app().PROJECT_LAYERS[layer('src').id()]["filtering"]
        return bool(dock().get_current_features()[0]) \
            and layer('tgt').id() in (dock().get_layers_to_filter() or []) \
            and filtering.get("has_buffer_value") is True \
            and filtering.get("buffer_value_expression") == BUFFER_EXPRESSION \
            and filtering.get("buffer_value_property") is True
    return ready


def s_configured_check():
    filtering = app().PROJECT_LAYERS[layer('src').id()]["filtering"]
    check('buffer expression set on the source', filtering.get("has_buffer_value") is True
          and filtering.get("buffer_value_expression") == BUFFER_EXPRESSION
          and filtering.get("buffer_value_property") is True,
          f"has_buffer={filtering.get('has_buffer_value')} expression={filtering.get('buffer_value_expression')!r} "
          f"property={filtering.get('buffer_value_property')}")


def s_filter():
    dock().launchTaskEvent(False, 'filter')
    return settled()


def s_filter_check():
    target = layer('tgt')
    unreadable = []
    try:
        count = sum(1 for _ in target.getFeatures())
    except Exception as exc:
        count = None
        unreadable.append(str(exc))
    if target.dataProvider().hasErrors():
        unreadable.append(str(target.dataProvider().errors()[-1:]))
        target.dataProvider().clearErrors()
    print(f"   subset(tgt) = {target.subsetString()[:400]!r}", flush=True)
    views = [row[0] for row in sql("SELECT schemaname || '.' || matviewname FROM pg_matviews "
                                   "WHERE schemaname LIKE 'filter%'")]
    print(f"   views = {views}", flush=True)
    check(f"target filtered to the points within the radius ({SRC_COUNT} source features)",
          count == STATE['expected'] and not unreadable,
          f"count={count} expected={STATE['expected']} total={STATE['tgt_total']} unreadable={unreadable}")


def s_finish():
    check('no Python error and no FilterMate critical message', not STATE['errors'], '; '.join(STATE['errors'][:3]))
    failed = [name for status, name in STATE['results'] if status == 'FAIL']
    print(f"\n{len(STATE['results']) - len(failed)} passed, {len(failed)} failed in "
          f"{time.time() - STATE['started']:.1f}s (QGIS {Qgis.QGIS_VERSION}, PostGIS, source {SRC_COUNT})", flush=True)
    os._exit(1 if failed else 0)


STEPS = [s_setup, s_open_plugin, s_prepare, s_configured_check, s_filter, s_filter_check, s_finish]


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
