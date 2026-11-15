# -*- coding: utf-8 -*-
"""Where the agent can look for data: open data platforms and MCP connectors, as one list the user controls."""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from typing import Any, Dict, Iterable, List, Sequence, Tuple
from urllib.parse import urlsplit

from .basemaps import BASEMAPS, template_problem
from .elevation import SOURCES as ELEVATION_SOURCES
from .osm import SERVERS as OVERPASS_SERVERS
from .population import SOURCES as POPULATION_SOURCES
from .mcp_client import server_url_problem
from .open_data import (
    KIND_CKAN, KIND_DATABASE, KIND_DATAGOUV, KIND_ELEVATION, KIND_GEOCODER, KIND_OPENDATASOFT, KIND_OVERPASS,
    KIND_POPULATION, KIND_STAC, KIND_WFS, KIND_WMS, KIND_WMTS, KIND_XYZ,
    NO_DATA_KINDS, base_url,
)

KIND_MCP = "mcp"
USER_KINDS = (KIND_MCP, KIND_OPENDATASOFT, KIND_CKAN, KIND_WFS, KIND_WMS, KIND_WMTS, KIND_STAC, KIND_XYZ, KIND_GEOCODER,
              KIND_OVERPASS)
ORIGIN_OFFICIAL = "official"
ORIGIN_COMMUNITY = "community"
ORIGIN_LOCAL = "local"
ORIGIN_USER = "user"
MAX_CUSTOM = 30
_ID = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True)
class Source:
    """One platform or connector. ``address`` is a host for a platform, a URL for a service or a connector."""

    id: str
    title: str
    kind: str
    address: str
    origin: str = ORIGIN_USER
    note: str = ""

    @property
    def is_connector(self) -> bool:
        return self.kind == KIND_MCP


# Every entry was checked to answer without an account when it was added (2026-11-09). Chosen after the countries
# where QGIS plugins are downloaded most (plugins-analytics.qgis.org).
BUILT_IN: Tuple[Source, ...] = (
    Source("datagouv", "data.gouv.fr", KIND_DATAGOUV, "www.data.gouv.fr", ORIGIN_OFFICIAL, "France, open data"),
    Source("opendatasoft", "Opendatasoft", KIND_OPENDATASOFT, "data.opendatasoft.com", ORIGIN_COMMUNITY,
           "Public hub of the Opendatasoft portals"),
    Source("ign_wfs", "IGN Géoplateforme (WFS)", KIND_WFS, "https://data.geopf.fr/wfs/ows", ORIGIN_OFFICIAL,
           "France, vector reference data"),
    Source("ign_wmts", "IGN Géoplateforme (WMTS)", KIND_WMTS, "https://data.geopf.fr/wmts", ORIGIN_OFFICIAL,
           "France, maps and imagery as tiles: orthophotos by year, old maps, cadastre, relief, land cover"),
    Source("ign_wms", "IGN Géoplateforme (WMS)", KIND_WMS, "https://data.geopf.fr/wms-r", ORIGIN_OFFICIAL,
           "France, maps and imagery drawn on request, in the CRS of the project"),
    Source("ign_geocoder", "IGN Géoplateforme (places, France)", KIND_GEOCODER, "https://data.geopf.fr/geocodage/search",
           ORIGIN_OFFICIAL, "France: addresses, streets and communes, for where they are"),
    Source("photon", "Photon (places, worldwide)", KIND_GEOCODER, "https://photon.komoot.io/api", ORIGIN_COMMUNITY,
           "Worldwide, from OpenStreetMap: towns, streets, places. Run by komoot: no heavy use"),
    Source("earth_search", "Earth Search (Sentinel-2, Landsat)", KIND_STAC, "https://earth-search.aws.element84.com/v1",
           ORIGIN_COMMUNITY, "Worldwide satellite imagery, free on AWS"),
    Source("ibge_br", "IBGE (Brasil, WFS)", KIND_WFS, "https://geoservicos.ibge.gov.br/geoserver/wfs", ORIGIN_OFFICIAL,
           "Brazil, statistics and reference layers"),
    Source("prg_pl", "PRG (Polska, WFS)", KIND_WFS,
           "https://mapy.geoportal.gov.pl/wss/service/PZGIK/PRG/WFS/AdministrativeBoundaries", ORIGIN_OFFICIAL,
           "Poland, administrative boundaries"),
    Source("data_gov_uk", "data.gov.uk", KIND_CKAN, "ckan.publishing.service.gov.uk", ORIGIN_OFFICIAL, "United Kingdom"),
    Source("open_canada", "open.canada.ca", KIND_CKAN, "open.canada.ca/data", ORIGIN_OFFICIAL, "Canada"),
    Source("data_gov_au", "data.gov.au", KIND_CKAN, "data.gov.au/data", ORIGIN_OFFICIAL, "Australia"),
    Source("govdata_de", "GovData", KIND_CKAN, "ckan.govdata.de", ORIGIN_OFFICIAL, "Germany"),
    Source("dati_gov_it", "dati.gov.it", KIND_CKAN, "dati.gov.it/opendata", ORIGIN_OFFICIAL, "Italy"),
    Source("data_overheid_nl", "data.overheid.nl", KIND_CKAN, "data.overheid.nl/data", ORIGIN_OFFICIAL, "Netherlands"),
    Source("data_gov_ie", "data.gov.ie", KIND_CKAN, "data.gov.ie", ORIGIN_OFFICIAL, "Ireland"),
    Source("geospatial_jp", "G-Spatial (geospatial.jp)", KIND_CKAN, "www.geospatial.jp/ckan", ORIGIN_COMMUNITY, "Japan"),
    Source("datagouv_mcp", "data.gouv.fr (MCP)", KIND_MCP, "https://mcp.data.gouv.fr/mcp", ORIGIN_OFFICIAL,
           "Datasets, data services and table queries"),
    Source("statsmcp", "StatsMCP", KIND_MCP, "https://statsmcp.dev/mcp", ORIGIN_COMMUNITY,
           "Eurostat and national statistics offices"),
    Source("ckan_mcp", "CKAN portals (MCP)", KIND_MCP, "https://ckan-mcp-server.andy-pr.workers.dev/mcp", ORIGIN_COMMUNITY,
           "CKAN portals worldwide: data.gov, dati.gov.it, open.canada.ca..."),
    Source("socrata_mcp", "Socrata portals (MCP)", KIND_MCP, "https://socrata.caseyjhand.com/mcp", ORIGIN_COMMUNITY,
           "United States: city, state and federal open data portals"),
    Source("publicdata_au", "publicdata.au (MCP)", KIND_MCP, "https://publicdata.au/mcp", ORIGIN_COMMUNITY,
           "Australia, not endorsed by a government agency"),
    Source("geocontext", "IGN geocontext (MCP local)", KIND_MCP, "http://127.0.0.1:3000/mcp", ORIGIN_LOCAL,
           "IGN Géoplateforme tools. Start it first: TRANSPORT_TYPE=http npx -y @ignfab/geocontext"),
    Source("osm_mcp", "OpenStreetMap (MCP)", KIND_MCP, "https://openstreetmap.caseyjhand.com/mcp", ORIGIN_COMMUNITY,
           "Places and Overpass queries, worldwide"),
)
BUILT_IN += tuple(Source(server.id, server.title, KIND_OVERPASS, server.url, ORIGIN_COMMUNITY, server.note)
                  for server in OVERPASS_SERVERS)
