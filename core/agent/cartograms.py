# -*- coding: utf-8 -*-
"""Cartograms: maps whose areas show a number instead of the land, for make_cartogram.

Plain Python and numpy (QGIS ships it from 3.22). The geometries come as rings of coordinates in a projected CRS
(metres): a feature is ``{"parts": [[ring, hole, ...], ...], "value": number}``, a ring an ``(n, 2)`` array whose
last point repeats the first.

- ``contiguous``: the polygons stay joined; each one grows or shrinks towards the area its value asks for. The
  algorithm of Dougenik, Chrisman and Niemeyer (1985): at each iteration every vertex is pushed by every polygon,
  away from its centroid when the polygon must grow, towards it when it must shrink. The push depends on where the
  vertex is, never on the polygon it belongs to: a vertex two polygons share moves the same in both, and the
  borders stay borders.
- ``noncontiguous`` (Olson): each polygon scaled around its centroid, its shape kept; the densest keeps its size.
- ``dorling``: a circle per feature, its area the value, moved apart from its neighbours until none overlap,
  pulled back towards where the feature is.
- ``demers``: the same with squares.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence, Tuple

KINDS = ("contiguous", "noncontiguous", "dorling", "demers")
MAX_ITERATIONS = 30
DEFAULT_ITERATIONS = 8
MAX_WORK = 120_000_000  # polygons x vertices x iterations of a contiguous cartogram, on the main thread
MAX_SYMBOLS = 2000  # circles or squares: the pairs are compared at each step
SYMBOL_STEPS = 120
SYMBOL_SHARE = 0.5  # of the area of the layer covered by the circles or squares
MAX_SYMBOL_WORK = 40_000_000  # pairs compared x steps: 2,000 symbols get 10 steps, 600 the 120 (2026-11-22, review)


class CartogramError(ValueError):
    """A cartogram that cannot be made: the words are for the model."""


def _np():
    import numpy  # QGIS ships it; imported when a cartogram is made only
    return numpy


def ring_area(ring) -> float:
    """Signed area of a ring (shoelace), from a local origin: large projected coordinates cancel otherwise
    (audit of 2026-11-24: the centroid of a mini-square at Lambert-93 came out kilometres away)."""
    x, y = ring[:, 0], ring[:, 1]
    if len(x) == 0:
        return 0.0
    x, y = x - x[0], y - y[0]
    return 0.5 * float((x[:-1] * y[1:] - x[1:] * y[:-1]).sum())


def area(parts: Sequence[Sequence[Any]]) -> float:
    """Area of a polygon or a multipolygon: its outer rings less its holes."""
    total = 0.0
    for polygon in parts:
        if not polygon:
            continue
        total += abs(ring_area(polygon[0])) - sum(abs(ring_area(hole)) for hole in polygon[1:])
    return max(total, 0.0)


def centroid(parts: Sequence[Sequence[Any]]) -> Tuple[float, float]:
    """The centroid of a polygon or a multipolygon, weighted by area: each ring its own centroid and its area,
    positive for an outer ring, negative for a hole (the mean of its points when it has no area)."""
    sum_x = sum_y = sum_a = 0.0
    for polygon in parts:
        for index, ring in enumerate(polygon):
            x, y = ring[:, 0], ring[:, 1]
            if len(x) == 0:
                continue
            ox, oy = x[0], y[0]  # local origin: the centroid is translation-equivariant, the cancellation is not
            x, y = x - ox, y - oy
            cross = x[:-1] * y[1:] - x[1:] * y[:-1]
            signed = 0.5 * float(cross.sum())
            if abs(signed) < 1e-12:
                continue
            ring_x = float(((x[:-1] + x[1:]) * cross).sum()) / (6.0 * signed) + ox  # whatever the winding
            ring_y = float(((y[:-1] + y[1:]) * cross).sum()) / (6.0 * signed) + oy
            weight = abs(signed) if index == 0 else -abs(signed)
            sum_x += weight * ring_x
            sum_y += weight * ring_y
            sum_a += weight
    if abs(sum_a) < 1e-12:
        points = [ring for polygon in parts for ring in polygon]
        if not points:
            return 0.0, 0.0
        stacked = _np().vstack(points)
        return float(stacked[:, 0].mean()), float(stacked[:, 1].mean())
    return sum_x / sum_a, sum_y / sum_a


def _values(features: Sequence[Dict[str, Any]]) -> List[float]:
    values = []
    for feature in features:
        value = feature.get("value")
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            values.append(None)
        elif value < 0:
            raise CartogramError("a cartogram shows quantities: the field has negative values")
        else:
            values.append(float(value))
    known = [value for value in values if value is not None]
    if not known or sum(known) <= 0:
        raise CartogramError("the field gives no positive value to show")
    return [value if value is not None else 0.0 for value in values]


def errors(features: Sequence[Dict[str, Any]]) -> float:
    """The mean of max(area, wanted) / min(area, wanted): 1 when every area shows its value exactly."""
    values = _values(features)
    areas = [area(feature["parts"]) for feature in features]
    total_area, total_value = sum(areas), sum(values)
    ratios = []
    for current, value in zip(areas, values):
        wanted = value / total_value * total_area
        small, large = sorted((max(current, 1e-9), max(wanted, 1e-9)))
        ratios.append(large / small)
    return sum(ratios) / len(ratios)


def contiguous(features: Sequence[Dict[str, Any]], iterations: int = DEFAULT_ITERATIONS,
               is_canceled=None) -> Tuple[List[Dict[str, Any]], List[float]]:
    """The features with their rings moved, and the mean error after each iteration (the first is before any).

    ``is_canceled``: called before each iteration (a long run on the main thread cannot be stopped otherwise:
    audit of 2026-11-24, 7.2 s without cancellation)."""
    np = _np()
    values = _values(features)
    if not 1 <= iterations <= MAX_ITERATIONS:
        raise CartogramError(f"iterations goes from 1 to {MAX_ITERATIONS}")
    rings, owners = [], []
    for index, feature in enumerate(features):
        for polygon in feature["parts"]:
            for ring in polygon:
                rings.append(np.asarray(ring, dtype=float))
                owners.append(index)
    if not rings:
        raise CartogramError("the layer has no polygon to deform")
    vertices = sum(len(ring) for ring in rings)
    if len(features) * vertices * iterations > MAX_WORK:
        raise CartogramError(f"{len(features)} polygons of {vertices} vertices are too many for this: simplify the "
                             "layer, filter it, or fewer iterations")
    cuts = np.cumsum([len(ring) for ring in rings])[:-1]
    points = np.vstack(rings)
    total_value = sum(values)
    history = []

    def shaped() -> List[Dict[str, Any]]:
        pieces = np.split(points, cuts)
        made, cursor = [], 0
        for index, feature in enumerate(features):
            parts = []
            for polygon in feature["parts"]:
                parts.append([pieces[cursor + offset] for offset in range(len(polygon))])
                cursor += len(polygon)
            made.append(dict(feature, parts=parts))
        return made

    for _ in range(iterations):
        if is_canceled is not None and is_canceled():
            raise CartogramError("the cartogram was canceled")
        current = shaped()
        areas = np.array([area(feature["parts"]) for feature in current])
        centres = np.array([centroid(feature["parts"]) for feature in current])
        total_area = float(areas.sum())
        wanted = np.array(values) / total_value * total_area
        safe_areas, safe_wanted = np.maximum(areas, 1e-9), np.maximum(wanted, 1e-9)
        ratio = np.maximum(safe_areas, safe_wanted) / np.minimum(safe_areas, safe_wanted)
        history.append(float(ratio.mean()))
        # A polygon showing nothing (value 0 or missing) shrinks away, but its wanted area of 0 makes its ratio
        # astronomical: in the mean it froze every step to ~0 and nothing moved (audit of 2026-11-24). Only the
        # polygons showing something drive the step size.
        showing = wanted > 0
        reduction = 1.0 / (1.0 + (float(ratio[showing].mean()) if showing.any() else 0.0))
        radius = np.sqrt(safe_areas / math.pi)
        mass = np.sqrt(safe_wanted / math.pi) - radius
        shift = np.zeros_like(points)
        for index in range(len(current)):
            offset = points - centres[index]
            distance = np.hypot(offset[:, 0], offset[:, 1])
            far = distance > radius[index]
            ratio_d = distance / radius[index]
            force = np.where(far, mass[index] * radius[index] / np.maximum(distance, 1e-12),
                             mass[index] * ratio_d * ratio_d * (4.0 - 3.0 * ratio_d))
            moving = distance > 1e-12
            shift[moving] += (offset[moving] / distance[moving, None]) * (force[moving, None] * reduction)
        points = points + shift
    result = shaped()
    history.append(errors(result))
    return result, history


def noncontiguous(features: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Each polygon scaled around its centroid so that its area shows its value; the densest keeps its size."""
    values = _values(features)
    areas = [area(feature["parts"]) for feature in features]
    densities = [value / current if current > 0 else 0.0 for value, current in zip(values, areas)]
    densest = max(densities)
    if densest <= 0:
        raise CartogramError("the polygons have no area")
    made = []
    for feature, density in zip(features, densities):
        factor = math.sqrt(density / densest)
        cx, cy = centroid(feature["parts"])
        parts = [[(ring - (cx, cy)) * factor + (cx, cy) for ring in polygon] for polygon in feature["parts"]]
        made.append(dict(feature, parts=parts))
    return made


