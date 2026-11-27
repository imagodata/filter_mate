# -*- coding: utf-8 -*-
"""Agent geodata belong to the open project, in RAM until the user chooses a destination.

GDAL virtual files keep their provider and their features when a layer is removed and restored by the
agent's undo stack. They are retained for the lifetime of the project, not of a conversation or panel.
No profile or operating-system temporary directory is used here. Disk writes are only made by persist(),
with an explicit destination, and never overwrite an existing dataset.
"""
from __future__ import annotations

import logging
import os
import re
import threading
import uuid
import json
import dataclasses
import xml.etree.ElementTree as ET  # nosec B405 - both VRT readers use _VrtTreeBuilder to reject DTDs
from contextlib import contextmanager
from typing import Dict

logger = logging.getLogger("FilterMate.AgentData")
PREFIX = "/vsimem/filtermate-agent-"
MAX_MEMORY_BYTES = 1024 * 1024 * 1024
NATIVE_OUTPUT_RESERVE = 128 * 1024  # conservative allowance per output container before a native writer starts
PERSISTENT_PROPERTY = "filtermate/agent/persistent_data"
_STORES = {}


def _gdal():
    from osgeo import gdal
    return gdal


def is_memory(path: str) -> bool:
    return isinstance(path, str) and path.startswith(PREFIX)


def memory_path(source: str) -> str:
    """The managed file in an OGR/GDAL source, including a member of a zip archive."""
    if not isinstance(source, str) or PREFIX not in source:
        return ""
    path = source[source.index(PREFIX):].split("|", 1)[0]
    if source.startswith("/vsizip/"):
        match = re.search(r"\.zip(?=/|$)", path, re.IGNORECASE)
        if match:
            path = path[:match.end()]
    return path


def exists(path: str) -> bool:
    return _gdal().VSIStatL(path) is not None if is_memory(path) else os.path.isfile(path)


def size(path: str) -> int:
    if is_memory(path):
        stat = _gdal().VSIStatL(path)
        return stat.size if stat else 0
    return os.path.getsize(path) if os.path.isfile(path) else 0


def discard(path: str) -> None:
    """Discard one managed asset and its sidecars; never remove a user's directory."""
    if not is_memory(path):
        return
    parts = path[len(PREFIX):].split("/")
    if len(parts) < 3:
        return
    _gdal().RmdirRecursive(PREFIX + parts[0] + "/" + parts[1])


