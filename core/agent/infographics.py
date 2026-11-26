# -*- coding: utf-8 -*-
"""Infographics of the agent: kept charts stacked into one SVG, and its standalone page.

Plain Python. An infographic is composed from charts the conversation already drew (show_chart): their SVGs,
drawn light for paper, are stacked under a title with a caption and a source into a single SVG. That SVG shows
in the chat like a chart and is written as an image, as SVG, or as a standalone HTML page (the SVG inline, no
script, nothing fetched: it opens offline, out of QGIS). An infographic is always light: it is made to be shared.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ElementTree  # nosec B405 - a DTD is refused before parsing (svg_size)
from dataclasses import dataclass
from typing import List, Sequence, Tuple
from xml.sax.saxutils import escape  # nosec B406 - escapes the text written, parses nothing

from .chart_render import clean, fit
from .charts import MAX_TITLE, PALETTES, SVG_NS, ChartError, _text, _write, sanitize_svg

MAX_PARTS = 4  # charts stacked in one infographic
MAX_CHART_ID = 20  # as run_chart_code takes them
MAX_CAPTION = 200
MAX_SOURCE = 200
MAX_INFOGRAPHIC_SIDE = 6000  # past this, fewer or smaller charts

_TITLE_BLOCK = 50  # top pad, title and the gap before the first part
_GAP = 16  # between two parts, and before the caption
_CAPTION_BASE = 11  # baseline of the caption below the parts
_SOURCE_DY = 16  # baseline of the source below the caption
_BOTTOM = 14
_REFERENCE = re.compile(r"url\(\s*['\"]?#([^)'\"\s]+)['\"]?\s*\)", re.I)


@dataclass(frozen=True)
class InfographicRequest:
    """What show_infographic asks, checked: the charts of the conversation to stack, in order."""

    title: str
    chart_ids: Tuple[str, ...]
    caption: str = ""
    source: str = ""


def parse_infographic(arguments: dict) -> InfographicRequest:
    """``arguments`` of show_infographic checked; ChartError says what is wrong. The charts themselves are
    resolved by the caller (it keeps them): only their ids travel here."""
    if not isinstance(arguments, dict):
        raise ChartError("the arguments are an object")
    title = _text(arguments, "title", MAX_TITLE)
    if not title:
        raise ChartError("title: what the infographic says, in the words of the user, is needed")
    raw = arguments.get("charts")
    if not isinstance(raw, list) or not raw:
        raise ChartError("charts: the charts to stack, by their chart_id from show_chart")
    if len(raw) > MAX_PARTS:
        raise ChartError(f"charts holds {MAX_PARTS} charts at most: keep the ones that tell the story")
    chart_ids = []
    for chart_id in raw:
        if not isinstance(chart_id, str) or not re.fullmatch(r"c[1-9][0-9]*", chart_id) or len(chart_id) > MAX_CHART_ID:
            raise ChartError("each chart is its chart_id from show_chart")
        if chart_id in chart_ids:
            raise ChartError(f"{chart_id!r} is stacked twice: show each chart once")
        chart_ids.append(chart_id)
    caption = arguments.get("caption")
    if caption is not None and not isinstance(caption, str):
        raise ChartError("caption is text")
    source = arguments.get("source")
    if source is not None and not isinstance(source, str):
        raise ChartError("source is text")
    return InfographicRequest(title=title, chart_ids=tuple(chart_ids),
                              caption=_text(arguments, "caption", MAX_CAPTION),
                              source=_text(arguments, "source", MAX_SOURCE))


def svg_size(svg: str) -> Tuple[int, int]:
    """``(width, height)`` of an SVG of a chart, from its size or its viewBox; ChartError when it has none."""
    svg = sanitize_svg(svg, max_side=MAX_INFOGRAPHIC_SIDE)
    try:
        root = ElementTree.fromstring(svg)  # nosec B314 - no DTD (refused above), drawn by FilterMate
    except ElementTree.ParseError as exc:
        raise ChartError(f"a part of the infographic could not be read ({exc})") from None
    if root.tag != "{%s}svg" % SVG_NS:
        raise ChartError("a part of the infographic is no SVG")

    def number(text: str) -> int:
        try:
            value = float(str(text or "").strip().lower().replace("px", ""))
        except ValueError:
            raise ChartError("a part of the infographic is no SVG")
        if value != value or value in (float("inf"), float("-inf")) or value <= 0:
            raise ChartError("a part of the infographic is no SVG")
        return int(round(value))

    width, height = root.attrib.get("width", ""), root.attrib.get("height", "")
    if width and height:
        return number(width), number(height)
    box = str(root.attrib.get("viewBox", "")).replace(",", " ").split()
    if len(box) == 4:
        try:
            return number(box[2]), number(box[3])
        except ChartError:
            pass
    raise ChartError("a part of the infographic has no size")


def _part(svg: str, position: int, left: int, top: int, width: int, height: int) -> str:
    svg = sanitize_svg(svg, max_side=MAX_INFOGRAPHIC_SIDE)
    root = ElementTree.fromstring(svg)  # nosec B314 - sanitize_svg rejects DTDs and entities before parsing
    ids = {element.attrib["id"]: f"part{position}_{element.attrib['id']}"
           for element in root.iter() if "id" in element.attrib}
    for element in root.iter():
        for name, value in list(element.attrib.items()):
            if name == "id":
                element.attrib[name] = ids[value]
            else:
                element.attrib[name] = _REFERENCE.sub(
                    lambda match: f"url(#{ids.get(match[1], f'part{position}_{match[1]}')})", value)
    scale_x = scale_y = 1.0
    offset_x = offset_y = 0.0
    if "viewBox" in root.attrib:
        origin_x, origin_y, box_width, box_height = (
            float(value) for value in root.attrib["viewBox"].replace(",", " ").split())
        scale_x, scale_y = width / box_width, height / box_height
        aspect = root.attrib.get("preserveAspectRatio", "xMidYMid meet").split()
        if "none" not in aspect:
            scale_x = scale_y = max(scale_x, scale_y) if "slice" in aspect else min(scale_x, scale_y)
            alignment = aspect[0] if aspect else "xMidYMid"
            offset_x = (width - box_width * scale_x) * (0 if "xMin" in alignment else 1 if "xMax" in alignment else 0.5)
            offset_y = (height - box_height * scale_y) * (0 if "YMin" in alignment else 1 if "YMax" in alignment else 0.5)
        offset_x -= origin_x * scale_x
        offset_y -= origin_y * scale_y
    root.tag = f"{{{SVG_NS}}}g"
    for name in ("x", "y", "width", "height", "viewBox", "preserveAspectRatio", "version"):
        root.attrib.pop(name, None)
    out: List[str] = []
    _write(root, out)
    clip_id = f"fm_part{position}_viewport"
    return (f'<g id="fm_part{position}" transform="translate({left},{top})">'
            f'<defs><clipPath id="{clip_id}"><rect width="{width}" height="{height}"/></clipPath></defs>'
            f'<g clip-path="url(#{clip_id})"><g transform="matrix({scale_x:g} 0 0 {scale_y:g} {offset_x:g} {offset_y:g})">'
            + "".join(out) + "</g></g></g>")


def compose_infographic(request: InfographicRequest, svgs: Sequence[str]) -> str:
    """The charts ``svgs`` (in the order of the request) stacked into one SVG, light for paper."""
    request = parse_infographic({"title": request.title, "charts": list(request.chart_ids),
                                 "caption": request.caption, "source": request.source})
    svgs = [sanitize_svg(svg) for svg in svgs]
    if len(svgs) != len(request.chart_ids):
        raise ChartError("the infographic stacks exactly its charts")
    sizes = [svg_size(svg) for svg in svgs]
    width = max(size[0] for size in sizes)
    height = _TITLE_BLOCK + sum(size[1] for size in sizes) + _GAP * len(sizes) \
        + _CAPTION_BASE + _SOURCE_DY + _BOTTOM
    if max(width, height) > MAX_INFOGRAPHIC_SIDE:
        raise ChartError("the infographic is too large: fewer charts, or smaller ones")
    palette = PALETTES["light"]
    out: List[str] = [f'<svg xmlns="{SVG_NS}" width="{width}" height="{height}" '
                      f'viewBox="0 0 {width} {height}" font-family="\'Segoe UI\', \'Noto Sans\', Arial, sans-serif">',
                      f'<rect width="{width}" height="{height}" fill="{palette["background"]}"/>',
                      f'<text x="16" y="36" font-size="18" font-weight="600" '
                      f'fill="{palette["text"]}" font-family="\'Segoe UI\', \'Noto Sans\', Arial, sans-serif">'
                      f'{escape(fit(clean(request.title), width - 32, 18, bold=True))}</text>']
    top = _TITLE_BLOCK
    for position, (svg, (part_width, part_height)) in enumerate(zip(svgs, sizes)):
        left = (width - part_width) // 2
        out.append(_part(svg, position, left, top, part_width, part_height))
        top += part_height + _GAP
    # Fixed grid: the caption and source lines are reserved whether written or not.
    if request.caption:
        out.append(f'<text x="16" y="{top + _CAPTION_BASE}" font-size="11" fill="{palette["muted"]}">'
                   f'{escape(fit(clean(request.caption), width - 32, 11))}</text>')
    if request.source:
        out.append(f'<text x="16" y="{top + _CAPTION_BASE + _SOURCE_DY}" font-size="10" '
                   f'fill="{palette["muted"]}">{escape(fit(clean(request.source), width - 32, 10))}</text>')
    out.append("</svg>")
    return "".join(out)


def infographic_page(title: str, svg: str, caption: str, source: str) -> str:
    """``svg`` as a standalone page: text and drawing inline, no script, nothing fetched — it opens offline."""
    if re.search(r"<script", svg, re.I):
        raise ChartError("the infographic holds a script: refused")
    svg = sanitize_svg(svg, max_side=MAX_INFOGRAPHIC_SIDE)
    from html import escape as html_escape  # local: the module otherwise stays XML-only
    body = "".join(f"<p class='{kind}'>{html_escape(text)}</p>" for kind, text in
                   (("caption", caption), ("source", source)) if text)
    return ("<!doctype html><html><head><meta charset=\"utf-8\">"
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'">'
            f"<title>{html_escape(title)}</title>"
            "<style>body{margin:0;background:#e8e7e3;font-family:'Segoe UI','Noto Sans',Arial,sans-serif}"
            "main{max-width:900px;margin:24px auto;background:#fff;padding:24px 28px;border-radius:8px}"
            "h1{font-size:22px;margin:0 0 12px}p.caption{color:#52514e}p.source{color:#8a897f;font-size:12px}"
            "figure{margin:0}svg{max-width:100%;height:auto}</style></head>"
            f"<body><main><h1>{html_escape(title)}</h1><figure>{svg}</figure>{body}</main></body></html>")
