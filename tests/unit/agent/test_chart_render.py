"""Python chart rendering: data geometry, readable limits, and safe SVG on both Qt generations."""
import math
import xml.etree.ElementTree as ElementTree

import pytest

from core.agent import chart_render, charts

pytestmark = pytest.mark.unit
NS = "{http://www.w3.org/2000/svg}"


def rendered(kind, rows, **arguments):
    request = charts.parse_request(dict(kind=kind, rows=rows, **arguments))
    data, meta = charts.rows_data(request, "Others", "(empty)")
    spec = charts.chart_spec(request, data, "light", x_type=meta.get("x_type", ""))
    svg, marks = chart_render.render(spec)
    return ElementTree.fromstring(charts.sanitize_svg(svg)), marks


@pytest.mark.parametrize("kind", charts.KINDS)
def test_every_standard_kind_renders_without_qt(kind):
    rows = ([{"x": 1, "y": 2}, {"x": 2, "y": 5}] if kind in ("line", "area", "scatter") else
            [{"label": "A <script> & é", "value": 2}, {"label": "B", "value": 5}])
    root, marks = rendered(kind, rows, title="A < B", width=280, height=200)
    assert root.attrib["width"] == "280" and root.attrib["height"] == "200"
    assert marks and root.find(NS + "script") is None
    for mark in marks:
        left, top, width, height = mark.box
        assert all(math.isfinite(value) for value in mark.box)
        assert 0 <= left <= left + width <= 280 and 0 <= top <= top + height <= 200


def test_kpi_limit_includes_the_remainder_and_keeps_the_aggregate():
    request = charts.parse_request({"kind": "kpi", "limit": 8,
                                    "rows": [{"label": str(index), "value": index} for index in range(12)]})
    data, meta = charts.rows_data(request, "Others", "(empty)")
    assert len(data) == meta["points"] == 8
    assert data[-1] == {"label": "Others", "value": 10.0, "others": True}
    root, marks = rendered("kpi", list(request.rows), limit=8, width=280, height=200)
    assert len(marks) == 8 and len(root.findall(NS + "rect")) == 9


def test_treemap_areas_follow_shares_without_overflowing_the_total():
    _, marks = rendered("treemap", [{"label": "A", "value": 1e308}, {"label": "B", "value": 5e307},
                                    {"label": "loss", "value": -1}])
    assert len(marks) == 2
    areas = [(mark.box[2] + 3) * (mark.box[3] + 3) for mark in marks]
    assert areas[0] / areas[1] == pytest.approx(2, rel=0.001)


@pytest.mark.parametrize("values", [[2, 5], [-5, -2], [-3, 4]])
def test_area_closes_at_zero_and_keeps_the_line(values):
    root, marks = rendered("area", [{"x": index, "y": value} for index, value in enumerate(values)])
    fills = [path for path in root.findall(NS + "path") if path.attrib.get("fill-opacity") == "0.22"]
    assert len(fills) == 1 and fills[0].attrib["d"].endswith("Z")
    assert any(mark.shape == "line" for mark in marks)
    assert sum(mark.shape == "dot" for mark in marks) == 2
    coordinates = fills[0].attrib["d"].replace("M", "").replace("L", " ").rstrip("Z").split()
    ground = float(coordinates[0].split(",")[1])
    assert float(coordinates[-1].split(",")[1]) == ground
    ys = [float(point.split(",")[1]) for point in coordinates[1:-1]]
    if min(values) > 0:
        assert ground > max(ys)
    if max(values) < 0:
        assert ground < min(ys)


def test_area_rows_honor_explicit_aggregation_and_time():
    request = charts.parse_request({"kind": "area", "aggregate": "mean",
                                    "rows": [{"x": "2026-01-01", "y": 2}, {"x": "2026-01-01", "y": 8}]})
    data, meta = charts.rows_data(request, "Others", "(empty)")
    assert data[0]["y"] == 5 and meta["x_type"] == "time"


def test_all_eight_kpi_cards_fit_at_minimum_size_and_a_single_card_groups_the_rest():
    rows = [{"label": "A very long category " + str(index), "value": 12345 + index} for index in range(20)]
    _, marks = rendered("kpi", rows, limit=8, width=280, height=200)
    assert len(marks) == 8 and max(mark.box[1] + mark.box[3] for mark in marks) <= 200
    request = charts.parse_request({"kind": "kpi", "rows": rows, "limit": 1, "aggregate": "mean"})
    data, _ = charts.rows_data(request, "Others", "(empty)")
    assert len(data) == 1 and data[0]["others"] and data[0]["value"] == pytest.approx(12354.5)
