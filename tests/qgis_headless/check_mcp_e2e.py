# -*- coding: utf-8 -*-
"""
End to end: a real MCP client -> the FilterMate MCP server -> the REST API -> the real plugin in a real QGIS.

QGIS starts with its GUI under Xvfb and runs this script (``--code``). The script opens the fixture layers, starts
the FilterMate plugin, serves the REST API (FastAPI + uvicorn, ``QGISFilterMateAccessor`` on the real plugin) in a
thread, then a worker thread runs a real MCP client (SDK ``ClientSession`` + ``stdio_client``) that launches
``python filtermate_api/mcp/__main__.py`` and calls the tools. After each call the worker reads the real state of
the QGIS layers on the main thread (``run_on_main_thread``, the mechanism the API itself uses). The Qt event loop
keeps running meanwhile: the REST routes marshal every QGIS call to it.

    pip install --break-system-packages fastapi uvicorn mcp      # in the QGIS image
    python3 tests/qgis_headless/make_fixtures.py /tmp/fm
    FM_FIXTURES=/tmp/fm xvfb-run -a qgis --nologo --noversioncheck --profiles-path /tmp/profiles \\
        --code tests/qgis_headless/check_mcp_e2e.py

Prints one ``PASS`` / ``FAIL`` / ``XFAIL`` line per check; QGIS exits with 0 when none failed, 1 otherwise.
"""
import asyncio
import json
import os
import shutil
import socket
import sys
import tempfile
import threading
import time
import traceback

from qgis.core import Qgis, QgsApplication, QgsProject, QgsRasterLayer, QgsVectorLayer
from qgis.PyQt.QtCore import QSettings, QTimer
import qgis.utils

STATE = {'results': [], 'started': time.time(), 'done': False, 'server': None}
KEY = 'e2e-key-' + os.urandom(8).hex()
PACKAGE = 'filter_mate'
EXCLUDED = ('.git', '.github', '.claude', '.serena', '_bmad', '_bmad-output', 'dist', 'build', 'scripts',
            'knowledge', 'website', 'tests', 'docs', 'logs', '__pycache__', '*.pyc', 'test_*.py')
REPO = os.environ.get('FM_REPO') or (os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                                     if '__file__' in globals() else '/src')
FIXTURES = os.environ.get('FM_FIXTURES', '/tmp/fm')
PYTHON = os.environ.get('FM_PYTHON') or shutil.which('python3') or 'python3'  # sys.executable is qgis here
POINT_CLOUD_MIN_VERSION = 32600

try:
    with open(os.path.join(FIXTURES, 'manifest.json'), encoding='utf-8') as _stream:
        M = json.load(_stream)
except Exception as _exc:
    print(f"FAIL   fixtures not readable in {FIXTURES}: {_exc} (run make_fixtures.py first)", flush=True)
    os._exit(3)
project = QgsProject.instance()


def report(status, name, detail=''):
    STATE['results'].append((status, name))
    print(f"{status:<5}  {name}  {detail}".rstrip(), flush=True)


def check(name, condition, detail='', expected_failure=''):
    if condition:
        report('PASS', name, detail)
    elif expected_failure:
        report('XFAIL', name, f"{detail} | known: {expected_failure}")
    else:
        report('FAIL', name, detail)
    return bool(condition)


def _watchdog():
    print('FAIL   watchdog: the run did not finish in 10 minutes', flush=True)
    os._exit(2)


QTimer.singleShot(10 * 60 * 1000, _watchdog)


def has_point_clouds():
    return Qgis.QGIS_VERSION_INT >= POINT_CLOUD_MIN_VERSION


def layer(name):
    found = project.mapLayersByName(name)
    return found[0] if found else None


def plugin():
    return qgis.utils.plugins[PACKAGE]


def tasks_idle():
    try:
        own = set(plugin().app.tasks_descriptions.values())
    except Exception:
        own = set()
    return not [task for task in QgsApplication.taskManager().activeTasks()
                if task.description().startswith('FilterMate') or task.description() in own]


