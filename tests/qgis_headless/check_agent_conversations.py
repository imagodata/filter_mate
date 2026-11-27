"""Archive and conversation history with native Qt 5/6 in QGIS."""
import os
import sys
import tempfile
import types

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('FILTERMATE_LOG_DIR', '/tmp/fm-conversations-logs')
from qgis.core import QgsApplication, QgsProject, Qgis

app = QgsApplication([], False)
app.initQgis()
package = types.ModuleType('filter_mate')
package.__path__ = [os.environ.get('FM_REPO', '/src')]
sys.modules['filter_mate'] = package
from filter_mate.core.agent.conversations import ConversationStore
from filter_mate.core.agent.transcript import entry
from filter_mate.ui.widgets.agent_panel import AgentPanel, HISTORY_CONVERSATIONS

directory = tempfile.TemporaryDirectory()
store = ConversationStore(os.path.join(directory.name, 'conversations.sqlite3'))
project_dirty = QgsProject.instance().isDirty()
project = store.project('current-project')
first = store.start(project, '/maps/current.qgz')
store.save(first, project, [entry('user', 'Analyse des communes'), entry('action', 'Filtre appliqué')],
           session='saved model context', path='/maps/current.qgz')
second = store.start(project)
other_project = store.project('other-project')
other = store.start(other_project, '/maps/other.qgz')
store.save(other, other_project, [entry('user', 'Autre projet')], path='/maps/other.qgz')
assert store.head(project)['id'] == second
assert ConversationStore(store.path).get(first)['session'] == 'saved model context'
assert QgsProject.instance().isDirty() == project_dirty

panel = AgentPanel()
panel.set_ready(True, 'Agent')
panel.set_conversations(store.list(), project, second)
panel.show_history()
panel.history_tabs.setCurrentIndex(HISTORY_CONVERSATIONS)
panel.resize(560, 700)
panel.show()
app.processEvents()
opened = []
panel.conversation_open_requested.connect(opened.append)
assert panel.conversation_list.count() == 2
panel.conversation_list.setCurrentRow(0)  # newest: other project, read only
assert panel.open_conversation_button.text() == 'Read conversation'
panel.open_conversation_button.click()
assert opened == [other]
panel.conversation_list.setCurrentRow(1)
assert panel.open_conversation_button.text() == 'Open conversation'
panel.open_conversation_button.click()
assert opened == [other, first]
panel.set_working(True)
assert not panel.open_conversation_button.isEnabled()
panel._open_selected_conversation()
assert opened == [other, first]
assert QgsProject.instance().isDirty() == project_dirty
from qgis.core import QgsSettings
from filter_mate.adapters.agent.conversation_store import _migrate
from filter_mate.core.agent.transcript import to_json
settings = QgsSettings()
settings.setValue('filter_mate/agent/transcripts_index', '["legacy-key"]')
settings.setValue('filter_mate/agent/transcripts/legacy-key', to_json([entry('user', 'Legacy thread')]))
_migrate(store)
legacy_project = store.project('legacy-key')
assert store.head(legacy_project)['transcript'][0]['text'] == 'Legacy thread'
empty = store.start(legacy_project)
_migrate(store)
assert store.head(legacy_project)['id'] == empty and not store.head(legacy_project)['transcript']
print(f'PASS QGIS {Qgis.QGIS_VERSION}: persisted archive, empty active thread, native history, busy guard, clean project',
      flush=True)
os._exit(0)
