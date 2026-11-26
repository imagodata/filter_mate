# -*- coding: utf-8 -*-
"""rewrite_saved_layer / reattach_project / switch_to_stream (adapters/qgis/stream_copy.py): a filter set on the
local copy in the language of the copy never goes back on the service (audit of 2026-11-24).

A GeoPackage filter such as ``json_each`` does not parse as QGIS and the WFS does not read it: put back as it is,
the layer reads everything with the filter text still displayed. The project file holds the service without it,
the record keeps it for the copy, the copy reads it again when the project is read, and going back to the service
drops it with a note.

The module loads for real under a synthetic package; qgis.core only gives QgsTask, QgsDataSourceUri (a stand-in
with the parameters the copy reads and writes) and QgsExpression (valid unless it names ``json_each``); the derived
sources registry is a stand-in recording what source each layer reads.
"""
import importlib
import os
import pathlib
import sys
import tempfile
import types

import pytest

pytestmark = pytest.mark.unit

_ROOT = pathlib.Path(__file__).resolve().parents[4]
_PKG = "fm_stream_copy_project_test"

SQLITE_SUBSET = '"tags" IN (SELECT value FROM json_each("tags"))'
QGIS_SUBSET = '"num" < 1000'
SERVICE = "url=http://127.0.0.1:9999/wfs&typename=fm:capped&version=auto"


class _Uri:
    """QgsDataSourceUri stand-in: the parameters of a source, read and written."""

    def __init__(self, source=""):
        self._params = {}
        for part in str(source or "").split("&"):
            if "=" in part:
                key, value = part.split("=", 1)
                self._params[key.strip().lower()] = value

    def param(self, name):
        return self._params.get((name or "").lower(), "")

    def removeParam(self, key):
        self._params.pop((key or "").lower(), None)

    def setParam(self, key, value):
        self._params[(key or "").lower()] = value

    def setSql(self, sql):
        self._sql = sql

    def uri(self, _expand=True):
        parts = [f"{key}={value}" for key, value in self._params.items()]
        if getattr(self, "_sql", ""):
            parts.append(f"sql={self._sql}")
        return "&".join(parts)


class _Expression:
    """QgsExpression stand-in: json_each is SQLite, unknown to QGIS."""

    def __init__(self, text):
        self._text = text or ""

    def isValid(self):
        return "json_each" not in self._text


class _Task:
    Flag = types.SimpleNamespace(CanCancel=1)


class _Signal:
    def connect(self, _slot):
        pass


class _QgsProjectType:
    """QgsProject stand-in: install() only connects its hooks."""

    writeMapLayer = _Signal()
    readProject = _Signal()

    @classmethod
    def instance(cls):
        return cls()


class _Layer:
    """A vector layer stand-in: source, provider, subset and custom properties."""

    def __init__(self, source, provider, subset="", layer_id="lyr1", name="Capped"):
        self._source = source
        self._provider = provider
        self._subset = subset
        self._id = layer_id
        self._name = name
        self._props = {}
        self.subsets = [subset]
        self.repaints = 0

    def source(self):
        return self._source

    def providerType(self):
        return self._provider

    def subsetString(self):
        return self._subset

    def setSubsetString(self, value):
        self._subset = value
        self.subsets.append(value)
        return True

    def isValid(self):
        return True

    def isEditable(self):
        return False

    def renderer(self):
        return None

    def customProperty(self, key):
        return self._props.get(key)

    def setCustomProperty(self, key, value):
        self._props[key] = value

    def removeCustomProperty(self, key):
        self._props.pop(key, None)

    def id(self):
        return self._id

    def name(self):
        return self._name

    def triggerRepaint(self):
        self.repaints += 1


class _Resolver:
    def writePath(self, path):
        return path

    def readPath(self, path):
        return path


class _Project:
    def __init__(self, layers):
        self._layers = {layer.id(): layer for layer in layers}

    def mapLayers(self):
        return dict(self._layers)

    def pathResolver(self):
        return _Resolver()

    def absoluteFilePath(self):
        return ""


