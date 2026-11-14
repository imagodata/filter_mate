# -*- coding: utf-8 -*-
"""What a WMS or WMTS service offers: its capabilities, read once, searched in memory, as ``wfs_catalog`` does.

Such a layer is an image drawn by its server: it is shown, never filtered, read nor exported. Its source is built
here, for a name the service really lists, with the provider ``wms`` of QGIS.
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Sequence, Tuple
from urllib.parse import urlsplit

from qgis.core import QgsDataSourceUri, QgsRasterLayer
from qgis.PyQt.QtCore import QByteArray, QXmlStreamReader

from ...core.agent.open_data import KIND_WMTS
from ..agent.bounded_http import HttpFailure, fetch
from .wfs_catalog import MAX_CAPABILITIES, MAX_LAYERS, MAX_TEXT, TIMEOUT_MS, TTL_SECONDS, _plain

XLINK = "http://www.w3.org/1999/xlink"
WEB_MERCATOR = ("EPSG:3857", "EPSG:900913")
_FORMATS = ("image/png", "image/jpeg")
MAX_CRS = 200_000  # codes read in one document: a server lists a few thousands, on its root layer
_CACHE: Dict[Tuple[str, str], Any] = {}


def _local(value) -> str:
    return value.toString() if hasattr(value, "toString") else str(value)


def _authid(text: str) -> str:
    """``EPSG:3857`` from what a service writes: ``urn:ogc:def:crs:EPSG::3857``, ``EPSG:3857``, a URL of opengis.net."""
    text = (text or "").strip()
    for mark in ("EPSG::", "EPSG:", "/EPSG/0/", "/EPSG/"):
        if mark in text.upper():
            code = text[text.upper().rindex(mark) + len(mark):].split(":")[-1].split("/")[-1]
            if code.isdigit():
                return f"EPSG:{code}"
    return text[:40]


def _text(reader) -> str:
    """The text of the element just started (its end is read with it)."""
    return " ".join(reader.readElementText(QXmlStreamReader.ReadElementTextBehaviour.SkipChildElements).split())


def _foreign(address: str, base: str) -> bool:
    """Whether an address of a capabilities document is elsewhere than the service: another host, port or scheme."""
    try:
        there, here = urlsplit(address), urlsplit(base)
        return ((there.hostname or "").lower(), there.port, there.scheme.lower()) != (
            (here.hostname or "").lower(), here.port, here.scheme.lower())
    except ValueError:
        return True


def _href(reader) -> str:
    """The link of an element, as QGIS reads it (the attribute written ``xlink:href``) and as XML does (the xlink
    namespace under any prefix): a document where the two differ is refused, it shows one address and hides another."""
    by_namespace = _local(reader.attributes().value(XLINK, "href"))
    literal = _local(reader.attributes().value("xlink:href"))
    if by_namespace != literal:
        raise ValueError("the service answered with a document whose links cannot be trusted")
    return literal


def offered_crs(item: Dict[str, Any]) -> List[str]:
    """The CRS a WMS layer can be asked in: its own, after those of the layers that hold it."""
    chain = []
    while item is not None:
        chain.append(item["crs"])
        item = item["parent"]
    seen: Dict[str, None] = {}
    for codes in reversed(chain):
        for code in codes:
            seen.setdefault(code)
    return list(seen)


def parse_wms(data: bytes, base: str = "") -> Tuple[List[Dict[str, Any]], List[str]]:
    """The named layers of a WMS capabilities document, and where it says its requests go.

    A layer keeps its own CRS and the layer that holds it (``offered_crs`` reads them all): a server lists
    thousands of them on its root layer, copied to each layer they would weigh hundreds of MB. The addresses of the
    requests are the endpoints; a layer whose legend is elsewhere than ``base`` is marked ``foreign`` (QGIS asks
    for the legend), the links of the attributions and of the metadata are not asked by QGIS.
    """
    layers: List[Dict[str, Any]] = []
    endpoints: List[str] = []
    formats: List[str] = []
    stack: List[Dict[str, Any]] = []
    reader = QXmlStreamReader(QByteArray(data))
    path: List[str] = []
    codes = 0
    while not reader.atEnd() and len(layers) < MAX_LAYERS:
        reader.readNext()
        if reader.isStartElement():
            name = _local(reader.name())
            path.append(name)
            in_request = "Request" in path and "Layer" not in path
            if name == "Layer":
                stack.append({"name": "", "title": "", "abstract": "", "crs": [], "known": set(), "styles": [],
                              "foreign": False, "parent": stack[-1] if stack else None})
            elif name == "OnlineResource" and in_request and "DCPType" in path:
                href = _href(reader)
                if href:
                    endpoints.append(href)
            elif name == "OnlineResource" and stack and "LegendURL" in path:
                href = _href(reader)
                if href and base and _foreign(href, base):
                    stack[-1]["foreign"] = True
            elif name == "Format" and in_request and path[-2] == "GetMap":
                image = _text(reader)
                path.pop()
                if image:
                    formats.append(image)
            elif stack and len(path) >= 2 and path[-2] == "Layer" and name in ("Name", "Title", "Abstract", "CRS", "SRS"):
                text = _text(reader)
                path.pop()
                if name in ("CRS", "SRS"):
                    for code in text.split():
                        codes += 1
                        if codes > MAX_CRS:
                            raise ValueError("this service lists too many CRS to be read")
                        if code not in stack[-1]["known"]:
                            stack[-1]["known"].add(code)
                            stack[-1]["crs"].append(code)
                else:
                    stack[-1][name.lower()] = text
            elif stack and len(path) >= 3 and path[-2] == "Style" and path[-3] == "Layer" and name == "Name":
                stack[-1]["styles"].append(_text(reader))
                path.pop()
        elif reader.isEndElement():
            if _local(reader.name()) == "Layer" and stack:
                done = stack.pop()
                del done["known"]
                if done["name"]:
                    layers.append(done)
            if path:
                path.pop()
    if reader.hasError() and len(layers) < MAX_LAYERS:
        raise ValueError("the service answered with a broken document")
    for layer in layers:
        layer["formats"] = formats
    return layers, endpoints


def parse_wmts(data: bytes, base: str = "") -> Tuple[List[Dict[str, Any]], List[str]]:
    """The layers of a WMTS capabilities document, each with the CRS of its tile matrix sets, and its endpoints.

    The addresses of the requests (Get and Post) are the endpoints. A layer whose tiles, feature information or
    legend are elsewhere than ``base`` is marked ``foreign``: QGIS asks for them where the document says.
    """
    layers: List[Dict[str, Any]] = []
    endpoints: List[str] = []
    matrix_crs: Dict[str, str] = {}
    current: Optional[Dict[str, Any]] = None
    matrix_set = ""
    reader = QXmlStreamReader(QByteArray(data))
    path: List[str] = []
    while not reader.atEnd() and len(layers) < MAX_LAYERS:
        reader.readNext()
        if reader.isStartElement():
            name = _local(reader.name())
            path.append(name)
            parent = path[-2] if len(path) >= 2 else ""
            if name in ("Get", "Post") and "OperationsMetadata" in path:
                href = _href(reader)
                if href:
                    endpoints.append(href)
            elif name == "Layer" and parent == "Contents":
                current = {"name": "", "title": "", "abstract": "", "styles": [], "formats": [], "sets": [],
                           "foreign": False, "default_style": ""}
            elif name == "ResourceURL" and current is not None:
                template = _local(reader.attributes().value("template"))
                if template and base and _foreign(template, base):
                    current["foreign"] = True
            elif name == "LegendURL" and current is not None:
                href = _href(reader)
                if href and base and _foreign(href, base):
                    current["foreign"] = True
            elif name == "Style" and current is not None and parent == "Layer":
                current["default_next"] = _local(reader.attributes().value("isDefault")).lower() == "true"
            elif current is not None and parent == "Layer" and name in ("Identifier", "Title", "Abstract", "Format"):
                text = _text(reader)
                path.pop()
                if name == "Format":
                    if text:
                        current["formats"].append(text)
                else:
                    current[{"Identifier": "name"}.get(name, name.lower())] = text
            elif current is not None and parent == "Style" and name == "Identifier":
                style = _text(reader)
                path.pop()
                current["styles"].append(style)
                if current.pop("default_next", False):
                    current["default_style"] = style
            elif current is not None and parent == "TileMatrixSetLink" and name == "TileMatrixSet":
                current["sets"].append(_text(reader))
                path.pop()
            elif current is None and parent == "TileMatrixSet" and len(path) >= 3 and path[-3] == "Contents":
                if name == "Identifier":
                    matrix_set = _text(reader)
                    path.pop()
                elif name == "SupportedCRS":
                    matrix_crs[matrix_set] = _authid(_text(reader))
                    path.pop()
        elif reader.isEndElement():
            if _local(reader.name()) == "Layer" and current is not None and len(path) >= 2 and path[-2] == "Contents":
                current.pop("default_next", None)
                if current["name"]:
                    layers.append(current)
                current = None
            if path:
                path.pop()
    if reader.hasError() and len(layers) < MAX_LAYERS:
        raise ValueError("the service answered with a broken document")
    for layer in layers:
        layer["crs"] = {name: matrix_crs.get(name, "") for name in layer["sets"]}
    return layers, endpoints


def capabilities_url(kind: str, base: str) -> str:
    """Where the capabilities of the service are asked; for a WMTS, QGIS reads this very address as the source."""
    separator = "&" if "?" in base else "?"
    if kind == KIND_WMTS:
        return f"{base}{separator}SERVICE=WMTS&REQUEST=GetCapabilities"
    return f"{base}{separator}SERVICE=WMS&VERSION=1.3.0&REQUEST=GetCapabilities"


def catalog(kind: str, base: str) -> List[Dict[str, Any]]:
    """The layers of the service at ``base``, from memory when it was read recently.

    Raises:
        ValueError: The service does not answer, is not of that kind, or sends its requests to another host.
    """
    cached = _CACHE.get((kind, base))
    if cached is not None and time.time() - cached[0] < TTL_SECONDS:
        return cached[1]
    try:
        reply = fetch(capabilities_url(kind, base), max_bytes=MAX_CAPABILITIES, timeout_ms=TIMEOUT_MS)
    except HttpFailure as exc:
        raise ValueError(f"the service did not answer: {exc}") from None
    if reply.status != 200:
        raise ValueError(f"the service answered with an error ({reply.status})")
    layers, endpoints = (parse_wmts if kind == KIND_WMTS else parse_wms)(reply.content, base)
    if not layers:
        raise ValueError(f"this address is not a {kind.upper()} service, or it offers no layer")
    # A service that says its requests go elsewhere (another host, port or scheme) is not followed. This reads the
    # document the plugin was given: QGIS asks for the capabilities again, so the source of a layer also tells it
    # to send its requests to the address of the service whatever the document says (source_parameters).
    if any(_foreign(address, base) for address in endpoints):
        raise ValueError("this service sends its requests to another host, which is not followed")
    _CACHE[(kind, base)] = (time.time(), layers)
    return layers


def search(kind: str, base: str, query: str, limit: int) -> List[Dict[str, Any]]:
    """Layers matching every word of ``query``, those with the words in their name or title first."""
    words = [word for word in _plain(query).split() if word]
    scored = []
    for item in catalog(kind, base):
        title = _plain(f"{item['name']} {item['title']}")
        text = f"{title} {_plain(item['abstract'])}"
        if all(word in text for word in words):
            scored.append((-sum(word in title for word in words), item["name"], item))
    scored.sort(key=lambda entry: entry[:2])
    return [{"id": item["name"], "title": item["title"][:MAX_TEXT], "publisher": "",
             "description": item["abstract"][:MAX_TEXT], "page": "",
             "resources": [{"title": item["title"][:MAX_TEXT], "format": kind, "typename": item["name"]}]}
            for _score, _name, item in scored[:limit]]


def _first(offered: Sequence[str], wanted: Sequence[str]) -> str:
    return next((value for value in wanted if value in offered), offered[0] if offered else "")


def source_parameters(kind: str, base: str, item: Dict[str, Any], project_crs: str = "") -> Dict[str, str]:
    """The parameters of the wms provider for a layer of the catalog: the CRS of the project when the layer has it,
    else Web Mercator, else its first one; PNG before JPEG; its first style."""
    image = _first(item["formats"], _FORMATS)
    # The requests go to the address of the service, whatever its capabilities say when QGIS reads them again.
    stay = {"IgnoreGetMapUrl": "1", "IgnoreGetFeatureInfoUrl": "1"}
    wanted = tuple(code.upper() for code in (project_crs,) + WEB_MERCATOR if code)
    if kind == KIND_WMTS:
        style = item.get("default_style") or (item["styles"][0] if item["styles"] else "")
        by_crs = {crs.upper(): (name, crs) for name, crs in reversed(list(item["crs"].items())) if crs}
        found = _first(list(by_crs), wanted)
        if not found:
            raise ValueError(f"{item['name']!r} names no tile matrix set QGIS can read")
        return dict(stay, crs=by_crs[found][1], format=image, layers=item["name"], styles=style,
                    tileMatrixSet=by_crs[found][0], url=capabilities_url(kind, base))
    style = item["styles"][0] if item["styles"] else ""
    offered = {(_authid(code) if code.upper().startswith("URN") else code).upper(): code for code in reversed(offered_crs(item))}
    found = _first(list(reversed(list(offered))), wanted + ("EPSG:4326",))
    if not found:
        raise ValueError(f"{item['name']!r} names no CRS")
    return dict(stay, crs=found if found.startswith("EPSG:") else offered[found], format=image, layers=item["name"],
                styles=style, url=base)


def open_layer(kind: str, base: str, typename: str, title: str, project_crs: str = "") -> QgsRasterLayer:
    """A layer of the service. The source is built here, for a name the service really lists.

    Raises:
        ValueError: A layer the service does not offer.
    """
    item = next((entry for entry in catalog(kind, base) if entry["name"] == typename), None)
    if item is None:
        raise ValueError(f"the service does not offer {typename!r}: use the id given by search_open_data")
    if item["foreign"]:
        raise ValueError(f"{typename!r} has its tiles or its legend on another host than its service, which is not "
                         "followed: choose another layer")
    uri = QgsDataSourceUri()
    for key, value in source_parameters(kind, base, item, project_crs).items():
        uri.setParam(key, value)
    return QgsRasterLayer(bytes(uri.encodedUri()).decode("ascii"), (title or item["title"] or typename)[:80], "wms")
