# -*- coding: utf-8 -*-
"""
FilterMate.unload (filter_mate.py, methods extracted with ast: the module cannot
be imported outside QGIS):

- the menu entries are removed from the submenu they were added to: a language
  change while QGIS runs renames self.menu, and the old submenu stayed after unload;
- the stale-cache timer of initGui is stopped: a QTimer.singleShot fired 30 s after
  startup even when the plugin had been unloaded, and imported the removed package again.
"""
import ast
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_PLUGIN = Path(__file__).resolve().parents[2] / "filter_mate.py"


def _methods(names):
    tree = ast.parse(_PLUGIN.read_text(encoding="utf-8"))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "FilterMate")
    return [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in names]


class _Plugin:
    pass


def _plugin(names):
    methods = _methods(names)
    assert len(methods) == len(names)
    namespace = {"logger": MagicMock(), "QCoreApplication": MagicMock(), "QIcon": MagicMock(), "QAction": MagicMock()}
    exec(compile(ast.Module(body=methods, type_ignores=[]), str(_PLUGIN), "exec"), namespace)
    plugin = _Plugin()
    plugin.iface = MagicMock()
    plugin.toolbar = MagicMock()
    plugin.actions = []
    plugin.menu = "&FilterMate"
    plugin.app = None
    plugin.processing_provider = None
    plugin._public_api = None
    plugin._disconnect_auto_activation_signals = MagicMock()
    plugin._teardown_extensions = MagicMock()
    for name in names:
        setattr(plugin, name, types.MethodType(namespace[name], plugin))
    return plugin


@pytest.mark.unit
class TestUnload:

    def test_menu_entries_are_removed_from_the_submenu_they_were_added_to(self):
        plugin = _plugin(["add_action", "retranslate_actions", "unload"])
        plugin.add_action(":/icon.png", "FilterMate", MagicMock())
        plugin.add_action(":/reset.png", "Reset", MagicMock())
        plugin.tr = lambda message: "&FiltreMate"  # language changed while QGIS runs
        plugin.retranslate_actions()

        plugin.unload()

        names = {c.args[0] for c in plugin.iface.removePluginVectorMenu.call_args_list}
        assert names == {"&FilterMate"}
        assert plugin.iface.removePluginVectorMenu.call_count == 2

    def test_the_stale_cache_timer_is_stopped(self):
        plugin = _plugin(["unload"])
        timer = MagicMock()
        plugin._stale_cache_timer = timer

        plugin.unload()

        timer.stop.assert_called_once_with()
        assert plugin._stale_cache_timer is None

    def test_init_gui_keeps_the_timer(self):
        """QTimer.singleShot(30000, ...) could not be stopped: it fired after an unload and
        imported the removed package again."""
        source = ast.unparse(_methods(["initGui"])[0])
        assert "singleShot(30000" not in source
        assert "self._stale_cache_timer" in source


@pytest.mark.unit
class TestUnloadLeavesNothingBehind:
    """2026-10-17: what a reload of the plugin left in QGIS."""

    def test_the_toolbar_leaves_the_main_window(self):
        """addToolBar() puts it in the main window; removeToolBarIcon() acts on the Plugins toolbar."""
        plugin = _plugin(["unload"])
        toolbar = plugin.toolbar
        plugin.unload()
        plugin.iface.mainWindow.return_value.removeToolBar.assert_called_once_with(toolbar)
        toolbar.deleteLater.assert_called_once_with()
        assert plugin.toolbar is None

    def test_the_translator_is_removed(self):
        plugin = _plugin(["unload"])
        translator = plugin.translator = MagicMock()
        qcore = plugin.unload.__func__.__globals__["QCoreApplication"]
        qcore.reset_mock()
        plugin.unload()
        qcore.removeTranslator.assert_called_once_with(translator)
        assert plugin.translator is None

    def test_the_dependency_check_timer_is_stopped(self):
        """QTimer.singleShot(1500 / 2000, check_and_clear_warnings) could not be canceled."""
        plugin = _plugin(["unload"])
        timer = plugin._dependency_check_timer = MagicMock()
        plugin.unload()
        timer.stop.assert_called_once_with()
        source = ast.unparse(_methods(["_install_message_filter"])[0])
        assert "singleShot" not in source and "clearWidgets" not in source

    def test_the_app_is_gone_and_the_dock_released(self):
        """perform_reinitialization skips an unloaded plugin by testing self.app is None."""
        plugin = _plugin(["unload"])
        app = plugin.app = MagicMock()
        app.dockwidget._controller_integration = None
        plugin.unload()
        app.dockwidget.release_qgis_connections.assert_called_once_with()
        app.cleanup.assert_called_once_with()
        assert plugin.app is None
