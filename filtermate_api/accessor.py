"""
FilterMate accessor — Protocol + in-memory stub.

The HTTP API needs to read layer state and apply filters, but it must run
without QGIS in the loop (standalone tests, headless deployments). This
module defines the seam between the FastAPI routes and "the FilterMate
plugin running inside QGIS":

* :class:`FilterMateAccessor` — a Protocol that captures the operations the
  REST endpoints need. The QGIS plugin can implement it by delegating to
  ``FilterMatePublicAPI``; tests inject :class:`InMemoryAccessor` instead.

The dependency-injection seam is wired in ``server.create_app`` so a test
can do::

    app = create_app(accessor=InMemoryAccessor(layers=[...]))
    client = TestClient(app)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Protocol, runtime_checkable


class FavoritesUnavailable(RuntimeError):
    """Raised when the favorites store is not (yet) ready to serve.

    P1-API-HARDEN (audit 2026-04-29): the QGIS-side FavoritesService
    can be missing entirely (plugin still booting, project not loaded
    yet, persistence layer offline) or raise ``FavoritesNotInitialized``
    on access. Routers translate this to ``503 Service Unavailable``
    with a ``Retry-After`` hint so callers don't get a silent ``[]``
    that misleads them into "no favorites configured".
    """


@dataclass(frozen=True)
class LayerSummary:
    """Lightweight projection of a QGIS layer for API consumers.

    Mirrors the subset of LayerInfo that REST clients care about — kept
    intentionally small so the response payload stays predictable across
    schema migrations.
    """
    layer_id: str
    name: str
    provider_type: str
    feature_count: int = -1
    geometry_type: str = ""
    crs_authid: str = ""
    has_active_filter: bool = False
    active_filter_expression: str = ""


@dataclass(frozen=True)
class HistoryStep:
    """One entry in the undo/redo stack — what an undo/redo response carries.

    Issue #33. Not the full HistoryService entry shape — clients only
    need to know *which* layer is now in *which* state.
    """
    layer_name: str
    expression: str  # "" when the step is "filter cleared"
    is_clear: bool = False


@dataclass(frozen=True)
class Favorite:
    """Stored filter preset surfaced to API consumers (issue #32)."""
    favorite_id: str
    name: str
    description: str = ""
    layer_name: str = ""
    expression: str = ""


@dataclass(frozen=True)
class FilterStatus:
    """Snapshot of the FilterMate session's filter state.

    Issue #31. The current PublicAPI is synchronous (apply returns when
    the filter is materialized) so ``status`` is always ``"idle"`` or
    ``"completed"``. The async ``"pending"`` / ``"running"`` states are
    reserved for the future task-based variant — keeping them in the
    enum stops a contract change when async lands.
    """
    status: str  # "idle" | "completed" | "pending" | "running" | "error"
    active_filters: Dict[str, str] = field(default_factory=dict)
    active_filters_count: int = 0
    last_applied_at: Optional[str] = None  # ISO-8601 UTC, None when idle
    last_applied_layer: Optional[str] = None
    last_applied_source: Optional[str] = None
    last_error: Optional[str] = None


@runtime_checkable
class FilterMateAccessor(Protocol):
    """The contract REST routes use to talk to the running FilterMate plugin."""

    def list_layers(self) -> List[LayerSummary]:
        """Return all vector layers visible to the current FilterMate session."""
        ...

    def apply_filter(self, layer_name: str, expression: str, source: str) -> bool:
        """Apply ``expression`` to ``layer_name``. Returns success."""
        ...

    def get_active_filters(self) -> Dict[str, str]:
        """Return ``{layer_name: expression}`` for layers with active filters."""
        ...

    def get_filter_status(self) -> FilterStatus:
        """Return a snapshot of the session's current filter state."""
        ...

    def undo_filter(self) -> Optional[HistoryStep]:
        """Pop the last filter from the history stack. Returns the restored
        step (the state we just rolled back TO), or ``None`` when there is
        nothing to undo — the route maps that to a 409.
        """
        ...

    def redo_filter(self) -> Optional[HistoryStep]:
        """Re-apply the most recently undone step. ``None`` when the redo
        stack is empty.
        """
        ...

    def list_favorites(self) -> List[Favorite]:
        """Return the favorites known to the FilterMate session."""
        ...

    def apply_favorite(self, favorite_id: str) -> Optional[HistoryStep]:
        """Apply the favorite identified by ``favorite_id``. Returns the
        resulting step, or ``None`` when the id doesn't resolve.
        """
        ...


@dataclass
class InMemoryAccessor:
    """Test-only accessor backed by an in-memory layer list.

    Keeps a side-table of active filters + a tiny undo/redo history so
    apply/undo/redo behave consistently across requests in a single test.
    """
    layers: List[LayerSummary] = field(default_factory=list)
    favorites: List[Favorite] = field(default_factory=list)
    _active: Dict[str, str] = field(default_factory=dict)
    _last_applied_at: Optional[str] = None
    _last_applied_layer: Optional[str] = None
    _last_applied_source: Optional[str] = None
    # Stacks of HistoryStep — _undo_stack stores past states (newest first),
    # _redo_stack stores undone steps available for redo.
    _undo_stack: List[HistoryStep] = field(default_factory=list)
    _redo_stack: List[HistoryStep] = field(default_factory=list)

    def list_layers(self) -> List[LayerSummary]:
        return [self._with_active(layer) for layer in self.layers]

    def apply_filter(self, layer_name: str, expression: str, source: str) -> bool:
        if not any(layer.name == layer_name for layer in self.layers):
            return False
        # Capture the previous state for undo BEFORE we overwrite it.
        previous = self._active.get(layer_name, "")
        self._undo_stack.append(
            HistoryStep(layer_name=layer_name, expression=previous, is_clear=not previous)
        )
        # A user-driven action invalidates the redo branch.
        self._redo_stack.clear()

        self._active[layer_name] = expression
        self._last_applied_at = datetime.now(timezone.utc).isoformat()
        self._last_applied_layer = layer_name
        self._last_applied_source = source
        return True

    def get_active_filters(self) -> Dict[str, str]:
        return dict(self._active)

    def get_filter_status(self) -> FilterStatus:
        active = self.get_active_filters()
        return FilterStatus(
            status="completed" if active else "idle",
            active_filters=active,
            active_filters_count=len(active),
            last_applied_at=self._last_applied_at,
            last_applied_layer=self._last_applied_layer,
            last_applied_source=self._last_applied_source,
        )

    def undo_filter(self) -> Optional[HistoryStep]:
        if not self._undo_stack:
            return None
        prev = self._undo_stack.pop()
        # Push the CURRENT state onto the redo stack so we can re-apply it later.
        current_expr = self._active.get(prev.layer_name, "")
        self._redo_stack.append(
            HistoryStep(layer_name=prev.layer_name, expression=current_expr,
                        is_clear=not current_expr)
        )
        # Restore the previous state (clear the active filter when prev.is_clear).
        if prev.is_clear:
            self._active.pop(prev.layer_name, None)
        else:
            self._active[prev.layer_name] = prev.expression
        return prev

    def redo_filter(self) -> Optional[HistoryStep]:
        if not self._redo_stack:
            return None
        nxt = self._redo_stack.pop()
        # Push the current state onto the undo stack to keep both directions consistent.
        current_expr = self._active.get(nxt.layer_name, "")
        self._undo_stack.append(
            HistoryStep(layer_name=nxt.layer_name, expression=current_expr,
                        is_clear=not current_expr)
        )
        if nxt.is_clear:
            self._active.pop(nxt.layer_name, None)
        else:
            self._active[nxt.layer_name] = nxt.expression
        return nxt

    def list_favorites(self) -> List[Favorite]:
        return list(self.favorites)

    def apply_favorite(self, favorite_id: str) -> Optional[HistoryStep]:
        fav = next((f for f in self.favorites if f.favorite_id == favorite_id), None)
        if fav is None or not fav.layer_name:
            return None
        applied = self.apply_filter(
            layer_name=fav.layer_name,
            expression=fav.expression,
            source=f"favorite:{favorite_id}",
        )
        if not applied:
            return None
        return HistoryStep(layer_name=fav.layer_name, expression=fav.expression)

    def _with_active(self, layer: LayerSummary) -> LayerSummary:
        expr = self._active.get(layer.name, layer.active_filter_expression)
        if not expr:
            return layer
        return LayerSummary(
            layer_id=layer.layer_id,
            name=layer.name,
            provider_type=layer.provider_type,
            feature_count=layer.feature_count,
            geometry_type=layer.geometry_type,
            crs_authid=layer.crs_authid,
            has_active_filter=True,
            active_filter_expression=expr,
        )
