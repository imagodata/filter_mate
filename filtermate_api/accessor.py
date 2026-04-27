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
from typing import Dict, List, Protocol, runtime_checkable


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


@dataclass
class InMemoryAccessor:
    """Test-only accessor backed by an in-memory layer list.

    Keeps a side-table of active filters so apply/get behave consistently
    across requests in a single test.
    """
    layers: List[LayerSummary] = field(default_factory=list)
    _active: Dict[str, str] = field(default_factory=dict)

    def list_layers(self) -> List[LayerSummary]:
        return [self._with_active(layer) for layer in self.layers]

    def apply_filter(self, layer_name: str, expression: str, source: str) -> bool:
        if not any(layer.name == layer_name for layer in self.layers):
            return False
        self._active[layer_name] = expression
        return True

    def get_active_filters(self) -> Dict[str, str]:
        return dict(self._active)

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
