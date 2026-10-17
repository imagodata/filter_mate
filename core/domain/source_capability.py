# -*- coding: utf-8 -*-
"""
Source capability - where the data of a layer lives and what its server can do.

Every vector layer that is not PostgreSQL, SpatiaLite or memory goes through
the OGR backend, which used to know nothing about web services: a WFS layer
was counted on the main thread, sorted client-side, filtered with an
unbounded key list and given "the first integer field" as its key.
:func:`classify` names, from the provider key and the data source string
alone, what FilterMate may do with a source:

- ``locality``: a local file, a database, a web service or a remote file
  (``/vsicurl/``, ``https://.../x.geojson``);
- ``server_filter``: the filter language the server applies (OGC Filter
  for WFS, CQL2 for OGC API Features, an SQL WHERE for ArcGIS Feature
  Services, the provider's SQL for files and databases);
- ``values``: RAW pixel values or a RENDERED image (WMS, XYZ / TMS tiles
  through GDAL ``<GDAL_WMS>``): a rendered raster is never analysed;
- ``network_cost``: HIGH when a feature count or a read goes over the
  network (never on the main thread);
- ``key_list_limit``: the longest key list FilterMate sends to the source
  (a web service gets ``IN (...)`` in a URL / request body);
- ``in_list_max``: the most literals one ``IN (...)`` may hold (Oracle:
  1000, ORA-01795), longer lists are split into ORed lists.

This is a PURE PYTHON module with NO QGIS dependencies: the QGIS provider
keys are compared in lower case (QGIS names them ``'WFS'``, ``'OAPIF'``,
``'arcgisfeatureserver'``, checked in QGIS 3.44).
"""
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional


class Locality(Enum):
    """Where the data of a layer lives."""

    LOCAL_FILE = "local_file"
    DATABASE = "database"
    REMOTE_SERVICE = "remote_service"
    REMOTE_FILE = "remote_file"


class ServerFilter(Enum):
    """Filter language applied by the data source itself."""

    NONE = "none"                  # evaluated by QGIS (memory, delimited text, rendered rasters)
    OGC_FILTER = "ogc_filter"      # WFS: QGIS translates the subset to an OGC Filter
    CQL2 = "cql2"                  # OGC API Features
    SQL_WHERE = "sql_where"        # ArcGIS Feature Service ``where=``
    PROVIDER_SQL = "provider_sql"  # OGR SQL / SQLite / the database's SQL


class ValueKind(Enum):
    """What the pixels of a raster are."""

    RAW = "raw"
    RENDERED = "rendered"


class NetworkCost(Enum):
    """Cost of a feature count / read: HIGH ones never run on the main thread."""

    LOW = "low"
    HIGH = "high"


# Longest key list sent to a web service (``"gml_id" IN (...)`` becomes an OGC
# Filter / CQL2 text / where= in every request): beyond it the filter is refused.
REMOTE_KEY_LIST_LIMIT = 500
# ORA-01795: maximum number of expressions in a list is 1000.
ORACLE_IN_LIST_MAX = 1000

# Vector web services (QGIS provider keys, lower case) and their filter language.
REMOTE_VECTOR_SERVICES = {
    'wfs': ServerFilter.OGC_FILTER,
    'oapif': ServerFilter.CQL2,
    'arcgisfeatureserver': ServerFilter.SQL_WHERE,
    'sensorthings': ServerFilter.NONE,
    'vectortile': ServerFilter.NONE,
    'arcgisvectortileservice': ServerFilter.NONE,
    'xyzvectortiles': ServerFilter.NONE,
}
# Raster web services: what their pixels are.
REMOTE_RASTER_SERVICES = {
    'wms': ValueKind.RENDERED,              # WMS, WMTS and XYZ tiles
    'arcgismapserver': ValueKind.RENDERED,
    'wcs': ValueKind.RAW,
}
REMOTE_SERVICE_PROVIDERS = frozenset(REMOTE_VECTOR_SERVICES) | frozenset(REMOTE_RASTER_SERVICES)
# Databases reached over the network that FilterMate has no backend for (OGR path).
NETWORK_DATABASES = ('mssql', 'oracle', 'hana', 'db2')
LOCAL_DATABASES = ('postgres', 'postgresraster')

