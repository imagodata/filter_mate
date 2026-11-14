# -*- coding: utf-8 -*-
"""Where the time of a request of the agent goes, in a real (headless) QGIS. Run inside a qgis/qgis image:

    docker run --rm -v "$PWD":/src -e QT_QPA_PLATFORM=offscreen qgis/qgis:ltr \\
        python3 /src/tests/qgis_headless/measure_agent_operations.py

A project of a realistic size (points by the hundred thousand, polygons, a score of small layers) and requests
played through the chat as a user sends them: the controller, the engine, the undo point, the tools. The model is a
local server that answers scripted turns at once, so what is timed is FilterMate, not a provider.

Prints, for each request: the wall time, the time in the tools, in the undo point, in what the panel does around a
request, and the functions of the plugin that cost most. Not a check: it passes or fails nothing.

    FM_MEASURE_POINTS=300000 FM_MEASURE_POLYGONS=60000 FM_MEASURE_EXTRA=20   the size of the project
    FM_MEASURE_REPEAT=3      every request is played that many times, the fastest is told (one run says little)
    FM_MEASURE_PROFILE=1     the functions that cost most; it slows every Python call, so never to compare times
"""
import cProfile
import io
import os
import pstats
import sys
import tempfile
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import check_agent_chat as bench  # noqa: E402 - the provider, the turns and the waits of the chat bench

from qgis.core import (  # noqa: E402
    Qgis, QgsApplication, QgsFeature, QgsGeometry, QgsPointXY, QgsProject, QgsRectangle, QgsVectorFileWriter,
    QgsVectorLayer,
)
from qgis.PyQt.QtWidgets import QLabel, QToolBox  # noqa: E402

POINTS = int(os.environ.get("FM_MEASURE_POINTS", "300000"))
POLYGONS = int(os.environ.get("FM_MEASURE_POLYGONS", "60000"))
EXTRA = int(os.environ.get("FM_MEASURE_EXTRA", "20"))
PROFILE = os.environ.get("FM_MEASURE_PROFILE", "0") == "1"  # it triples the cost of a Python loop: off to compare
REPEAT = max(1, int(os.environ.get("FM_MEASURE_REPEAT", "3")))
X0, Y0 = 500000.0, 6200000.0
KINDS = ("habitation", "commerce", "industrie", "agricole", "public")
SPENT = {}


def _written(memory, path, name):
    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName = "GPKG"
    options.layerName = name
    QgsVectorFileWriter.writeAsVectorFormatV3(memory, path, QgsProject.instance().transformContext(), options)
    layer = QgsVectorLayer(f"{path}|layername={name}", name, "ogr")
    QgsProject.instance().addMapLayer(layer)
    return layer


