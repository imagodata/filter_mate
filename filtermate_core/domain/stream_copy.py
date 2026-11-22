# -*- coding: utf-8 -*-
"""Local copies of web services: what can be copied, where a copy goes, what is said before, what is kept.

A layer read from a web service (WFS, OGC API Features, ArcGIS Feature Service; WMS, WMTS, XYZ tiles) is copied
over the visible map to a file of this computer, and the layer then reads that file (2026-11-22). The project file
keeps the address of the service: it opens anywhere, with or without FilterMate, and the copy is found again next
to the project when it is there. Pure Python, no QGIS: the adapter is ``adapters/qgis/stream_copy.py``.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterable, Optional, Sequence, Tuple
from urllib.parse import parse_qsl, unquote, urlsplit

KIND_IMAGE = "image"  # what a server draws: copied as a GeoTIFF (red, green, blue, alpha)
KIND_FEATURES = "features"  # data: copied as a GeoPackage
# QGIS provider keys, lower case. The ``wms`` provider reads WMS, WMTS and XYZ tiles.
IMAGE_PROVIDERS = ("wms",)
FEATURE_PROVIDERS = ("wfs", "oapif", "arcgisfeatureserver")

# Servers whose terms forbid keeping their tiles: the copy is refused, whatever its size. OpenStreetMap: "Bulk
# downloading of tiles is prohibited", and so is using its tiles offline (tile usage policy). Google and Bing: their
# terms forbid caching or storing their imagery. A copy made by the filter of another layer (the capture of the area
# kept, never kept beyond the session) is not this.
_FORBIDDEN_HOSTS = (
    ("tile.openstreetmap.org", "OpenStreetMap"),
    ("tile.osm.org", "OpenStreetMap"),
    ("virtualearth.net", "Bing"),
)
# Google serves its tiles from many names (mt1.google.com, khms0.google.fr, *.googleapis.com, *.gstatic.com): any
# host with one of these labels.
_SECOND_LEVELS = ("co", "com", "ac", "gov", "org", "net", "ne", "or")
_FORBIDDEN_LABELS = (("google", "Google"), ("googleapis", "Google"), ("gstatic", "Google"), ("ggpht", "Google"))

FOLDER_SUFFIX = "_filtermate_local"
PROFILE_PARTS = ("filtermate", "local_copies")
UNSAVED = "unsaved_project"
PROPERTY = "filtermate/local_copy"
MAX_NAME = 60

# What one copy may cost, by default (APP.OPTIONS.STREAM_COPY): 64 million pixels (8,000 x 8,000), 200,000
# features, 10 minutes.
DEFAULT_MAX_PIXELS = 64_000_000
MIN_PIXELS = 65_536  # one tile of 256 pixels
MAX_PIXELS = 268_435_456  # 16,384 x 16,384, as the capture of the filter
DEFAULT_MAX_FEATURES = 200_000
DEFAULT_TIMEOUT_SECONDS = 600.0
# A WMS draws at any resolution: never finer than twice what the screen shows now.
SCREEN_DETAIL = 2.0
TILE_SIZE = 256
# What QGIS writes a raster by: blocks of this many pixels a side, one GetMap each for a WMS.
WRITER_BLOCK = 2000

_UNSAFE = re.compile(r"[^A-Za-z0-9._-]+")
_WINDOWS_DEVICE = re.compile(r"con|prn|aux|nul|com[0-9]|lpt[0-9]", re.IGNORECASE)
# Where QGIS keeps a project that is not a file of its own (QgsProjectStorage).
_PROJECT_STORAGES = ("geopackage:", "postgresql:", "postgres:", "oracle:", "mssql:", "hana:")
_QUOTED_URL = re.compile(r"""(?:^|\s)url=(['"])(.*?)\1""")


def copy_kind(provider: str) -> str:
    """``KIND_IMAGE``, ``KIND_FEATURES``, or "" for a layer that is not a web service FilterMate copies."""
    key = (provider or "").strip().lower()
    if key in IMAGE_PROVIDERS:
        return KIND_IMAGE
    if key in FEATURE_PROVIDERS:
        return KIND_FEATURES
    return ""


def service_url(source: str) -> str:
    """The address of the service in the source of a layer: ``url='...'`` (WFS) or ``&url=...`` (WMS, XYZ)."""
    source = source or ""
    quoted = _QUOTED_URL.search(source)
    if quoted:
        return quoted.group(2)
    for key, value in parse_qsl(source, keep_blank_values=True):
        if key.strip().lower() == "url":
            return unquote(value)
    return ""


def service_host(source: str) -> str:
    """The host the service is read from, lower case; a template part (``{s}.tile...``) is left out."""
    url = service_url(source)
    try:
        host = (urlsplit(url).hostname or "").lower()
    except ValueError:
        return ""
    if "}" in host:
        host = host.rsplit("}", 1)[1]
    elif "%7d" in host:
        host = host.rsplit("%7d", 1)[1]
    return host.lstrip(".")


def forbidden_by(source: str) -> str:
    """The name of the server whose terms forbid keeping its tiles ("OpenStreetMap"), or ""."""
    host = service_host(source).rstrip(".")  # "tile.openstreetmap.org." is the same server
    for forbidden, name in _FORBIDDEN_HOSTS:
        if host == forbidden or host.endswith("." + forbidden):
            return name
    # The registered name: google of google.fr, of google.co.uk and of google.com.br alike.
    labels = host.split(".")
    registered = labels[-3] if len(labels) >= 3 and labels[-2] in _SECOND_LEVELS else (labels[-2] if len(labels) >= 2 else "")
    for label, name in _FORBIDDEN_LABELS:
        if registered == label:
            return name
    return ""


# --- where the copies go ---------------------------------------------------------------------------------------

def project_folder(project_file: str) -> str:
    """``<folder of the project>/<name of the project>_filtermate_local``; "" for a project with no file of its own.

    A project never saved, or kept in a database or a GeoPackage (``geopackage:``, ``postgresql:``), has none: its
    copies go to the profile (``profile_folder``).
    """
    path = (project_file or "").strip()
    if not path or "://" in path or path.lower().startswith(_PROJECT_STORAGES):
        return ""
    cut = max(path.rfind("/"), path.rfind("\\"))  # a project of Windows read anywhere: both separators
    folder, name = (path[:cut], path[cut + 1:]) if cut >= 0 else ("", path)
    stem = os.path.splitext(name)[0]
    if not folder or not stem:
        return ""
    return folder + path[cut] + stem + FOLDER_SUFFIX


def profile_folder(profile_dir: str, project_file: str) -> str:
    """A folder of the QGIS profile for the copies of one project (by its path), or of the projects never saved."""
    tag = UNSAVED
    if (project_file or "").strip():
        stem = _plain(os.path.splitext(os.path.basename(project_file.rstrip("/\\")))[0])[:30] or "project"
        tag = stem + "_" + hashlib.sha256(project_file.encode("utf-8", "replace")).hexdigest()[:10]
    return os.path.join(profile_dir, *PROFILE_PARTS, tag)


def folder_candidates(project_file: str, profile_dir: str) -> Tuple[str, ...]:
    """Where a copy is written, in order: next to the project, then the profile."""
    return tuple(folder for folder in (project_folder(project_file), profile_folder(profile_dir, project_file))
                 if folder)


def _plain(text: str) -> str:
    return _UNSAFE.sub("_", text or "").strip("._-")


def file_name(layer_name: str, kind: str, stamp: str) -> str:
    """``<layer>_<stamp>.tif`` or ``.gpkg``: plain characters only, never a device name of Windows."""
    stem = _plain(layer_name)[:MAX_NAME].strip("._-") or "layer"
    if _WINDOWS_DEVICE.fullmatch(stem.split(".", 1)[0]):
        stem = "layer_" + stem
    suffix = ".tif" if kind == KIND_IMAGE else ".gpkg"
    return f"{stem}_{_plain(stamp)}{suffix}"


# --- what is said before -----------------------------------------------------------------------------------------

@dataclass(frozen=True)
class ImageEstimate:
    """What a copy of a web map will cost: its grid, the requests sent, and its size on disk at most."""

    columns: int
    rows: int
    resolution: float
    requests: int
    megabytes_at_most: float


def image_estimate(columns: int, rows: int, resolution: float, tiled: bool) -> ImageEstimate:
    """Requests: one per tile of 256 pixels for a tile service, one per block of the writer for a WMS.

    The size is that of the pixels uncompressed (red, green, blue, alpha) with their overviews (a third more): the
    file is compressed, so it is smaller, by how much depends on the image.
    """
    columns, rows = max(1, int(columns)), max(1, int(rows))
    step = TILE_SIZE if tiled else WRITER_BLOCK
    requests = math.ceil(columns / step) * math.ceil(rows / step)
    return ImageEstimate(columns, rows, float(resolution), requests, columns * rows * 4 * 4 / 3 / 1048576)


def finest_resolutions(native: Sequence[float], screen_resolution: float) -> Tuple[float, ...]:
    """The levels a capture may take: those of a tile service, or for a WMS (no level) twice the detail of the screen.

    ``screen_resolution``: map units per pixel of the map now, in the CRS of the layer.
    """
    levels = tuple(float(level) for level in native or ()
                   if isinstance(level, (int, float)) and not isinstance(level, bool)
                   and math.isfinite(level) and level > 0)
    if levels:
        return levels
    if isinstance(screen_resolution, (int, float)) and math.isfinite(screen_resolution) and screen_resolution > 0:
        return (float(screen_resolution) / SCREEN_DETAIL,)
    return ()


def bounded_number(value: Any, default: float, low: float, high: float) -> float:
    """A number of the configuration: ``default`` when unreadable or 0, else brought inside ``[low, high]``."""
    if isinstance(value, dict):
        value = value.get("value")
    if isinstance(value, str):
        value = value.replace(" ", "").replace(" ", "").replace("_", "")
    try:
        number = float(value) if value is not None and not isinstance(value, bool) else 0.0
    except (TypeError, ValueError, OverflowError):
        number = 0.0
    if not math.isfinite(number) or number <= 0:
        return default
    return min(high, max(low, number))


# --- what is kept with the layer ---------------------------------------------------------------------------------

@dataclass(frozen=True)
class LocalCopy:
    """A layer reading its local copy: the service it was copied from, the file, the area, and how complete it is.

    ``path`` is absolute in memory; the project file holds it relative to the project when it can
    (``QgsProject.writePath``). ``extent`` is ``(x_min, y_min, x_max, y_max)`` in ``crs``.
    """

    kind: str
    stream_source: str
    stream_provider: str
    path: str
    extent: Tuple[float, float, float, float]
    crs: str
    captured: str
    complete: bool = True
    features: int = -1
    resolution: float = 0.0
    holes: int = 0
    subset: str = ""  # the filter of the layer when its project was written: put back on the copy when it is read
    notes: Tuple[str, ...] = field(default_factory=tuple)
    opacity: float = -1.0  # of a web map: its service, offline, opens with no renderer to carry it

    def to_json(self) -> str:
        data = asdict(self)
        data["extent"] = list(self.extent)
        data["notes"] = list(self.notes)
        return json.dumps(data, ensure_ascii=False)

    @classmethod
    def from_json(cls, raw: Any) -> Optional["LocalCopy"]:
        """The record kept in a layer; None when it is missing or unreadable."""
        if not raw or not isinstance(raw, str):
            return None
        try:
            data = json.loads(raw)
        except (ValueError, RecursionError):
            return None
        if not isinstance(data, dict):
            return None
        try:
            extent = tuple(float(value) for value in data.get("extent") or ())
            if len(extent) != 4 or not all(math.isfinite(value) for value in extent):
                return None
            kind = str(data.get("kind") or "")
            if kind not in (KIND_IMAGE, KIND_FEATURES):
                return None
            source, provider, path = (str(data.get(key) or "") for key in ("stream_source", "stream_provider", "path"))
            if not (source and provider and path):
                return None
            notes = data.get("notes") or ()
            opacity = float(data.get("opacity", -1.0))
            return cls(kind, source, provider, path, extent, str(data.get("crs") or ""), str(data.get("captured") or ""),
                       bool(data.get("complete", True)), int(data.get("features", -1)),
                       float(data.get("resolution") or 0.0), int(data.get("holes") or 0), str(data.get("subset") or ""),
                       tuple(str(note) for note in notes) if isinstance(notes, (list, tuple)) else (),
                       opacity if math.isfinite(opacity) and 0.0 <= opacity <= 1.0 else -1.0)
        except (TypeError, ValueError, OverflowError):
            return None

    def with_path(self, path: str) -> "LocalCopy":
        return self.replaced(path=path)

    def replaced(self, **changes: Any) -> "LocalCopy":
        return LocalCopy(**{**self._fields(), **changes})

    def _fields(self) -> Dict[str, Any]:
        return {name: getattr(self, name) for name in self.__dataclass_fields__}


def same_path(first: str, second: str) -> bool:
    """Whether two spellings of a file path name the same file (case and slashes of Windows included)."""
    def key(path: str) -> str:
        return os.path.normcase(os.path.normpath((path or "").replace("\\", "/"))).replace("\\", "/")
    return bool(first) and bool(second) and key(first) == key(second)


def file_of_source(source: str) -> str:
    """The file a GDAL or OGR source reads (``path|layername=...`` for a GeoPackage table)."""
    return (source or "").split("|", 1)[0]


def is_copy_of(source: str, record: LocalCopy) -> bool:
    """Whether ``source`` reads the copy ``record`` names."""
    return same_path(file_of_source(source), record.path)


def unique(items: Iterable[str]) -> Tuple[str, ...]:
    return tuple(dict.fromkeys(item for item in items if item))


def free_path(path: str, taken) -> str:
    """``path``, or ``<stem>_2<ext>``, ``_3``... the first that ``taken(candidate)`` says is free."""
    stem, extension = os.path.splitext(path)
    candidate, number = path, 1
    while taken(candidate) and number < 1000:
        number += 1
        candidate = f"{stem}_{number}{extension}"
    return candidate
