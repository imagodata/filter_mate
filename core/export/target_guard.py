# -*- coding: utf-8 -*-
"""
Which files do the layers of the project read from?

An export writes its target file, replacing it (``CreateOrOverwriteFile``,
``qgis:package`` OVERWRITE, ``os.remove``) and removes it again if the write
fails: exporting onto the GeoPackage a layer is read from destroys every layer
stored in it. This module finds the file behind each layer source so that the
exporters can refuse such a target.

Standard library only (no QGIS import): the parsing is testable on its own.
"""

import logging
import base64
import json
import os
import re
import zlib
from typing import Iterable, List, Optional, Tuple
from urllib.parse import unquote, urlparse

logger = logging.getLogger('FilterMate.Export')

_SPATIALITE_DBNAME = re.compile(r"dbname='((?:[^'\\]|\\.)*)'")
_GDAL_PREFIX = re.compile(r'^([A-Za-z][A-Za-z0-9_]+):(.+)$', re.DOTALL)
_WINDOWS_DRIVE = re.compile(r'^[A-Za-z]:[\\/]')
# prefixes of sources that are not a file at all
_NOT_FILES = {'PG', 'MYSQL', 'ODBC', 'OCI', 'MSSQLSPATIAL', 'WFS', 'WMS', 'WCS', 'HTTP', 'HTTPS', 'FTP', 'MEMORY'}


def _file_url_path(url: str) -> str:
    """Path of a ``file:`` URL (``file:///C:/a.csv?delimiter=,``, ``file://server/share/a.csv``)."""
    parsed = urlparse(url)
    path = unquote(parsed.path)
    if _WINDOWS_DRIVE.match(path[1:]):
        return path[1:]  # /C:/data/a.csv -> C:/data/a.csv
    if parsed.netloc and parsed.netloc != 'localhost':
        return '//' + parsed.netloc + path
    return path


def _subdataset_path(rest: str) -> str:
    """File part of a GDAL ``DRIVER:path:subdataset`` source (after the driver prefix)."""
    if rest.startswith('"'):
        end = rest.find('"', 1)
        return rest[1:end] if end > 0 else rest[1:]
    start = 2 if _WINDOWS_DRIVE.match(rest) else 0  # skip the "C:" of a Windows drive
    colon = rest.find(':', start)
    return rest[:colon] if colon >= 0 else rest


def layer_source_file_paths(source: str) -> List[str]:
    """Files a layer reads from (empty when its source is not a plain file).

    Handles the OGR form (``/data/a.gpkg|layername=roads``), the Spatialite form
    (``dbname='/data/b.sqlite' table=...``), ``file:///...`` URLs (delimited text:
    ``file:///data/a.csv?delimiter=,``) and GDAL subdatasets
    (``GPKG:/data/a.gpkg:table``, ``NETCDF:"/data/a.nc":var``). PostgreSQL, memory,
    remote and ``/vsi`` sources give nothing.

    Args:
        source: ``layer.source()``.

    Returns:
        list: File paths (one, today).
    """
    if not source or not isinstance(source, str):
        return []
    text = source.strip()
    match = _SPATIALITE_DBNAME.search(text)
    if match:
        if 'host=' in text or 'service=' in text:
            return []  # PostgreSQL: dbname is a database, not a file
        path = match.group(1)
    elif text.lower().startswith('file:'):
        path = _file_url_path(text)
    else:
        head = text.split('|')[0].strip()
        prefixed = _GDAL_PREFIX.match(head)
        if prefixed and not _WINDOWS_DRIVE.match(head) and not head.startswith('/'):
            if prefixed.group(1).upper() in _NOT_FILES:
                return []
            path = _subdataset_path(prefixed.group(2).strip())
        else:
            path = head
    if not path or path.startswith('/vsi') or '://' in path or not os.path.splitext(path)[1]:
        return []
    return [path]


def layer_source_file_path(source: str) -> Optional[str]:
    """First file a layer reads from, or None (see :func:`layer_source_file_paths`)."""
    paths = layer_source_file_paths(source)
    return paths[0] if paths else None


def _key(path: str) -> str:
    return os.path.normcase(os.path.abspath(path))


def _resolved(path: str) -> str:
    """Real path (symlinks resolved); a network share is not touched, it may be disconnected."""
    key = _key(path)
    if path.startswith(('\\\\', '//')):
        return key
    try:
        return os.path.normcase(os.path.realpath(path))
    except OSError:
        return key


def same_file(first: str, second: str) -> bool:
    """Whether two paths name one file (symlinks, ``..`` and case rules resolved)."""
    try:
        if os.path.exists(first) and os.path.exists(second):
            return os.path.samefile(first, second)
    except OSError:
        pass
    return _resolved(first) == _resolved(second)


class ProjectSources:
    """The files the layers of a project read from, worked out once.

    Building it parses every layer source and resolves each distinct file once;
    :meth:`layer_using` then compares a target with that list without touching the
    disk again for the sources (an unreachable network share is asked about once
    at most, not once per layer of an export).
    """

    def __init__(self, project, layers: Iterable = (), additional_sources: Iterable[Tuple[str, str]] = ()) -> None:
        self._entries = []  # (layer name, path, normalised key, real path)
        resolved = {}

        def add(name, source):
            for path in layer_source_file_paths(source):
                if path not in resolved:
                    resolved[path] = (_key(path), _resolved(path))
                self._entries.append((name, path) + resolved[path])

        try:
            project_layers = list(project.mapLayers().values()) if project is not None else []
        except Exception as e:  # a project we cannot inspect must not block the export
            logger.debug(f"Could not list the files the project layers read from: {e}")
            project_layers = []
        for layer in project_layers + list(layers):
            try:
                add(layer.name(), layer.source())
                # Derived layers read the cache now, but Unfilter / Undo and
                # project reload still need their original files intact.
                getter = getattr(layer, 'customProperty', None)
                raw = getter('filtermate/derived') if getter is not None else None
                if isinstance(raw, str) and raw.startswith('zlib:'):
                    raw = zlib.decompress(base64.b64decode(raw[5:], validate=True)).decode('utf-8')
                snapshot = json.loads(raw) if isinstance(raw, str) else raw
                if isinstance(snapshot, dict):
                    for key in ('source', 'original_source', 'enriched_source'):
                        add(layer.name(), snapshot.get(key))
            except (AttributeError, RuntimeError, TypeError, ValueError, zlib.error) as exc:
                logger.debug("Could not inspect an export source: %s", exc)
        for name, source in additional_sources:
            add(name, source)

    def __len__(self) -> int:
        return len(self._entries)

    def layer_using(self, output_path: str) -> Optional[str]:
        """Name of the project layer that reads from ``output_path``, if any."""
        if not output_path or not self._entries:
            return None
        target_key, target_real = _key(output_path), _resolved(output_path)
        target_name = os.path.basename(output_path).lower()
        for name, path, key, real in self._entries:
            if {target_key, target_real} & {key, real}:
                return name
            if os.path.basename(path).lower() == target_name and same_file(path, output_path):
                return name  # same name on a case-insensitive filesystem, or a hard link
        return None