def _snapshots_module():
    module = types.ModuleType(f"{_PKG}.adapters.qgis.coverage_layers.snapshots")
    state = {"swaps": []}

    def registry():
        return types.SimpleNamespace(get=lambda _key: None, is_derived=lambda _key: False)

    def swap_source(layer, source, provider, _registry=None):
        layer._source = source
        layer._provider = provider
        state["swaps"].append((source, provider))
        return True

    def _set_text(element, _document, tag, text):
        element["tags"][tag] = text

    def _set_custom_property(element, _document, name, value):
        element["props"][name] = value

    def _remove_custom_property(element, name):
        element["props"].pop(name, None)

    def _set_tree_layer_source(document, layer_id, source, provider):
        document["tree"][layer_id] = (source, provider)

    module.registry = registry
    module.swap_source = swap_source
    module._set_text = _set_text
    module._set_custom_property = _set_custom_property
    module._remove_custom_property = _remove_custom_property
    module._set_tree_layer_source = _set_tree_layer_source
    module.state = state
    return module


def _load():
    for name, path in (("", _ROOT), (".core", _ROOT / "core"), (".core.domain", _ROOT / "core" / "domain"),
                       (".adapters", _ROOT / "adapters"), (".adapters.qgis", _ROOT / "adapters" / "qgis"),
                       (".adapters.qgis.coverage_layers", _ROOT / "adapters" / "qgis" / "coverage_layers")):
        package = types.ModuleType(_PKG + name)
        package.__path__ = [str(path)]
        sys.modules[_PKG + name] = package
    sys.modules[f"{_PKG}.adapters.qgis.coverage_layers.snapshots"] = _snapshots_module()
    core = sys.modules["qgis.core"]
    saved = {name: getattr(core, name, None) for name in ("QgsTask", "QgsDataSourceUri", "QgsExpression")}
    core.QgsTask, core.QgsDataSourceUri, core.QgsExpression = _Task, _Uri, _Expression
    try:
        return importlib.import_module(f"{_PKG}.adapters.qgis.stream_copy")
    finally:
        for name, value in saved.items():
            if value is None:
                delattr(core, name)
            else:
                setattr(core, name, value)


stream_copy = _load()
rules = stream_copy.rules


@pytest.fixture(autouse=True)
def qgis_stand_ins(monkeypatch):
    monkeypatch.setattr(sys.modules["qgis.core"], "QgsDataSourceUri", _Uri, raising=False)
    monkeypatch.setattr(sys.modules["qgis.core"], "QgsExpression", _Expression, raising=False)
    monkeypatch.setattr(sys.modules["qgis.core"], "QgsProject", _QgsProjectType, raising=False)


def _copy_path():
    handle, path = tempfile.mkstemp(prefix="fm-copy-", suffix=".gpkg")
    os.close(handle)
    return path


def _drop(path):
    try:
        os.remove(path)
    except OSError:
        pass


def _record(path, subset=""):
    return rules.LocalCopy(kind=rules.KIND_FEATURES, stream_source=SERVICE, stream_provider="wfs", path=path,
                           extent=(-5.0, -5.0, 405.0, 205.0), crs="EPSG:3857", captured="2026-11-24T00:00:00",
                           subset=subset)


def _element():
    return {"tags": {}, "props": {}}


def test_project_holds_service_without_copy_side_filter_but_record_keeps_it():
    path = _copy_path()
    try:
        record = _record(path)
        layer = _Layer(f"{path}|layername=capped", "ogr", SQLITE_SUBSET)
        layer.setCustomProperty(rules.PROPERTY, record.to_json())
        element, document = _element(), {"tree": {}}
        stream_copy.rewrite_saved_layer(_Project([layer]), layer, element, document)
        assert "json_each" not in element["tags"]["datasource"]
        assert "filter=" not in element["tags"]["datasource"]
        assert "127.0.0.1:9999" in element["tags"]["datasource"]
        stored = rules.LocalCopy.from_json(element["props"][rules.PROPERTY])
        assert stored is not None and stored.subset == SQLITE_SUBSET
        assert rules.LocalCopy.from_json(layer.customProperty(rules.PROPERTY)).subset == SQLITE_SUBSET
    finally:
        _drop(path)


def test_project_keeps_service_readable_filter_on_service_and_record():
    path = _copy_path()
    try:
        record = _record(path)
        layer = _Layer(f"{path}|layername=capped", "ogr", QGIS_SUBSET)
        layer.setCustomProperty(rules.PROPERTY, record.to_json())
        element, document = _element(), {"tree": {}}
        stream_copy.rewrite_saved_layer(_Project([layer]), layer, element, document)
        assert "filter=" in element["tags"]["datasource"]
        assert rules.LocalCopy.from_json(element["props"][rules.PROPERTY]).subset == QGIS_SUBSET
    finally:
        _drop(path)


