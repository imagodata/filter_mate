# -*- coding: utf-8 -*-
"""Cartograms (core/agent/cartograms.py, 2026-11-22): areas that show a number, borders kept."""
import math

import numpy as np
import pytest

from core.agent import cartograms
from core.agent.cartograms import CartogramError

pytestmark = pytest.mark.unit


def square(x, y, side=10.0, steps=4):
    """A closed square ring with ``steps`` points per side (a contiguous cartogram moves every vertex)."""
    points = []
    for (x0, y0), (x1, y1) in (((x, y), (x + side, y)), ((x + side, y), (x + side, y + side)),
                               ((x + side, y + side), (x, y + side)), ((x, y + side), (x, y))):
        for step in range(steps):
            t = step / steps
            points.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t))
    points.append(points[0])
    return np.array(points)


def grid(values):
    """A row of squares sharing their sides, one value each."""
    return [{"parts": [[square(index * 10.0, 0.0)]], "value": value} for index, value in enumerate(values)]


def test_area_and_centroid_of_a_polygon_with_a_hole():
    ring, hole = square(0, 0, 10), square(2, 2, 2)[::-1]
    assert cartograms.area([[ring, hole]]) == pytest.approx(96.0)
    x, y = cartograms.centroid([[ring]])
    assert (x, y) == pytest.approx((5.0, 5.0))
    x, _ = cartograms.centroid([[square(0, 0, 10)], [square(20, 0, 10)]])
    assert x == pytest.approx(15.0)


def test_a_contiguous_cartogram_brings_areas_towards_their_values_and_keeps_borders():
    features = grid([1.0, 1.0, 6.0, 1.0])
    made, history = cartograms.contiguous(features, iterations=10)
    assert history[-1] < history[0] and history[-1] < 1.6
    areas = [cartograms.area(feature["parts"]) for feature in made]
    assert areas[2] > 2.0 * areas[0]
    # The side the third square shares with the second moved the same in both: no gap, no overlap.
    second, third = made[1]["parts"][0][0], made[2]["parts"][0][0]
    shared_second = {tuple(np.round(point, 6)) for point in second}
    shared_third = {tuple(np.round(point, 6)) for point in third}
    assert len(shared_second & shared_third) >= 5


def test_olson_scales_each_polygon_and_keeps_the_densest():
    made = cartograms.noncontiguous(grid([4.0, 1.0]))
    assert cartograms.area(made[0]["parts"]) == pytest.approx(100.0)
    assert cartograms.area(made[1]["parts"]) == pytest.approx(25.0)
    assert cartograms.centroid(made[1]["parts"]) == pytest.approx((15.0, 5.0))


@pytest.mark.parametrize("squares", [False, True])
def test_circles_and_squares_show_the_values_and_do_not_overlap(squares):
    placed = cartograms.symbols(grid([1.0, 4.0, 1.0, 9.0]), squares=squares)
    sizes = [size for _, _, size in placed]
    assert sizes[1] == pytest.approx(2.0 * sizes[0]) and sizes[3] == pytest.approx(3.0 * sizes[0])
    total = sum((4 * size * size) if squares else (math.pi * size * size) for size in sizes)
    assert total == pytest.approx(cartograms.SYMBOL_SHARE * 400.0)
    for i, (x1, y1, s1) in enumerate(placed):
        for x2, y2, s2 in placed[i + 1:]:
            if squares:
                assert abs(x1 - x2) >= s1 + s2 - 1e-6 or abs(y1 - y2) >= s1 + s2 - 1e-6
            else:
                assert math.hypot(x1 - x2, y1 - y2) >= s1 + s2 - 1e-6


def test_what_a_cartogram_refuses():
    with pytest.raises(CartogramError, match="negative"):
        cartograms.contiguous(grid([1.0, -2.0]))
    with pytest.raises(CartogramError, match="no positive"):
        cartograms.noncontiguous(grid([0.0, 0.0]))
    with pytest.raises(CartogramError, match="iterations"):
        cartograms.contiguous(grid([1.0, 2.0]), iterations=99)
    many = [{"parts": [[square(0, 0)]], "value": 1.0}] * (cartograms.MAX_SYMBOLS + 1)
    with pytest.raises(CartogramError, match="at most"):
        cartograms.symbols(many)


def test_a_missing_value_counts_as_nothing():
    made = cartograms.noncontiguous(grid([4.0, None]))
    assert cartograms.area(made[1]["parts"]) == pytest.approx(0.0)


def test_a_canceled_contiguous_cartogram_stops():
    """Audit of 2026-11-24: a long run on the main thread could not be stopped."""
    calls = []
    with pytest.raises(CartogramError, match="canceled"):
        cartograms.contiguous(grid([1.0, 4.0]), iterations=10,
                              is_canceled=lambda: calls.append(True) or len(calls) > 2)
    assert len(calls) == 3


def test_canceled_symbols_stop():
    with pytest.raises(CartogramError, match="canceled"):
        cartograms.symbols(grid([400.0, 400.0]), is_canceled=lambda: True)


def test_a_zero_value_does_not_freeze_the_contiguous_cartogram():
    """Audit of 2026-11-24: one value at 0 or NULL and nothing moved (a vertex moved 5e-11 m, against 367 m
    with all values positive)."""
    features = grid([1.0, 0.0, 6.0, 1.0])
    made, history = cartograms.contiguous(features, iterations=8)
    before = np.vstack([ring for feature in features for polygon in feature["parts"] for ring in polygon])
    after = np.vstack([ring for feature in made for polygon in feature["parts"] for ring in polygon])
    assert float(np.abs(after - before).max()) > 1.0
    assert history[-1] < history[0]
    areas = [cartograms.area(feature["parts"]) for feature in made]
    assert areas[2] > 2.0 * areas[0]  # the big one still grows


def test_centroid_of_a_tiny_square_in_projected_coordinates():
    """Audit of 2026-11-24: on a layer of points in projected coordinates the centroid of the mini-square was
    off by kilometres (a Lambert-93 point came out 2,295 km away)."""
    big = 1_000_000.0
    ring = np.array([(big, 2 * big), (big + 1e-3, 2 * big), (big + 1e-3, 2 * big + 1e-3),
                     (big, 2 * big + 1e-3), (big, 2 * big)])
    x, y = cartograms.centroid([[ring]])
    assert (x, y) == pytest.approx((big + 5e-4, 2 * big + 5e-4), abs=1e-6)
    assert cartograms.ring_area(ring) == pytest.approx(1e-6, rel=1e-6)


def _mini_square(big, index):
    """A closed 1e-3 square, as the API builds them for points."""
    x, y = big + index, 2 * big
    return np.array([(x, y), (x + 1e-3, y), (x + 1e-3, y + 1e-3), (x, y + 1e-3), (x, y)])


def test_symbols_of_projected_points_stay_on_their_points():
    """Dorling and Demers through the same path: no circle hundreds of kilometres from its point."""
    big = 1_000_000.0
    features = [{"parts": [[_mini_square(big, index)]], "value": 1.0} for index in range(5)]
    for squares in (False, True):
        for (x, y, _), index in zip(cartograms.symbols(features, squares=squares), range(5)):
            assert math.hypot(x - (big + index), y - 2 * big) < 1.0
