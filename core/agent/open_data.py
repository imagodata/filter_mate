# -*- coding: utf-8 -*-
"""Open data platforms: which ones may be asked, how to ask them, and what they answer. Pure, no network.

A query written by a model leaves the machine, and a resource URL it picks is then read by QGIS, so
only platforms the user allowed are reachable, and the answers are reduced to what a layer needs.
"""
from __future__ import annotations

import ipaddress
import re
import socket
import threading
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple, Union
from urllib.parse import parse_qs, quote, unquote, urljoin, urlsplit

from .basemaps import BASEMAPS

KIND_DATAGOUV = "datagouv"
KIND_OPENDATASOFT = "opendatasoft"
KIND_CKAN = "ckan"
KIND_WFS = "wfs"
KIND_STAC = "stac"
KIND_XYZ = "xyz"  # a web basemap: tiles drawn by a server, never searched nor read as data
KINDS = (KIND_DATAGOUV, KIND_OPENDATASOFT, KIND_CKAN, KIND_WFS, KIND_STAC, KIND_XYZ)

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
PLATFORMS.update({basemap.id: (KIND_XYZ, basemap.url) for basemap in BASEMAPS})
# What add_layer can open from a URL (a service needs a provider URI, which a model does not get to write).
GEO_FORMATS = frozenset({
    "geojson", "gpkg", "geopackage", "shp", "shapefile", "zip", "kml", "gml", "csv", "fgb", "flatgeobuf",
    "tif", "tiff", "geotiff", "cog",
})
LOCAL_FORMATS = frozenset({"csv", "fgb", "geojson", "gml", "gpkg", "json", "kml", "shp", "tif", "tiff"})
# What a link serves, when its address ends with the name of a format instead of a file name (``exports/shp``,
# ``download?format=shp``) or only its content type tells: the extension GDAL knows it by. A shapefile comes zipped.
_FORMAT_WORDS = {
    "geojson": "geojson", "json": "json", "gpkg": "gpkg", "geopackage": "gpkg", "shp": "zip", "shapefile": "zip",
    "zip": "zip", "kml": "kml", "gml": "gml", "csv": "csv", "fgb": "fgb", "flatgeobuf": "fgb", "tif": "tif",
    "tiff": "tif", "geotiff": "tif", "cog": "tif",
}
_CONTENT_TYPES = {
    "application/zip": "zip", "application/x-zip-compressed": "zip", "application/x-zip": "zip", "text/csv": "csv",
    "application/geo+json": "geojson",
    "application/vnd.geo+json": "geojson", "application/json": "geojson", "application/geopackage+sqlite3": "gpkg",
    "application/vnd.google-earth.kml+xml": "kml", "application/gml+xml": "gml", "image/tiff": "tif",
}
_EXPORT_WORDS = ("download", "export", "exports", "file")
_WEB_PAGES = ("text/html", "application/xhtml+xml")
# Formats GDAL reads by parts: worth leaving on a server that gives parts, whatever their size.
_READ_BY_PARTS = frozenset({"fgb", "gpkg", "shp", "tif", "tiff", "zip"})
# A .json or a .csv next to the data is often its metadata (datapackage.json): they come last.
_ARCHIVE_VECTORS = ("shp", "gpkg", "fgb", "geojson", "kml", "gml", "json", "csv")
_ARCHIVE_RASTERS = ("tif", "tiff")
_SENT_NAME = re.compile(r"""filename\*?\s*=\s*(?:[\w-]+'[^']*')?"?([^";]+)""", re.IGNORECASE)
# Formats a resource is named by while its address ends with a format word (an Opendatasoft export listed as json).
_VAGUE_FORMATS = ("", "json")
_UNSAFE_IN_NAME = re.compile(r"[^A-Za-z0-9._-]+")
_PLAIN_MEMBER = re.compile(r"[\w .()+/-]+")
_WINDOWS_DEVICE = re.compile(r"con|prn|aux|nul|com[0-9]|lpt[0-9]", re.IGNORECASE)
_BYTE_COUNT = re.compile(r"[0-9]{1,15}")
MAX_NAME = 60
MAX_SOURCE = 2000
_LAYER_NAME_SUFFIX = re.compile(r"\|layername=[\w .-]+$")
_DRIVER_PREFIX = re.compile(r"^[A-Za-z0-9_]+:")
_DAY = re.compile(r"\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])")
_WINDOWS_DRIVE = re.compile(r"^[A-Za-z]:[\\/]")
MAX_RESULTS = 20
MAX_TEXT = 300
_LOOPBACK = ("localhost", "127.0.0.1", "::1")
# A name Python, Qt and curl all ask for as it is written. Python resolves an international name in IDNA 2003, Qt 6
# in IDNA 2008, curl as it was built, and Qt decodes a name in percent-encoding: the name checked would not be the one read.
_PLAIN_HOST = re.compile(r"[a-z0-9._-]+")
_NOT_PLAIN_HOST = ("this server name is not plain ASCII letters, digits and hyphens: write an international name in its "
                   "ASCII form (xn--...)")
