# -*- coding: utf-8 -*-
"""Open data platforms: which ones may be asked, how to ask them, and what they answer. Pure, no network.

A query written by a model leaves the machine, and a resource URL it picks is then read by QGIS, so
only platforms the user allowed are reachable, and the answers are reduced to what a layer needs.
"""
from __future__ import annotations

import ipaddress
import re
from typing import Any, Callable, Dict, List, Tuple
from urllib.parse import quote, urljoin, urlsplit

KIND_DATAGOUV = "datagouv"
KIND_OPENDATASOFT = "opendatasoft"
KIND_CKAN = "ckan"
KIND_WFS = "wfs"
KIND_STAC = "stac"
KINDS = (KIND_DATAGOUV, KIND_OPENDATASOFT, KIND_CKAN, KIND_WFS, KIND_STAC)

# Built in: name -> (kind, host). The user adds others in the configuration (APP.OPTIONS.AGENT.open_data_domains).
PLATFORMS: Dict[str, Tuple[str, str]] = {
    "datagouv": (KIND_DATAGOUV, "www.data.gouv.fr"),
    "opendatasoft": (KIND_OPENDATASOFT, "data.opendatasoft.com"),
    "ign_wfs": (KIND_WFS, "data.geopf.fr/wfs/ows"),
    "earth_search": (KIND_STAC, "earth-search.aws.element84.com/v1"),
    "ibge_br": (KIND_WFS, "geoservicos.ibge.gov.br/geoserver/wfs"),
    "prg_pl": (KIND_WFS, "mapy.geoportal.gov.pl/wss/service/PZGIK/PRG/WFS/AdministrativeBoundaries"),
    "data_gov_uk": (KIND_CKAN, "ckan.publishing.service.gov.uk"),
    "open_canada": (KIND_CKAN, "open.canada.ca/data"),
    "data_gov_au": (KIND_CKAN, "data.gov.au/data"),
    "govdata_de": (KIND_CKAN, "ckan.govdata.de"),
    "dati_gov_it": (KIND_CKAN, "dati.gov.it/opendata"),
    "data_overheid_nl": (KIND_CKAN, "data.overheid.nl/data"),
    "data_gov_ie": (KIND_CKAN, "data.gov.ie"),
    "geospatial_jp": (KIND_CKAN, "www.geospatial.jp/ckan"),
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
_DAY = re.compile(r"\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])")
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
        # Some portals give the EU vocabulary URI (.../file-type/SHP) for the format.
        fmt = str(item.get("format") or "").strip().rstrip("/").rsplit("/", 1)[-1].lower().lstrip(".")
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
    host = (parts.hostname or "").lower().rstrip(".")  # "localhost." is localhost
    if not host or parts.username or parts.password or port not in (None, 443) or any(char in url for char in " |<>\\"):
        return "this URL cannot be read"
    if host == "localhost" or host.endswith((".localhost", ".local", ".internal", ".lan")) or "." not in host.strip("[]"):
        return "only a public address can be read"
    try:
        address = ipaddress.ip_address(host)
    except ValueError:  # 127.1, 0x7f.0.0.1: a real name ends with letters
        return "" if host.rsplit(".", 1)[-1].isalpha() else "only a public address can be read"
    return "" if address.is_global else "only a public address can be read"


def gdal_source(url: str, kind: str) -> str:
    """How GDAL reads a public URL without downloading it first. Built here, never written by a model."""
    path = urlsplit(url).path.lower()
    extension = path.rsplit(".", 1)[-1]
    if extension == "zip":
        return "/vsizip//vsicurl/" + url
    if path.rsplit("/", 1)[-1] == "csv":  # an export link with no extension: GDAL has to be told
        return "CSV:/vsicurl/" + url
    if kind == "raster" or extension in ("gpkg", "fgb", "shp", "tif", "tiff"):
        return "/vsicurl/" + url
    return url


def follow_redirects(url: str, head: Callable[[str], Tuple[int, str]], max_hops: int = 4) -> str:
    """The URL a resource really ends at, each hop held to the rules of the first.

    Raises:
        ValueError: A hop leaves public https, or there are too many.
    """
    for _ in range(max_hops):
        status, location = head(url)
        if not 300 <= status < 400:
            return url
        url = urljoin(url, location)
        problem = source_problem(url, True) if url.lower().startswith("https://") else "it redirects to an address in clear"
        if problem:
            raise ValueError(f"this link cannot be followed: {problem}")
    raise ValueError("this link redirects too many times")


def valid_day(text: str) -> bool:
    return not text or _DAY.fullmatch(text) is not None


def stac_search_body(collections: List[str], bbox: List[float], start: str, end: str, max_cloud: float,
                     limit: int) -> Dict[str, Any]:
    """The body of a STAC ``/search``: newest and least cloudy first."""
    body: Dict[str, Any] = {"bbox": bbox, "limit": max(1, min(int(limit), MAX_RESULTS)),
                            "sortby": [{"field": "properties.datetime", "direction": "desc"}]}
    if collections:
        body["collections"] = collections
    if start or end:
        body["datetime"] = f"{start or '..'}T00:00:00Z/{end or '..'}T23:59:59Z".replace("..T00:00:00Z", "..").replace(
            "..T23:59:59Z", "..")
    if max_cloud < 100:
        body["query"] = {"eo:cloud_cover": {"lte": max_cloud}}
    return body


def parse_stac_items(payload: Any) -> List[Dict[str, Any]]:
    """Scenes of a STAC answer with the assets QGIS can show: public https GeoTIFFs only."""
    try:
        return _parse_stac_items(payload)
    except (AttributeError, TypeError, RecursionError):
        return []


def _parse_stac_items(payload: Any) -> List[Dict[str, Any]]:
    scenes = []
    for item in _dicts(payload.get("features") if isinstance(payload, dict) else None):
        properties = item.get("properties") if isinstance(item.get("properties"), dict) else {}
        assets = item.get("assets") if isinstance(item.get("assets"), dict) else {}
        images = []
        for key in ("visual", "red", "green", "blue", "nir", "scl"):
            asset = assets.get(key) if isinstance(assets.get(key), dict) else {}
            href = _link(asset.get("href"))
            if href.startswith("https://") and "image/tiff" in str(asset.get("type", "")):
                images.append({"title": _text(asset.get("title") or key), "format": key, "url": href})
        if images:
            scenes.append({"id": _text(item.get("id")), "title": _text(item.get("id")), "publisher": _text(item.get("collection")),
                           "description": f"{_text(properties.get('datetime'))} · cloud cover {properties.get('eo:cloud_cover', '?')} %",
                           "page": "", "resources": images})
    return scenes[:MAX_RESULTS]


def display_source(source: str) -> str:
    """What the user reads before accepting: the host first, the rest cut."""
    if source.lower().startswith("https://"):
        parts = urlsplit(source)
        path = parts.path if len(parts.path) <= 80 else parts.path[:77] + "..."
        query = f"?{parts.query[:120]}" if parts.query else ""  # what would leave with the request is shown
        return f"{parts.hostname}\n{parts.scheme}://{parts.netloc}{path}{query}"
    return source[:300]
