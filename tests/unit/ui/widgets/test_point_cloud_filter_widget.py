# -*- coding: utf-8 -*-
"""
PointCloudFilterWidget (WP-F): the pure ``build_criteria`` function and the
panel itself (populate / criteria / reset / set_current_subset).

The module is loaded by path under a private synthetic package: the domain
modules (WP-A) are stubbed with equivalent dataclasses and the Qt classes are
replaced by minimal fakes only for the duration of the load, so the shared
qgis mocks of the root conftest are left untouched.
"""
import importlib.util
import pathlib
import sys
import types
from dataclasses import dataclass
from typing import FrozenSet, Optional, Tuple

import pytest

_PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[4]
_PKG = "fm_pc_widget_test"


# ---------------------------------------------------------------------------
# Domain stubs (same contract as core.domain.point_cloud_filter_criteria)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AttributeRange:
    attribute: str
    minimum: Optional[float] = None
    maximum: Optional[float] = None

    def __post_init__(self):
        if self.minimum is not None and self.maximum is not None and self.minimum > self.maximum:
            raise ValueError("minimum > maximum")


@dataclass(frozen=True)
class PointCloudFilterCriteria:
    classification_codes: FrozenSet[int] = frozenset()
    ranges: Tuple[AttributeRange, ...] = ()
    return_number: Optional[int] = None
    extra_clauses: Tuple[str, ...] = ()

    @property
    def is_empty(self):
        return not self.classification_codes and not self.ranges and self.return_number is None and not self.extra_clauses


@dataclass(frozen=True)
class PointCloudAttributeSummary:
    name: str
    minimum: Optional[float] = None
    maximum: Optional[float] = None


@dataclass(frozen=True)
class PointCloudLayerSummary:
    layer_id: str
    layer_name: str
    provider: str = ""
    point_count: int = -1
    attributes: Tuple[str, ...] = ()
    classes: Tuple[Tuple[int, int], ...] = ()
    ranges: Tuple[PointCloudAttributeSummary, ...] = ()
    statistics_available: bool = False
    current_subset: str = ""

    def has_attribute(self, name):
        return name in self.attributes

    def range_of(self, name):
        for item in self.ranges:
            if item.name == name:
                return item
        return None


ASPRS_CLASS_NAMES = {0: "Created, never classified", 1: "Unclassified", 2: "Ground", 6: "Building"}


def asprs_class_label(code):
    return f"{code} - {ASPRS_CLASS_NAMES.get(code, f'Class {code}')}"


# ---------------------------------------------------------------------------
# Qt fakes
# ---------------------------------------------------------------------------

class _Signal:
    def __init__(self):
        self._slots = []

    def connect(self, slot):
        self._slots.append(slot)

    def emit(self, *args):
        for slot in list(self._slots):
            slot(*args)


class _Widget:
    def __init__(self, parent=None):
        self._parent = parent
        self._visible = True
        self._enabled = True
        self._tooltip = ""
        self._object_name = ""

    def setVisible(self, visible):
        self._visible = bool(visible)

    def isHidden(self):
        return not self._visible

    def setEnabled(self, enabled):
        self._enabled = bool(enabled)

    def isEnabled(self):
        return self._enabled

    def setToolTip(self, text):
        self._tooltip = text

    def toolTip(self):
        return self._tooltip

    def setObjectName(self, name):
        self._object_name = name

    def objectName(self):
        return self._object_name

    def setMaximumHeight(self, height):
        self._max_height = height

    def setLayout(self, layout):
        self._layout = layout

    def tr(self, text):
        return text


class _GroupBox(_Widget):
    def setTitle(self, title):
        self._title = title

    def title(self):
        return self._title


class _Label(_Widget):
    def __init__(self, text="", parent=None):
        super().__init__(parent)
        self._text = text

    def setText(self, text):
        self._text = text

    def text(self):
        return self._text

    def setWordWrap(self, wrap):
        self._wrap = wrap


class _CheckBox(_Widget):
    def __init__(self, text="", parent=None):
        super().__init__(parent)
        self._text = text
        self._checked = False
        self.toggled = _Signal()

    def setChecked(self, checked):
        checked = bool(checked)
        if checked != self._checked:
            self._checked = checked
            self.toggled.emit(checked)

    def isChecked(self):
        return self._checked


