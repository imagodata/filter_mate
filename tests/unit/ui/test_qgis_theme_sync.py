"""Theme synchronization without a QGIS GUI; palettes have no Qt 5 enum aliases."""
import importlib.util
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def theme_modules(monkeypatch):
    monkeypatch.setattr(sys.modules['qgis.PyQt.QtGui'], 'QColor', Color)
    root = Path(__file__).resolve().parents[3]
    prefix = '_theme_sync_test'
    for name, path in [('', root), ('.ui', root / 'ui'),
                       ('.ui.styles', root / 'ui/styles'), ('.config', root / 'config')]:
        package = types.ModuleType(prefix + name)
        package.__path__ = [str(path)]
        monkeypatch.setitem(sys.modules, prefix + name, package)
    loaded = {}
    for name in ['config.theme_helpers', 'ui.styles.style_loader',
                 'ui.styles.base_styler', 'ui.styles.theme_manager', 'ui.styles.theme_watcher']:
        spec = importlib.util.spec_from_file_location(prefix + '.' + name, root / (name.replace('.', '/') + '.py'))
        module = importlib.util.module_from_spec(spec)
        monkeypatch.setitem(sys.modules, spec.name, module)
        spec.loader.exec_module(module)
        loaded[name.rsplit('.', 1)[-1]] = module
    return types.SimpleNamespace(**loaded)


class Color:
    def __init__(self, hex_value):
        self.value = hex_value

    def name(self):
        return self.value

    def lightness(self):
        rgb = [int(self.value[i:i + 2], 16) for i in (1, 3, 5)]
        return (min(rgb) + max(rgb)) / 2

    def lighter(self, factor):
        return self

    def darker(self, factor):
        return self


def palette(background, text, accent='#308cc6'):
    # No Window attribute, as in PyQt6. Only Qt brush accessors are exposed.
    roles = {'window': background, 'base': background, 'text': text,
             'windowText': text, 'mid': '#808080', 'placeholderText': '#888888',
             'highlight': accent, 'highlightedText': '#ffffff',
             'alternateBase': background}
    return types.SimpleNamespace(**{
        role: (lambda value=value: types.SimpleNamespace(color=lambda: Color(value)))
        for role, value in roles.items()
    })


@pytest.mark.parametrize('background,field,text,expected', [
    ('#efefef', '#ffffff', '#000000', 'default'),
    ('#202020', '#303030', '#eeeeee', 'dark'),
    ('#323232', '#202020', '#aaaaaa', 'dark'),  # Night Mapping
    ('#727272', '#b2b2b2', '#0e0e0e', 'default'),  # Blend of Gray: dark icons
])
def test_effective_theme_colors(theme_modules, monkeypatch, background, field, text, expected):
    qt = sys.modules['qgis.PyQt.QtWidgets']
    window_widget, input_widget = MagicMock(), MagicMock()
    window_widget.palette.return_value = palette(background, text)
    input_widget.palette.return_value = palette(field, text)
    monkeypatch.setattr(qt, 'QMainWindow', MagicMock(return_value=window_widget))
    monkeypatch.setattr(qt, 'QLineEdit', MagicMock(return_value=input_widget))
    loader = theme_modules.style_loader.StyleLoader
    colors = loader.get_qgis_colors()
    assert colors['color_bg_0'] == background
    assert colors['color_1'] == field
    assert colors['color_font_0'] == text
    assert colors['color_accent_light_bg'] == field
    assert colors['color_accent_dark'] == text
    assert loader.detect_qgis_theme() == expected
    assert window_widget.deleteLater.call_count == 2
    input_widget.ensurePolished.assert_called()


@pytest.mark.parametrize('config,expected', [
    ({}, 'auto'),
    ({'app': {'active_theme': 'default'}}, 'auto'),
    ({'app': {'active_theme': {'value': 'default'}}}, 'auto'),
    ({'APP': {'DOCKWIDGET': {'COLORS': {'ACTIVE_THEME': {'value': 'default'}}}}}, 'auto'),
    ({'APP': {'DOCKWIDGET': {'COLORS': {'ACTIVE_THEME': 'default'}}}}, 'auto'),
    ({'app': {'active_theme': 'dark'}}, 'dark'),
    ({'APP': {'DOCKWIDGET': {'COLORS': {'ACTIVE_THEME': {'value': 'auto'}}}}}, 'auto'),
    ({'APP': {'DOCKWIDGET': {'COLORS': {'ACTIVE_THEME': {'value': 'light'}}}}}, 'light'),
])
def test_config_schema(theme_modules, config, expected):
    assert theme_modules.theme_helpers.get_active_theme(config) == expected


def test_theme_manager_reads_real_dock_config(theme_modules):
    dock = types.SimpleNamespace(CONFIG_DATA={'app': {'active_theme': 'dark'}})
    manager = theme_modules.theme_manager.ThemeManager(dock)
    manager._load_config()
    assert manager.current_theme == 'dark'
    assert not manager._auto_detect


def test_explicit_theme_stops_following_qgis(theme_modules, monkeypatch):
    manager = theme_modules.theme_manager.ThemeManager(types.SimpleNamespace())
    monkeypatch.setattr(manager, 'apply', lambda: True)
    manager.set_theme('dark')
    assert not manager.follows_qgis_theme
    assert manager.get_colors()['color_bg_0'] == '#3A3A3A'