def _squares(count, size, step, per_row, fields, attributes):
    memory = QgsVectorLayer(f"Polygon?crs=EPSG:2154{fields}", "m", "memory")
    features = []
    for index in range(count):
        x, y = X0 + (index % per_row) * step, Y0 + (index // per_row) * step
        feature = QgsFeature(memory.fields())
        feature.setGeometry(QgsGeometry.fromRect(QgsRectangle(x, y, x + size, y + size)))
        feature.setAttributes(attributes(index))
        features.append(feature)
    memory.dataProvider().addFeatures(features)
    return memory


def make_project(work):
    """communes (2 000 squares of 1 km), batiments (squares of 10 m), adresses (points), and small layers."""
    started = time.monotonic()
    communes = _written(_squares(2000, 1000.0, 1000.0, 50, "&field=nom:string&field=pop:integer&field=dept:string",
                                 lambda i: [f"Commune {i}", (i * 37) % 50000, str(31 + i % 5)]),
                        os.path.join(work, "communes.gpkg"), "communes")
    row = int(POLYGONS ** 0.5) + 1
    spread = 50000.0 / row
    batiments = _written(_squares(POLYGONS, 10.0, spread, row, "&field=usage:string&field=hauteur:double",
                                  lambda i: [KINDS[i % 5], 3.0 + (i % 40)]),
                         os.path.join(work, "batiments.gpkg"), "batiments")
    memory = QgsVectorLayer("Point?crs=EPSG:2154&field=numero:integer&field=type:string&field=insee:string", "m", "memory")
    row = int(POINTS ** 0.5) + 1
    spread = 50000.0 / row
    features = []
    for index in range(POINTS):
        feature = QgsFeature(memory.fields())
        feature.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(X0 + (index % row) * spread, Y0 + (index // row) * spread)))
        feature.setAttributes([index % 200, KINDS[index % 5], str(31000 + index % 600)])
        features.append(feature)
        if len(features) == 50000:
            memory.dataProvider().addFeatures(features)
            features = []
    memory.dataProvider().addFeatures(features)
    adresses = _written(memory, os.path.join(work, "adresses.gpkg"), "adresses")
    for index in range(EXTRA):
        _written(_squares(20, 500.0, 600.0, 5, "&field=nom:string", lambda i: [f"Zone {i}"]),
                 os.path.join(work, f"zone_{index}.gpkg"), f"zone_{index}")
    print(f"project: {communes.featureCount()} communes, {batiments.featureCount()} batiments, "
          f"{adresses.featureCount()} adresses, {EXTRA} small layers, made in {time.monotonic() - started:.1f} s", flush=True)
    return communes, batiments, adresses


def timed(owner, name, label):
    """Count the time spent in ``owner.name`` under ``label`` (the calls nested in one another are counted once)."""
    original = getattr(owner, name)
    depth = [0]

    def wrapper(*args, **kwargs):
        depth[0] += 1
        started = time.perf_counter()
        try:
            return original(*args, **kwargs)
        finally:
            depth[0] -= 1
            if not depth[0]:
                SPENT[label] = SPENT.get(label, 0.0) + time.perf_counter() - started

    setattr(owner, name, wrapper)


def top_functions(profile, limit=10):
    """Where the time is really spent: the functions by their own time, those of QGIS and of Python included (a
    call into QGIS shows as ``{method 'featureCount' of ...}``), each with the function of the plugin that calls it
    most."""
    stats = pstats.Stats(profile, stream=io.StringIO())
    rows = []
    for (path, line, name), (_calls, count, own, cumulative, callers) in stats.stats.items():
        if own < 0.01:
            continue
        where = f"{path.split('filter_mate/', 1)[-1]}:{line} {name}" if "filter_mate" in path else name
        caller = max(callers.items(), key=lambda item: item[1][2], default=None)
        if caller is not None:
            (caller_path, caller_line, caller_name), _ = caller
            where += f"   <- {caller_path.split('filter_mate/', 1)[-1].rsplit('/', 1)[-1]}:{caller_line} {caller_name}"
        rows.append((own, cumulative, count, where))
    rows.sort(reverse=True)
    return rows[:limit]


def main():
    from filter_mate.adapters.agent.settings import AgentSettings, save_settings, target_of
    from filter_mate.adapters.agent.turn_checkpoint import TurnCheckpoint
    from filter_mate.adapters.public_api.filter_mate_public_api import FilterMatePublicAPI
    from filter_mate.core.agent.tool_executor import ToolExecutor
    from filter_mate.ui.controllers.agent_chat_controller import AgentChatController

    print(f"QGIS {Qgis.QGIS_VERSION}, Python {sys.version.split()[0]}", flush=True)
    work = tempfile.mkdtemp()
    provider = bench.Provider()
    communes, batiments, adresses = make_project(work)
    authcfg = bench.check_key_store()

    class Plugin:
        def get_public_api(self):
            return api

    api = FilterMatePublicAPI(None)
    save_settings(AgentSettings())
    host = QToolBox()
    host.addItem(QLabel("filtering"), "FILTERING")
    chat = AgentChatController(lambda page: host.insertItem(0, page, "AGENT"), Plugin(), host,
                               ask_user=lambda title, text: True)
    host.show()
    panel = chat.panel
    host.setCurrentWidget(panel)
    chat.open_settings = lambda: False
    chat._settings_dialog = lambda: False
    save_settings(AgentSettings(preset="anthropic", model="test-model", base_url=provider.url, consent=True,
                                authcfg=authcfg, consent_target=target_of("anthropic", provider.url),
                                key_target=target_of("anthropic", provider.url), tool_families=False))
    chat._refresh_ready()
    chat.new_conversation()

    timed(ToolExecutor, "execute", "tools")
    for name in ("begin", "end", "commit"):
        timed(TurnCheckpoint, name, "undo point")
    for name in ("_project_context", "_remember_project", "_save_transcript", "_refresh_history", "_build_engine",
                 "on_tool_end", "on_tool_start", "on_text", "on_finished"):
        if hasattr(AgentChatController, name):
            timed(AgentChatController, name, f"panel: {name.lstrip('_')}")

    def ask(text, seconds=600.0):
        panel.input.setText(text)
        panel.input.returnPressed.emit()
        return bench.wait(lambda: not panel._working, seconds)

    def turn(name, arguments, call_id="toolu_1"):
        return (200, {}, bench.tool_turn(name, arguments, call_id))

    done = (200, {}, bench.text_turn("Fait."))
    selected = '"pop" > 49000'
    requests = [
        ("nothing asked of QGIS (a greeting)", [done]),
        ("list_layers", [turn("list_layers", {}), done]),
        ("describe_layer + field_values (adresses)", [turn("describe_layer", {"layer": "adresses"}),
                                                      turn("field_values", {"layer": "adresses", "field": "type"}, "t2"),
                                                      done]),
        ("layer_statistics by group (adresses)", [turn("layer_statistics", {"layer": "adresses", "group_by": "type"}), done]),
        ("sample_features (batiments)", [turn("sample_features", {"layer": "batiments", "limit": 5}), done]),
        ("apply_filter (adresses, one value in five)", [
            turn("preview_filter", {"layer_name": "adresses", "expression": "\"type\" = 'commerce'"}),
            turn("apply_filter", {"layer_name": "adresses", "expression": "\"type\" = 'commerce'"}, "t2"), done]),
        ("clear, then apply_filter that keeps nine in ten (adresses)", [
            turn("clear_filters", {"layers": ["adresses"]}),
            turn("preview_filter", {"layer_name": "adresses", "expression": '"numero" >= 20'}, "t2"),
            turn("apply_filter", {"layer_name": "adresses", "expression": '"numero" >= 20'}, "t3"), done]),
        ("clear, then apply_filter without a preview (adresses)", [
            turn("clear_filters", {"layers": ["adresses"]}),
            turn("apply_filter", {"layer_name": "adresses", "expression": "\"type\" = 'commerce'"}, "t2"), done]),
        ("apply_filter narrowed with AND (adresses)", [
            turn("apply_filter", {"layer_name": "adresses", "expression": '"numero" < 50', "operator": "AND"}), done]),
        ("clear_filters (adresses)", [turn("clear_filters", {"layers": ["adresses"]}), done]),
        ("select_features + cross_filter (batiments in the selected communes)", [
            turn("select_features", {"layer": "communes", "expression": selected}),
            turn("cross_filter", {"source_layer": "communes", "target_layers": ["batiments"],
                                  "predicates": ["Intersect"]}, "t2"), done]),
        ("cross_filter with a buffer, two targets", [
            turn("cross_filter", {"source_layer": "communes", "target_layers": ["batiments", "adresses"],
                                  "predicates": ["Intersect"], "buffer": 200}), done]),
        ("clear_filters (two layers)", [turn("clear_filters", {"layers": ["batiments", "adresses"]}), done]),
        ("set_layer_style graduated + set_labels (communes)", [
            turn("set_layer_style", {"layer": "communes", "mode": "graduated", "field": "pop"}),
            turn("set_labels", {"layer": "communes", "field": "nom"}, "t2"), done]),
        ("five changes in a row (visibility of five layers)", [
            turn("set_layers_visibility", {"layers": [f"zone_{index}"], "visible": False}, f"t{index}")
            for index in range(5)] + [done]),
    ]
    best = {}
    for run in range(REPEAT):
        for label, script in requests:
            SPENT.clear()
            provider.reset(*script)
            profile = cProfile.Profile() if PROFILE and not run else None
            started = time.perf_counter()
            if profile is not None:
                profile.enable()
            ended = ask(label)
            if profile is not None:
                profile.disable()
            wall = time.perf_counter() - started
            tools = SPENT.get("tools", 0.0)
            undo = SPENT.get("undo point", 0.0)
            around = sum(value for key, value in SPENT.items() if key.startswith("panel: "))
            row = (tools, wall, undo, around, len(provider.requests), ended,
                   top_functions(profile) if profile is not None and wall >= 0.3 else [])
            if label not in best or tools < best[label][0]:
                best[label] = row[:6] + (best.get(label, row)[6] or row[6],)
    print(f"\nfastest of {REPEAT}:\n{'request':<70} {'tools':>7} {'wall':>7} {'undo':>7} {'panel':>7}  turns", flush=True)
    for label, _script in requests:
        tools, wall, undo, around, turns, ended, functions = best[label]
        print(f"{label:<70} {tools:7.2f} {wall:7.2f} {undo:7.2f} {around:7.2f}  {turns}"
              + ("" if ended else "  NOT ENDED"), flush=True)
        for own, cumulative, count, where in functions:
            print(f"      own {own:5.2f} s (with what it calls {cumulative:5.2f}, {count:>7} calls)  {where}", flush=True)
    kept = {layer.name(): layer.subsetString() for layer in (communes, batiments, adresses)}
    print(f"\nfilters at the end: {kept}", flush=True)


if __name__ == "__main__":
    app = QgsApplication([], True)
    app.initQgis()
    package_root = tempfile.mkdtemp()
    bench._link(os.environ.get("FM_REPO", "/src"), os.path.join(package_root, "filter_mate"))
    sys.path.insert(0, package_root)
    sys.dont_write_bytecode = True
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
    os._exit(0)