# --- main thread: QGIS side ---------------------------------------------------------------------

def setup():
    layers = [QgsVectorLayer(M['zones'] + '|layername=zones', 'zones', 'ogr'),
              QgsRasterLayer(M['dem'], 'dem', 'gdal')]
    if has_point_clouds():
        from qgis.core import QgsPointCloudLayer, QgsProviderRegistry
        if 'pdal' in QgsProviderRegistry.instance().providerList():
            layers.append(QgsPointCloudLayer(M['las'], 'cloud', 'pdal'))
        else:
            layers.append(QgsPointCloudLayer(M['ept'], 'cloud', 'ept'))
    memory = QgsVectorLayer('Point?crs=EPSG:2154&field=x:integer', 'mem', 'memory')
    project.addMapLayers(layers + [memory])
    check('fixture layers load', all(item.isValid() for item in layers + [memory]),
          str([item.name() for item in layers + [memory]]))

    settings = QSettings()
    settings.setValue('FilterMate/discord_welcome_dismissed', True)  # modal dialogs would block the run
    settings.setValue('FilterMate/whats_new_seen', 99)
    settings.setValue('qgis/digitizing/validate_geometries', 0)
    plugins = os.path.join(tempfile.mkdtemp(prefix='fm_mcp_'), 'plugins')
    shutil.copytree(REPO, os.path.join(plugins, PACKAGE), ignore=shutil.ignore_patterns(*EXCLUDED))
    sys.path.insert(0, plugins)
    qgis.utils.plugin_paths.insert(0, plugins)
    qgis.utils.updateAvailablePlugins()
    started = qgis.utils.loadPlugin(PACKAGE) and qgis.utils.startPlugin(PACKAGE)
    check('plugin starts with iface', started and PACKAGE in qgis.utils.plugins)
    from filter_mate.adapters.qgis.coverage_layers import cache
    cache.set_cache_root(os.path.join(os.path.dirname(plugins), 'cache'))
    plugin().run()
    STATE['plugins_dir'] = plugins


def ready():
    expected = ['zones', 'dem'] + (['cloud'] if has_point_clouds() else [])
    try:
        app = plugin().app
        return (app.dockwidget is not None and tasks_idle()
                and all(layer(n) is not None and layer(n).id() in app.PROJECT_LAYERS for n in expected))
    except Exception:
        return False


def start_rest_api():
    """The recipe of docs/AUTOMATION.md: create_app on a QGISFilterMateAccessor, uvicorn in a thread."""
    import uvicorn
    from filter_mate.filtermate_api.config import APIConfig
    from filter_mate.filtermate_api.qgis_accessor import QGISFilterMateAccessor
    from filter_mate.filtermate_api.server import create_app

    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    STATE['export_root'] = os.path.join(tempfile.mkdtemp(prefix='fm_mcp_export_'), 'exports')
    os.environ['FILTERMATE_API_KEY'] = KEY
    config = APIConfig(host='127.0.0.1', port=port, api_key=KEY, export_root=STATE['export_root'])
    app = create_app(config=config, accessor=QGISFilterMateAccessor(plugin().get_public_api(), plugin()))
    server = uvicorn.Server(uvicorn.Config(app, host=config.host, port=config.port, log_level='warning'))
    threading.Thread(target=server.run, daemon=True, name='uvicorn').start()
    STATE['server'] = server
    STATE['url'] = f'http://127.0.0.1:{port}'
    deadline = time.time() + 20
    while not server.started and time.time() < deadline:
        time.sleep(0.05)
        QgsApplication.processEvents()
    check('REST API (uvicorn) started', server.started, STATE['url'])


# --- worker thread: the MCP client ---------------------------------------------------------------

def on_main(function):
    from filter_mate.filtermate_api.main_thread import run_on_main_thread
    return run_on_main_thread(function)