def test_read_again_applies_record_filter_to_copy_when_service_holds_none():
    path = _copy_path()
    try:
        stored = _record(path, SQLITE_SUBSET)
        layer = _Layer(SERVICE, "wfs", "")
        layer.setCustomProperty(rules.PROPERTY, stored.to_json())
        reattached, missing = stream_copy.reattach_project(_Project([layer]))
        assert (reattached, missing) == (1, [])
        assert layer.providerType() == "ogr"
        assert layer.subsetString() == SQLITE_SUBSET
    finally:
        _drop(path)


def test_read_again_keeps_service_filter_from_project():
    path = _copy_path()
    try:
        stored = _record(path, QGIS_SUBSET)
        layer = _Layer(f"{SERVICE}&filter={QGIS_SUBSET}", "wfs", QGIS_SUBSET)
        layer.setCustomProperty(rules.PROPERTY, stored.to_json())
        reattached, _missing = stream_copy.reattach_project(_Project([layer]))
        assert reattached == 1
        assert layer.subsetString() == QGIS_SUBSET
    finally:
        _drop(path)


def test_back_to_service_drops_copy_side_filter_with_a_note():
    path = _copy_path()
    try:
        layer = _Layer(f"{path}|layername=capped", "ogr", SQLITE_SUBSET)
        layer.setCustomProperty(rules.PROPERTY, _record(path).to_json())
        notes = stream_copy.switch_to_stream(layer)
        assert layer.providerType() == "wfs"
        assert layer.subsetString() == ""
        assert notes
    finally:
        _drop(path)


def test_back_to_service_keeps_service_readable_filter():
    path = _copy_path()
    try:
        layer = _Layer(f"{path}|layername=capped", "ogr", QGIS_SUBSET)
        layer.setCustomProperty(rules.PROPERTY, _record(path).to_json())
        assert stream_copy.switch_to_stream(layer) == []
        assert layer.subsetString() == QGIS_SUBSET
    finally:
        _drop(path)


def test_stored_service_readable_filter_is_not_resurrected_once_cleared():
    """A stale compatible subset in the record never comes back: the project source decides."""
    path = _copy_path()
    try:
        stored = _record(path, QGIS_SUBSET)
        layer = _Layer(SERVICE, "wfs", "")
        layer.setCustomProperty(rules.PROPERTY, stored.to_json())
        reattached, _missing = stream_copy.reattach_project(_Project([layer]))
        assert reattached == 1
        assert layer.subsetString() == ""
    finally:
        _drop(path)


def test_clearing_copy_filter_updates_the_record_before_reopening():
    path = _copy_path()
    try:
        layer = _Layer(f"{path}|layername=capped", "ogr", "")
        layer.setCustomProperty(rules.PROPERTY, _record(path, SQLITE_SUBSET).to_json())
        element, document = _element(), {"tree": {}}
        stream_copy.rewrite_saved_layer(_Project([layer]), layer, element, document)
        stored = rules.LocalCopy.from_json(element["props"][rules.PROPERTY])
        assert stored.subset == ""
        reopened = _Layer(element["tags"]["datasource"], "wfs", "")
        reopened.setCustomProperty(rules.PROPERTY, stored.to_json())
        assert stream_copy.reattach_project(_Project([reopened])) == (1, [])
        assert reopened.subsetString() == ""
    finally:
        _drop(path)


def test_recopy_keeps_the_previous_file_until_replacement(monkeypatch):
    path = _copy_path()
    try:
        layer = _Layer(f"{path}|layername=capped", "ogr", SQLITE_SUBSET)
        layer.setCustomProperty(rules.PROPERTY, _record(path).to_json())
        core = sys.modules['qgis.core']
        monkeypatch.setattr(core, 'QgsCoordinateReferenceSystem', lambda crs: crs, raising=False)
        monkeypatch.setattr(core, 'QgsRectangle', lambda *coords: types.SimpleNamespace(width=lambda: 410),
                            raising=False)

        def plan_copy(*_args):
            assert os.path.isfile(path)
            assert layer.providerType() == "wfs" and layer.subsetString() == ""
            return types.SimpleNamespace(refusal="")

        monkeypatch.setattr(stream_copy, 'plan_copy', plan_copy)
        monkeypatch.setattr(stream_copy, 'evict_service_cache', lambda: True)
        _plan, previous = stream_copy.recopy_plan(layer)
        assert previous.subset == SQLITE_SUBSET
        assert os.path.isfile(previous.path)
        stream_copy.back_to(layer, previous)
        assert stream_copy.is_local_copy(layer)
        assert layer.subsetString() == SQLITE_SUBSET
    finally:
        _drop(path)
