# -*- coding: utf-8 -*-
"""The d3 charts of the agent, without QGIS: requests, data, the page and the SVG handed back (2026-11-22)."""
import math

import pytest

from core.agent import charts
from core.agent.charts import ChartError, parse_request

pytestmark = pytest.mark.unit


def test_a_request_needs_a_layer_or_rows_never_both_and_never_code():
    assert parse_request({"kind": "bar", "layer": "batiments", "field": "usage"}).layer == "batiments"
    for arguments in ({"kind": "bar"}, {"kind": "bar", "layer": "a", "field": "x", "rows": [{"label": "a"}]},
                      {"kind": "donut", "rows": [{"label": "a", "value": 1}]},
                      {"kind": "bar", "layer": "a"},
                      {"kind": "scatter", "layer": "a", "field": "x"},
                      {"kind": "bar", "rows": [{"label": "a", "value": [1]}]},
                      {"kind": "bar", "rows": [{"label": "a", "value": 1, "color": "red"}]},
                      {"kind": "bar", "rows": [{"label": "a", "value": 1}], "width": math.inf},
                      {"kind": "bar", "rows": [{"label": "a", "value": 1}], "width": True}):
        with pytest.raises(ChartError):
            parse_request(arguments)
    request = parse_request({"kind": "bar", "rows": [{"label": "a", "value": 1}], "code": "while(1){}"})
    assert "code" not in request.as_arguments()  # never a field of a request, whoever wrote the arguments


def test_categories_keep_the_largest_and_aggregate_the_rest_from_its_features():
    pairs = [("a", 1)] * 5 + [("b", 2)] * 3 + [("c", 10)] + [(None, 4)]
    count = charts.category_values(pairs, "count", 2, "value", "Others", "(empty)")
    assert count == [{"label": "a", "value": 5.0, "others": False}, {"label": "b", "value": 3.0, "others": False},
                     {"label": "Others", "value": 2.0, "others": True}]
    mean = charts.category_values(pairs, "mean", 1, "value", "Others", "(empty)")
    assert mean[0] == {"label": "c", "value": 10.0, "others": False}
    assert mean[1]["value"] == pytest.approx((5 * 1 + 3 * 2 + 4) / 9)  # of the features, not of the bars


def test_labels_that_are_numbers_sort_as_numbers():
    pairs = [("10", 1), ("2", 1), ("1", 1)]
    assert [bar["label"] for bar in charts.category_values(pairs, "count", 10, "label", "O", "E")] == ["1", "2", "10"]


def test_a_sum_beyond_a_float_is_refused_in_words():
    with pytest.raises(ChartError, match="beyond"):
        charts.category_values([("a", 1e308), ("a", 1e308)], "sum", 5, "value", "O", "E")
    request = parse_request({"kind": "bar", "rows": [{"label": "a", "value": 1e308}, {"label": "a", "value": 1e308}]})
    with pytest.raises(ChartError):
        charts.rows_data(request, "O", "E")


def test_a_long_line_is_sampled_along_its_whole_length():
    triples = [(x, float(x), "A") for x in range(3000)] + [(x, float(x), "B") for x in range(3000)]
    points, dropped = charts.line_values(triples, "sum", "number", "E", "O")
    assert dropped and len(points) == charts.MAX_LINE_POINTS
    assert {point["series"] for point in points} == {"A", "B"} and max(point["x"] for point in points) > 2900


def test_a_time_axis_takes_dates_only():
    triples = [("2024-01-01", 1, None), ("12:30:00", 2, None), ("2024-01-02T08:00:00", 3, None)]
    points, _ = charts.line_values(triples, "sum", "time", "E", "O")
    assert [point["x"] for point in points] == ["2024-01-01", "2024-01-02T08:00:00"]


def test_rows_mixing_numbers_and_dates_in_x_are_refused():
    request = parse_request({"kind": "line", "rows": [{"x": 1, "y": 1}, {"x": "2024-01-01", "y": 2}]})
    with pytest.raises(ChartError, match="either"):
        charts.rows_data(request, "O", "E")


def test_a_scatter_keeps_three_series_and_samples_evenly():
    triples = [(index, index, name) for index in range(7000) for name in ("a",)] + [(1, 1, "b"), (2, 2, "c"),
                                                                                    (3, 3, "d")]
    dots, total = charts.scatter_values(triples, "Others", "E")
    assert total == 7003 and len(dots) == charts.MAX_POINTS
    assert {dot["series"] for dot in dots} <= {"a", "b", "c", "Others"}


def test_the_page_keeps_values_as_data_and_holds_the_guard():
    request = parse_request({"kind": "bar", "rows": [{"label": "</script><script>alert(1)</script>", "value": 1}]})
    data, _ = charts.rows_data(request, "O", "E")
    page = charts.page_html(charts.chart_spec(request, data, "light"), d3_source="", templates="")
    assert "</script><script>alert" not in page and "\\u003c/script\\u003e" in page
    assert page.index("RTCPeerConnection") < page.index("FMCharts.draw")
    coded = charts.page_html(charts.chart_spec(request, data, "light"), code="x = '</script>'", d3_source="",
                             templates="")
    assert "x = '<\\/script>'" in coded
    with pytest.raises(ChartError):
        charts.page_html(charts.chart_spec(request, data, "light"), d3_source="x" * 1_500_000, templates="")


