"""Real Qt slash completion and real skill-loading pipeline, with a local recording transport (no model calls)."""
import json
import os
import sys
import types
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('FILTERMATE_LOG_DIR', '/tmp/fm-skill-command-logs')
from qgis.core import QgsApplication, QgsProject, QgsVectorLayer, Qgis
from qgis.PyQt.QtCore import Qt, QModelIndex, QTranslator
from qgis.PyQt.QtTest import QTest

app = QgsApplication([], False)
app.initQgis()
root = Path(os.environ.get('FM_REPO', '/src'))
translator = QTranslator()
assert translator.load(str(root / 'i18n/FilterMate_fr.qm'))
app.installTranslator(translator)
package = types.ModuleType('filter_mate')
package.__path__ = [str(root)]
sys.modules['filter_mate'] = package
from filter_mate.core.agent.chat_engine import ChatEngine
from filter_mate.core.agent.messages import Message, ROLE_ASSISTANT, STOP_END, TextPart, TurnComplete
from filter_mate.core.agent.permissions import PermissionPolicy
from filter_mate.core.agent.providers import PRESETS, ProviderConfig, create_provider
from filter_mate.core.agent.session import AgentSession
from filter_mate.core.agent.skills import all_skills
from filter_mate.core.agent.tool_catalog import skill_tool
from filter_mate.core.agent.tool_executor import ToolExecutor
from filter_mate.adapters.agent.plugin_settings import skill_loader
from filter_mate.ui.widgets.agent_panel import AgentPanel

project = QgsProject.instance()
layer = QgsVectorLayer('Point?crs=EPSG:2154', 'Unchanged layer', 'memory')
project.addMapLayer(layer)
project.setDirty(False)
offered = {'ask_user', 'describe_layer', 'qgis_capabilities'}
tool = skill_tool(offered)
names = tool.input_schema['properties']['name']['enum']
registry = all_skills()
panel = AgentPanel()
panel.set_ready(True, 'Test local')
panel.resize(360, 600)
panel.input.skill_rows = lambda: [(f'/{name} — {registry[name].summary}', name) for name in names]
assert len(panel.input.skill_rows()) == len(names)
panel.show()
app.processEvents()
panel.activateWindow()
QTest.qWait(50)
sent, stopped = [], []
panel.send_requested.connect(sent.append)
panel.stop_requested.connect(lambda: stopped.append(True))
for prefix, command, key in (('/bra', 'brainstorm', Qt.Key.Key_Return),
                             ('/bra', 'brainstorm', Qt.Key.Key_Tab),
                             ('/find', 'find-skills', Qt.Key.Key_Return),
                             ('/find', 'find-skills', Qt.Key.Key_Tab)):
    panel.input.setText('')
    panel.input.setFocus()
    QTest.qWait(30)
    QTest.keyClicks(panel.input, prefix)
    QTest.qWait(30)
    assert panel.input.completer.popup().isVisible(), {
        'text': panel.input.text(), 'names': names, 'rows': panel.input._mention_rows,
        'prefix': panel.input.completer.completionPrefix(), 'count': panel.input.completer.completionCount(),
        'focus': panel.input.hasFocus(), 'cursor': panel.input.textCursor().position(),
        'source': list(panel.input.skill_rows())}
    QTest.keyClick(panel.input, key)
    assert panel.input.text() == f'/{command} ' and not sent
panel.input.setText('/')
panel.input._offer_names()
QTest.keyClick(panel.input, Qt.Key.Key_Escape)
assert not panel.input.completer.popup().isVisible() and not stopped
panel.input.setText('/tmp/data.geojson')
panel.input._offer_names()
assert not panel.input.completer.popup().isVisible()
panel.input.layer_rows = lambda: [('id_communes', 'Communes', '')]
panel.input.setText('Inspect @Com')
panel.input._offer_names()
popup = panel.input.completer.popup()
assert popup.isVisible()
panel.input.completer.activated[QModelIndex].emit(popup.model().index(0, 0))
assert panel.input.text() == 'Inspect Communes'
popup.hide()
print('PASS slash keyboard Enter/Tab/Escape, editable request, paths and @ layer completion', flush=True)

for provider in ('anthropic', 'openai', 'ollama'):
    calls, records, outcomes = [], [], []
    loader = skill_loader(offered)
    def load(arguments):
        calls.append(arguments['name'])
        return loader(arguments)
    transport = types.SimpleNamespace(start=lambda request, parser, callback:
                                      records.append((request, callback)) or types.SimpleNamespace(abort=lambda: None))
    listener = types.SimpleNamespace(on_text=lambda text: None, on_tool_start=lambda call: None,
                                     on_tool_end=lambda call, result: None, on_finished=outcomes.append,
                                     confirm=lambda call: False)
    checkpoint = types.SimpleNamespace(begin=lambda call=None: None, commit=lambda: ())
    policy = PermissionPolicy()
    policy.set_posture('respond')
    kind, base_url = PRESETS[provider]
    session = AgentSession(create_provider(ProviderConfig(kind, 'test', base_url=base_url)), [tool], 'Local test')
    engine = ChatEngine(session, ToolExecutor([tool], {'load_skill': load}), transport, listener, checkpoint,
                        policy=policy)
    engine.send('/brainstorm Compare two proposals; change nothing.')
    assert calls == ['brainstorm'] and len(records) == 1 and policy.posture == 'respond'
    result = json.loads(session.messages[2].parts[0].content)
    assert result['skill'] == 'brainstorm' and result['instructions']
    records[-1][1](TurnComplete(Message(ROLE_ASSISTANT, (TextPart('Two proposals.'),)), STOP_END))
    assert outcomes[-1].status == 'done'
    engine.send('/brainstorm Refine the second proposal.')
    assert calls == ['brainstorm', 'brainstorm'] and len(records) == 2
    assert json.loads(session.messages[-1].parts[0].content)['already_loaded']
    engine.cancel()
    records.clear()
    engine.send('/find-skills Recommend GIS and dataviz skills offline; change nothing.')
    assert calls[-1] == 'find-skills' and len(records) == 1 and policy.posture == 'respond'
    result = json.loads(session.messages[-1].parts[0].content)
    assert result['skill'] == 'find-skills' and result['instructions']
    records[-1][1](TurnComplete(Message(ROLE_ASSISTANT, (TextPart('Recommended skills.'),)), STOP_END))
    assert outcomes[-1].status == 'done'
    records.clear()
    engine.send('/missing-skill')
    assert not records and not engine.busy
    policy.rules = {'load_skill': 'never'}
    engine.send('/brainstorm')
    assert not records and not engine.busy
    print(f'PASS {provider}: actual built-in loader before first request, repeat reuse, unavailable/disabled stop', flush=True)

assert not project.isDirty() and len(project.mapLayers()) == 1
out = os.environ.get('FM_SKILL_COMMAND_OUTPUT', '/audit/fm-skill-commands.json')
Path(out).write_text(json.dumps({'qgis': Qgis.QGIS_VERSION, 'checks_passed': True,
                                'providers_serialized': ['anthropic', 'openai', 'ollama'],
                                'network_requests': 0}, indent=2))
panel.close()
os._exit(0)