# GDAL virtual file systems that read over the network.
_REMOTE_VSI = ('/vsicurl/', '/vsicurl?', '/vsis3/', '/vsiaz/', '/vsiadls/', '/vsigs/', '/vsioss/',
               '/vsiswift/', '/vsiwebhdfs/', '/vsihttp')
_URL_SCHEMES = ('http://', 'https://', 'ftp://')


@dataclass(frozen=True)
class SourceCapability:
    """What FilterMate may do with the data source of one layer."""

    provider_key: str
    locality: Locality
    server_filter: ServerFilter
    values: ValueKind = ValueKind.RAW
    network_cost: NetworkCost = NetworkCost.LOW
    key_list_limit: Optional[int] = None
    in_list_max: Optional[int] = None

    @property
    def is_remote(self) -> bool:
        """A web service or a remote file."""
        return self.locality in (Locality.REMOTE_SERVICE, Locality.REMOTE_FILE)

    @property
    def is_remote_service(self) -> bool:
        """A web service (WFS, OGC API Features, ArcGIS, WMS...)."""
        return self.locality is Locality.REMOTE_SERVICE

    @property
    def is_local(self) -> bool:
        """A local file (or a memory / virtual layer)."""
        return self.locality is Locality.LOCAL_FILE

    @property
    def counts_cheaply(self) -> bool:
        """Whether featureCount() may run on the main thread."""
        return self.network_cost is NetworkCost.LOW

    @property
    def has_raw_values(self) -> bool:
        """Whether raster pixels are values (False for a rendered image)."""
        return self.values is ValueKind.RAW


def _is_remote_path(text: str) -> bool:
    lower = text.strip().strip('"').strip("'").lower()
    return lower.startswith(_URL_SCHEMES) or any(prefix in lower for prefix in _REMOTE_VSI)


def _delimited_text_url(source: str) -> str:
    """The file URL of a delimited text source (``file:///x.csv?delimiter=...``)."""
    return source.split('?', 1)[0]