BUILT_IN += tuple(Source(source.id, source.title, KIND_ELEVATION, source.base,
                         ORIGIN_OFFICIAL if source.official else ORIGIN_COMMUNITY, source.note)
                  for source in ELEVATION_SOURCES)
BUILT_IN += tuple(Source(source.id, source.title, KIND_POPULATION, source.base,
                         ORIGIN_OFFICIAL if source.official else ORIGIN_COMMUNITY, source.note)
                  for source in POPULATION_SOURCES)
BUILT_IN += tuple(Source(basemap.id, basemap.title, KIND_XYZ, basemap.url,
                         ORIGIN_OFFICIAL if basemap.official else ORIGIN_COMMUNITY, basemap.note)
                  for basemap in BASEMAPS)
_BUILT_IN_IDS = frozenset(source.id for source in BUILT_IN)


def make_source(address: str, kind: str, title: str = "") -> Source:
    """A source the user adds.

    Raises:
        ValueError: With the reason.
    """
    address = (address or "").strip()
    if kind not in USER_KINDS:
        raise ValueError("unknown type of source")
    if "," in address:
        raise ValueError("this address cannot be read")
    if kind != KIND_MCP:  # a connector keeps its address as given: /mcp/ and /mcp are not the same
        address = base_url(address.rstrip("/"))
    problem = (template_problem(address) if kind == KIND_XYZ else "") or server_url_problem(address)
    if problem:
        raise ValueError(problem)
    parts = urlsplit(address)
    origin = ORIGIN_LOCAL if parts.scheme == "http" else ORIGIN_USER
    if kind not in (KIND_MCP, KIND_WFS, KIND_WMS, KIND_WMTS, KIND_STAC, KIND_XYZ, KIND_GEOCODER, KIND_OVERPASS):
        address = parts.netloc if parts.scheme == "https" and not parts.path else address
    digest = hashlib.blake2b(f"{kind}|{address}".encode("utf-8"), digest_size=3).hexdigest()
    identifier = _ID.sub("_", f"{kind}_{parts.netloc}{parts.path}".lower()).strip("_")[:30] + "_" + digest
    return Source(identifier, " ".join((title or "").split())[:60] or parts.netloc, kind, address, origin)


