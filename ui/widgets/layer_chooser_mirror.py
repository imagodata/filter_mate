# -*- coding: utf-8 -*-
"""A second chooser of the current layer, for EXPLORING away from FILTERING.

The current layer is chosen in FILTERING (``comboBox_filtering_current_layer``). When EXPLORING and FILTERING are no
longer in the same panel (one of them is in its own panel of QGIS, ui/layout/section_panels.py), EXPLORING shows
this chooser at its top: the same list, the same choice. It is a second view of the list of the first chooser (its
model), so the layers offered, their order and their icons are never two things to keep in step; only the choice
is carried from one to the other. It shows each layer as that list does, with its CRS (the first chooser, made
editable to find a layer by typing, shows the name alone once the list is closed).

The first chooser is often set with its signals blocked (after a filter, an undo, a project that closes): what it
shows is read again a few times a second while this one is in view, on top of the signals that do come.
"""
from __future__ import annotations

from typing import Any, Optional

FOLLOW_MS = 400  # how often what the first chooser shows is read again, while this one is in view
NAME = "comboBox_exploring_current_layer"


def next_index(shown: int, source: int, list_open: bool) -> Optional[int]:
    """The row this chooser must show to follow the first one, None when it already does, or while its list is
    open (the user is choosing: the row under the pointer must not move)."""
    if list_open or shown == source:
        return None
    return source


def _mirror_class():
    from qgis.PyQt.QtCore import QTimer
    from qgis.PyQt.QtWidgets import QComboBox, QSizePolicy

    class LayerChooserMirror(QComboBox):
        """The chooser of the current layer again, tied to ``source`` (the one of FILTERING)."""

        def __init__(self, source: Any, parent: Any = None) -> None:
            super().__init__(parent)
            self._source = source
            self.setObjectName(NAME)
            self.setModel(source.model())  # one list for both: what QGIS lists, filtered as the first chooser is
            self.setIconSize(source.iconSize())
            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            self.setToolTip(source.toolTip())
            self.activated.connect(self._choose)  # a choice of the user only, never a row set by code
            source.currentIndexChanged.connect(self.follow)
            self._timer = QTimer(self)
            self._timer.setInterval(FOLLOW_MS)
            self._timer.timeout.connect(self.follow)
            self.follow()

        def follow(self, *_args: Any) -> None:
            """Show what the first chooser shows."""
            try:
                index = next_index(self.currentIndex(), self._source.currentIndex(), self.view().isVisible())
            except RuntimeError:  # the first chooser went away with the dock
                self._timer.stop()
                return
            if index is None:
                return
            blocked = self.blockSignals(True)
            try:
                self.setCurrentIndex(index)
            finally:
                self.blockSignals(blocked)

        def _choose(self, index: int) -> None:
            """The user picked a layer here: the first chooser takes it as a choice made in its own list, and the
            dock follows as it always does. Its row set by code would not do: QgsMapLayerComboBox says
            ``layerChanged``, which the dock follows, for a choice of the user and for ``setLayer`` only."""
            try:
                source = self._source
                if index == source.currentIndex():
                    return
                layer = source.layer(index) if hasattr(source, "layer") else None
                if layer is not None and hasattr(source, "setLayer"):
                    source.setLayer(layer)
                else:
                    source.setCurrentIndex(index)
                    source.activated.emit(index)
            except RuntimeError:  # the first chooser went away with the dock
                pass

        def showEvent(self, event: Any) -> None:  # noqa: N802 - Qt name
            super().showEvent(event)
            self._fit_to_source()
            self.follow()
            self._timer.start()

        def hideEvent(self, event: Any) -> None:  # noqa: N802 - Qt name
            super().hideEvent(event)
            self._timer.stop()

        def _fit_to_source(self) -> None:
            """The height the display profile gave the first chooser (compact, normal, large)."""
            try:
                height = self._source.height() if self._source.isVisible() else self._source.sizeHint().height()
                low, high = self._source.minimumHeight(), self._source.maximumHeight()
                if low > 0:
                    self.setMinimumHeight(low)
                if 0 < high < 16777215:
                    self.setMaximumHeight(high)
                elif height > 0:
                    self.setMinimumHeight(min(height, self.maximumHeight()))
            except RuntimeError:
                pass

    return LayerChooserMirror


def make_mirror(source: Any, parent: Any = None) -> Any:
    """A chooser tied to ``source`` (the class is made once, when Qt is there)."""
    global _CLASS
    if _CLASS is None:
        _CLASS = _mirror_class()
    return _CLASS(source, parent)


_CLASS: Any = None
