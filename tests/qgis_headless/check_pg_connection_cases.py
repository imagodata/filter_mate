# -*- coding: utf-8 -*-
"""
FilterMate on PostGIS: three cases of the 2026-11-12 PostgreSQL fixes (QGIS GUI under Xvfb).

``FM_PG_CASE`` picks one case per QGIS run:

- ``service``: the three layers are opened through a ``pg_service.conf`` service (``PGSERVICEFILE``),
  then a geometric filter (Intersect) goes from the source to two distant layers (#357). FilterMate's
  own psycopg2 connection must name the service, and both targets hold the features the SQL count gives.
- ``no_psycopg2``: QGIS reads the layers, but every psycopg2 connection of FilterMate fails, as with a
  password asked at opening and not saved (#355). An Intersect filter to two distant layers, an
  unfilter, then a filter with a buffer expression (the materialized-view path): the distant layers
  are filtered all the same.
- ``or_buffer``: a first filter with a buffer expression from a selection holding OR and BETWEEN,
  then a second one on another selection with the OR operator, to the same target and to a new one
  (#368: the distant layers followed the previous subset of the source, its OR written as AND).

The source is made of 12 m squares (no target point ever lies on an edge), the targets of points on
grids; each expected count is a SQL count, the buffers with 5 segments per quarter circle.

    docker network create fm_pg_net
    docker run -d --name fm_pg --network fm_pg_net -e POSTGRES_PASSWORD=fm postgis/postgis:16-3.4
    docker run --init --rm --network fm_pg_net -v "$PWD:/src:ro" -e FM_PG_CASE=service \\
        -e FM_PG="host=fm_pg port=5432 dbname=postgres user=postgres password=fm" qgis/qgis:stable \\
        xvfb-run -a qgis --nologo --noversioncheck --profiles-path /tmp/p \\
        --code /src/tests/qgis_headless/check_pg_connection_cases.py

``--init``: without it ``xvfb-run`` runs as PID 1 and waits for ever for the signal of Xvfb. With
``qgis/qgis:ltr`` (3.44) add ``-e DBUS_SESSION_BUS_ADDRESS=disabled:``: D-Bus autolaunch starts a
GNOME keyring prompt that QGIS waits for, and the script never runs.
"""
import faulthandler
import logging
import os
import shutil
import sys
import tempfile
import time
import traceback

import psycopg2
from qgis.core import Qgis, QgsApplication, QgsDataSourceUri, QgsProject, QgsProperty, QgsVectorLayer
from qgis.PyQt.QtCore import QSettings, Qt, QTimer
from qgis.utils import iface
import qgis.utils

STATE = {'results': [], 'errors': [], 'connect_lines': [], 'started': time.time()}
faulthandler.enable(all_threads=True)
PG = os.environ.get('FM_PG', 'host=fm_pg port=5432 dbname=postgres user=postgres password=fm')
CASE = os.environ.get('FM_PG_CASE', 'service')
REPO = os.environ.get('FM_REPO') or (os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                                     if '__file__' in globals() else '/src')
PACKAGE = 'filter_mate'
EXCLUDED = ('.git', '.github', '.claude', '.serena', '_bmad', '_bmad-output', 'dist', 'build', 'scripts',
            'knowledge', 'website', 'tests', 'docs', 'logs', '__pycache__', '*.pyc', 'test_*.py')
SERVICE = 'fm_svc'
REAL_CONNECT = psycopg2.connect  # this script's own SQL keeps a working connection
REFUSAL = 'fe_sendauth: no password supplied'
# Errors this case is expected to log (the refused psycopg2 connections)
EXPECTED_ERRORS = {'no_psycopg2': (REFUSAL, 'PostgreSQL connection failed')}.get(CASE, ())
project = QgsProject.instance()

SRC, TGT_A, TGT_B = 'fm_cs_src', 'fm_cs_tgt_a', 'fm_cs_tgt_b'
FIRST_SELECTION = '"id" <= 50 OR "id" BETWEEN 201 AND 250'
SECOND_SELECTION = '"id" BETWEEN 221 AND 250'
PLAIN_SELECTION = '"id" <= 100'
BUFFER_EXPRESSION = '"radius"'


def _show_exception(type_, value, tb, msg=None, messagebar=False, level=None):
    text = ''.join(traceback.format_exception(type_, value, tb)).strip()
    STATE['errors'].append(f"{msg or ''} {text.splitlines()[-1] if text else value}".strip())
    print(f"   [Python exception] {msg or ''}\n{text}", flush=True)


qgis.utils.showException = _show_exception
QTimer.singleShot(8 * 60 * 1000, lambda: (print('FAIL   watchdog', flush=True), os._exit(2)))


def _error(text):
    if not any(expected in text for expected in EXPECTED_ERRORS):
        STATE['errors'].append(text)


