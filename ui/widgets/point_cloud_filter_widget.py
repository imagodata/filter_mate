# -*- coding: utf-8 -*-
"""
Point Cloud Filter Widget.

Group box shown in the filtering tab when the current layer is a point cloud:
ASPRS classification checklist, elevation (Z) and intensity ranges, return
number and the current subset string. It has no action button of its own: the
dock's Filter / Unfilter / Undo / Redo buttons drive it through
``PointCloudUIController``, which reads ``criteria()``.
"""
import logging
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:
    from qgis.PyQt.QtCore import Qt
    from qgis.PyQt.QtWidgets import (
        QCheckBox, QComboBox, QDoubleSpinBox, QGroupBox, QHBoxLayout, QLabel,
        QListWidget, QListWidgetItem, QPushButton, QVBoxLayout, QWidget,
    )
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False
    Qt = None
    QGroupBox = object

try:
    from ...core.domain.point_cloud_filter_criteria import AttributeRange, PointCloudFilterCriteria
except ImportError:
    AttributeRange = None
    PointCloudFilterCriteria = None

try:
    from ...core.domain.point_cloud_support import ASPRS_CLASS_NAMES, asprs_class_label
except ImportError:
    ASPRS_CLASS_NAMES = {}

    def asprs_class_label(code: int) -> str:
        """Fallback label when the domain module is unavailable."""
        return f"{code} - Class {code}"

logger = logging.getLogger(__name__)

RangeTuple = Optional[Tuple[Optional[float], Optional[float]]]

CLASSIFICATION_ATTRIBUTE = "Classification"
Z_ATTRIBUTE = "Z"
INTENSITY_ATTRIBUTE = "Intensity"
RETURN_NUMBER_ATTRIBUTE = "ReturnNumber"
DEFAULT_RETURN_NUMBERS = 5
MAX_RETURN_NUMBERS = 15
SPIN_BOX_LIMIT = 1e9


def _to_attribute_range(attribute: str, bounds: RangeTuple) -> Optional[Any]:
    """Build an AttributeRange from ``(minimum, maximum)``, None when both bounds are unset."""
    if bounds is None:
        return None
    minimum, maximum = bounds
    if minimum is None and maximum is None:
        return None
    if minimum is not None and maximum is not None and minimum > maximum:
        minimum, maximum = maximum, minimum
    if AttributeRange is None:
        raise RuntimeError("core.domain.point_cloud_filter_criteria is not importable")
    return AttributeRange(attribute=attribute, minimum=minimum, maximum=maximum)


def build_criteria(
    checked_codes: Iterable[int],
    z_range: RangeTuple = None,
    intensity_range: RangeTuple = None,
    return_number: Optional[int] = None
) -> 'PointCloudFilterCriteria':
    """
    Build the criteria from the panel state (pure function, testable without Qt).

    Args:
        checked_codes: Checked ASPRS classification codes.
        z_range: ``(minimum, maximum)`` elevation bounds, each optional, or None.
        intensity_range: ``(minimum, maximum)`` intensity bounds, each optional, or None.
        return_number: Selected return number, or None for any.

    Returns:
        PointCloudFilterCriteria for ``PointCloudFilterService.apply``.
    """
    if PointCloudFilterCriteria is None:
        raise RuntimeError("core.domain.point_cloud_filter_criteria is not importable")
    ranges: List[Any] = []
    for attribute, bounds in ((Z_ATTRIBUTE, z_range), (INTENSITY_ATTRIBUTE, intensity_range)):
        attribute_range = _to_attribute_range(attribute, bounds)
        if attribute_range is not None:
            ranges.append(attribute_range)
    return PointCloudFilterCriteria(
        classification_codes=frozenset(int(code) for code in checked_codes),
        ranges=tuple(ranges),
        return_number=None if return_number is None else int(return_number),
    )


def _attribute_available(summary: Any, name: str) -> bool:
    """True when the summary lists the attribute, or lists no attribute at all."""
    attributes = tuple(getattr(summary, 'attributes', ()) or ())
    if not attributes:
        return True
    try:
        return bool(summary.has_attribute(name))
    except Exception:
        return name in attributes


def _range_bounds(summary: Any, name: str) -> Tuple[Optional[float], Optional[float]]:
    """Return ``(minimum, maximum)`` of the attribute from the summary, None when unknown."""
    try:
        attribute_range = summary.range_of(name)
    except Exception:
        return None, None
    if attribute_range is None:
        return None, None
    return getattr(attribute_range, 'minimum', None), getattr(attribute_range, 'maximum', None)