def classify(provider_key: str, source: str, is_raster: bool = False) -> SourceCapability:
    """Capability of a data source from its QGIS provider key and source string.

    Args:
        provider_key: ``layer.providerType()`` (any case).
        source: ``layer.source()``.
        is_raster: True for a raster layer (a GDAL source that is a service).

    Returns:
        SourceCapability: never None; an unknown provider is a local source
        filtered by QGIS.
    """
    key = (provider_key or '').strip().lower()
    text = source or ''
    stripped = text.lstrip().strip('"').strip("'")
    upper = stripped.upper()

    if key in REMOTE_VECTOR_SERVICES:
        return SourceCapability(key, Locality.REMOTE_SERVICE, REMOTE_VECTOR_SERVICES[key],
                                network_cost=NetworkCost.HIGH, key_list_limit=REMOTE_KEY_LIST_LIMIT)
    if key in REMOTE_RASTER_SERVICES:
        return SourceCapability(key, Locality.REMOTE_SERVICE, ServerFilter.NONE,
                                values=REMOTE_RASTER_SERVICES[key], network_cost=NetworkCost.HIGH)
    if key in LOCAL_DATABASES:
        return SourceCapability(key, Locality.DATABASE, ServerFilter.PROVIDER_SQL)
    if key in NETWORK_DATABASES:
        return SourceCapability(key, Locality.DATABASE, ServerFilter.PROVIDER_SQL, network_cost=NetworkCost.HIGH,
                                in_list_max=ORACLE_IN_LIST_MAX if key == 'oracle' else None)

    if key == 'gdal' or (is_raster and key not in ('virtualraster',)):
        # GDAL rasters: a WMS / tile service (rendered), a WCS (values) or a remote file.
        if upper.startswith('WMS:') or '<GDAL_WMS>' in upper:
            return SourceCapability(key, Locality.REMOTE_SERVICE, ServerFilter.NONE,
                                    values=ValueKind.RENDERED, network_cost=NetworkCost.HIGH)
        if upper.startswith('WCS:') or '<WCS_GDAL>' in upper:
            return SourceCapability(key, Locality.REMOTE_SERVICE, ServerFilter.NONE, network_cost=NetworkCost.HIGH)
        if _is_remote_path(text):
            return SourceCapability(key, Locality.REMOTE_FILE, ServerFilter.NONE, network_cost=NetworkCost.HIGH)
        return SourceCapability(key, Locality.LOCAL_FILE, ServerFilter.NONE)

    if key == 'ogr':
        # GDAL vector drivers opened by connection string.
        if upper.startswith('WFS:'):
            return SourceCapability(key, Locality.REMOTE_SERVICE, ServerFilter.OGC_FILTER,
                                    network_cost=NetworkCost.HIGH, key_list_limit=REMOTE_KEY_LIST_LIMIT)
        if upper.startswith('OAPIF:'):
            return SourceCapability(key, Locality.REMOTE_SERVICE, ServerFilter.CQL2,
                                    network_cost=NetworkCost.HIGH, key_list_limit=REMOTE_KEY_LIST_LIMIT)
        if upper.startswith('PG:'):
            return SourceCapability(key, Locality.DATABASE, ServerFilter.PROVIDER_SQL)
        if upper.startswith(('MSSQL:', 'OCI:')):
            return SourceCapability(key, Locality.DATABASE, ServerFilter.PROVIDER_SQL, network_cost=NetworkCost.HIGH,
                                    in_list_max=ORACLE_IN_LIST_MAX if upper.startswith('OCI:') else None)
        if _is_remote_path(text.split('|', 1)[0]):
            return SourceCapability(key, Locality.REMOTE_FILE, ServerFilter.PROVIDER_SQL, network_cost=NetworkCost.HIGH)
        return SourceCapability(key, Locality.LOCAL_FILE, ServerFilter.PROVIDER_SQL)

    if key == 'delimitedtext':
        if _is_remote_path(_delimited_text_url(text)):
            return SourceCapability(key, Locality.REMOTE_FILE, ServerFilter.NONE, network_cost=NetworkCost.HIGH)
        return SourceCapability(key, Locality.LOCAL_FILE, ServerFilter.NONE)

    if key in ('spatialite', 'virtual'):
        return SourceCapability(key, Locality.LOCAL_FILE, ServerFilter.PROVIDER_SQL)

    if key in ('memory', 'virtualraster', 'gpx', 'mdal', 'copc', 'ept', 'pdal', 'vpc', 'grass', 'grassraster'):
        return SourceCapability(key, Locality.LOCAL_FILE, ServerFilter.NONE)

    if _is_remote_path(text):
        return SourceCapability(key, Locality.REMOTE_FILE, ServerFilter.NONE, network_cost=NetworkCost.HIGH)
    return SourceCapability(key, Locality.LOCAL_FILE, ServerFilter.NONE)


def classify_layer(layer: Any, is_raster: bool = False) -> SourceCapability:
    """:func:`classify` on any object with ``providerType()`` and ``source()`` (duck-typed).

    Without QGIS (or for a deleted layer) the source is an empty string.
    """
    try:
        provider_key = layer.providerType()
    except (AttributeError, RuntimeError):
        provider_key = ''
    try:
        source = layer.source()
    except (AttributeError, RuntimeError):
        source = ''
    return classify(provider_key if isinstance(provider_key, str) else '',
                    source if isinstance(source, str) else '', is_raster)
