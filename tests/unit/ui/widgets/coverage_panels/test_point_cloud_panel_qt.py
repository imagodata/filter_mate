# -*- coding: utf-8 -*-
"""
The object detector part of the real point cloud panel, on real Qt widgets (PyQt5, offscreen).

The panel is loaded under a private package with ``qgis.PyQt`` pointing at PyQt5 for the
import only (the root conftest mocks Qt for the other tests) and no ``qgis.gui`` (plain
QGroupBox / QComboBox). Skipped without PyQt5 (the CI test job has none).
"""
import importlib
import os
import pathlib
import sys
import types

import pytest

pytestmark = pytest.mark.unit

QtWidgets = pytest.importorskip("PyQt5.QtWidgets")
from PyQt5 import QtCore, QtGui  # noqa: E402

_ROOT = pathlib.Path(__file__).resolve().parents[5]
_PKG = "fm_pc_panel_qt_test"


def _load_panel():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    qt = {"qgis.PyQt": types.ModuleType("qgis.PyQt"), "qgis.PyQt.QtCore": QtCore, "qgis.PyQt.QtGui": QtGui,
          "qgis.PyQt.QtWidgets": QtWidgets, "qgis.gui": types.ModuleType("qgis.gui")}
    saved = {name: sys.modules.get(name) for name in qt}
    sys.modules.update(qt)  # for the imports only: the modules loaded keep the real Qt classes
    try:
        for name, path in (("", _ROOT), (".core", _ROOT / "core"), (".core.domain", _ROOT / "core" / "domain"),
                           (".ui", _ROOT / "ui"), (".ui.widgets", _ROOT / "ui" / "widgets"),
                           (".ui.widgets.coverage_panels", _ROOT / "ui" / "widgets" / "coverage_panels")):
            package = types.ModuleType(_PKG + name)
            package.__path__ = [str(path)]
            sys.modules[_PKG + name] = package
        module = importlib.import_module(f"{_PKG}.ui.widgets.coverage_panels.point_cloud_exploring_panel")
        importlib.import_module(f"{_PKG}.ui.widgets.selection_strip")  # object_summary imports it later
    finally:
        for name, previous in saved.items():
            if previous is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous
    return app, module


_APP, cloud = _load_panel()


@pytest.fixture
def panel():
    widget = cloud.PointCloudExploringPanel()
    widget.populate(cloud.PointCloudLayerSummary(
        "lidar", "lidar", "copc", 1000, ("X", "Y", "Z", "Classification"), ((2, 600), (5, 300), (6, 100))))
    yield widget
    widget.deleteLater()


def _object(code=6, box=(0.0, 0.0, 10.0, 12.0)):
    return {"x": box[0] + 1, "y": box[1] + 1, "code": code, "box": list(box), "wkt": "POLYGON((0 0,10 0,10 12,0 0))",
            "truncated": False}


def _checked_item(panel, code):
    for index in range(panel._classes_list.count()):
        item = panel._classes_list.item(index)
        if item.data(QtCore.Qt.ItemDataRole.UserRole) == code:
            return item
    raise AssertionError(code)


class TestDetectorOnTheRealPanel:
    def test_an_object_added_keeps_through_its_class_being_checked(self, panel):
        """The class of the object is checked with the list signals blocked: itemChanged does not drop it."""
        dropped = []
        panel.objectsChanged.connect(lambda: dropped.append(True))
        assert panel.add_object(_object(6))
        assert [item["code"] for item in panel.object_items()] == [6]
        assert panel.checked_class_codes() == [6] and dropped == []
        assert panel.objects_pending()
        assert panel.expression() == "Classification = 6 AND X >= 0 AND X <= 10 AND Y >= 0 AND Y <= 12"

    def test_ctrl_click_adds_an_object_of_another_class(self, panel):
        panel.add_object(_object(6))
        panel.add_object(_object(5, (20.0, 20.0, 25.0, 25.0)), extend=True)
        assert panel.checked_class_codes() == [5, 6] and len(panel.object_items()) == 2
        assert " OR " in panel.expression()

    def test_checking_a_class_by_hand_drops_the_objects(self, panel):
        dropped = []
        panel.objectsChanged.connect(lambda: dropped.append(True))
        panel.add_object(_object(6))
        _checked_item(panel, 2).setCheckState(QtCore.Qt.CheckState.Checked)
        assert panel.object_items() == [] and dropped == [True]
        assert panel.checked_class_codes() == [2, 6]
        assert panel.expression() == "Classification IN (2, 6)"  # already the classes in the text shown

    def test_detection_gives_the_zone_and_the_strip_figures(self, panel):
        panel.add_object(_object(6))
        panel.set_detected_objects("POLYGON((0 0,10 0,10 12,0 0))", [[6, 0, 0, 10, 12]], 1, 120.0, False)
        assert not panel.objects_pending()
        assert panel.zone_wkt() == "POLYGON((0 0,10 0,10 12,0 0))"
        assert panel.detected_objects() == (1, 120.0, False, False)
        assert panel.class_point_counts() == (None, None)  # not the points of the whole class
        assert panel._class_summary_label.text() == "1 object(s) · 120 m²"

    def test_the_objects_come_back_with_classes(self, panel):
        panel.add_object(_object(6))
        panel.set_detected_objects("POLYGON((0 0,10 0,10 12,0 0))", [[6, 0, 0, 10, 12]], 1, 120.0, False)
        panel._ranges_group.setChecked(True)
        assert panel.zone_wkt() == "" and panel.detected_objects() is None
        panel._classes_group.setChecked(True)
        assert panel.zone_wkt().startswith("POLYGON") and len(panel.object_items()) == 1
        panel.add_object(_object(5, (20.0, 20.0, 25.0, 25.0)), extend=True)
        assert len(panel.object_items()) == 2

    def test_many_similar_objects_say_they_show_the_whole_class(self, panel):
        panel.add_object(_object(6))
        boxes = [[6, i * 10.0, 0.0, i * 10.0 + 5, 5.0] for i in range(cloud.MAX_OBJECT_BOXES + 1)]
        panel.set_object_target(cloud.SIMILAR_OBJECTS_TARGET)
        panel.set_detected_objects("MULTIPOLYGON(((0 0,1 0,1 1,0 0)))", boxes, len(boxes), None, False)
        assert panel.detected_objects()[3] is True
        assert "shown as the whole class in their box" in panel._class_summary_label.text()
        assert panel.expression().count("X >=") == 1

    def test_the_other_tiles_get_the_classes_only(self, panel):
        panel.add_object(_object(6))
        assert panel.tiles_expression() == "Classification = 6"
        assert "X >=" in panel.expression()

    def test_reset_clears_the_objects_and_the_target(self, panel):
        panel.add_object(_object(6))
        panel.set_object_target(cloud.SIMILAR_OBJECTS_TARGET)
        panel.reset()
        assert panel.object_items() == [] and panel.object_target() == cloud.OBJECT_TARGET

    def test_state_round_trip(self, panel):
        panel.add_object(_object(6))
        panel.set_detected_objects("POLYGON((0 0,10 0,10 12,0 0))", [[6, 0, 0, 10, 12]], 1, 120.0, True)
        state = panel.state()
        panel.reset()
        panel.restore_state(state)
        assert panel.detected_objects() == (1, 120.0, True, False) and panel.checked_class_codes() == [6]
