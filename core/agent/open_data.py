# -*- coding: utf-8 -*-
"""Open data platforms: which ones may be asked, how to ask them, and what they answer. Pure, no network.

A query written by a model leaves the machine, and a resource URL it picks is then read by QGIS, so
only platforms the user allowed are reachable, and the answers are reduced to what a layer needs.
"""
from __future__ import annotations

import ipaddress
import re
from typing import Any, Dict, List, Tuple
from urllib.parse import quote, urlsplit

KIND_DATAGOUV = "datagouv"
KIND_OPENDATASOFT = "opendatasoft"
KIND_CKAN = "ckan"
KINDS = (KIND_DATAGOUV, KIND_OPENDATASOFT, KIND_CKAN)

# Built in: name -> (kind, host). The user adds others in the configuration (APP.OPTIONS.AGENT.open_data_domains).
PLATFORMS: Dict[str, Tuple[str, str]] = {
    "datagouv": (KIND_DATAGOUV, "www.data.gouv.fr"),
    "opendatasoft": (KIND_OPENDATASOFT, "data.opendatasoft.com"),
}
# What add_layer can open from a URL (a service needs a provider URI, which a model does not get to write).
GEO_FORMATS = frozenset({
    "geojson", "gpkg", "geopackage", "shp", "shapefile", "zip", "kml", "gml", "csv", "fgb", "flatgeobuf",
    "tif", "tiff", "geotiff", "cog",
})
LOCAL_FORMATS = frozenset({"csv", "fgb", "geojson", "gml", "gpkg", "json", "kml", "shp", "tif", "tiff"})
MAX_SOURCE = 2000
_LAYER_NAME_SUFFIX = re.compile(r"\|layername=[\w .-]+$")
_DRIVER_PREFIX = re.compile(r"^[A-Za-z0-9_]+:")
_WINDOWS_DRIVE = re.compile(r"^[A-Za-z]:[\\/]")
MAX_RESULTS = 20
MAX_TEXT = 300
_LOOPBACK = ("localhost", "127.0.0.1", "::1")


def parse_extra_domains(text: str) -> Dict[str, Tuple[str, str]]:
    """``host``, ``host:kind`` or ``http://127.0.0.1:8000:kind`` entries, comma separated, as platforms."""
    platforms: Dict[str, Tuple[str, str]] = {}
    for raw in (text or "").split(","):
        item = raw.strip()
        if not item:
            continue
        kind = KIND_OPENDATASOFT
        tail = item.rsplit(":", 1)[-1] if ":" in item else ""
        if tail.isalpha():
            if tail.lower() not in KINDS:
                continue  # a typo must not become part of the address
            kind, item = tail.lower(), item[:-len(tail) - 1]
        platforms[item.lower()] = (kind, item)
    return platforms


def platforms_available(extra: str = "") -> Dict[str, Tuple[str, str]]:
    merged = dict(PLATFORMS)
    merged.update(parse_extra_domains(extra))
    return merged


def base_url(host: str) -> str:
    """``https://host``; an explicit ``http://`` is only accepted for this machine (tests, a local mirror)."""
    if "://" in host:
        parts = urlsplit(host)
        if parts.scheme == "https" or (parts.scheme == "http" and parts.hostname in _LOOPBACK):
            return host.rstrip("/")
        raise ValueError(f"a platform address must be https: {host!r}")
    return "https://" + host.rstrip("/")


def resolve_platform(name: str, extra: str = "") -> Tuple[str, str]:
    """``(kind, base url)`` of a platform the user allowed.

    Raises:
        ValueError: Not in the list; the message says how to add one.
    """
    platforms = platforms_available(extra)
    key = (name or "").strip().lower()
    for candidate in (key, key.replace("https://", "").replace("http://", "").rstrip("/")):
        if candidate in platforms:
            kind, host = platforms[candidate]
            return kind, base_url(host)
    raise ValueError(f"{name!r} is not an allowed open data platform. Allowed: {', '.join(sorted(platforms))}. "
                     "The user can add one in the FilterMate configuration (AGENT > open_data_domains).")


def search_url(kind: str, base: str, query: str, limit: int) -> str:
    limit = max(1, min(int(limit), MAX_RESULTS))
    q = quote(query, safe="")
    if kind == KIND_DATAGOUV:
        return f"{base}/api/1/datasets/?q={q}&page_size={limit}"
    if kind == KIND_OPENDATASOFT:
        literal = quote('"' + query.replace("\\", "").replace('"', "") + '"', safe="")
        return f"{base}/api/explore/v2.1/catalog/datasets?where={literal}&limit={limit}"
    if kind == KIND_CKAN:
        return f"{base}/api/3/action/package_search?q={q}&rows={limit}"
    raise ValueError(f"unknown platform kind {kind!r}")


def _text(value: Any) -> str:
    text = " ".join(str(value or "").split())
    return text[:MAX_TEXT]


def _link(value: Any) -> str:
    """A URL from an answer, kept only when it is plain."""
    text = str(value or "")
    return text if len(text) <= MAX_SOURCE and not any(char.isspace() for char in text) else ""