def test_existing_default_profile_follows_qgis_colors(theme_modules, monkeypatch):
    config = {'APP': {'DOCKWIDGET': {'COLORS': {'ACTIVE_THEME': {'value': 'default'}}}}}
    manager = theme_modules.theme_manager.ThemeManager(types.SimpleNamespace(CONFIG_DATA=config))
    colors = theme_modules.style_loader.StyleLoader.COLOR_SCHEMES['dark'].copy()
    monkeypatch.setattr(theme_modules.style_loader.StyleLoader, 'get_qgis_colors', lambda: colors)
    manager._load_config()
    assert manager.follows_qgis_theme
    assert manager.get_colors() == colors


def test_selecting_default_resumes_qgis_theme(theme_modules, monkeypatch):
    manager = theme_modules.theme_manager.ThemeManager(types.SimpleNamespace())
    monkeypatch.setattr(manager, 'apply', lambda: True)
    monkeypatch.setattr(manager, 'detect_system_theme', lambda: 'dark')
    manager.set_theme('light')
    assert not manager.follows_qgis_theme
    manager.set_theme('default')
    assert manager.follows_qgis_theme
    assert manager.current_theme == 'dark'


def test_auto_stylesheet_refreshes_colors_without_changing_contrast(theme_modules, monkeypatch):
    root = Path(__file__).resolve().parents[3]
    loader = theme_modules.style_loader.StyleLoader
    manager = theme_modules.theme_manager.ThemeManager(types.SimpleNamespace(plugin_dir=str(root)))
    colors = loader.COLOR_SCHEMES['dark'].copy()
    monkeypatch.setattr(loader, 'get_qgis_colors', lambda: colors)
    monkeypatch.setattr(loader, '_apply_dynamic_dimensions', lambda css: css)
    before = manager._load_stylesheet('dark')
    colors['color_bg_0'] = '#323232'
    colors['color_selected_text'] = '#010203'
    after = manager._load_stylesheet('dark')
    assert before != after
    assert 'background-color: #323232;' in after
    assert 'selection-color: #010203;' in after
    assert '{color_selected_text}' not in after


def test_legacy_theme_colors_are_normalized(theme_modules):
    config = {'APP': {'DOCKWIDGET': {'COLORS': {'THEMES': {
        'dark': {'BACKGROUND': ['#202020'], 'FONT': ['#eeeeee']}
    }}}}}
    assert theme_modules.theme_helpers.get_theme_colors(config, 'dark') == {
        'background': ['#202020'], 'font': ['#eeeeee']}


def test_same_contrast_different_theme_notifies(theme_modules, monkeypatch):
    loader = theme_modules.style_loader.StyleLoader
    monkeypatch.setattr(loader, 'detect_qgis_theme', lambda: 'dark')
    monkeypatch.setattr(loader, 'get_qgis_colors', lambda: {'color_bg_0': '#323232'})
    watcher = theme_modules.theme_watcher.QGISThemeWatcher()
    watcher._last_theme = 'dark'
    watcher._last_colors = {'color_bg_0': '#202020'}
    callback = MagicMock()
    watcher.add_callback(callback)
    watcher._on_palette_changed()
    watcher._on_palette_changed()
    callback.assert_called_once_with('dark')


@pytest.mark.parametrize('nested', [False, True])
def test_reload_theme_notifies_owning_icon_manager(theme_modules, monkeypatch, nested):
    loader = theme_modules.style_loader.StyleLoader
    manager = types.SimpleNamespace(on_theme_changed=MagicMock())
    dock = types.SimpleNamespace(_icon_manager=manager)
    widget = types.SimpleNamespace(parentWidget=lambda: dock) if nested else dock
    def apply_theme(target, theme):
        assert target is widget
        loader._current_theme = theme
    monkeypatch.setattr(loader, 'set_theme', apply_theme)
    loader.reload_theme(widget, 'dark')
    manager.on_theme_changed.assert_called_once_with('dark')


def test_icon_sync_without_a_dock_is_safe(theme_modules):
    loader = theme_modules.style_loader.StyleLoader
    loader.sync_icon_theme()
    loader.sync_icon_theme(types.SimpleNamespace())


def test_qgis4_signal_lifecycle(theme_modules, monkeypatch):
    loader = theme_modules.style_loader.StyleLoader
    monkeypatch.setattr(loader, 'detect_qgis_theme', lambda: 'default')
    monkeypatch.setattr(loader, 'get_qgis_colors', lambda: {})
    app = MagicMock()
    monkeypatch.setattr(theme_modules.theme_watcher.QgsApplication, 'instance', lambda: app)
    watcher = theme_modules.theme_watcher.QGISThemeWatcher()
    assert watcher.start_watching()
    app.themeChanged.connect.assert_called_once()
    watcher.stop_watching()
    app.themeChanged.disconnect.assert_called_once()


def test_qgis3_without_theme_changed_signal(theme_modules, monkeypatch):
    loader = theme_modules.style_loader.StyleLoader
    monkeypatch.setattr(loader, 'detect_qgis_theme', lambda: 'default')
    monkeypatch.setattr(loader, 'get_qgis_colors', lambda: {})
    app = types.SimpleNamespace(paletteChanged=MagicMock())
    monkeypatch.setattr(theme_modules.theme_watcher.QgsApplication, 'instance', lambda: app)
    watcher = theme_modules.theme_watcher.QGISThemeWatcher()
    assert watcher.start_watching()
    app.paletteChanged.connect.assert_called_once()
    watcher.stop_watching()
    app.paletteChanged.disconnect.assert_called_once()
