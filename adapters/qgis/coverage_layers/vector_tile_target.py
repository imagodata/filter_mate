# -*- coding: utf-8 -*-
"""Spatial display filtering of vector tiles, prepared without reading tiles."""
import time

from ....core.domain.cross_filter import CoverageSide, predicate_methods
from ....core.domain.layer_kind import LayerKind
from ....core.filter.pk_formatter import qgis_string_literal
from .target_appliers import TargetJob, translate
from .vector_tile_filters import apply_filter, bounded_wkt, style_xml


class VectorTileTargetJob(TargetJob):
    """Keep tile fragments intersecting the selected area (Disjoint keeps the others)."""

    kind = LayerKind.VECTOR_TILE

    def __init__(self, layer, operator):
        super().__init__(layer, operator)
        self.expression = ''

    def compute(self, source_geometry, source_crs, context, request, is_canceled):
        started = time.perf_counter()
        if is_canceled():
            return
        if request.coverage_min:
            self.outcome.message = translate('VectorTileFilter', 'Minimum coverage is unavailable for clipped tile objects')
            return
        if any(method not in ('intersects', 'disjoint') for method in predicate_methods(request.predicates)):
            self.outcome.message = translate('VectorTileFilter', 'Vector tile targets support Intersect and Disjoint only')
            return
        if not self.crs.authid():
            self.outcome.message = translate('VectorTileFilter', 'Vector tile filtering requires a CRS authority code')
            return
        geometry = self._target_geometry(source_geometry, source_crs, context)
        if request.side is CoverageSide.ALL:
            self.expression = 'TRUE'
        elif geometry.isEmpty():
            self.expression = 'TRUE' if request.side is CoverageSide.OUTSIDE else 'FALSE'
        else:
            wkt = qgis_string_literal(bounded_wkt(geometry))
            crs = qgis_string_literal(self.crs.authid() or self.crs.toWkt())
            # The MVT decoder transforms feature geometries to the map CRS.
            # The map can change CRS after filtering, so transform at render time.
            selected = f"transform(geom_from_wkt({wkt}), {crs}, coalesce(nullif(@map_crs, ''), {crs}))"
            self.expression = f'intersects($geometry, {selected})'
            if request.side is CoverageSide.OUTSIDE:
                self.expression = f'NOT ({self.expression})'
        self.outcome.success = True
        self.outcome.emptied = self.expression == 'FALSE' and (self.operator or '').upper() not in ('OR', 'AND NOT')
        self.outcome.elapsed = time.perf_counter() - started
        self.outcome.message = translate('VectorTileFilter',
                                        'Vector tile display filter: attributes depend on zoom; objects split across tiles may differ')

    def apply(self, layer):
        if not self.outcome.success:
            return None
        if style_xml(layer) != self.before.renderer_xml:
            raise RuntimeError(translate('VectorTileFilter', 'The vector tile style changed while the filter was running; try again'))
        return apply_filter(layer, self.expression, self.operator)