def _on_log(message, tag, level):
    if tag == 'Python error' or (tag == 'FilterMate' and level == Qgis.MessageLevel.Critical):
        _error(f"[{tag}] {message[:300]}")
    if tag == 'FilterMate' and level >= Qgis.MessageLevel.Warning:
        print(f"   | QGIS log [{tag}] {message[:240]}", flush=True)
    if 'Task failed' in message or 'Tâche échouée' in message:
        STATE['errors'].append(f"[{tag}] {message[:300]}")


QgsApplication.messageLog().messageReceived.connect(_on_log)


class _Records(logging.Handler):
    """FilterMate's errors, and its lines about connections, buffers and views."""

    def emit(self, record):
        message = record.getMessage()
        if record.levelno >= logging.ERROR:
            _error(f"[{record.name}] {message[:300]}")
        if 'pg_layer_connect' in message:
            STATE['connect_lines'].append(message)
        lowered = message.lower()
        if record.levelno >= logging.WARNING or 'pg_layer_connect' in message or 'buffer expr' in lowered \
                or 'materialized view' in lowered or 'distant layers' in lowered:
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
    conn = REAL_CONNECT(PG)
    try:
        with conn.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall() if fetch and cur.description else []
        conn.commit()
        return rows
    finally:
        conn.close()


def expected(target, selection, buffered):
    """Target points that intersect a selected square, or its buffer by its radius."""
    shape = "ST_Buffer(s.geom, s.radius, 'quad_segs=5')" if buffered else 's.geom'
    return sql(f"WITH b AS MATERIALIZED (SELECT {shape} AS g FROM public.{SRC} s WHERE {selection}) "
               f"SELECT count(*) FROM public.{target} t WHERE EXISTS "
               f"(SELECT 1 FROM b WHERE ST_Intersects(t.geom, b.g))")[0][0]


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
    if CASE == 'service':
        uri = QgsDataSourceUri(f"service='{SERVICE}'")
    else:
        uri = QgsDataSourceUri(PG)
    uri.setDataSource('public', table, 'geom', '', 'id')
    return QgsVectorLayer(uri.uri(False), name, 'postgres')


def count(name):
    target = layer(name)
    problems = []
    try:
        total = sum(1 for _ in target.getFeatures())
    except Exception as exc:
        total = None
        problems.append(str(exc))
    if target.dataProvider().hasErrors():
        problems.append(str(target.dataProvider().errors()[-1:]))
        target.dataProvider().clearErrors()
    return total, problems


def check_count(label, name, wanted):
    total, problems = count(name)
    print(f"   subset({name}) = {layer(name).subsetString()[:300]!r}", flush=True)
    check(f"{label}: {name} holds {wanted} features", total == wanted and not problems,
          f"count={total} expected={wanted} unreadable={problems}")


# --- configuration of the dock --------------------------------------------------------------------

def set_targets(names):
    d = dock()
    combo = d.checkableComboBoxLayer_filtering_layers_to_filter
    for row in range(combo.model().rowCount()):
        item = combo.model().item(row)
        wanted = any(item.text().startswith(f"{name} [") for name in names)
        item.setCheckState(Qt.CheckState.Checked if wanted else Qt.CheckState.Unchecked)
    d.pushButton_checkable_filtering_layers_to_filter.setChecked(True)


def set_buffer_expression(active):
    d = dock()
    widgets = d.widgets["FILTERING"]
    widgets["HAS_BUFFER_VALUE"]["WIDGET"].setChecked(active)
    button = widgets["BUFFER_VALUE_PROPERTY"]["WIDGET"]
    if active:
        button.setToProperty(QgsProperty.fromExpression(BUFFER_EXPRESSION))
    button.setActive(active)
    d.filtering_buffer_property_changed()


def set_combine_operator(operator):
    d = dock()
    d.pushButton_checkable_filtering_current_layer_combine_operator.setChecked(operator is not None)
    if operator is not None:
        index = {'AND': 0, 'AND NOT': 1, 'OR': 2}[operator]
        d.comboBox_filtering_source_layer_combine_operator.setCurrentIndex(index)
        d.comboBox_filtering_other_layers_combine_operator.setCurrentIndex(index)


def configure(selection, targets, buffered, operator=None):
    """Selection, targets, Intersect, buffer and operator; returns a readiness test."""
    d = dock()

    def apply():
        d.mGroupBox_exploring_custom_selection.setChecked(True)
        d.mFieldExpressionWidget_exploring_custom_selection.setExpression(selection)
        set_targets(targets)
        d.pushButton_checkable_filtering_geometric_predicates.setChecked(True)
        d.comboBox_filtering_geometric_predicates.setCheckedItems(['Intersect'])
        set_buffer_expression(buffered)
        set_combine_operator(operator)

    QTimer.singleShot(1500, apply)
    since = time.time()
    wanted_ids = {layer(name).id() for name in targets}

    def ready():
        if time.time() - since < 2.5:
            return False
        filtering = app().PROJECT_LAYERS[layer(SRC).id()]["filtering"]
        has_buffer = filtering.get("has_buffer_value") is True \
            and filtering.get("buffer_value_expression") == BUFFER_EXPRESSION
        return bool(dock().get_current_features()[0]) \
            and wanted_ids <= set(dock().get_layers_to_filter() or []) \
            and has_buffer == buffered \
            and (operator is None or filtering.get("other_layers_combine_operator") == operator)
    return ready


