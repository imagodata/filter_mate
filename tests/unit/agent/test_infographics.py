# -*- coding: utf-8 -*-
"""The infographics of the agent, without QGIS: stacking kept charts into one SVG, and its standalone page."""
import pytest

from core.agent.charts import ChartError
from core.agent.infographics import (
    MAX_PARTS,
    compose_infographic,
    infographic_page,
    parse_infographic,
    svg_size,
)

pytestmark = pytest.mark.unit

KPI = ('<svg xmlns="http://www.w3.org/2000/svg" width="640" height="140">'
       '<rect width="640" height="140" fill="#ffffff"/>'
       '<text x="12" y="60">45200</text></svg>')
CHART = ('<svg xmlns="http://www.w3.org/2000/svg" width="480" height="400">'
         '<rect width="480" height="400" fill="#ffffff"/>'
         '<text x="12" y="22">Bars</text></svg>')


def test_parts_are_checked_before_anything_is_drawn():
    request = parse_infographic({"title": "Flood", "charts": ["c1", "c2"], "caption": "QNEAT3",
                                 "source": "Copernicus DEM"})
    assert request.title == "Flood" and request.chart_ids == ("c1", "c2")
    assert request.caption == "QNEAT3" and request.source == "Copernicus DEM"
    for arguments in ({"title": "T"},
                      {"title": "T", "charts": []},
                      {"title": "T", "charts": ["c1"] * (MAX_PARTS + 1)},
                      {"title": "T", "charts": ["c1", "c1"]},
                      {"title": "T", "charts": ["c1", 4]},
                      {"title": "T", "charts": ["c1"], "caption": {"x": 1}}):
        with pytest.raises(ChartError):
            parse_infographic(arguments)


def test_stacking_keeps_the_widest_and_escapes_texts():
    svg = compose_infographic(parse_infographic(
        {"title": "Crue <Urumea> & affluents", "charts": ["c1", "c2"],
         "caption": "Houses < 5 m", "source": "cadastre & OSM"}),
        [KPI, CHART])
    assert svg.startswith('<svg xmlns="http://www.w3.org/2000/svg"')
    assert 'width="640"' in svg and 'height="663"' in svg  # 44 + 140 + 16 + 400 + 63
    assert "Crue &lt;Urumea&gt; &amp; affluents" in svg
    assert "Houses &lt; 5 m" in svg and "cadastre &amp; OSM" in svg
    assert "45200" in svg and "Bars" in svg  # both parts drawn
    assert "<script" not in svg


def test_a_part_that_is_no_svg_is_refused():
    request = parse_infographic({"title": "T", "charts": ["c1"]})
    with pytest.raises(ChartError):
        compose_infographic(request, ["<html/>"])
    assert svg_size(KPI) == (640, 140)
    assert svg_size('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 480 400"></svg>') == (480, 400)
    with pytest.raises(ChartError):
        svg_size("<html/>")


def test_the_standalone_page_is_offline_text():
    svg = compose_infographic(parse_infographic({"title": "Crue", "charts": ["c1"]}), [KPI])
    page = infographic_page("Crue <Urumea>", svg, "Houses", "cadastre & OSM")
    assert page.startswith("<!doctype html>") and "<html" in page
    assert "Crue &lt;Urumea&gt;" in page and "cadastre &amp; OSM" in page
    assert "<svg" in page and "</svg>" in page
    assert "<script" not in page  # the xmlns namespace aside, nothing is fetched
    assert "http://www.w3.org" in page and page.count("http://") == 1
    assert "src=" not in page and "href=" not in page


def test_parts_keep_their_root_style_viewbox_and_unique_references():
    import xml.etree.ElementTree as ElementTree
    part = ('<?xml version="1.0"?>'
            '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="100" '
            'viewBox="10 20 400 200" fill="#123456" font-family="Arial">'
            '<defs><linearGradient id="ink"/></defs><rect fill="url(#ink)"/></svg>')
    request = parse_infographic({"title": "Two", "charts": ["c1", "c2"]})
    svg = compose_infographic(request, [part, part])
    root = ElementTree.fromstring(svg)
    assert not root.findall(".//{http://www.w3.org/2000/svg}svg")
    parts = [element for element in root.iter() if element.attrib.get("fill") == "#123456"]
    assert len(parts) == 2 and all(part.attrib["font-family"] == "Arial" for part in parts)
    assert svg.count('transform="matrix(0.5 0 0 0.5 -5 -10)"') == 2
    assert 'id="part0_ink"' in svg and 'id="part1_ink"' in svg
    assert 'fill="url(#part0_ink)"' in svg and 'fill="url(#part1_ink)"' in svg


def test_composition_and_offline_page_remove_active_and_external_content():
    part = (KPI[:-6] + '<image href="https://example.invalid/private.png"/>'
            '<rect onclick="alert(1)" fill="url(https://example.invalid/paint)"/>'
            '<animate attributeName="fill" to="url(https://example.invalid/paint)"/></svg>')
    svg = compose_infographic(parse_infographic({"title": "Offline", "charts": ["c1"]}), [part])
    page = infographic_page("Offline", svg, "", "")
    assert "example.invalid" not in page and "onclick" not in page and "<image" not in page
    assert "Content-Security-Policy" in page
    with pytest.raises(ChartError):
        infographic_page("T", KPI[:-6] + "<script>alert(1)</script></svg>", "", "")


@pytest.mark.parametrize("size", ["nan", "inf", "0", "1000000"])
def test_bad_viewbox_sizes_are_refused(size):
    with pytest.raises(ChartError):
        svg_size(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 {size}"/>')