_NAT64 = ipaddress.ip_network("64:ff9b::/96")  # the gateway reaches the IPv4 address of the last 32 bits
_LOCAL_NAT64 = ipaddress.ip_network("64:ff9b:1::/48")  # a gateway of the local network, which places the IPv4 itself


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
    listed = sorted(key for key, (kind, _) in platforms.items() if kind != KIND_XYZ)  # a basemap holds no data
    raise ValueError(f"{name!r} is not an allowed open data platform. Allowed: {', '.join(listed)}. "
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


def _link_format(url: str) -> str:
    """The format the address of a resource ends with: ``exports/geojson``, ``communes.gpkg``."""
    try:
        last = urlsplit(url).path.rstrip("/").rsplit("/", 1)[-1].lower()
    except ValueError:
        return ""
    return last if last in GEO_FORMATS else last.rsplit(".", 1)[-1] if "." in last else ""


def _geo_resources(items: Any) -> List[Dict[str, str]]:
    resources = []
    for item in _dicts(items):
        url = _link(item.get("url"))
        # Some portals give the EU vocabulary URI (.../file-type/SHP) for the format.
        fmt = str(item.get("format") or "").strip().rstrip("/").rsplit("/", 1)[-1].lower().lstrip(".")
        if fmt in _VAGUE_FORMATS:  # data.gouv.fr lists the GeoJSON export of a harvested portal as "json"
            fmt = _link_format(url) or fmt
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
        if not _PLAIN_HOST.fullmatch(host):
            return _NOT_PLAIN_HOST
        return "" if host.rsplit(".", 1)[-1].isalpha() else "only a public address can be read"
    return "" if _public(address) else "only a public address can be read"


def _public(address: Union[ipaddress.IPv4Address, ipaddress.IPv6Address]) -> bool:
    """Whether ``address`` is on the internet, the IPv4 address an IPv6 one carries (mapped, NAT64, 6to4) too.

    Python takes 64:ff9b::a00:1 for global: through a NAT64 gateway, it is 10.0.0.1 (audit of 13/11/2026).
    """
    if address.version == 6 and address.ipv4_mapped is not None:
        address = address.ipv4_mapped
    if address.version == 4:
        return address.is_global
    if address in _LOCAL_NAT64:
        return False
    carried = address.sixtofour or (ipaddress.IPv4Address(int(address) & 0xFFFFFFFF) if address in _NAT64 else None)
    return address.is_global and (carried is None or carried.is_global)


RESOLVE_TIMEOUT_S = 3.0  # a name a resolver cannot answer for in this time is not read


def resolved_problem(url: str, resolve: Optional[Callable[..., Any]] = None,
                     timeout: float = RESOLVE_TIMEOUT_S, checked: Optional[Dict[str, str]] = None) -> str:
    """Why ``url`` cannot be read once its name is resolved; "" when every address of it is public.

    _url_problem judges the name only: a public name that resolves to 127.0.0.1, to the local network or to the
    metadata of a cloud (169.254.169.254) passed (audit of 12/11/2026). Called just before a request to a server
    a model or a portal named, never for one the user chose (a connector, a WFS of the settings, an open data
    platform of the list). The name is resolved again by the request itself, so a server that answers another
    address meanwhile (rebinding) is not stopped: this closes the plain case. The resolution runs in a thread of its
    own, ``timeout`` at most, so a slow resolver never holds QGIS long, and once per name in a tool call.

    Args:
        url: An address _url_problem already accepted.
        resolve: socket.getaddrinfo, or a stand-in for the tests.
        timeout: Seconds to wait for the resolver.
        checked: What the names already resolved in this tool call answered, filled here. It lives as long as the
            call: a longer memory would give a server more time to answer another address.
    """
    try:
        host = (urlsplit(url).hostname or "").strip("[]")
    except ValueError:
        return "this URL cannot be read"
    if not host:
        return "this URL cannot be read"
    try:
        ipaddress.ip_address(host)
        return ""  # an address, not a name: _url_problem judged it
    except ValueError:
        pass
    if checked is not None and host in checked:
        return checked[host]
    problem = _resolved_problem(host, resolve, timeout)
    if checked is not None:
        checked[host] = problem
    return problem


def _resolved_problem(host: str, resolve: Optional[Callable[..., Any]], timeout: float) -> str:
    found: Dict[str, Any] = {}

    def work() -> None:
        try:
            found["infos"] = (resolve or socket.getaddrinfo)(host, None)
        except (OSError, UnicodeError) as exc:
            found["error"] = exc

    worker = threading.Thread(target=work, name="FilterMate resolve", daemon=True)
    worker.start()
    worker.join(timeout)
    if worker.is_alive():
        return "the address of this server could not be checked in time"
    if "error" in found:
        return ""  # a name nobody knows: the request says so in its own words
    for info in found.get("infos") or ():
        try:
            address = ipaddress.ip_address(str(info[4][0]).split("%", 1)[0])
        except (ValueError, IndexError, TypeError):
            return "only a public address can be read"
        if not _public(address):
            return "only a public address can be read"
    return ""


@dataclass(frozen=True)
class RemoteFile:
    """What a server says of a file before it is read."""
    name: str  # for a copy on this machine: plain characters, and the extension GDAL knows the format by
    by_parts: bool  # the server gives parts of the file: GDAL can read it where it is
    size: int  # in bytes, -1 when the server does not say


def megabytes(size: int) -> str:
    return f"{size / 1048576:.1f} MB" if size < 10 * 1048576 else f"{size / 1048576:.0f} MB"


def _plain_name(text: str) -> str:
    """A file name with nothing a path or a provider URI would read."""
    return _UNSAFE_IN_NAME.sub("_", text).strip("._-")


def _last_part(text: str) -> str:
    return unquote(text).replace("\\", "/").rsplit("/", 1)[-1]


def is_web_page(headers: Mapping[str, str]) -> bool:
    return str(headers.get("content-type") or "").split(";", 1)[0].strip().lower() in _WEB_PAGES


def remote_file(url: str, status: int, headers: Mapping[str, str]) -> RemoteFile:
    """What the answer to a request for the first byte of ``url`` tells of the file.

    Its format is the extension of the name the server gives it (``Content-Disposition``), else of its address,
    else the format its address or its content type names: an export link has no file name.

    Raises:
        ValueError: The answer is an error or a web page; the message can be shown.
    """
    if status != 416 and not 200 <= status < 300:  # 416: an empty file, or a server that takes no range
        raise ValueError(f"its server answered with an error ({status})")
    content_type = str(headers.get("content-type") or "").split(";", 1)[0].strip().lower()
    if status != 416 and is_web_page(headers):  # a 416 comes with the error page of the server
        raise ValueError("this link is a web page, not a data file")
    parts = urlsplit(url)
    last = parts.path.rstrip("/").rsplit("/", 1)[-1]
    sent = _SENT_NAME.search(str(headers.get("content-disposition") or ""))
    names = [_last_part(sent.group(1))] if sent else []
    names.append(_last_part(last))
    stem, extension = "", ""
    for name in names:  # the extension is read before the name is made plain: 市区町村.zip is a zip
        base, dot, tail = name.rpartition(".")
        if dot and tail.lower() in LOCAL_FORMATS | {"zip"}:
            stem, extension = _plain_name(base), tail.lower()
            break
    if not extension:
        query = {key.lower(): values for key, values in parse_qs(parts.query).items()}
        asked = (query.get("format") or [""])[0]
        extension = (_FORMAT_WORDS.get(last.lower()) or _FORMAT_WORDS.get(asked.lower())
                     or _CONTENT_TYPES.get(content_type, ""))
        stem = _plain_name(names[0].rpartition(".")[0] or names[0])
        if stem.lower() in _FORMAT_WORDS or stem.lower() in _EXPORT_WORDS:  # says the format, not what it is
            stem = ""
    stem = stem[:MAX_NAME].strip("._-")
    if not stem or _WINDOWS_DEVICE.fullmatch(stem.split(".", 1)[0]):
        stem = "layer"
    by_parts = status == 206
    if by_parts:  # "bytes 0-0/1234"
        told = str(headers.get("content-range") or "").rsplit("/", 1)[-1].strip()
    else:
        told = str(headers.get("content-length") or "").strip() if status != 416 else ""
    return RemoteFile(stem + ("." + extension if extension else ""), by_parts,
                      int(told) if _BYTE_COUNT.fullmatch(told) else -1)


def reads_in_place(url: str, kind: str, found: RemoteFile) -> bool:
    """Whether GDAL reads the file where it is: its server gives parts of it, and its address says what it is.

    Anything else is downloaded first: an export made on request has no size and cannot be read by parts, and a
    text format (GeoJSON, CSV, KML) is read whole anyway.
    """
    return found.by_parts and (kind == "raster" or urlsplit(url).path.lower().rsplit(".", 1)[-1] in _READ_BY_PARTS)


def gdal_source(url: str) -> str:
    """How GDAL reads a public URL where it is. Built here, never written by a model."""
    return ("/vsizip//vsicurl/" if urlsplit(url).path.lower().endswith(".zip") else "/vsicurl/") + url


def archive_member(names: Sequence[str], kind: str) -> str:
    """The data file of a zip archive a layer is made of, a shapefile first; "" when none can be named.

    The names come from the archive, and the one returned ends in a source QGIS interprets: only plain ones.
    """
    for extension in _ARCHIVE_RASTERS if kind == "raster" else _ARCHIVE_VECTORS:
        for name in names:
            folders = name.split("/")
            if (name.lower().endswith("." + extension) and _PLAIN_MEMBER.fullmatch(name)
                    and not any(part.startswith((".", "__MACOSX")) or not part for part in folders)):
                return name
    return ""


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