def symbols(features: Sequence[Dict[str, Any]], squares: bool = False, steps: int = SYMBOL_STEPS,
            total_area: Optional[float] = None, is_canceled=None) -> List[Tuple[float, float, float]]:
    """``(x, y, size)`` per feature: a circle (size its radius) or a square (size half its side) whose area is its
    value, moved apart until none overlap and pulled back towards its feature. ``total_area``: what the symbols
    share (``SYMBOL_SHARE`` of it); the area of the polygons by default, the extent of points for points.
    ``is_canceled``: called before each step, as in :func:`contiguous`."""
    np = _np()
    values = np.array(_values(features))
    if len(features) > MAX_SYMBOLS:
        raise CartogramError(f"{len(features)} features: {MAX_SYMBOLS} at most for circles or squares, filter first")
    areas = [area(feature["parts"]) for feature in features]
    centres = np.array([centroid(feature["parts"]) for feature in features], dtype=float)
    total_area = total_area if total_area and total_area > 0 else (sum(areas) or 1.0)
    steps = max(5, min(steps, int(MAX_SYMBOL_WORK / max(1, len(features)) ** 2)))
    scale = math.sqrt(SYMBOL_SHARE * total_area / float(values.sum()))
    sizes = np.sqrt(values) * scale / (1.0 if squares else math.sqrt(math.pi))
    if squares:
        sizes = sizes / 2.0  # half the side
    positions = centres.copy()
    count = len(features)
    if count > 1:
        for _ in range(steps):
            if is_canceled is not None and is_canceled():
                raise CartogramError("the cartogram was canceled")
            delta = positions[:, None, :] - positions[None, :, :]
            reach = sizes[:, None] + sizes[None, :]
            np.fill_diagonal(reach, 0.0)
            if squares:
                overlap_x = reach - np.abs(delta[:, :, 0])
                overlap_y = reach - np.abs(delta[:, :, 1])
                touching = (overlap_x > 0) & (overlap_y > 0)
                along_x = touching & (overlap_x <= overlap_y)
                along_y = touching & ~along_x
                push = np.zeros_like(delta)
                push[:, :, 0] = np.where(along_x, np.sign(delta[:, :, 0] + 1e-12) * overlap_x / 2.0, 0.0)
                push[:, :, 1] = np.where(along_y, np.sign(delta[:, :, 1] + 1e-12) * overlap_y / 2.0, 0.0)
            else:
                distance = np.hypot(delta[:, :, 0], delta[:, :, 1])
                overlap = reach - distance
                touching = (overlap > 0) & (distance > 0)
                unit = np.where(touching[:, :, None], delta / np.maximum(distance, 1e-12)[:, :, None], 0.0)
                push = unit * (np.where(touching, overlap, 0.0) / 2.0)[:, :, None]
            moved = push.sum(axis=1)
            positions = positions + moved + 0.02 * (centres - positions)
            if not touching.any():
                break
    return [(float(x), float(y), float(size)) for (x, y), size in zip(positions, sizes)]


def symbol_ring(x: float, y: float, size: float, squares: bool, sides: int = 48):
    """The outline of a circle or a square, closed."""
    np = _np()
    if squares:
        return np.array([(x - size, y - size), (x + size, y - size), (x + size, y + size), (x - size, y + size),
                         (x - size, y - size)])
    angles = np.linspace(0.0, 2.0 * math.pi, sides + 1)
    return np.column_stack((x + size * np.cos(angles), y + size * np.sin(angles)))
