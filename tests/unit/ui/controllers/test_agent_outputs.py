import json
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from .test_agent_chat_lifecycle import _PKG, _load, ctrl_module

pytestmark = pytest.mark.unit


@pytest.fixture
def output_ui(ctrl_module, monkeypatch, tmp_path):
    _load(monkeypatch, 'ui.widgets.agent_markdown', 'ui/widgets/agent_markdown.py')
    _load(monkeypatch, 'filtermate_api.export_root', 'filtermate_api/export_root.py')
    module = _load(monkeypatch, 'ui.controllers.agent_outputs', 'ui/controllers/agent_outputs.py')
    monkeypatch.setattr(sys.modules[_PKG + '.filtermate_api.config'], '_default_export_root', lambda: tmp_path)
    host = SimpleNamespace(panel=MagicMock(), _record=MagicMock())
    return module, module.AgentOutputsController(host), host, tmp_path


def test_exports_add_file_and_containing_folder_links(output_ui):
    _, outputs, host, root = output_ui
    folder = root / 'export'
    folder.mkdir()
    file = folder / 'résultat.gpkg'
    file.write_bytes(b'data')
    call = SimpleNamespace(name='export_layers', arguments={})
    result = SimpleNamespace(is_error=False, content=json.dumps({'outputs': {'A': file.name, 'B': file.name}}))
    outputs.from_result(call, result)
    host.panel.add_output.assert_called_once_with(str(file), 'export/résultat.gpkg', False)
    refs = host.panel.thread.file_references()
    assert {item.path for item in refs} == {str(file), str(folder)}
    host._record.assert_called_once_with('output', 'export/résultat.gpkg', detail=str(file), count='')


def test_a_zip_links_the_archive_instead_of_old_files_named_like_its_members(output_ui):
    _, outputs, host, root = output_ui
    folder = root / 'export'
    folder.mkdir()
    (folder / 'old.gpkg').write_bytes(b'old output')
    archive = folder / 'results.zip'
    archive.write_bytes(b'zip')
    outputs.from_result(SimpleNamespace(name='export_layers', arguments={'zip': True}),
                        SimpleNamespace(is_error=False, content=json.dumps({'package': archive.name,
                                                                             'outputs': {'A': 'old.gpkg'}})))
    host.panel.add_output.assert_called_once_with(str(archive), 'export/results.zip', False)


def test_all_pages_of_an_image_layout_are_linked(output_ui):
    _, outputs, host, root = output_ui
    folder = root / 'layouts'
    folder.mkdir()
    for name in ('atlas.png', 'atlas_2.png', 'atlas_3.png'):
        (folder / name).write_bytes(b'image')
    outputs.from_result(SimpleNamespace(name='export_layout', arguments={}),
                        SimpleNamespace(is_error=False, content='{"path": "atlas.png", "files": 3}'))
    assert host.panel.add_output.call_count == 3


def test_no_path_is_followed_from_failed_exports_or_unrelated_tools(output_ui):
    _, outputs, host, root = output_ui
    (root / 'file.pdf').write_bytes(b'file')
    for name, error in (('export_layout', True), ('sample_features', False)):
        outputs.from_result(SimpleNamespace(name=name, arguments={}),
                            SimpleNamespace(is_error=error, content='{"path": "file.pdf"}'))
    host.panel.add_output.assert_not_called()


def test_output_paths_cannot_escape_the_export_folder(output_ui):
    module, _, host, root = output_ui
    (root / 'outside.pdf').write_bytes(b'file')
    (root / 'layouts').mkdir()
    assert module.exported_paths('export_layout', {}, {'path': '../outside.pdf'}, root) == []
    host.panel.add_output.assert_not_called()


def test_manual_save_destinations_and_missing_restored_outputs_remain_navigable(output_ui):
    _, outputs, host, root = output_ui
    chosen = root / 'chosen project.qgz'
    chosen.write_bytes(b'project')
    assert outputs.show(str(chosen))
    chosen.unlink()
    outputs.clear()
    assert outputs.show(str(chosen), record=False, restore=True)
    assert chosen.name in host.panel.thread.file_references()[0].name
    host._record.assert_called_once()


def test_open_uses_the_local_file_url_and_checks_missing_outputs(output_ui, monkeypatch):
    _, outputs, host, root = output_ui
    path = root / 'chart.pdf'
    path.write_bytes(b'chart')
    outputs.show(str(path))
    qtcore = sys.modules['qgis.PyQt.QtCore']
    qtgui = sys.modules['qgis.PyQt.QtGui']
    monkeypatch.setattr(qtcore, 'QUrl', SimpleNamespace(fromLocalFile=lambda value: ('local', value)))
    opener = MagicMock(return_value=True)
    monkeypatch.setattr(qtgui, 'QDesktopServices', SimpleNamespace(openUrl=opener))
    outputs.open(str(path))
    opener.assert_called_once_with(('local', str(path)))
    path.unlink()
    outputs.open(str(path))
    host.panel.set_status.assert_called_once()
    outputs.open('/etc/passwd')
    assert opener.call_count == 1