def run_task(name):
    dock().launchTaskEvent(False, name)
    return settled()


# --- steps ----------------------------------------------------------------------------------------

def s_setup():
    iface.mainWindow().resize(1600, 1000)
    iface.mainWindow().show()
    sql("CREATE EXTENSION IF NOT EXISTS postgis", fetch=False)
    sql("DROP SCHEMA IF EXISTS filter_mate_temp CASCADE", fetch=False)
    sql(f"DROP TABLE IF EXISTS public.{SRC}, public.{TGT_A}, public.{TGT_B} CASCADE", fetch=False)
    sql(f"CREATE TABLE public.{SRC} AS SELECT id::int AS id, (5 + (id % 3) * 10)::double precision AS radius, "
        "ST_Expand(ST_SetSRID(ST_MakePoint(700000.5 + (id * 37) % 1000, 6599000.5 + (id * 91) % 1000), 2154), 6)"
        "::geometry(Polygon, 2154) AS geom FROM generate_series(1, 2000) id", fetch=False)
    for table, offset in ((TGT_A, 0), (TGT_B, 5)):
        sql(f"CREATE TABLE public.{table} AS SELECT row_number() OVER ()::int AS id, "
            f"ST_SetSRID(ST_MakePoint(700000 + {offset} + x * 10, 6599000 + {offset} + y * 10), 2154)"
            "::geometry(Point, 2154) AS geom FROM generate_series(0, 99) x, generate_series(0, 99) y", fetch=False)
    for table in (SRC, TGT_A, TGT_B):
        sql(f"ALTER TABLE public.{table} ADD PRIMARY KEY (id); CREATE INDEX ON public.{table} USING GIST (geom); "
            f"ANALYZE public.{table}", fetch=False)
    if CASE == 'service':
        host = dict(part.split('=', 1) for part in PG.split())
        folder = tempfile.mkdtemp(prefix='fm_pgsvc_')
        path = os.path.join(folder, 'pg_service.conf')
        with open(path, 'w', encoding='utf-8') as handle:
            handle.write(f"[{SERVICE}]\n" + ''.join(f"{key}={value}\n" for key, value in host.items()))
        os.environ['PGSERVICEFILE'] = path  # read by QGIS's libpq and by psycopg2's at each connection
    layers = [pg_layer(table, table) for table in (SRC, TGT_A, TGT_B)]
    project.addMapLayers(layers)
    STATE['total'] = {table: sql(f"SELECT count(*) FROM public.{table}")[0][0] for table in (TGT_A, TGT_B)}
    check(f"PostGIS layers load ({CASE})", all(item.isValid() for item in layers),
          ' '.join(f"{item.name()}={item.featureCount()}" for item in layers)
          + (f" uri={layers[0].source()[:80]!r}" if CASE == 'service' else ''))
    if CASE == 'no_psycopg2':
        def refused(*args, **kwargs):
            raise psycopg2.OperationalError(REFUSAL)
        psycopg2.connect = refused
        print("   psycopg2.connect now refuses every connection of FilterMate", flush=True)


def s_open_plugin():
    settings = QSettings()
    settings.setValue('FilterMate/discord_welcome_dismissed', True)
    settings.setValue('FilterMate/whats_new_seen', 99)
    plugins = os.path.join(tempfile.mkdtemp(prefix='fm_pgcases_'), 'plugins')
    shutil.copytree(REPO, os.path.join(plugins, PACKAGE), ignore=shutil.ignore_patterns(*EXCLUDED))
    sys.path.insert(0, plugins)
    qgis.utils.plugin_paths.insert(0, plugins)
    qgis.utils.updateAvailablePlugins()
    check('plugin starts', qgis.utils.loadPlugin(PACKAGE) and qgis.utils.startPlugin(PACKAGE))
    qgis.utils.plugins[PACKAGE].run()
    ids = {layer(name).id() for name in (SRC, TGT_A, TGT_B)}

    def ready():
        if not (dock() is not None and ids <= set(app().PROJECT_LAYERS) and tasks_idle()):
            return False
        dock().comboBox_filtering_current_layer.setLayer(layer(SRC))
        return True
    return ready


# service / no_psycopg2: Intersect without a buffer, to both targets