def _dicts(value: Any) -> List[Dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _geo_resources(items: Any) -> List[Dict[str, str]]:
    resources = []
    for item in _dicts(items):
        url = _link(item.get("url"))
        fmt = str(item.get("format") or "").strip().lower().lstrip(".")
        if not url.startswith("https://") or fmt not in GEO_FORMATS:
            continue
        resources.append({"title": _text(item.get("title") or item.get("name") or fmt), "format": fmt, "url": url})
    return resources[:10]


def parse_results(kind: str, payload: Any, base: str) -> List[Dict[str, Any]]:
    """Datasets of an answer, with the resources a layer can be made of. Anything odd is left out."""
    try:
        return _parse_results(kind, payload, base)
    except (AttributeError, TypeError, RecursionError):
        return []


def _parse_results(kind: str, payload: Any, base: str) -> List[Dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    found: List[Dict[str, Any]] = []
    if kind == KIND_DATAGOUV:
        for item in _dicts(payload.get("data")):
            organization = item.get("organization") if isinstance(item.get("organization"), dict) else {}
            found.append({
                "id": _text(item.get("id")), "title": _text(item.get("title")),
                "publisher": _text(organization.get("name")), "description": _text(item.get("description")),
                "page": _link(item.get("page")), "resources": _geo_resources(item.get("resources"))})
    elif kind == KIND_OPENDATASOFT:
        for item in _dicts(payload.get("results")):
            if not item.get("dataset_id"):
                continue
            metas = item.get("metas") if isinstance(item.get("metas"), dict) else {}
            metas = metas.get("default") if isinstance(metas.get("default"), dict) else {}
            dataset_id = _text(item["dataset_id"])
            exports = f"{base}/api/explore/v2.1/catalog/datasets/{quote(dataset_id, safe='')}/exports/"
            # The platform exports GeoJSON for any dataset: only one with a geometry makes a map layer.
            features = item.get("features") if isinstance(item.get("features"), list) else []
            formats = ("geojson", "csv") if "geo" in features else ("csv",)
            found.append({
                "id": dataset_id, "title": _text(metas.get("title")), "publisher": _text(metas.get("publisher")),
                "description": _text(metas.get("description")), "page": f"{base}/explore/dataset/{quote(dataset_id, safe='')}/",
                "resources": [{"title": _text(metas.get("title")) + f" ({fmt})", "format": fmt, "url": exports + fmt}
                              for fmt in formats] if base.startswith("https://") else [],
                "has_geometry": "geo" in features})
    elif kind == KIND_CKAN:
        result = payload.get("result") if isinstance(payload.get("result"), dict) else {}
        for item in _dicts(result.get("results")):
            organization = item.get("organization") if isinstance(item.get("organization"), dict) else {}
            name = _text(item.get("name"))
            found.append({
                "id": name, "title": _text(item.get("title")), "publisher": _text(organization.get("title")),
                "description": _text(item.get("notes")), "page": f"{base}/dataset/{quote(name, safe='')}" if name else "",
                "resources": _geo_resources(item.get("resources"))})
    return found[:MAX_RESULTS]


def source_problem(source: str, allow_remote: bool) -> str:
    """Why a layer source written by a model cannot be opened; "" when it can.

    Only two shapes exist: a plain local data file, and a plain public https URL. A string QGIS or GDAL would
    interpret otherwise can reach a database, a share or any host (``PG:``, ``/vsicurl/``, UNC paths, ``<GDAL_WMS>``,
    ``|subset=``, provider URIs).
    """
    source = source or ""
    if len(source) > MAX_SOURCE or any(ord(char) < 32 for char in source):
        return "this source cannot be read"
    if source.lower().startswith("https://"):
        if not allow_remote:
            return "layers are not read over the network: the user did not allow open data platforms in the agent settings"
        return _url_problem(source)
    path = _LAYER_NAME_SUFFIX.sub("", source)
    if path.lower().startswith(("http://", "ftp://", "file:")) or "://" in path:
        return "only a local file or an https URL can be added"
    if path.startswith(("\\\\", "//")) or path.lower().startswith("/vsi") or any(char in path for char in '|<>?*"=&%'):
        return "only a plain local file can be added"
    if _DRIVER_PREFIX.match(path) and not _WINDOWS_DRIVE.match(path):
        return "only a plain local file can be added"
    if path.rsplit(".", 1)[-1].lower() not in LOCAL_FORMATS or "." not in path:
        return f"this file type cannot be added: {', '.join(sorted(LOCAL_FORMATS))}"
    return ""


def _url_problem(url: str) -> str:
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError:
        return "this URL cannot be read"
    host = (parts.hostname or "").lower()
    if not host or parts.username or parts.password or port not in (None, 443) or any(char in url for char in " |<>\\"):
        return "this URL cannot be read"
    if host == "localhost" or host.endswith((".localhost", ".local", ".internal", ".lan")) or "." not in host.strip("[]"):
        return "only a public address can be read"
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return ""
    return "" if address.is_global else "only a public address can be read"


def display_source(source: str) -> str:
    """What the user reads before accepting: the host first, the rest cut."""
    if source.lower().startswith("https://"):
        parts = urlsplit(source)
        path = parts.path if len(parts.path) <= 80 else parts.path[:77] + "..."
        return f"{parts.hostname}\n{parts.scheme}://{parts.netloc}{path}"
    return source[:300]
