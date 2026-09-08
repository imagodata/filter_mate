"""Real Qt 5/6 checks for theme-only changes: preserve artwork and geometry."""
import importlib.util
import os
from pathlib import Path
import re
import sys
import types

import pytest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
QT_BINDING = os.environ.get('FILTERMATE_TEST_QT_BINDING', 'PyQt6')
QtCore = pytest.importorskip(QT_BINDING + '.QtCore')
QtGui = importlib.import_module(QT_BINDING + '.QtGui')
QtWidgets = importlib.import_module(QT_BINDING + '.QtWidgets')

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def styles(monkeypatch):
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    for name, module in [('QtCore', QtCore), ('QtGui', QtGui), ('QtWidgets', QtWidgets)]:
        monkeypatch.setitem(sys.modules, 'qgis.PyQt.' + name, module)
    package = types.ModuleType('_real_qt_theme_styles')
    package.__path__ = [str(ROOT / 'ui/styles')]
    monkeypatch.setitem(sys.modules, package.__name__, package)
    loaded = {}
    for name in ('icon_manager', 'button_styler', 'style_loader'):
        spec = importlib.util.spec_from_file_location(package.__name__ + '.' + name,
                                                     ROOT / 'ui/styles' / (name + '.py'))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        loaded[name] = module
    yield app, types.SimpleNamespace(**loaded)


@pytest.mark.parametrize('theme,variant', [('default', 'auto_layer_black.png'),
                                          ('dark', 'auto_layer_black.png')])
def test_existing_icon_variant_keeps_its_artwork(styles, theme, variant):
    _, modules = styles
    dock = QtWidgets.QWidget()
    dock.plugin_dir = str(ROOT)
    manager = modules.icon_manager.IconManager(dock)
    manager._current_theme = theme
    for configured in ('auto_layer_black.png', 'auto_layer_white.png'):
        actual = manager.get_icon(configured).pixmap(24, 24).toImage()
        pixmap = QtGui.QPixmap(str(ROOT / 'icons' / variant))
        if theme == 'dark':
            pixmap = manager._invert_pixmap(pixmap)
        expected = QtGui.QIcon(pixmap).pixmap(24, 24).toImage()
        assert not actual.isNull()
        assert actual == expected


@pytest.mark.parametrize('theme', ['default', 'dark'])
def test_paired_icons_have_readable_contrast(styles, theme):
    _, modules = styles
    dock = QtWidgets.QWidget()
    dock.plugin_dir = str(ROOT)
    manager = modules.icon_manager.IconManager(dock)
    manager._current_theme = theme
    for pair in manager.VARIANT_ICONS.values():
        for filename in pair:
            pixels = manager.get_icon(filename).pixmap(24, 24).toImage()
            visible = [pixels.pixelColor(x, y).lightness()
                       for x in range(pixels.width()) for y in range(pixels.height())
                       if pixels.pixelColor(x, y).alpha() > 128]
            assert visible, filename
            assert (sum(visible) / len(visible) > 128) == (theme == 'dark'), filename


@pytest.mark.parametrize('theme', ['default', 'dark'])
def test_all_action_icons_remain_available(styles, theme):
    _, modules = styles
    dock = QtWidgets.QWidget()
    dock.plugin_dir = str(ROOT)
    manager = modules.icon_manager.IconManager(dock)
    manager._current_theme = theme
    for name in ('filter.png', 'undo.png', 'redo.png', 'unfilter.png', 'export.png',
                 'layers.png', 'add_multi.png', 'geo_predicates.png',
                 'buffer_value.png', 'buffer_type.png'):
        assert not manager.get_icon(name).isNull(), name


def test_button_theme_replacement_changes_only_colors(styles):
    app, modules = styles
    dock = QtWidgets.QWidget()
    dock._theme_manager = types.SimpleNamespace(
        follows_qgis_theme=True,
        get_colors=lambda: modules.style_loader.StyleLoader.COLOR_SCHEMES['dark'])
    styler = modules.button_styler.ButtonStyler(dock)
    before = styler._get_light_action_button_style()
    after = styler._theme_colors_only(before)
    assert before != after
    assert re.sub(r'#[0-9a-fA-F]{6}', 'COLOR', before) == re.sub(r'#[0-9a-fA-F]{6}', 'COLOR', after)
    button = QtWidgets.QPushButton(dock)
    button.setIcon(QtGui.QIcon(str(ROOT / 'icons/filter.png')))
    button.setFixedSize(40, 40)
    button.setStyleSheet(before)
    button.ensurePolished()
    size, hint, icon = button.size(), button.sizeHint(), button.icon().cacheKey()
    button.setStyleSheet(after)
    app.processEvents()
    assert button.size() == size
    assert button.sizeHint() == hint
    assert button.icon().cacheKey() == icon


def test_setup_recolors_icons_loaded_before_theme_and_refreshes_auxiliary_icons(styles):
    _, modules = styles
    dock = QtWidgets.QWidget()
    dock.plugin_dir = str(ROOT)
    callbacks = []
    dock._theme_manager = types.SimpleNamespace(
        current_theme='dark', add_theme_changed_callback=callbacks.append)
    dock.toolBox_tabTools = QtWidgets.QToolBox(dock)
    for label in ('Filtering', 'Exporting', 'Configuration'):
        dock.toolBox_tabTools.addItem(QtWidgets.QWidget(), label)
    dock.checkBox_filtering_use_centroids_source_layer = QtWidgets.QCheckBox(dock)
    button = QtWidgets.QPushButton(dock)
    manager = modules.icon_manager.IconManager(dock)
    manager.set_button_icon(button, 'filter.png')  # Real startup loads icons first.
    light = button.icon().pixmap(24, 24).toImage()
    manager.setup()
    dark = button.icon().pixmap(24, 24).toImage()
    assert dark != light
    assert dark == manager.get_icon('filter.png').pixmap(24, 24).toImage()
    assert dock.toolBox_tabTools.itemIcon(0).pixmap(24, 24).toImage() == manager.get_icon('filter_multi.png').pixmap(24, 24).toImage()
    assert not dock.checkBox_filtering_use_centroids_source_layer.icon().isNull()
    callbacks[0]('default')
    assert button.icon().pixmap(24, 24).toImage() == light