class AgentDataStore:
    def __init__(self, limit: int = MAX_MEMORY_BYTES):
        self.root = PREFIX + uuid.uuid4().hex
        self.limit = limit
        self.persisted: Dict[str, str] = {}
        self.protected = set()
        self.destination = ""
        self._lock = threading.RLock()
        self._closed = False
        self._writers = 0

    def new_path(self, name: str, expected_bytes: int = 0) -> str:
        with self._lock:
            if self._closed:
                raise ValueError("the project was closed")
            self.check_capacity(expected_bytes)
            folder = self.root + "/" + uuid.uuid4().hex
            _gdal().MkdirRecursive(folder, 0o700)
            # A tool supplies a file name, never a location from the model.
            name = re.sub(r"[^\w. -]", "_", os.path.basename(name.replace("\\", "/")))
            return folder + "/" + (name.strip(". ") or "layer")

    def disk_path(self, name: str) -> str:
        """For a file-only provider, only after the user selected and saved a project destination."""
        if not self.destination:
            raise ValueError("this output needs files on disk: use Save project and layers in the agent menu "
                             "to choose a destination, then run the request again")
        folder = os.path.join(self.destination, uuid.uuid4().hex)
        os.makedirs(folder)
        return os.path.join(folder, os.path.basename(name))

    def check_capacity(self, extra: int = 0) -> None:
        gdal = _gdal()
        used = sum(size(self.root + "/" + name) for name in (gdal.ReadDirRecursive(self.root) or ())
                   if not name.endswith("/"))
        if used + max(0, extra) > self.limit:
            raise ValueError("the agent's memory budget is full: use a smaller area or resolution. "
                             "To release data retained for Undo, save the project and its layers, then close and "
                             "reopen the saved project. Saving alone retains these data in memory")

    @contextmanager
    def native_outputs(self, paths, feedback, interval=0.05):
        """Guard native GDAL/OGR output files, which do not pass through ``writer``.

        Cancellation is cooperative: a provider may allocate between checks or ignore cancellation.
        Always reject an over-budget result before adding its layers. Own only fresh managed assets;
        their files and sidecars are removed on failure, while pre-existing inputs and undo data stay.
        A lease also keeps project-close cleanup from unlinking a live native writer's files.
        """
        owned = list(dict.fromkeys(path for path in paths if is_memory(path)))
        if not owned:
            yield
            return
        for path in owned:
            if not path.startswith(self.root + '/'):
                raise ValueError('an output belongs to another project')
            if _gdal().ReadDirRecursive(os.path.dirname(path)):
                raise ValueError('a native output must use a fresh managed asset')
        stopped = threading.Event()
        errors = []

        def check():
            with self._lock:
                if self._closed:
                    raise ValueError('the project was closed')
                self.check_capacity()

        def watch():
            while not stopped.wait(interval):
                try:
                    check()
                except Exception as exc:
                    errors.append(exc)
                    # Native feedback marshals this request to its owning GUI thread.
                    getattr(feedback, 'request_cancel', feedback.cancel)()
                    return

        monitor = threading.Thread(target=watch, name='FilterMateNativeBudget', daemon=True)
        success = False
        with self._lock:
            if self._closed:
                raise ValueError('the project was closed')
            self._writers += 1
        try:
            self.check_capacity(NATIVE_OUTPUT_RESERVE * len(owned))
            monitor.start()
            failure = None
            try:
                yield
            except Exception as exc:
                failure = exc
            finally:
                stopped.set()
                monitor.join()
            if errors:
                raise ValueError(str(errors[0]))
            if failure is not None:
                raise failure
            check()
            success = True
        finally:
            if not success:
                for path in owned:
                    discard(path)
            with self._lock:
                self._writers -= 1
                if self._closed and not self._writers:
                    _gdal().RmdirRecursive(self.root)

    @contextmanager
    def writer(self, path: str):
        """A bounded streaming sink, also safe when the project closes during an HTTP request."""
        gdal = _gdal()
        with self._lock:
            if self._closed:
                raise ValueError("the project was closed")
            handle = gdal.VSIFOpenL(path, "wb")
            if handle is None:
                raise ValueError("the downloaded data could not be held in memory")
            self._writers += 1
        try:
            def write(chunk: bytes):
                with self._lock:
                    if self._closed:
                        raise ValueError("the project was closed")
                    self.check_capacity(len(chunk))
                    if gdal.VSIFWriteL(chunk, 1, len(chunk), handle) != len(chunk):
                        raise ValueError("the downloaded data could not be held in memory")
            yield write
        finally:
            gdal.VSIFCloseL(handle)
            with self._lock:
                self._writers -= 1
                if self._closed and not self._writers:
                    gdal.RmdirRecursive(self.root)

    def close(self):
        with self._lock:
            self._closed = True
            if not self._writers:
                _gdal().RmdirRecursive(self.root)

    def resolve(self, source: str) -> str:
        path = memory_path(source)
        saved = self.persisted.get(path)
        return source.replace(path, saved.replace('\\', '/'), 1) if saved and os.path.isfile(saved) else source


def store_for(project=None) -> AgentDataStore:
    from qgis.core import QgsProject
    project = project if project is not None else QgsProject.instance()
    key = id(project)
    if key not in _STORES:
        store = AgentDataStore()
        for layer in project.mapLayers().values():
            if layer.customProperty(PERSISTENT_PROPERTY) is True:
                store.protected.add(layer.source().split('|', 1)[0])
        _STORES[key] = store

        def cleared():
            _STORES.pop(key, None)
            store.close()
            try:
                project.cleared.disconnect(cleared)
            except (TypeError, RuntimeError):
                pass
        project.cleared.connect(cleared)
    return _STORES[key]


def new_path(name: str, expected_bytes: int = 0, project=None) -> str:
    return store_for(project).new_path(name, expected_bytes)


def read_bytes(path: str) -> bytes:
    gdal = _gdal()
    handle = gdal.VSIFOpenL(path, "rb")
    if handle is None:
        raise ValueError("the data in memory could not be read")
    try:
        return bytes(gdal.VSIFReadL(1, size(path), handle))
    finally:
        gdal.VSIFCloseL(handle)


def pending_layers(project=None):
    from qgis.core import QgsProject
    project = project if project is not None else QgsProject.instance()
    return [layer for layer in project.mapLayers().values() if _layer_sources(layer)]


