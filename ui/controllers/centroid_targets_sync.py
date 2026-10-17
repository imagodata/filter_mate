# -*- coding: utf-8 -*-
"""
Centroids of the FILTERING targets, chosen layer by layer (FilterMate 5).

Each line / polygon target of the "layers to filter" list has its own centroid
toggle (a small square on the right of its item). The centroid button beside
the list sums them up and sets them all:

* checked: every checked line / polygon target uses its centroids;
* partial: only some do;
* unchecked: none does;
* disabled: no line / polygon target is checked (points, rasters and point
  clouds have no centroid to use), or the source is a raster / point cloud.

The choice is stored per source layer in ``filtering.centroid_layers``; the old
global ``filtering.use_centroids_distant_layers`` flag follows the button (True
only when every target uses its centroids) and still seeds the toggles of
projects saved before (:func:`core.domain.centroid_targets.initial_centroid_layers`).
"""
import logging
from typing import Any, List, Optional

try:
    from qgis.PyQt.QtCore import QObject, Qt, QTimer
except ImportError:  # pragma: no cover - unit tests without Qt
    QObject = object
    Qt = QTimer = None

from ...core.domain.centroid_targets import (
    CENTROID_LAYERS_KEY, LEGACY_FLAG_KEY, global_centroid_state, initial_centroid_layers,
)

logger = logging.getLogger(__name__)

COMBO = 'checkableComboBoxLayer_filtering_layers_to_filter'
BUTTON = 'checkBox_filtering_use_centroids_distant_layers'
TARGETS_KEY = 'pushButton_checkable_filtering_layers_to_filter'


class CentroidTargetsSync(QObject):
    """Keeps the per-target centroid toggles, the centroid button and the source layer properties in step."""

    def __init__(self, dockwidget: Any) -> None:
        super().__init__(dockwidget if isinstance(dockwidget, QObject) else None)
        self._dw = dockwidget
        self._refreshing = False
        self._connected = False
        self._timer = None

    def _catalog(self) -> None:  # pragma: no cover - never called
        """Literal tr() calls of the tooltips, for pylupdate."""
        self.tr("Test the checked line and polygon targets by their centroids (point on surface): faster on "
                "large geometries. Each target has its own square in the list")
        self.tr("Centroids apply to line and polygon targets: check one in the list of layers to filter")

    # === Wiring ===

    def connect(self) -> bool:
        """Connect the combo, the button and the targets key, once (after the dock widgets exist)."""
        if self._connected:
            return True
        combo, button = self._widget(COMBO), self._widget(BUTTON)
        if combo is None or button is None or not hasattr(combo, 'centroidsChanged'):
            return False
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.setInterval(0)
        timer.timeout.connect(self.refresh)
        self._timer = timer
        combo.populated.connect(self.apply_stored)
        combo.centroidsChanged.connect(self._on_toggles_changed)
        combo.checkedItemsChanged.connect(self.schedule)
        button.clicked.connect(self._on_button_clicked)
        # A programmatic change (the properties of the layer loaded into the widgets) is
        # corrected on the next pass: the button always shows the per-target toggles.
        button.toggled.connect(self.schedule)
        targets = self._widget(TARGETS_KEY)
        if targets is not None:
            targets.toggled.connect(self.schedule)
        self._connected = True
        return True

    def _widget(self, name: str) -> Any:
        return getattr(self._dw, name, None)

    def schedule(self, *_args) -> None:
        if self._timer is not None and not self._refreshing:
            self._timer.start()

    # === State ===

    def _source_filtering(self) -> Optional[dict]:
        layer = getattr(self._dw, 'current_layer', None)
        try:
            layer_id = layer.id() if layer is not None else None
        except RuntimeError:
            return None
        props = (getattr(self._dw, 'PROJECT_LAYERS', None) or {}).get(layer_id)
        return props.setdefault('filtering', {}) if isinstance(props, dict) else None

    def _source_is_vector(self) -> bool:
        layer = getattr(self._dw, 'current_layer', None)
        try:
            from qgis.core import QgsVectorLayer
            return isinstance(layer, QgsVectorLayer)
        except ImportError:  # pragma: no cover
            return layer is not None

    def centroid_ids(self) -> Optional[List[str]]:
        """Targets tested by their centroids (None before the list exists: the task keeps the global flag)."""
        combo = self._widget(COMBO)
        if combo is None or not hasattr(combo, 'centroid_layer_ids'):
            return None
        return combo.centroid_layer_ids() if self._source_is_vector() else []

    def apply_stored(self) -> None:
        """The list of targets was filled: turn on the toggles stored for the source layer."""
        combo = self._widget(COMBO)
        if combo is None:
            return
        filtering = self._source_filtering()
        ids = initial_centroid_layers(filtering, combo.centroid_eligible_ids()) if self._source_is_vector() else []
        combo.set_centroid_layer_ids(ids)
        self.refresh()

    def set_all(self, enabled: bool) -> None:
        """Every checked line / polygon target uses its centroids (or none does)."""
        combo = self._widget(COMBO)
        if combo is None:
            return
        checked = set(combo.centroid_eligible_ids(checked_only=True))
        current = set(combo.centroid_layer_ids())
        combo.set_centroid_layer_ids(sorted(current | checked) if enabled else sorted(current - checked))
        self._store()
        self.refresh()

    def _on_toggles_changed(self, _ids=None) -> None:
        self._store()
        self.refresh()

    def _on_button_clicked(self, *_args) -> None:
        button = self._widget(BUTTON)
        if button is None:
            return
        self.set_all(button.checkState() == Qt.CheckState.Checked)

    def _store(self) -> None:
        """Save the toggles in the source layer properties (and the variables of a vector source)."""
        filtering, combo = self._source_filtering(), self._widget(COMBO)
        if filtering is None or combo is None or not self._source_is_vector():
            return
        filtering[CENTROID_LAYERS_KEY] = combo.centroid_layer_ids()
        filtering[LEGACY_FLAG_KEY] = global_centroid_state(
            combo.centroid_eligible_ids(checked_only=True), filtering[CENTROID_LAYERS_KEY]) is True
        setter = getattr(self._dw, 'setLayerVariableEvent', None)
        if setter is not None:
            try:
                setter(self._dw.current_layer, [('filtering', CENTROID_LAYERS_KEY), ('filtering', LEGACY_FLAG_KEY)])
            except Exception as exc:
                logger.debug(f"centroid targets not saved: {exc}")

    def refresh(self) -> None:
        """Show on the button what the toggles of the checked targets say."""
        combo, button = self._widget(COMBO), self._widget(BUTTON)
        if combo is None or button is None or self._refreshing:
            return
        targets = self._widget(TARGETS_KEY)
        listing = targets is None or targets.isChecked()
        checked = combo.centroid_eligible_ids(checked_only=True) if listing and self._source_is_vector() else []
        state = global_centroid_state(checked, combo.centroid_layer_ids())
        self._refreshing = True
        try:
            button.blockSignals(True)
            button.setTristate(state is None)  # a click on a partial button checks every target
            button.setCheckState(Qt.CheckState.PartiallyChecked if state is None
                                 else Qt.CheckState.Checked if state else Qt.CheckState.Unchecked)
            button.blockSignals(False)
            button.setEnabled(bool(checked))
            button.setToolTip(self.tr(
                "Test the checked line and polygon targets by their centroids (point on surface): faster on "
                "large geometries. Each target has its own square in the list") if checked else self.tr(
                "Centroids apply to line and polygon targets: check one in the list of layers to filter"))
            button.update()
        finally:
            self._refreshing = False
