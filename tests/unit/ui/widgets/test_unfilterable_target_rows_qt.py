# -*- coding: utf-8 -*-
"""
A web basemap in the FILTERING targets list: a greyed row that nothing checks, on real Qt widgets
(PyQt5, offscreen).

``ui/widgets/custom_widgets.py`` is loaded under a private package with ``qgis.PyQt`` pointing at
PyQt5 for the import only (the root conftest mocks Qt for the other tests). Skipped without PyQt5
(the CI test job has none).
"""
import ast
import importlib
import os
import pathlib
import sys
import types

import pytest

pytestmark = pytest.mark.unit

QtWidgets = pytest.importorskip("PyQt5.QtWidgets")
from PyQt5 import QtCore, QtGui  # noqa: E402

Qt = QtCore.Qt
_ROOT = pathlib.Path(__file__).resolve().parents[4]
_PKG = "fm_unfilterable_rows_qt_test"


def _load_widgets():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    qt = {"qgis.PyQt": types.ModuleType("qgis.PyQt"), "qgis.PyQt.QtCore": QtCore, "qgis.PyQt.QtGui": QtGui,
          "qgis.PyQt.QtWidgets": QtWidgets}
    saved = {name: sys.modules.get(name) for name in qt}
    sys.modules.update(qt)  # for the imports only: the module loaded keeps the real Qt classes
    try:
        for name, path in (("", _ROOT), (".core", _ROOT / "core"), (".core.domain", _ROOT / "core" / "domain"),
                           (".infrastructure", _ROOT / "infrastructure"), (".ui", _ROOT / "ui"),
                           (".ui.widgets", _ROOT / "ui" / "widgets")):
            package = types.ModuleType(_PKG + name)
            package.__path__ = [str(path)]
            sys.modules[_PKG + name] = package
        utils = types.ModuleType(_PKG + ".infrastructure.utils")
        utils.safe_iterate_features = lambda *args, **kwargs: iter(())
        utils.is_layer_valid = lambda layer: True
        sys.modules[utils.__name__] = utils
        module = importlib.import_module(f"{_PKG}.ui.widgets.custom_widgets")
    finally:
        for name, previous in saved.items():
            if previous is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous
    return app, module


_APP, widgets = _load_widgets()


def _get_layers_to_filter():
    """FilterMateDockWidget.get_layers_to_filter, read from the dock source: what a launch saves as targets."""
    path = _ROOT / "filter_mate_dockwidget.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    dock = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "FilterMateDockWidget")
    method = next(node for node in dock.body if isinstance(node, ast.FunctionDef) and node.name == "get_layers_to_filter")
    namespace = {"Qt": Qt}
    exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), "exec"), namespace)
    return namespace["get_layers_to_filter"]


@pytest.fixture
def targets():
    combo = widgets.QgsCheckableComboBoxLayer()
    combo.set_target_hints(True)
    combo.addItem(QtGui.QIcon(), "roads [EPSG:31370]", {"layer_id": "roads", "layer_geometry_type": "GeometryType.Line"})
    combo.addItem(QtGui.QIcon(), "dem [EPSG:31370]", {"layer_id": "dem", "layer_geometry_type": "GeometryType.Raster"})
    combo.add_unfilterable_item(QtGui.QIcon(), "OpenStreetMap [EPSG:3857]", "osm")
    yield combo
    combo.deleteLater()


def _greyed(combo):
    return combo.model().item(2)


def _checked_rows(combo):
    return [row for row in range(combo.count()) if combo.model().item(row).checkState() == Qt.CheckState.Checked]