def state_of(*names):
    """{layer name: (subsetString, source)} read on the main thread."""
    def read():
        out = {}
        for name in names:
            item = layer(name)
            out[name] = (item.subsetString() if hasattr(item, 'subsetString') else '', item.source())
        return out
    return on_main(read)


def text_of(result):
    return ''.join(block.text for block in result.content if getattr(block, 'type', '') == 'text')


def is_error(result):
    return bool(result.model_dump(by_alias=True).get('isError'))


async def scenario(session):
    original = {name: source for name, (_, source) in state_of('zones', 'dem').items()}
    cloud = has_point_clouds()

    async def call(name, arguments=None):
        result = await session.call_tool(name, arguments or {})
        return result, text_of(result)

    tools = {tool.name for tool in (await session.list_tools()).tools}
    check('MCP: 13 tools listed', len(tools) == 13, str(sorted(tools)))

    # -- layers
    result, text = await call('list_layers')
    rows = json.loads(text)['layers'] if not is_error(result) else []
    kinds = {row['name']: row['layer_kind'] for row in rows}
    expected_kinds = {'zones': 'vector', 'dem': 'raster', **({'cloud': 'point_cloud'} if cloud else {})}
    check('list_layers: names and kinds of the project', all(kinds.get(k) == v for k, v in expected_kinds.items()),
          str(kinds) if kinds else text)

    # -- apply_filter, valid then invalid
    result, text = await call('apply_filter', {'layer_name': 'zones', 'expression': '"name" = \'east_a\''})
    now = state_of('zones')['zones'][0]
    check('apply_filter: valid expression sets the real subset string',
          not is_error(result) and 'east_a' in now, f"subset={now!r} answer={text[:120]}")
    names = on_main(lambda: sorted(f['name'] for f in layer('zones').getFeatures()))
    check('apply_filter: the layer shows only east_a', names == ['east_a'], str(names))

    result, text = await call('filter_state')
    states = {row['name']: row for row in json.loads(text)['layers']} if not is_error(result) else {}
    check('filter_state: zones listed with its subset', 'east_a' in states.get('zones', {}).get('subset', ''), text[:200])

    # A provider that refuses the expression (setSubsetString False): the message names both possible causes.
    # (Memory layer: its subset is a QGIS expression, validated.)
    before = state_of('mem')['mem'][0]
    result, text = await call('apply_filter', {'layer_name': 'mem', 'expression': '"x" = ('})
    after = state_of('mem')['mem'][0]
    check('apply_filter: expression refused by the provider gives the 404 message with both causes',
          is_error(result) and 'HTTP 404' in text and 'refused by the data provider' in text
          and 'vector layer not found by its name' in text, text[:200])
    check('apply_filter: refused expression leaves the subset string alone', before == after, f"{before!r} -> {after!r}")

    # Known limit, not of the MCP server: OGR accepts invalid SQL (setSubsetString returns True), so the layer is
    # left with a broken subset and no features. Reported as an expected failure; clear_filters recovers.
    before = state_of('zones')['zones'][0]
    result, text = await call('apply_filter', {'layer_name': 'zones', 'expression': '"no_such_field" = ('})
    after = state_of('zones')['zones'][0]
    check('apply_filter: invalid SQL on a GeoPackage is refused and leaves the subset alone',
          is_error(result) and before == after, f"answer={'error' if is_error(result) else 'accepted'} "
          f"{before!r} -> {after!r}",
          expected_failure='OGR setSubsetString returns True for invalid SQL (featureCount -1): the layer shows nothing')
    result, text = await call('list_layers')
    count = {row['name']: row['feature_count'] for row in json.loads(text)['layers']}.get('zones')
    check('list_layers: a broken GeoPackage subset shows as feature_count -1 or 0 (the assistant can notice)',
          count in (-1, 0), f"feature_count={count}")

    result, text = await call('apply_filter', {'layer_name': 'ghost', 'expression': '1 = 1'})
    check('apply_filter: unknown layer is an error, not a crash', is_error(result), text[:160])

    result, text = await call('filter_status')
    check('filter_status: reports the filter applied through the API',
          not is_error(result) and 'zones' in json.loads(text).get('active_filters', {}), text[:200])

    # -- undo: apply_filter is not in the dock history
    result, text = await call('undo_filter')
    check('undo_filter: nothing to undo (REST changes are not in the dock history)',
          is_error(result) and 'Nothing to undo' in text, text[:200])

    # -- clear
    result, text = await call('clear_filters', {'layers': ['zones']})
    now = state_of('zones')['zones'][0]
    check('clear_filters: subset string emptied', not is_error(result) and now == '', f"subset={now!r} {text[:120]}")

    # -- cross filter: selected zone -> raster
    on_main(lambda: layer('zones').selectByExpression('"name" = \'east_a\''))
    result, text = await call('cross_filter', {'source_layer': 'zones', 'target_layers': ['dem'],
                                               'predicates': ['Intersect'], 'selected_only': True})
    answer = json.loads(text) if not is_error(result) else {}
    dem_source = state_of('dem')['dem'][1]
    check('cross_filter: raster target filtered, now read from a clipped copy',
          answer.get('filtered') == ['dem'] and dem_source != original['dem'], f"{text[:160]} source={dem_source}")
    result, text = await call('filter_state')
    states = {row['name']: row for row in json.loads(text)['layers']} if not is_error(result) else {}
    check('filter_state: dem is listed as derived', states.get('dem', {}).get('derived') is True, text[:200])
    on_main(lambda: layer('zones').removeSelection())

    # -- geometry filter: a rectangle of the east half on the vector layer
    x0, y0, x1, y1 = 700600, 6599050, 700900, 6599550
    wkt = f'POLYGON(({x0} {y0}, {x1} {y0}, {x1} {y1}, {x0} {y1}, {x0} {y0}))'
    result, text = await call('geometry_filter', {'wkt': wkt, 'crs': M['crs'], 'target_layers': ['zones'],
                                                  'predicates': ['Intersect']})
    answer = json.loads(text) if not is_error(result) else {}
    names = on_main(lambda: sorted(f['name'] for f in layer('zones').getFeatures()))
    check('geometry_filter: zones intersecting the rectangle', answer.get('filtered') == ['zones']
          and names == ['east_a', 'east_b'], f"{text[:140]} features={names}")
    subset = state_of('zones')['zones'][0]
    check('geometry_filter: the real subset string changed', subset != '', f"subset={subset[:120]!r}")

    # -- point cloud
    if cloud:
        result, text = await call('point_cloud_filter', {'layers': ['cloud'], 'criteria': {'classes': [6]}})
        subset = state_of('cloud')['cloud'][0]
        check('point_cloud_filter: real subset string of the point cloud',
              not is_error(result) and 'Classification' in subset and '6' in subset, f"subset={subset!r} {text[:100]}")
    else:
        report('SKIP', 'point cloud checks', f'QGIS {Qgis.QGIS_VERSION} has no point clouds')

    # -- export
    result, text = await call('export_layers', {'layers': ['zones', 'dem'], 'subfolder': 'e2e/run1',
                                                'vector_format': 'GPKG', 'raster_format': 'GTiff'})
    answer = json.loads(text) if not is_error(result) else {}
    outputs = answer.get('outputs', {})
    folder = os.path.join(STATE['export_root'], 'e2e', 'run1')
    files = sorted(os.listdir(folder)) if os.path.isdir(folder) else []
    check('export_layers: files written below the export root',
          set(outputs) == {'zones', 'dem'} and all(os.path.isfile(p) and p.startswith(os.path.realpath(
              STATE['export_root'])) for p in outputs.values()), f"{files} {text[:140]}")
    result, text = await call('export_layers', {'layers': ['zones'], 'subfolder': '../escape'})
    check('export_layers: a sub-folder outside the root is refused', is_error(result) and '422' in text, text[:140])

    # -- clear everything
    names = ['zones', 'dem'] + (['cloud'] if cloud else [])
    result, text = await call('clear_filters', {'layers': names})
    state = state_of(*names)
    check('clear_filters: every layer back to its original source with no filter',
          not is_error(result) and state['zones'] == ('', original['zones']) and state['dem'][1] == original['dem']
          and (not cloud or state['cloud'][0] == ''), f"{state} {text[:120]}")
    names_now = on_main(lambda: sorted(f['name'] for f in layer('zones').getFeatures()))
    check('clear_filters: zones shows every feature again', names_now == sorted(M['zone_names']), str(names_now))
    result, text = await call('filter_state')
    check('filter_state: empty after clear', not is_error(result) and json.loads(text)['layers'] == [], text[:160])

    # -- favorites, resource
    result, text = await call('list_favorites')
    check('list_favorites answers (a list)', not is_error(result) and 'favorites' in json.loads(text), text[:120])
    contents = (await session.read_resource('filtermate://layers')).contents
    check('resource filtermate://layers', len(json.loads(contents[0].text)) >= 2, contents[0].text[:100])


