# -*- coding: utf-8 -*-
"""Typed contract between ``FavoritesSpatialHandler`` and the dockwidget.

F4 step 3 — XCUT-3 close-out (2026-04-29). The original step-3 memo
proposed a ``DockwidgetSurface`` Protocol but the implementation skipped
it; the handler reaches into ``self._controller.dockwidget`` and reads
~10 widget/state attributes directly, with no static contract. That's
code displacement, not seam-extraction: headless tests still need
``MagicMock`` because nothing tells them which attributes the handler
actually touches.

This module pins the contract. It does **not** change runtime behaviour
— the handler still pulls the dockwidget from its controller — but it
documents the surface, lets ``mypy`` catch missing attributes when the
handler grows, and gives tests a typed double to aim for instead of
``MagicMock(spec=...)`` against a 4000-line widget.

Qt widgets remain typed as ``Any`` on purpose: pinning them to
``QgsDoubleSpinBox`` etc. would force tests to instantiate real Qt
widgets just to satisfy the Protocol. The honest contract is "an
opaque handle the handler will ``.value()`` / ``.setValue()``".
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Protocol, Set, Tuple


class DockwidgetSurface(Protocol):
    """The slice of ``FilterMateDockWidget`` that ``FavoritesSpatialHandler``
    reads or writes. Anything outside this Protocol is out-of-bounds for
    the handler — adding a new access here is a deliberate API decision.
    """

    # State (read-only) ------------------------------------------------
    widgets_initialized: bool
    current_exploring_groupbox: Optional[str]
    current_layer: Any  # QgsVectorLayer | None
    widgets: Dict[str, Dict[str, Any]]
    PROJECT_LAYERS: Dict[str, Any]

    # Restored state cookies (read + write) ---------------------------
    _restored_task_features: Optional[Set[int]]
    _restored_predicates: Optional[Dict[str, bool]]

    # Qt widgets we mutate by reference (kept Any — Qt opaque handles)
    mQgsDoubleSpinBox_filtering_buffer_value: Any
    mQgsFieldExpressionWidget_filtering_active_expression: Any
    comboBox_filtering_current_layer: Any
    favorites_indicator_label: Any

    # Methods ---------------------------------------------------------
    def get_current_features(self) -> Tuple[Any, Any]:
        ...

    def _restore_groupbox_ui_state(self, state: str) -> None:
        ...


class FavoritesControllerSurface(Protocol):
    """The slice of ``FavoritesController`` that ``FavoritesSpatialHandler``
    reads. Lets the handler stay decoupled from controller internals.

    ``dockwidget`` is typed as ``DockwidgetSurface`` — anything else
    would let new dockwidget attributes leak into the handler silently.
    """

    dockwidget: DockwidgetSurface
    _favorites_service: Any  # FavoritesService — Any to avoid import cycle

    def _show_warning(self, message: str) -> None:
        ...

    def tr(self, source_text: str, *args: Any, **kwargs: Any) -> str:
        ...