class TestGreyedRow:
    def test_neither_enabled_nor_checkable_nor_a_target(self, targets):
        item = _greyed(targets)
        assert not item.isEnabled() and not item.isCheckable() and not item.isSelectable()
        assert item.data(Qt.ItemDataRole.CheckStateRole) is None
        assert "layer_id" not in item.data(Qt.ItemDataRole.UserRole)
        assert item.data(Qt.ItemDataRole.UserRole) == {"unfilterable_layer_id": "osm"}

    def test_it_says_why(self, targets):
        item = _greyed(targets)
        assert item.data(widgets.TARGET_HINT_ROLE) == "not filterable"
        assert item.toolTip().startswith("OpenStreetMap [EPSG:3857]\n")
        assert "colours only" in item.toolTip() and "WMS" in item.toolTip()

    def test_select_all_and_the_menu_entries_skip_it(self, targets):
        targets.select_all()
        assert _checked_rows(targets) == [0, 1]
        targets.deselect_all()
        targets.select_by_kind("vector", Qt.CheckState.Checked)  # its data has no geometry type: "vector"
        targets.select_by_geometry("GeometryType.Raster", Qt.CheckState.Checked)
        assert _checked_rows(targets) == [0, 1]
        assert _greyed(targets).data(Qt.ItemDataRole.CheckStateRole) is None
        assert targets.checkedItems() == ["dem [EPSG:31370]", "roads [EPSG:31370]"]

    def test_no_check_by_index_or_by_text(self, targets):
        targets.setItemCheckState(2, Qt.CheckState.Checked)
        targets.setItemCheckState(2)
        targets.setItemsCheckState([2], Qt.CheckState.Checked)
        targets.setCheckedItems(["OpenStreetMap [EPSG:3857]"])
        assert _checked_rows(targets) == []

    def test_a_click_on_it_toggles_nothing(self, targets):
        """Qt keeps the last enabled row current: clicking the greyed row toggled the row hovered before."""
        targets.resize(300, 30)
        targets.show()
        targets.showPopup()
        view = targets.view()
        view.setCurrentIndex(targets.model().index(1, 0))  # dem hovered
        view.setCurrentIndex(targets.model().index(2, 0))  # moving onto the greyed row
        assert view.currentIndex().row() == 1
        center = view.visualRect(targets.model().index(2, 0)).center()
        release = QtGui.QMouseEvent(QtCore.QEvent.Type.MouseButtonRelease, QtCore.QPointF(center),
                                    Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton,
                                    Qt.KeyboardModifier.NoModifier)
        assert targets.eventFilter(view.viewport(), release) is True
        assert _checked_rows(targets) == []
        center = view.visualRect(targets.model().index(0, 0)).center()
        release = QtGui.QMouseEvent(QtCore.QEvent.Type.MouseButtonRelease, QtCore.QPointF(center),
                                    Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton,
                                    Qt.KeyboardModifier.NoModifier)
        targets.eventFilter(view.viewport(), release)
        assert _checked_rows(targets) == [0]  # the row under the click, not the current one
        targets.hidePopup()

    def test_never_saved_as_a_target(self, targets):
        """get_layers_to_filter (the targets a launch saves and splits) never holds it, even forced checked."""
        dock = types.SimpleNamespace(widgets_initialized=True, _controller_integration=None,
                                     widgets={"FILTERING": {"LAYERS_TO_FILTER": {"WIDGET": targets}}})
        get_layers_to_filter = _get_layers_to_filter()
        targets.select_all()
        assert get_layers_to_filter(dock) == ["roads", "dem"]
        _greyed(targets).setCheckState(Qt.CheckState.Checked)  # bypassing the widget
        assert get_layers_to_filter(dock) == ["roads", "dem"]

    def test_painted_greyed_without_check_box(self, targets):
        """Both rows paint under PyQt5 (flags tested with &, opacity), the greyed one fainter."""
        delegate = targets.itemDelegate()
        images = []
        for row in (1, 2):
            image = QtGui.QImage(300, 22, QtGui.QImage.Format.Format_ARGB32)
            image.fill(Qt.GlobalColor.white)
            painter = QtGui.QPainter(image)
            painter.setPen(QtGui.QColor(Qt.GlobalColor.black))
            option = QtWidgets.QStyleOptionViewItem()
            option.rect = QtCore.QRect(0, 0, 300, 22)
            delegate.paint(painter, option, targets.model().index(row, 0))
            painter.end()
            images.append(image)
        darkest = [min(QtGui.QColor(image.pixel(x, y)).value() for x in range(300) for y in range(22))
                   for image in images]
        assert darkest[1] > darkest[0]  # nothing drawn at full contrast on the greyed row