def _layer_sources(layer):
    sources = [layer.source()]
    raw = layer.customProperty('filtermate/derived')
    if isinstance(raw, str) and raw:
        try:
            state = json.loads(raw)
            sources.extend(state.get(key, '') for key in ('original_source', 'enriched_source'))
        except (ValueError, AttributeError):
            pass
    return [source for source in sources if memory_path(source)]


class _VrtTreeBuilder(ET.TreeBuilder):
    """VRTs need no DTD: reject it before an entity can be expanded, in any XML encoding."""

    def doctype(self, name, pubid, system):
        raise ValueError("VRT documents must not contain a DTD")


def _dependencies(path):
    if path.lower().endswith('.vrt'):
        parser = ET.XMLParser(target=_VrtTreeBuilder())  # nosec B314 - custom target rejects DTDs and entity declarations
        document = ET.fromstring(read_bytes(path), parser=parser)  # nosec B314 - parser rejects all DTDs
        return [memory_path(node.text) for node in document.iter()
                if node.tag in ('SourceDataset', 'SourceFilename') and memory_path(node.text)]
    return []


def _rewrite_vrt(path, copied):
    parser = ET.XMLParser(target=_VrtTreeBuilder())  # nosec B314 - custom target rejects DTDs and entity declarations
    document = ET.parse(path, parser=parser)  # nosec B314 - parser rejects all DTDs
    for node in document.iter():
        if node.tag in ('SourceDataset', 'SourceFilename') and memory_path(node.text) in copied:
            source = memory_path(node.text)
            node.text = node.text.replace(source, os.path.relpath(copied[source], os.path.dirname(path)).replace('\\', '/'), 1)
            node.set('relativeToVRT', '1')
    document.write(path, encoding='utf-8', xml_declaration=True)


def _copy_file(source: str, destination: str):
    """Stream a virtual file to its chosen destination, without duplicating it in RAM."""
    gdal = _gdal()
    handle = gdal.VSIFOpenL(source, "rb")
    if handle is None:
        raise ValueError("the data in memory could not be read")
    created = False
    try:
        with open(destination, "xb") as out:
            created = True
            while True:
                chunk = gdal.VSIFReadL(1, 1024 * 1024, handle)
                if not chunk:
                    break
                out.write(chunk)
        if os.path.getsize(destination) != size(source):
            raise ValueError("the saved data are incomplete; the layers stay in memory")
    except Exception:
        if created:
            os.unlink(destination)
        raise
    finally:
        gdal.VSIFCloseL(handle)


def _asset_destinations(names, primary, folder, reserved):
    """Keep a dataset and its sidecars together, suffixing the whole group on a name collision."""
    stem = os.path.splitext(primary)[0]
    number = 1
    while True:
        suffix = "" if number == 1 else f"_{number}"
        destinations = {}
        for name in names:
            if name == stem or name.casefold().startswith((stem.casefold() + ".", stem.casefold() + "-")):
                renamed = name[:len(stem)] + suffix + name[len(stem):]
            else:
                base, extension = os.path.splitext(name)
                renamed = base + suffix + extension
            destinations[name] = os.path.join(folder, renamed)
        keys = {os.path.normcase(path) for path in destinations.values()}
        if len(keys) != len(destinations):
            raise ValueError("the dataset has conflicting filenames on this filesystem")
        if not keys.intersection(reserved) and not any(os.path.lexists(path) for path in destinations.values()):
            reserved.update(keys)
            return destinations
        number += 1


