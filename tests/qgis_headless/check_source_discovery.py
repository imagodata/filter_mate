"""Native Qt source review form and bounded search parsing; optional live read uses a public query only."""
import json
import os
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('FILTERMATE_LOG_DIR', '/tmp/fm-source-discovery-logs')
from qgis.core import QgsApplication, QgsSettings, Qgis
from qgis.PyQt.QtCore import QTranslator

app = QgsApplication([], False)
app.initQgis()
root = Path(os.environ.get('FM_REPO', '/src'))
translator = QTranslator()
assert translator.load(str(root / 'i18n/FilterMate_fr.qm'))
app.installTranslator(translator)
package = types.ModuleType('filter_mate')
package.__path__ = [str(root)]
sys.modules['filter_mate'] = package
from filter_mate.adapters.agent.settings import AgentSettings, target_of
from filter_mate.adapters.agent.bounded_http import BoundedReply
from filter_mate.adapters.agent import source_search
from filter_mate.core.agent.source_search import SourceSearchError
from filter_mate.core.agent.sources import source_draft
from filter_mate.ui.widgets.agent_panel import AgentSettingsDialog

settings = QgsSettings()
before = {key: settings.value(key) for key in settings.allKeys() if key.startswith('FilterMate/')}
tester = MagicMock(return_value='Le service répond.')
dialog = AgentSettingsDialog(AgentSettings(), target_of, tester=tester)
dialog.show()
app.processEvents()
draft = source_draft('https://geo.example.org/ows?SERVICE=WFS&REQUEST=GetCapabilities&map=water', title='Hydrologie')
dialog.prefill_source(draft)
assert not dialog._custom and not dialog.new_enabled.isChecked()
assert dialog.new_name.text() == 'Hydrologie' and dialog.new_kind.currentData() == 'wfs'
assert 'Suggestion non vérifiée' in dialog.source_result.text()
tester.assert_not_called()
dialog.add_button.click()
assert len(dialog._custom) == 1
source = dialog._custom[0]
assert source.address == 'https://geo.example.org/ows?map=water'
assert source.id not in dialog.chosen_sources() and dialog._selected_source() == source
assert dialog.test_button.isEnabled()
tester.assert_not_called()
dialog.test_button.click()
tester.assert_called_once_with(source)
assert {key: settings.value(key) for key in settings.allKeys() if key.startswith('FilterMate/')} == before
print('PASS French prefilled review, no automatic test or activation, user Add/Test, settings unchanged until Save', flush=True)

reply = BoundedReply(200, {}, b'<a class="result__a" href="https://geo.example.org/wfs">WFS catalogue</a>'
                              b'<a class="result__snippet">A candidate service</a>')
with patch.object(source_search, 'fetch', return_value=reply) as fetch:
    result = source_search.search_data_sources('public geospatial WFS', 3)
    assert result['results'][0]['verified'] is False
    fetch.assert_called_once()
    assert fetch.call_args.args[0].startswith('https://html.duckduckgo.com/html/?')
    assert fetch.call_args.kwargs['timeout_ms'] <= 20_000
    assert fetch.call_args.kwargs['max_bytes'] <= 2 * 1024 * 1024
print('PASS actual search parser, fixed provider, bounded read and unverified results without site visits', flush=True)

live = {'status': 'not requested'}
if os.environ.get('FM_SOURCE_SEARCH_LIVE') == '1':
    try:
        result = source_search.search_data_sources('Belgium official geospatial WFS open data', 3)
        live = {'status': 'results', 'count': len(result['results']), 'results': result['results']}
        print(f'LIVE results: {len(result["results"])} candidates; no result site visited', flush=True)
    except SourceSearchError as exc:
        live = {'status': 'unavailable', 'reason': str(exc)}
        print(f'LIVE unavailable: {exc}', flush=True)
out = os.environ.get('FM_SOURCE_DISCOVERY_OUTPUT', '/audit/fm-source-discovery.json')
Path(out).write_text(json.dumps({'qgis': Qgis.QGIS_VERSION, 'native_checks_passed': True, 'live': live}, indent=2))
dialog.close()
print(f'PASS QGIS {Qgis.QGIS_VERSION}: custom source review workflow', flush=True)
os._exit(0)
