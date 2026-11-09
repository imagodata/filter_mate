# -*- coding: utf-8 -*-
"""What a WFS service offers: its capabilities, read once, searched in memory.

A catalog can hold thousands of layers (5 MB for the IGN Géoplateforme), so it is kept for the session.
"""
from __future__ import annotations

import time
import unicodedata
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlsplit

from qgis.core import QgsDataSourceUri, QgsVectorLayer
from qgis.PyQt.QtCore import QByteArray, QXmlStreamReader

from ..agent.bounded_http import HttpFailure, fetch

MAX_TEXT = 300
MAX_LAYERS = 50_000
MAX_CAPABILITIES = 32 * 1024 * 1024
TIMEOUT_MS = 90_000
TTL_SECONDS = 6 * 3600
_CACHE: Dict[str, Any] = {}


def _plain(text: str) -> str:
    """Lower case without accents: a search must not depend on them."""
    return "".join(char for char in unicodedata.normalize("NFKD", text or "") if not unicodedata.combining(char)).lower()


def parse_capabilities(data: bytes) -> Tuple[List[Dict[str, str]], List[str]]:
    """The feature types of a capabilities document, and the addresses it says its operations are at.

    Qt's reader does not expand external entities.

    Raises:
        ValueError: A document that is broken or cut: a partial catalog must not be kept.
    """
    reader = QXmlStreamReader(QByteArray(data))
    types: List[Dict[str, str]] = []
    endpoints: List[str] = []
    current: Optional[Dict[str, str]] = None
    depth = feature_depth = 0

    def local(value) -> str:
        return value.toString() if hasattr(value, "toString") else str(value)

    while not reader.atEnd() and len(types) < MAX_LAYERS:
        reader.readNext()
        if reader.isStartElement():
            depth += 1
            name = local(reader.name())
            if name in ("Get", "Post"):
                href = local(reader.attributes().value("http://www.w3.org/1999/xlink", "href"))
                if href:
                    endpoints.append(href)
            if name == "FeatureType":
                current, feature_depth = {"name": "", "title": "", "abstract": "", "crs": ""}, depth
            elif current is not None and depth == feature_depth + 1 and name in ("Name", "Title", "Abstract", "DefaultCRS", "DefaultSRS"):
                text = reader.readElementText(QXmlStreamReader.ReadElementTextBehaviour.SkipChildElements)
                depth -= 1  # the end of this element was read with it
                key = {"Name": "name", "Title": "title", "Abstract": "abstract"}.get(name, "crs")
                current[key] = " ".join(text.split())
        elif reader.isEndElement():
            if local(reader.name()) == "FeatureType" and current is not None:
                if current["name"]:
                    types.append(current)
                current = None
            depth -= 1
    if reader.hasError() and len(types) < MAX_LAYERS:
        raise ValueError("the service answered with a broken document")
    return types, endpoints


def catalog(base: str) -> List[Dict[str, str]]:
    """The layers of the service at ``base``, from memory when it was read recently.

    Raises:
        ValueError: The service does not answer, is no WFS, or sends its requests to another host.
    """
    cached = _CACHE.get(base)
    if cached is not None and time.time() - cached[0] < TTL_SECONDS:
        return cached[1]
    separator = "&" if "?" in base else "?"
    try:
        reply = fetch(f"{base}{separator}SERVICE=WFS&VERSION=2.0.0&REQUEST=GetCapabilities",
                      max_bytes=MAX_CAPABILITIES, timeout_ms=TIMEOUT_MS)
    except HttpFailure as exc:
        raise ValueError(f"the service did not answer: {exc}") from None
    if reply.status != 200:
        raise ValueError(f"the service answered with an error ({reply.status})")
    types, endpoints = parse_capabilities(reply.content)
    if not types:
        raise ValueError("this address is not a WFS service, or it offers no layer")
    # QGIS sends its requests where the capabilities say: not to another machine than the one the user allowed.
    host = urlsplit(base).hostname
    if any(urlsplit(address).hostname != host for address in endpoints):
        raise ValueError("this service sends its requests to another host, which is not followed")
    _CACHE[base] = (time.time(), types)
    return types


def search(base: str, query: str, limit: int) -> List[Dict[str, Any]]:
    """Layers matching every word of ``query``, those with the words in their name or title first."""
    words = [word for word in _plain(query).split() if word]
    scored = []
    for item in catalog(base):
        title = _plain(f"{item['name']} {item['title']}")
        text = f"{title} {_plain(item['abstract'])}"
        if all(word in text for word in words):
            scored.append((-sum(word in title for word in words), item["name"], item))
    scored.sort(key=lambda entry: entry[:2])
    return [{"id": item["name"], "title": item["title"][:MAX_TEXT], "publisher": "",
             "description": item["abstract"][:MAX_TEXT], "page": "",
             "resources": [{"title": item["title"][:MAX_TEXT], "format": "wfs", "typename": item["name"]}]}
            for _score, _name, item in scored[:limit]]


def open_layer(base: str, typename: str, title: str) -> QgsVectorLayer:
    """A layer of the service. The URI is built here, for a name the service really lists.

    Raises:
        ValueError: A layer the service does not offer.
    """
    item = next((entry for entry in catalog(base) if entry["name"] == typename), None)
    if item is None:
        raise ValueError(f"the service does not offer {typename!r}: use the id given by search_open_data")
    uri = QgsDataSourceUri()
    uri.setParam("url", base)
    uri.setParam("typename", typename)
    uri.setParam("version", "auto")
    uri.setParam("pagingEnabled", "true")
    uri.setParam("restrictToRequestBBOX", "1")
    if item["crs"]:
        uri.setParam("srsname", item["crs"])
    return QgsVectorLayer(uri.uri(False), (title or item["title"] or typename)[:80], "WFS")
