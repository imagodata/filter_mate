# -*- coding: utf-8 -*-
"""Geometry for hosts other than QGIS: ``IGeometry`` implemented with shapely.

shapely (and pyproj, for reprojection) are optional: the modules import
without them, and the functions that need them raise ``RuntimeError``.
"""
from .shapely_geometry import (  # noqa: F401
    PYPROJ_AVAILABLE,
    SHAPELY_AVAILABLE,
    ShapelyGeometry,
    matches,
    normalize_predicate,
    source_union,
)

__all__ = [
    'PYPROJ_AVAILABLE',
    'SHAPELY_AVAILABLE',
    'ShapelyGeometry',
    'matches',
    'normalize_predicate',
    'source_union',
]
