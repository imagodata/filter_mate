"""Save suggestions can be muted for this QGIS process without disabling manual saves."""
import os
import sys
import types
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('FILTERMATE_LOG_DIR', '/tmp/fm-save-offer-session-logs')
from qgis.core import QgsApplication, Qgis
from qgis.PyQt.QtCore import QTimer
from qgis.PyQt.QtWidgets import QMessageBox, QFileDialog

app = QgsApplication([], False)
app.initQgis()
package = types.ModuleType('filter_mate')
package.__path__ = [os.environ.get('FM_REPO', '/src')]
sys.modules['filter_mate'] = package
from filter_mate.ui.widgets.agent_panel import AgentPanel
from filter_mate.ui.widgets.agent_thread import ConfirmCard
from filter_mate.ui.controllers import agent_data

panel = AgentPanel()
panel.resize(600, 700)
panel.show()
host = types.SimpleNamespace(panel=panel, chat_busy=lambda: False)
ui = agent_data.AgentDataController(host)
assert not agent_data.save_offers_suppressed()

def decline():
    box = app.activeModalWidget()
    assert isinstance(box, QMessageBox)
    box.checkBox().setChecked(True)
    box.button(QMessageBox.StandardButton.No).click()

QTimer.singleShot(0, decline)
assert ui._ask_to_save('/chosen/project.qgz') == QMessageBox.StandardButton.No
assert agent_data.save_offers_suppressed()
ui.close()
ui = agent_data.AgentDataController(host)
with patch.object(agent_data.data_store, 'pending_layers', side_effect=AssertionError('muted offers do not inspect data')):
    ui.offer()
with patch.object(QFileDialog, 'getSaveFileName', return_value=('', '')) as choose, patch.object(
        agent_data.data_store, 'pending_layers', return_value=[]):
    assert ui.save() is False
    assert choose.call_count == 1
print('PASS native checkbox, dock recreation and explicit manual save', flush=True)

app.setProperty(agent_data._SUPPRESS_SAVE_OFFERS, False)
layer = types.SimpleNamespace(id=lambda: 'l1', source=lambda: '/vsimem/file', name=lambda: 'Results')
with patch.object(agent_data.data_store, 'pending_layers', return_value=[layer]), patch.object(
        agent_data, 'suggested_project_path', return_value='/chosen/project.qgz'):
    ui.offer()
card = panel.findChildren(ConfirmCard)[-1]
assert card.always_button is not None
card.always_button.click()
assert agent_data.save_offers_suppressed()
assert card.done and 'session' in card.result.text()
print(f'PASS QGIS {Qgis.QGIS_VERSION}: session-only choice on the save card', flush=True)
os._exit(0)
