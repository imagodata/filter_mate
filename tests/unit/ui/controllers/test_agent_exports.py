"""Explicit, persistent export destinations without a fallback into a QGIS profile."""
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from .test_agent_chat_lifecycle import _load, controller, ctrl_module, dock  # noqa: F401

pytestmark = pytest.mark.unit


@pytest.fixture
def exports(ctrl_module, controller, monkeypatch, tmp_path):
    _load(monkeypatch, 'filtermate_api.plugin_package', 'filtermate_api/plugin_package.py')
    config = _load(monkeypatch, 'filtermate_api.config', 'filtermate_api/config.py')
    root = _load(monkeypatch, 'filtermate_api.export_root', 'filtermate_api/export_root.py')
    module = _load(monkeypatch, 'ui.controllers.agent_exports', 'ui/controllers/agent_exports.py')
    values = {}
    settings = SimpleNamespace(value=lambda key, default='', **kwargs: values.get(key, default),
                               setValue=lambda key, value: values.update({key: value}))
    monkeypatch.setattr(sys.modules['qgis.core'], 'QgsSettings', lambda: settings, raising=False)
    monkeypatch.setattr(config, '_qgis_profile_dir', lambda: str(tmp_path / 'profiles' / 'default'))
    chosen = tmp_path / 'user_exports'
    chosen.mkdir()
    widgets = sys.modules['qgis.PyQt.QtWidgets']
    dialog = SimpleNamespace(getExistingDirectory=MagicMock(return_value=str(chosen)))
    warning = MagicMock()
    monkeypatch.setattr(widgets, 'QFileDialog', dialog)
    monkeypatch.setattr(widgets, 'QMessageBox', SimpleNamespace(warning=warning))
    return SimpleNamespace(config=config, root=root, module=module, values=values, chosen=chosen,
                           dialog=dialog, warning=warning, ctrl=controller, tmp=tmp_path, failure=ctrl_module.ToolFailure)


def test_the_first_export_asks_then_reuses_the_user_choice(exports):
    e = exports
    assert e.config.configured_export_root() is None
    assert e.ctrl._agent_export_root() == e.chosen
    assert e.values[e.config.EXPORT_FOLDER_KEY] == str(e.chosen)
    assert e.ctrl._agent_export_root() == e.chosen
    e.dialog.getExistingDirectory.assert_called_once()
    assert e.config._default_export_root() == e.chosen


def test_cancel_does_not_choose_or_create_an_implicit_default(exports):
    e = exports
    e.dialog.getExistingDirectory.return_value = ''
    with pytest.raises(e.failure, match='Export cancelled'):
        e.ctrl._agent_export_root()
    assert not e.values
    assert not (e.tmp / 'profiles').exists()


@pytest.mark.parametrize('place', ['profiles/default/export', 'profiles/other/export'])
def test_a_profile_destination_is_refused_without_remembering_it(exports, place):
    e = exports
    destination = e.tmp / place
    destination.mkdir(parents=True)
    e.dialog.getExistingDirectory.return_value = str(destination)
    assert e.module.choose_export_folder(e.ctrl.panel) is None
    assert not e.values
    e.warning.assert_called_once()


def test_an_old_profile_preference_is_ignored_and_requires_a_new_choice(exports):
    e = exports
    old = e.tmp / 'profiles' / 'default' / 'FilterMate' / 'exports'
    old.mkdir(parents=True)
    e.values[e.config.EXPORT_FOLDER_KEY] = str(old)
    assert e.config.configured_export_root() is None
    assert e.ctrl._agent_export_root() == e.chosen


def test_missing_or_relative_preference_does_not_get_used(exports):
    e = exports
    for path in ('relative', str(e.tmp / 'missing')):
        e.values[e.config.EXPORT_FOLDER_KEY] = path
        assert e.config.configured_export_root() is None


def test_a_project_change_while_the_picker_is_open_cancels_the_pending_export(exports):
    e = exports
    def choose(*args):
        e.ctrl._memory_generation += 1
        return str(e.chosen)
    e.dialog.getExistingDirectory.side_effect = choose
    with pytest.raises(e.failure, match='Export cancelled'):
        e.ctrl._agent_export_root()


def test_the_menu_can_change_the_folder_only_when_the_agent_is_idle(exports, monkeypatch):
    e = exports
    monkeypatch.setattr(e.ctrl, 'chat_busy', lambda: True)
    e.ctrl._choose_export_folder()
    e.dialog.getExistingDirectory.assert_not_called()
    monkeypatch.setattr(e.ctrl, 'chat_busy', lambda: False)
    e.ctrl._choose_export_folder()
    assert e.config.configured_export_root() == e.chosen


def test_an_absolute_input_file_does_not_require_an_export_folder(exports):
    e = exports
    forbidden = MagicMock(side_effect=AssertionError('this read must not open the export picker'))
    assert e.root.resolve_exported_file(forbidden, '/data/layer.gpkg') == ('/data/layer.gpkg', '')
    forbidden.assert_not_called()


def test_a_link_into_a_profile_is_not_a_valid_export_choice(exports):
    e = exports
    profile = e.tmp / 'profiles' / 'default'
    profile.mkdir(parents=True)
    link = e.tmp / 'looks_like_exports'
    link.symlink_to(profile, target_is_directory=True)
    e.dialog.getExistingDirectory.return_value = str(link)
    assert e.module.choose_export_folder(e.ctrl.panel) is None
    assert not e.values