async def run_client(url, key):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    script = os.path.join(REPO, 'filtermate_api', 'mcp', '__main__.py')
    params = StdioServerParameters(command=PYTHON, args=[script, '--url', url],
                                   env={'FILTERMATE_API_KEY': key, 'PYTHONDONTWRITEBYTECODE': '1'},
                                   cwd=tempfile.gettempdir())
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            await scenario(session)

    # a wrong key is reported, not leaked
    wrong = StdioServerParameters(command=PYTHON, args=[script, '--url', url],
                                  env={'FILTERMATE_API_KEY': 'not-the-key'}, cwd=tempfile.gettempdir())
    async with stdio_client(wrong) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool('list_layers', {})
            check('wrong key: readable error, key not echoed',
                  is_error(result) and 'rejected the API key' in text_of(result) and 'not-the-key' not in text_of(result),
                  text_of(result)[:140])


def worker():
    try:
        asyncio.run(run_client(STATE['url'], KEY))
    except BaseException:
        report('FAIL', 'MCP client run raised', traceback.format_exc().strip().splitlines()[-1])
        print(traceback.format_exc(), flush=True)
    STATE['done'] = True


# --- main thread driver ----------------------------------------------------------------------------

def finish():
    server = STATE.get('server')
    if server is not None:
        server.should_exit = True
    counts = {s: sum(1 for status, _ in STATE['results'] if status == s) for s in ('PASS', 'FAIL', 'SKIP', 'XFAIL')}
    print(f"\n{counts['PASS']} passed, {counts['FAIL']} failed, {counts['SKIP']} skipped, {counts['XFAIL']} known "
          f"failures in {time.time() - STATE['started']:.1f}s (QGIS {Qgis.QGIS_VERSION}, MCP end to end)", flush=True)
    failed = [name for status, name in STATE['results'] if status == 'FAIL']
    if failed:
        print('FAILED: ' + '; '.join(failed), flush=True)
    os._exit(1 if failed else 0)


def wait_ready(since):
    if not ready() and time.time() - since < 120:
        QTimer.singleShot(250, lambda: wait_ready(since))
        return
    check('dock open, every fixture layer registered', ready())
    try:
        start_rest_api()
        threading.Thread(target=worker, daemon=True, name='mcp-client').start()
    except Exception:
        report('FAIL', 'REST API start raised', traceback.format_exc().strip().splitlines()[-1])
        print(traceback.format_exc(), flush=True)
        STATE['done'] = True
    poll()


def poll():
    if STATE['done']:
        QTimer.singleShot(500, finish)
        return
    QTimer.singleShot(250, poll)


def begin():
    try:
        setup()
    except Exception:
        report('FAIL', 'setup raised', traceback.format_exc().strip().splitlines()[-1])
        print(traceback.format_exc(), flush=True)
        QTimer.singleShot(0, finish)
        return
    wait_ready(time.time())


QTimer.singleShot(2000, begin)