class _DoubleSpinBox(_Widget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._min, self._max, self._value, self._decimals = 0.0, 99.99, 0.0, 2

    def setDecimals(self, decimals):
        self._decimals = decimals

    def decimals(self):
        return self._decimals

    def setRange(self, low, high):
        self._min, self._max = low, high
        self._value = min(max(self._value, low), high)

    def minimum(self):
        return self._min

    def maximum(self):
        return self._max

    def setValue(self, value):
        self._value = min(max(value, self._min), self._max)

    def value(self):
        return self._value


class _ComboBox(_Widget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._items = []
        self._index = -1

    def addItem(self, text, data=None):
        self._items.append((text, data))
        if self._index < 0:
            self._index = 0

    def clear(self):
        self._items = []
        self._index = -1

    def count(self):
        return len(self._items)

    def setCurrentIndex(self, index):
        self._index = index if 0 <= index < len(self._items) else -1

    def currentIndex(self):
        return self._index

    def currentData(self):
        return self._items[self._index][1] if self._index >= 0 else None

    def itemText(self, index):
        return self._items[index][0]


class _ListWidgetItem:
    def __init__(self, text=""):
        self._text = text
        self._flags = 0
        self._state = 0
        self._data = {}

    def setFlags(self, flags):
        self._flags = flags

    def flags(self):
        return self._flags

    def setCheckState(self, state):
        self._state = state

    def checkState(self):
        return self._state

    def setData(self, role, value):
        self._data[role] = value

    def data(self, role):
        return self._data.get(role)

    def text(self):
        return self._text


class _ListWidget(_Widget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._items = []

    def addItem(self, item):
        self._items.append(item)

    def clear(self):
        self._items = []

    def count(self):
        return len(self._items)

    def item(self, index):
        return self._items[index]


class _PushButton(_Widget):
    def __init__(self, text="", parent=None):
        super().__init__(parent)
        self._text = text
        self.clicked = _Signal()


class _Layout:
    def __init__(self, parent=None):
        self._items = []
        if parent is not None:
            parent.setLayout(self)

    def addWidget(self, widget, *args):
        self._items.append(widget)

    def addLayout(self, layout, *args):
        self._items.append(layout)

    def addStretch(self, *args):
        pass

    def setContentsMargins(self, *args):
        pass

    def setSpacing(self, spacing):
        pass


class _Qt:
    class ItemFlag:
        ItemIsUserCheckable = 16
        ItemIsEnabled = 32

    class CheckState:
        Unchecked = 0
        PartiallyChecked = 1
        Checked = 2

    class ItemDataRole:
        UserRole = 256


def _package(name):
    module = types.ModuleType(name)
    module.__path__ = []
    module.__package__ = name
    sys.modules[name] = module
    return module


def _load_widget_module():
    for name in (_PKG, f"{_PKG}.ui", f"{_PKG}.ui.widgets", f"{_PKG}.core", f"{_PKG}.core.domain"):
        _package(name)
    criteria_module = types.ModuleType(f"{_PKG}.core.domain.point_cloud_filter_criteria")
    criteria_module.AttributeRange = AttributeRange
    criteria_module.PointCloudFilterCriteria = PointCloudFilterCriteria
    sys.modules[criteria_module.__name__] = criteria_module
    support_module = types.ModuleType(f"{_PKG}.core.domain.point_cloud_support")
    support_module.ASPRS_CLASS_NAMES = ASPRS_CLASS_NAMES
    support_module.asprs_class_label = asprs_class_label
    sys.modules[support_module.__name__] = support_module

    fake_core = types.ModuleType("qgis.PyQt.QtCore")
    fake_core.Qt = _Qt
    fake_widgets = types.ModuleType("qgis.PyQt.QtWidgets")
    for attr, value in {
        "QCheckBox": _CheckBox, "QComboBox": _ComboBox, "QDoubleSpinBox": _DoubleSpinBox,
        "QGroupBox": _GroupBox, "QHBoxLayout": _Layout, "QLabel": _Label, "QListWidget": _ListWidget,
        "QListWidgetItem": _ListWidgetItem, "QPushButton": _PushButton, "QVBoxLayout": _Layout, "QWidget": _Widget,
    }.items():
        setattr(fake_widgets, attr, value)

    saved = {name: sys.modules.get(name) for name in ("qgis.PyQt.QtCore", "qgis.PyQt.QtWidgets")}
    sys.modules["qgis.PyQt.QtCore"] = fake_core
    sys.modules["qgis.PyQt.QtWidgets"] = fake_widgets
    try:
        name = f"{_PKG}.ui.widgets.point_cloud_filter_widget"
        path = _PROJECT_ROOT / "ui" / "widgets" / "point_cloud_filter_widget.py"
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        module.__package__ = f"{_PKG}.ui.widgets"
        sys.modules[name] = module
        spec.loader.exec_module(module)
    finally:
        for name, original in saved.items():
            if original is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original
    return module


_widget_module = _load_widget_module()
build_criteria = _widget_module.build_criteria
PointCloudFilterWidget = _widget_module.PointCloudFilterWidget


def _summary(attributes=("X", "Y", "Z", "Classification", "Intensity", "ReturnNumber"), classes=((2, 1500), (6, 300)),
             ranges=(("Z", 12.5, 187.0), ("Intensity", 0, 4095), ("ReturnNumber", 1, 3)), current_subset=""):
    return PointCloudLayerSummary(
        layer_id="pc1", layer_name="cloud", attributes=tuple(attributes), classes=tuple(classes),
        ranges=tuple(PointCloudAttributeSummary(*item) for item in ranges), current_subset=current_subset,
    )


# ---------------------------------------------------------------------------
# build_criteria (pure)
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestBuildCriteria:

    def test_full_state(self):
        criteria = build_criteria([6, 2], (10, 150), (100, None), 1)

        assert criteria.classification_codes == frozenset({2, 6})
        assert criteria.ranges == (AttributeRange("Z", 10, 150), AttributeRange("Intensity", 100, None))
        assert criteria.return_number == 1
        assert criteria.is_empty is False

    def test_empty_state(self):
        criteria = build_criteria([], None, None, None)

        assert criteria.classification_codes == frozenset()
        assert criteria.ranges == ()
        assert criteria.return_number is None
        assert criteria.is_empty is True

    def test_range_with_both_bounds_unset_is_dropped(self):
        assert build_criteria([], (None, None), (None, None), None).ranges == ()

    def test_inverted_bounds_are_normalized(self):
        criteria = build_criteria([], (150, 10), None, None)
        assert criteria.ranges == (AttributeRange("Z", 10, 150),)

    def test_codes_and_return_number_are_cast_to_int(self):
        criteria = build_criteria(["2", 6.0], None, None, "3")
        assert criteria.classification_codes == frozenset({2, 6})
        assert criteria.return_number == 3

    def test_intensity_only(self):
        criteria = build_criteria((), None, (None, 200.0), None)
        assert criteria.ranges == (AttributeRange("Intensity", None, 200.0),)


# ---------------------------------------------------------------------------
# PointCloudFilterWidget
# ---------------------------------------------------------------------------

@pytest.fixture
def widget():
    return PointCloudFilterWidget(None)


def _items(widget):
    return [widget._classification_list.item(i) for i in range(widget._classification_list.count())]


@pytest.mark.unit
class TestPopulate:

    def test_classification_items_carry_label_count_and_code(self, widget):
        widget.populate(_summary())

        items = _items(widget)
        assert [item.text() for item in items] == ["2 - Ground (1500 pts)", "6 - Building (300 pts)"]
        assert [item.data(_Qt.ItemDataRole.UserRole) for item in items] == [2, 6]
        assert all(item.checkState() == _Qt.CheckState.Unchecked for item in items)
        assert all(item.flags() == _Qt.ItemFlag.ItemIsUserCheckable | _Qt.ItemFlag.ItemIsEnabled for item in items)

    def test_unknown_counts_are_not_displayed(self, widget):
        widget.populate(_summary(classes=((2, -1), (42, -1))))
        assert [item.text() for item in _items(widget)] == ["2 - Ground", "42 - Class 42"]

    def test_no_classes_falls_back_to_the_asprs_table(self, widget):
        widget.populate(_summary(classes=()))
        assert [item.data(_Qt.ItemDataRole.UserRole) for item in _items(widget)] == sorted(ASPRS_CLASS_NAMES)

    def test_ranges_are_calibrated_on_the_summary(self, widget):
        widget.populate(_summary())

        assert (widget._z_min.minimum(), widget._z_max.maximum()) == (12.5, 187.0)
        assert (widget._z_min.value(), widget._z_max.value()) == (12.5, 187.0)
        assert (widget._intensity_min.value(), widget._intensity_max.value()) == (0, 4095)
        assert widget._z_check.isChecked() is False
        assert widget._z_min.isEnabled() is False
        assert widget._z_check.isEnabled() is True
        assert widget._intensity_check.isEnabled() is True

    def test_range_checkbox_disabled_without_known_bounds(self, widget):
        # Qt defaults an unset QDoubleSpinBox to 0.0: an enabled-but-unset
        # checkbox would let a user silently apply "Z >= 0 AND Z <= 0" and
        # empty the layer. The checkbox itself must stay disabled instead.
        widget.populate(_summary(ranges=()))

        assert widget._z_check.isEnabled() is False
        assert widget._z_check.isChecked() is False
        assert widget._intensity_check.isEnabled() is False
        assert widget._intensity_check.isChecked() is False
        assert widget.criteria().ranges == ()

    def test_return_numbers_follow_the_summary_maximum(self, widget):
        widget.populate(_summary())

        combo = widget._return_combo
        assert [combo.itemText(i) for i in range(combo.count())] == ["Any", "1", "2", "3"]
        assert combo.currentData() is None

    def test_return_numbers_default_to_five_without_statistics(self, widget):
        widget.populate(_summary(ranges=()))
        assert widget._return_combo.count() == 6

    def test_missing_attributes_hide_their_section(self, widget):
        widget.populate(_summary(attributes=("X", "Y", "Z", "Classification")))

        assert widget._classification_box.isHidden() is False
        assert widget._z_box.isHidden() is False
        assert widget._intensity_box.isHidden() is True
        assert widget._return_box.isHidden() is True

    def test_unknown_attribute_list_shows_every_section(self, widget):
        widget.populate(_summary(attributes=()))

        assert widget._classification_box.isHidden() is False
        assert widget._intensity_box.isHidden() is False
        assert widget._return_box.isHidden() is False

    def test_current_subset_is_shown(self, widget):
        widget.populate(_summary(current_subset="Classification = 2"))
        assert widget._current_filter_label.text() == "Current filter: Classification = 2"

    def test_repopulating_replaces_the_items(self, widget):
        widget.populate(_summary())
        widget.populate(_summary(classes=((9, 10),)))
        assert [item.data(_Qt.ItemDataRole.UserRole) for item in _items(widget)] == [9]


@pytest.mark.unit
class TestCriteria:

    def test_criteria_reflects_the_panel_state(self, widget):
        widget.populate(_summary())
        for item in _items(widget):
            item.setCheckState(_Qt.CheckState.Checked)
        widget._z_check.setChecked(True)
        widget._z_min.setValue(20)
        widget._z_max.setValue(100)
        widget._return_combo.setCurrentIndex(2)

        criteria = widget.criteria()

        assert criteria.classification_codes == frozenset({2, 6})
        assert criteria.ranges == (AttributeRange("Z", 20.0, 100.0),)
        assert criteria.return_number == 2

    def test_disabled_range_is_ignored(self, widget):
        widget.populate(_summary())
        widget._intensity_min.setValue(10)

        assert widget.criteria().ranges == ()

    def test_hidden_section_is_ignored_even_when_set(self, widget):
        widget.populate(_summary(attributes=("X", "Y", "Z", "Classification")))
        widget._intensity_check.setChecked(True)
        widget._return_combo.setCurrentIndex(1)

        criteria = widget.criteria()

        assert criteria.ranges == ()
        assert criteria.return_number is None

    def test_empty_panel_gives_empty_criteria(self, widget):
        widget.populate(_summary())
        assert widget.criteria().is_empty is True

    def test_checking_a_range_enables_its_spin_boxes(self, widget):
        widget.populate(_summary())
        widget._z_check.setChecked(True)
        assert widget._z_min.isEnabled() is True
        assert widget._z_max.isEnabled() is True


@pytest.mark.unit
class TestButtonsAndReset:

    def test_all_and_none_buttons(self, widget):
        widget.populate(_summary())

        widget._button_all.clicked.emit()
        assert widget.criteria().classification_codes == frozenset({2, 6})

        widget._button_none.clicked.emit()
        assert widget.criteria().classification_codes == frozenset()

    def test_reset_clears_everything(self, widget):
        widget.populate(_summary())
        widget._button_all.clicked.emit()
        widget._z_check.setChecked(True)
        widget._intensity_check.setChecked(True)
        widget._return_combo.setCurrentIndex(3)

        widget.reset()

        assert widget.criteria().is_empty is True
        assert widget._return_combo.currentIndex() == 0

    def test_set_current_subset(self, widget):
        widget.set_current_subset("Z >= 10 AND Z <= 150")
        assert widget._current_filter_label.text() == "Current filter: Z >= 10 AND Z <= 150"
        assert widget._current_filter_label.toolTip() == "Z >= 10 AND Z <= 150"

        widget.set_current_subset("")
        assert widget._current_filter_label.text() == "Current filter: none"

    def test_title_and_object_name(self, widget):
        assert widget.title() == "Point cloud filter"
        assert widget.objectName() == "groupBox_point_cloud_filter"