def persist(project, project_path: str, *, write_project: bool = True) -> str:
    """Save complete sources (not just filtered features), then rebind the existing layer objects.

    Datasets and sidecars go directly beside the chosen project. Existing names get a numeric suffix. A failure
    restores the sources and removes only the new files. Memory assets remain available to undo/redo.
    """
    from qgis.core import QgsDataProvider, QgsReadWriteContext
    from qgis.PyQt.QtXml import QDomDocument
    project_path = os.path.abspath(project_path)
    if not project_path.lower().endswith((".qgz", ".qgs")):
        raise ValueError("choose a QGIS project file (.qgz or .qgs)")
    parent = os.path.dirname(project_path)
    if not os.path.isdir(parent):
        raise ValueError("the chosen project folder does not exist")
    layers = pending_layers(project)
    if any(getattr(layer, "isEditable", lambda: False)() for layer in layers):
        raise ValueError("save or discard the layer edits before saving the project and its data")
    store = store_for(project)
    snapshots, copied, created, groups = [], {}, [], {}
    reserved = {os.path.normcase(project_path)}
    old_name, old_dirty = project.fileName(), project.isDirty()
    old_paths = project.filePathStorage()
    try:
        # A virtual asset folder also holds sidecars and the members of multi-file formats.
        pending = [memory_path(source) for layer in layers for source in _layer_sources(layer)]
        while pending:
            path = pending.pop()
            if path in copied:
                continue
            pending.extend(_dependencies(path))
            source_folder = path.rsplit("/", 1)[0]
            primary = path.rsplit("/", 1)[-1]
            if source_folder not in groups:
                names = sorted(name for name in (_gdal().ReadDir(source_folder) or ()) if name not in (".", ".."))
                destinations = _asset_destinations(names, primary, parent, reserved)
                for name, target in destinations.items():
                    _copy_file(source_folder + "/" + name, target)
                    created.append(target)
                groups[source_folder] = destinations
            copied[path] = groups[source_folder][primary]
        for path, target in copied.items():
            if path.lower().endswith('.vrt'):
                _rewrite_vrt(target, copied)
        context = QgsReadWriteContext()
        for layer in layers:
            document = QDomDocument()
            element = document.createElement("maplayer")
            document.appendChild(element)
            layer.writeLayerXml(element, document, context)
            selection = layer.selectedFeatureIds() if hasattr(layer, 'selectedFeatureIds') else None
            from ..qgis.coverage_layers.snapshots import registry
            derived = registry().get(layer.id())
            snapshots.append((layer, document, selection, derived))
            source = layer.source()
            path = memory_path(source)
            durable_source = source.replace(path, copied[path].replace('\\', '/'), 1) if path else source
            layer.setDataSource(durable_source, layer.name(), layer.providerType(),
                                QgsDataProvider.ProviderOptions(), False)
            if not layer.isValid():
                raise ValueError("a saved layer could not be opened; the layers stay in memory")
            # Restore the full layer state with just its datasource changed: styles, joins, subset, forms,
            # layer id, metadata, named styles and custom properties all survive the provider change.
            replacement = document.cloneNode(True).toDocument()
            node = replacement.documentElement().firstChildElement("datasource")
            if not node.isNull():
                while not node.firstChild().isNull():
                    node.removeChild(node.firstChild())
                node.appendChild(replacement.createTextNode(durable_source))
            if not layer.readLayerXml(replacement.documentElement(), context) or not layer.isValid():
                raise ValueError("a saved layer could not be restored; the layers stay in memory")
            if selection is not None:
                layer.selectByIds(selection)
            if derived is not None:
                def resolve(source):
                    path = memory_path(source)
                    return source.replace(path, copied[path].replace('\\', '/'), 1) if path in copied else source
                registry().record(dataclasses.replace(derived, source=durable_source,
                    original_source=resolve(derived.original_source), enriched_source=resolve(derived.enriched_source)), layer)
            layer.setCustomProperty(PERSISTENT_PROPERTY, True)
            # A local copy must open as a durable local layer even without FilterMate installed.
            from ...core.domain.stream_copy import PROPERTY, LocalCopy
            record = LocalCopy.from_json(layer.customProperty(PROPERTY))
            if record is not None:
                layer.setCustomProperty(PROPERTY, record.with_path(copied.get(record.path, record.path)).to_json())
        if write_project:
            from qgis.core import Qgis
            project.setFileName(project_path)
            project.setFilePathStorage(Qgis.FilePathType.Relative)
            if not project.write():
                raise ValueError("the project could not be saved; the layers stay in memory")
        store.persisted.update(copied)
        store.protected.update(copied.values())
        store.destination = parent
        return parent if copied else ""
    except Exception:
        for layer, document, selection, derived in reversed(snapshots):
            layer.readLayerXml(document.documentElement(), QgsReadWriteContext())
            if derived is not None:
                registry().record(derived, layer)
            if selection is not None:
                layer.selectByIds(selection)
        project.setFileName(old_name)
        project.setFilePathStorage(old_paths)
        project.setDirty(old_dirty)
        for path in reversed(created):
            try:
                os.unlink(path)
            except OSError:
                logger.warning("A newly saved dataset could not be removed: %s", path, exc_info=True)
        raise