def s_plain_configure():
    return configure(PLAIN_SELECTION, (TGT_A, TGT_B), buffered=False)


def s_plain_filter():
    return run_task('filter')


def s_plain_check():
    for name in (TGT_A, TGT_B):
        check_count('Intersect without buffer', name, expected(name, PLAIN_SELECTION, buffered=False))


def s_service_check():
    lines = STATE['connect_lines']
    check('FilterMate connects through the service of the layers',
          any(f"service={SERVICE}" in line for line in lines),
          f"{len(lines)} connection line(s): {lines[:2]}")


# no_psycopg2: unfilter, then a buffer expression (materialized-view path when a connection opens)

def s_unfilter():
    return run_task('unfilter')


def s_unfilter_check():
    for name in (TGT_A, TGT_B):
        check_count('unfilter', name, STATE['total'][name])


def s_buffer_configure():
    return configure(PLAIN_SELECTION, (TGT_A, TGT_B), buffered=True)


def s_buffer_filter():
    return run_task('filter')


def s_buffer_check():
    for name in (TGT_A, TGT_B):
        check_count('buffer expression', name, expected(name, PLAIN_SELECTION, buffered=True))


def s_no_connection_check():
    check('every psycopg2 connection of FilterMate was refused', not STATE['connect_lines'],
          f"{len(STATE['connect_lines'])} connection line(s)")


# or_buffer: two filters with a buffer expression, the second with OR

def s_first_configure():
    return configure(FIRST_SELECTION, (TGT_A,), buffered=True)


def s_first_filter():
    return run_task('filter')


def s_first_check():
    STATE['first'] = expected(TGT_A, f"({FIRST_SELECTION})", buffered=True)
    check_count('first filter (selection with OR / BETWEEN)', TGT_A, STATE['first'])
    print(f"   subset({SRC}) = {layer(SRC).subsetString()[:300]!r}", flush=True)


def s_second_configure():
    return configure(SECOND_SELECTION, (TGT_A, TGT_B), buffered=True, operator='OR')


def s_second_filter():
    return run_task('filter')


def s_second_check():
    # The new target follows the second selection only, not the previous subset of the source (#368).
    # The target filtered twice: a geometric subset is replaced whatever the operator, by design
    # (FilterOrchestrator._determine_subset_strategy: only AND NOT is kept): OR would keep the first result.
    second = expected(TGT_B, SECOND_SELECTION, buffered=True)
    previous = expected(TGT_B, f"({FIRST_SELECTION})", buffered=True)
    check_count('second filter, OR: its geometric subset replaced', TGT_A,
                expected(TGT_A, SECOND_SELECTION, buffered=True))
    print(f"   (OR applied to the previous geometric subset would keep {STATE['first']})", flush=True)
    check_count('second filter, OR (new target)', TGT_B, second)
    print(f"   (a new target that followed the previous subset of the source would hold {previous})", flush=True)
    print(f"   subset({SRC}) = {layer(SRC).subsetString()[:300]!r}", flush=True)
    total, problems = count(SRC)
    kept = sql(f"SELECT count(*) FROM public.{SRC} WHERE {FIRST_SELECTION}")[0][0]
    check('second filter, OR: the source keeps the first selection', total == kept and not problems,
          f"count={total} expected={kept} unreadable={problems}")


def s_finish():
    check('no Python error, no FilterMate critical message, no failed task', not STATE['errors'],
          '; '.join(STATE['errors'][:3]))
    failed = [name for status, name in STATE['results'] if status == 'FAIL']
    print(f"\n{len(STATE['results']) - len(failed)} passed, {len(failed)} failed in "
          f"{time.time() - STATE['started']:.1f}s (QGIS {Qgis.QGIS_VERSION}, PostGIS, case {CASE})", flush=True)
    os._exit(1 if failed else 0)


CASES = {
    'service': [s_plain_configure, s_plain_filter, s_plain_check, s_service_check],
    'no_psycopg2': [s_plain_configure, s_plain_filter, s_plain_check, s_unfilter, s_unfilter_check,
                    s_buffer_configure, s_buffer_filter, s_buffer_check, s_no_connection_check],
    'or_buffer': [s_first_configure, s_first_filter, s_first_check, s_second_configure, s_second_filter,
                  s_second_check],
}
if CASE not in CASES:
    print(f"FAIL   unknown FM_PG_CASE {CASE!r}: {', '.join(CASES)}", flush=True)
    os._exit(2)
STEPS = [s_setup, s_open_plugin] + CASES[CASE] + [s_finish]


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
        if not done and time.time() - since < 120:
            QTimer.singleShot(250, lambda: wait(index, until, since))
            return
        if not done:
            print(f"   (timeout at the end of {STEPS[index].__name__})", flush=True)
    QTimer.singleShot(300, lambda: run_step(index + 1))


QTimer.singleShot(2000, run_step)