class PointCloudFilterWidget(QGroupBox):
    """Point cloud filter panel: classification, Z, intensity, return number."""

    def __init__(self, parent: Any = None) -> None:
        """
        Build the panel.

        Args:
            parent: Parent widget (the dock widget).
        """
        super().__init__(parent)
        self._sections: Dict[str, bool] = {
            CLASSIFICATION_ATTRIBUTE: True,
            Z_ATTRIBUTE: True,
            INTENSITY_ATTRIBUTE: True,
            RETURN_NUMBER_ATTRIBUTE: True,
        }
        self._summary: Any = None
        self.setObjectName("groupBox_point_cloud_filter")
        self.setTitle(self.tr("Point cloud filter"))
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        self._classification_box = QWidget(self)
        classification_layout = QVBoxLayout(self._classification_box)
        classification_layout.setContentsMargins(0, 0, 0, 0)
        classification_layout.addWidget(QLabel(self.tr("Classification"), self._classification_box))
        self._classification_list = QListWidget(self._classification_box)
        self._classification_list.setMaximumHeight(180)
        classification_layout.addWidget(self._classification_list)
        buttons_layout = QHBoxLayout()
        self._button_all = QPushButton(self.tr("All"), self._classification_box)
        self._button_none = QPushButton(self.tr("None"), self._classification_box)
        self._button_all.clicked.connect(self._check_all_classes)
        self._button_none.clicked.connect(self._uncheck_all_classes)
        buttons_layout.addWidget(self._button_all)
        buttons_layout.addWidget(self._button_none)
        buttons_layout.addStretch()
        classification_layout.addLayout(buttons_layout)
        layout.addWidget(self._classification_box)

        self._z_box, self._z_check, self._z_min, self._z_max = self._build_range_row(self.tr("Elevation (Z)"), 2)
        layout.addWidget(self._z_box)
        self._intensity_box, self._intensity_check, self._intensity_min, self._intensity_max = self._build_range_row(self.tr("Intensity"), 0)
        layout.addWidget(self._intensity_box)

        self._return_box = QWidget(self)
        return_layout = QHBoxLayout(self._return_box)
        return_layout.setContentsMargins(0, 0, 0, 0)
        return_layout.addWidget(QLabel(self.tr("Return number"), self._return_box))
        self._return_combo = QComboBox(self._return_box)
        return_layout.addWidget(self._return_combo)
        return_layout.addStretch()
        layout.addWidget(self._return_box)
        self._fill_return_numbers(DEFAULT_RETURN_NUMBERS)

        self._current_filter_label = QLabel("", self)
        self._current_filter_label.setWordWrap(True)
        layout.addWidget(self._current_filter_label)
        self.set_current_subset("")

    def _build_range_row(self, title: str, decimals: int) -> Tuple[Any, Any, Any, Any]:
        """Return ``(container, enabling checkbox, minimum spin box, maximum spin box)``."""
        box = QWidget(self)
        row = QHBoxLayout(box)
        row.setContentsMargins(0, 0, 0, 0)
        check = QCheckBox(title, box)
        minimum = QDoubleSpinBox(box)
        maximum = QDoubleSpinBox(box)
        for spin in (minimum, maximum):
            spin.setDecimals(decimals)
            spin.setRange(-SPIN_BOX_LIMIT, SPIN_BOX_LIMIT)
            spin.setEnabled(False)
        minimum.setToolTip(self.tr("Minimum"))
        maximum.setToolTip(self.tr("Maximum"))
        check.toggled.connect(minimum.setEnabled)
        check.toggled.connect(maximum.setEnabled)
        row.addWidget(check)
        row.addWidget(minimum)
        row.addWidget(QLabel("–", box))
        row.addWidget(maximum)
        row.addStretch()
        return box, check, minimum, maximum

    # === Public API ===

    def populate(self, summary: Any) -> None:
        """
        Fill the panel from a ``PointCloudLayerSummary``.

        Args:
            summary: Summary read by ``read_point_cloud_summary``.
        """
        self._summary = summary
        self._populate_classes(summary)
        self._calibrate_range(Z_ATTRIBUTE, self._z_box, self._z_check, self._z_min, self._z_max, summary)
        self._calibrate_range(INTENSITY_ATTRIBUTE, self._intensity_box, self._intensity_check, self._intensity_min, self._intensity_max, summary)
        self._populate_return_numbers(summary)
        self.set_current_subset(getattr(summary, 'current_subset', "") or "")

    def criteria(self) -> 'PointCloudFilterCriteria':
        """Return the criteria matching the current panel state."""
        return build_criteria(
            self._checked_codes(),
            self._range_value(Z_ATTRIBUTE, self._z_check, self._z_min, self._z_max),
            self._range_value(INTENSITY_ATTRIBUTE, self._intensity_check, self._intensity_min, self._intensity_max),
            self._selected_return_number(),
        )

    def reset(self) -> None:
        """Uncheck every class, disable both ranges and select any return number."""
        self._uncheck_all_classes()
        self._z_check.setChecked(False)
        self._intensity_check.setChecked(False)
        self._return_combo.setCurrentIndex(0)

    def set_current_subset(self, text: str) -> None:
        """
        Show the subset string currently applied to the layer.

        Args:
            text: Subset string, "" when the layer is unfiltered.
        """
        text = text or ""
        self._current_filter_label.setText(self.tr("Current filter: {0}").format(text or self.tr("none")))
        self._current_filter_label.setToolTip(text)

    # === Classification ===

    def _populate_classes(self, summary: Any) -> None:
        available = _attribute_available(summary, CLASSIFICATION_ATTRIBUTE)
        self._sections[CLASSIFICATION_ATTRIBUTE] = available
        self._classification_box.setVisible(available)
        self._classification_list.clear()
        if not available:
            return
        classes = tuple(getattr(summary, 'classes', ()) or ())
        if not classes:
            classes = tuple((code, -1) for code in sorted(ASPRS_CLASS_NAMES)) or tuple((code, -1) for code in range(19))
        for code, count in classes:
            label = asprs_class_label(code)
            if count is not None and count >= 0:
                label = f"{label} ({count} pts)"
            item = QListWidgetItem(label)
            item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            item.setCheckState(Qt.CheckState.Unchecked)
            item.setData(Qt.ItemDataRole.UserRole, int(code))
            self._classification_list.addItem(item)

    def _set_all_classes(self, state: Any) -> None:
        for index in range(self._classification_list.count()):
            item = self._classification_list.item(index)
            if item is not None:
                item.setCheckState(state)

    def _check_all_classes(self) -> None:
        self._set_all_classes(Qt.CheckState.Checked)

    def _uncheck_all_classes(self) -> None:
        self._set_all_classes(Qt.CheckState.Unchecked)

    def _checked_codes(self) -> List[int]:
        if not self._sections[CLASSIFICATION_ATTRIBUTE]:
            return []
        codes = []
        for index in range(self._classification_list.count()):
            item = self._classification_list.item(index)
            if item is not None and item.checkState() == Qt.CheckState.Checked:
                codes.append(int(item.data(Qt.ItemDataRole.UserRole)))
        return codes

    # === Ranges ===

    def _calibrate_range(self, name: str, box: Any, check: Any, minimum: Any, maximum: Any, summary: Any) -> None:
        available = _attribute_available(summary, name)
        self._sections[name] = available
        box.setVisible(available)
        check.setChecked(False)
        low, high = _range_bounds(summary, name)
        if low is None or high is None:
            # No known bounds: leave the checkbox disabled. Qt's QDoubleSpinBox
            # defaults to 0.0, so an enabled-but-unset range would let a user
            # check the box and silently filter "name >= 0 AND name <= 0",
            # which empties the layer.
            check.setEnabled(False)
            for spin in (minimum, maximum):
                spin.setRange(-SPIN_BOX_LIMIT, SPIN_BOX_LIMIT)
            return
        check.setEnabled(True)
        for spin in (minimum, maximum):
            spin.setRange(low, high)
        minimum.setValue(low)
        maximum.setValue(high)

    def _range_value(self, name: str, check: Any, minimum: Any, maximum: Any) -> RangeTuple:
        if not self._sections[name] or not check.isChecked():
            return None
        return float(minimum.value()), float(maximum.value())

    # === Return number ===

    def _fill_return_numbers(self, count: int) -> None:
        self._return_combo.clear()
        self._return_combo.addItem(self.tr("Any"), None)
        for number in range(1, max(1, min(MAX_RETURN_NUMBERS, count)) + 1):
            self._return_combo.addItem(str(number), number)
        self._return_combo.setCurrentIndex(0)

    def _populate_return_numbers(self, summary: Any) -> None:
        available = _attribute_available(summary, RETURN_NUMBER_ATTRIBUTE)
        self._sections[RETURN_NUMBER_ATTRIBUTE] = available
        self._return_box.setVisible(available)
        count = DEFAULT_RETURN_NUMBERS
        _, high = _range_bounds(summary, RETURN_NUMBER_ATTRIBUTE)
        if high is not None:
            try:
                count = int(high)
            except (TypeError, ValueError):
                count = DEFAULT_RETURN_NUMBERS
        self._fill_return_numbers(count)

    def _selected_return_number(self) -> Optional[int]:
        if not self._sections[RETURN_NUMBER_ATTRIBUTE]:
            return None
        value = self._return_combo.currentData()
        return None if value is None else int(value)