SVG = '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="10" height="10">'


def test_the_svg_keeps_shapes_and_text_only():
    svg = (SVG + '<rect width="5" height="5" fill="red" onclick="x()"/><image href="/home/me/secret.png"/>'
           '<g><image xlink:href="C:\\\\secret.png"/><text x="1" y="2">a &lt; b</text></g>'
           '<foreignObject><div>html</div></foreignObject><use href="file:///etc/x.svg#a"/>'
           '<rect fill="url(http://x/y)" stroke="url(#gradient)"/><linearGradient id="gradient"/>'
           '<path d="M0 0" style="fill:url(/x.png)"/></svg>')
    clean = charts.sanitize_svg(svg)
    for gone in ("image", "secret", "foreignObject", "onclick", "file:", "http://x", "style=", "<use"):
        assert gone not in clean, gone
    assert "a &lt; b" in clean and 'stroke="url(#gradient)"' in clean and "<rect" in clean


def test_an_svg_with_a_dtd_or_not_an_svg_is_refused():
    for text in ('<!DOCTYPE svg [<!ENTITY a "aaaa">]>' + SVG + "&a;</svg>", "<html/>", "not xml", ""):
        with pytest.raises(ChartError):
            charts.sanitize_svg(text)


def test_the_svg_is_walked_without_recursion_and_bounded():
    deep = SVG + "<g>" * 3000 + "</g>" * 3000 + "</svg>"
    with pytest.raises(ChartError, match="deep"):
        charts.sanitize_svg(deep)
    for size in ('width="1" height="10000000"', 'width="nan" height="10"', 'width="-5" height="10"'):
        with pytest.raises(ChartError):
            charts.sanitize_svg(f'<svg xmlns="http://www.w3.org/2000/svg" {size}></svg>')


def test_every_url_of_a_value_must_point_inside():
    svg = (SVG + '<rect fill="url(#a) url(file:///etc/x)"/><rect fill="URL( file:///x )"/>'
           '<rect fill="url(  #ok )"/><rect fill="url(\'#q\')"/></svg>')
    clean = charts.sanitize_svg(svg)
    assert "file:" not in clean and clean.count("fill=") == 2


def test_cleaning_leaves_elementtree_as_it_was():
    import xml.etree.ElementTree as ElementTree
    before = dict(ElementTree._namespace_map)
    charts.sanitize_svg(SVG + '<text x="1">a</text></svg>')
    assert dict(ElementTree._namespace_map) == before
    assert charts.sanitize_svg(SVG + "<rect/></svg>").startswith('<svg xmlns="http://www.w3.org/2000/svg"')


def test_a_category_called_like_the_nulls_or_the_rest_is_not_merged():
    pairs = [("(empty)", 5), (None, 7), ("Others", 3), ("b", 1)]
    bars = charts.category_values(pairs, "sum", 10, "value", "Others", "(empty)")
    by_label = {bar["label"]: bar["value"] for bar in bars}
    assert by_label["(empty)"] == 5.0 and by_label['"(empty)"'] == 7.0  # the data verbatim, the NULLs quoted
    assert by_label["Others"] == 3.0 and not any(bar["others"] for bar in bars if bar["label"] == "Others")


def test_the_rest_is_quoted_when_a_category_is_called_like_it():
    pairs = [("Others", 10), ("a", 9), ("b", 8)]
    bars = charts.category_values(pairs, "sum", 2, "value", "Others", "(empty)")
    assert bars[0]["label"] == "Others" and not bars[0]["others"]
    assert bars[-1] == {"label": '"Others"', "value": 8.0, "others": True}


def test_rows_honor_the_aggregate_of_the_request():
    rows = [{"label": "a", "value": 4}, {"label": "a", "value": 6}, {"label": "b", "value": 100}]
    summed = charts.rows_data(parse_request({"kind": "bar", "rows": rows}), "O", "E")
    assert [bar["value"] for bar in summed[0]] == [100.0, 10.0]  # the default adds the values up
    averaged = charts.rows_data(parse_request({"kind": "bar", "rows": rows, "aggregate": "mean"}), "O", "E")
    assert [bar["value"] for bar in averaged[0]] == [100.0, 5.0]
    counted = charts.rows_data(parse_request({"kind": "bar", "rows": rows, "aggregate": "count"}), "O", "E")
    assert [bar["value"] for bar in counted[0]] == [2.0, 1.0]


def test_a_pie_says_which_negative_slices_it_leaves_out():
    rows = [{"label": "a", "value": 5}, {"label": "b", "value": -2}, {"label": "c", "value": 0}]
    data, meta = charts.rows_data(parse_request({"kind": "pie", "rows": rows}), "O", "E")
    assert meta["dropped"] and "1 negative slice(s)" in meta["dropped_note"]
    assert [bar["label"] for bar in data] == ["a", "c", "b"]  # the data stays whole for the answer
    with pytest.raises(ChartError, match="no slice is above zero"):
        charts.rows_data(parse_request({"kind": "pie", "rows": [{"label": "x", "value": -1}]}), "O", "E")