def database_sources(names: Iterable[Any]) -> Tuple[Source, ...]:
    """The PostgreSQL connections of QGIS as sources the user can tick: not stored here, read from QGIS each time.

    A model names one by its id; the name of the connection is its title, and its address and its credentials stay
    in QGIS.
    """
    found = []
    for item in names:
        # (name, what it connects to): a connection made again under the same name, to another server, is another
        # source, not ticked.
        name, target = (str(item[0]), str(item[1])) if isinstance(item, (tuple, list)) else (str(item), "")
        digest = hashlib.blake2b(f"{name}|{target}".encode("utf-8"), digest_size=3).hexdigest()
        identifier = "db_" + _ID.sub("_", name.lower()).strip("_")[:24] + "_" + digest
        found.append(Source(identifier, " ".join(name.split())[:60] or identifier, KIND_DATABASE, name, ORIGIN_LOCAL,
                            "A PostgreSQL connection of QGIS: the agent can list its tables and add one as a layer"))
    return tuple(found)


def custom_to_json(sources: Iterable[Source]) -> str:
    return json.dumps([asdict(source) for source in sources], ensure_ascii=False)


def custom_from_json(text: str) -> List[Source]:
    """The sources the user added; what no longer passes the rules is dropped."""
    try:
        data = json.loads(text or "[]")
    except (ValueError, RecursionError):
        return []
    kept: List[Source] = []
    for item in data if isinstance(data, list) else []:
        if not isinstance(item, dict):
            continue
        try:
            source = make_source(str(item.get("address") or ""), str(item.get("kind") or ""), str(item.get("title") or ""))
        except ValueError:
            continue
        if source.id not in _BUILT_IN_IDS and all(source.id != other.id for other in kept):
            kept.append(source)
    return kept[:MAX_CUSTOM]


def all_sources(custom: Sequence[Source]) -> Tuple[Source, ...]:
    return BUILT_IN + tuple(custom)


def enabled(sources: Iterable[Source], enabled_ids: Sequence[str]) -> Tuple[Source, ...]:
    return tuple(source for source in sources if source.id in enabled_ids)


def platform_domains(sources: Iterable[Source]) -> str:
    """The user's portals, in the form ``open_data.parse_extra_domains`` reads."""
    return ",".join(f"{source.address}:{source.kind}" for source in sources
                    if not source.is_connector and source.id not in _BUILT_IN_IDS and source.kind != KIND_DATABASE)


def platform_name(source: Source) -> str:
    """What a model passes as ``platform``."""
    return source.id if source.id in _BUILT_IN_IDS else source.address.lower()


# Sources the user adds by the address of a service, a path and a query with it: a basemap, a geocoder, a WMS, a
# WMTS, a WFS, a STAC catalog. A portal (CKAN, Opendatasoft) is a host name.
_ADDRESSED = (KIND_XYZ, KIND_GEOCODER, KIND_WMS, KIND_WMTS, KIND_WFS, KIND_STAC, KIND_OVERPASS)


def model_name(source: Source) -> str:
    """What a model passes for a source of the chat: a service the user added by its address goes by its id.

    The address may hold the key of an account (``?apikey=...``), which the provider of the model, the thread and a
    recipe kept in the project must never see; and a model would have to copy a long address without a slip.
    """
    return source.id if source.kind in _ADDRESSED and source.id not in _BUILT_IN_IDS else platform_name(source)


def platform_aliases(sources: Iterable[Source]) -> Dict[str, str]:
    """For each source a model names otherwise than the plugin: the name of the model, and the platform it is."""
    return {model_name(source): platform_name(source) for source in sources
            if not source.is_connector and model_name(source) != platform_name(source)}


def describe_enabled(sources: Sequence[Source]) -> Dict[str, Any]:
    """Names for the instructions of the conversation."""
    def named(source: Source) -> str:
        name = model_name(source)
        return name if name == platform_name(source) else f"{name} ({source.title})"

    return {"platforms": [named(source) for source in sources
                          if not source.is_connector and source.kind not in NO_DATA_KINDS],
            "geocoders": [named(source) for source in sources if source.kind == KIND_GEOCODER],
            "basemaps": [named(source) for source in sources if source.kind == KIND_XYZ],
            "elevation": [named(source) for source in sources if source.kind == KIND_ELEVATION],
            "osm": [named(source) for source in sources if source.kind == KIND_OVERPASS],
            "population": [named(source) for source in sources if source.kind == KIND_POPULATION],
            "databases": [f"{source.id} ({source.title})" for source in sources if source.kind == KIND_DATABASE],
            "connectors": [source.title for source in sources if source.is_connector]}
