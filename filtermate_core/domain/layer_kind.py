# -*- coding: utf-8 -*-
"""
Layer kind - the three layer families FilterMate 5 can explore and filter.

The kind drives which EXPLORING panel is shown, how a selection becomes a
source geometry and how a target layer applies a spatial relation.

This is a PURE PYTHON module with NO QGIS dependencies.
"""
from enum import Enum


class LayerKind(Enum):
    """Family of a map layer, as far as FilterMate is concerned."""

    VECTOR = "vector"
    RASTER = "raster"
    POINT_CLOUD = "point_cloud"
    VECTOR_TILE = "vector_tile"
    OTHER = "other"

    @property
    def is_vector(self) -> bool:
        """True for vector layers (the historical FilterMate path)."""
        return self is LayerKind.VECTOR

    @property
    def is_coverage(self) -> bool:
        """True for raster and point cloud layers (no features, no subset of features)."""
        return self in (LayerKind.RASTER, LayerKind.POINT_CLOUD)

    @property
    def is_filter_target(self) -> bool:
        """Kinds handled by the cross filter engine, including target-only tiles."""
        return self.is_coverage or self is LayerKind.VECTOR_TILE


def kind_label(kind: LayerKind) -> str:
    """Return the English display label of a kind (translated by the UI)."""
    return {
        LayerKind.VECTOR: "Vector",
        LayerKind.RASTER: "Raster",
        LayerKind.POINT_CLOUD: "Point cloud",
        LayerKind.VECTOR_TILE: "Vector tiles",
    }.get(kind, "Other")
