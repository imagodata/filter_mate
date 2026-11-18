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

import time
from typing import Any, Optional

FOLLOW_MS = 400  # how often what the first chooser shows is read again, while this one is in view
NAME = "comboBox_exploring_current_layer"


def next_index(shown: int, source: int, list_open: bool) -> Optional[int]:
    """The row this chooser must show to follow the first one, None when it already does, or while its list is
    open (the user is choosing: the row under the pointer must not move)."""
    if list_open or shown == source:
        return None
    return source


def record_user_pick(dock: Any, layer: Any) -> None:
    """Note ``layer`` as the layer the user picked, as ``ConfigurationManager._stamp_user_layer_picks`` does for the
    chooser of FILTERING: the checks that put the source layer back after a filter or an undo leave a layer picked
    since alone (``dock._user_layer_pick``), a pick made in the window that follows a filter ends it (its handler
    applies the pick), and a pick the dock did not take (the chooser's handler was disconnected: start-up
    refreshes, a task that adds layers) is applied now unless a filter runs (the one that ends the task applies it).
    """
    layer_id = layer.id()
    dock._user_layer_pick = (time.perf_counter(), layer_id)
    end_window = getattr(dock, "_end_post_filter_window", None)
    if callable(end_window):
        end_window()
        return
    current = getattr(dock, "current_layer", None)
    if (current is None or current.id() != layer_id) and not getattr(dock, "_filtering_in_progress", False):
        dock.current_layer_changed(layer, manual_change=True)


def choose(source: Any, dock: Any, index: int) -> None:
    """The user picked row ``index`` in the chooser tied to ``source``: ``source`` takes the layer, and ``dock``
    (None: nobody keeps the picks) notes it as the user's."""
    changed = index != source.currentIndex()
    if changed:
        layer = source.layer(index) if hasattr(source, "layer") else None
        if layer is not None and hasattr(source, "setLayer"):
            source.setLayer(layer)
        else:
            source.setCurrentIndex(index)
            source.activated.emit(index)
    picked = source.currentLayer() if hasattr(source, "currentLayer") else None
    if dock is None or picked is None:
        return
    current = getattr(dock, "current_layer", None)
    # The first chooser may already show the layer while the dock does not have it (its handler was
    # disconnected): picking it here is the choice that makes it current.
    if changed or current is None or current.id() != picked.id():
        record_user_pick(dock, picked)


def _mirror_class():
    from qgis.PyQt.QtCore import QTimer
    from qgis.PyQt.QtWidgets import QComboBox, QSizePolicy

    class LayerChooserMirror(QComboBox):
        """The chooser of the current layer again, tied to ``source`` (the one of FILTERING)."""

        def __init__(self, source: Any, parent: Any = None, dock: Any = None) -> None:
            super().__init__(parent)
            self._source = source
            self._dock = dock  # who keeps the layer the user picked (``record_user_pick``)
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
            ``layerChanged``, which the dock follows, for a choice of the user and for ``setLayer`` only. It is
            also noted as the user's choice (``record_user_pick``): the first chooser, which notes what is done in
            its own list, does not see this one, and the dock put the layer of the filter back over it."""
            try:
                choose(self._source, self._dock, index)
            except (RuntimeError, AttributeError):  # the first chooser went away with the dock
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


def make_mirror(source: Any, parent: Any = None, dock: Any = None) -> Any:
    """A chooser tied to ``source`` (the class is made once, when Qt is there); ``dock`` notes the picks."""
    global _CLASS
    if _CLASS is None:
        _CLASS = _mirror_class()
    return _CLASS(source, parent, dock)


_CLASS: Any = None
