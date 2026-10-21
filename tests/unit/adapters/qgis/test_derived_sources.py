# -*- coding: utf-8 -*-
"""FilterMate 5 derived sources: project file hook, copies, Unfilter, unload, replay on reopen."""
import gc
import importlib
import json
import os
import pathlib
import sys
import types
import weakref
from xml.dom import minidom

import pytest

pytestmark = pytest.mark.unit

_ROOT = pathlib.Path(__file__).resolve().parents[4]
_PKG = "fm_derived_sources_test"


def _load():
    for name, path in (("", _ROOT), (".core", _ROOT / "core"), (".core.domain", _ROOT / "core" / "domain"),
                       (".core.services", _ROOT / "core" / "services"), (".adapters", _ROOT / "adapters"),
                       (".adapters.qgis", _ROOT / "adapters" / "qgis"),
                       (".adapters.qgis.coverage_layers", _ROOT / "adapters" / "qgis" / "coverage_layers")):
        package = types.ModuleType(_PKG + name)
        package.__path__ = [str(path)]
        sys.modules[_PKG + name] = package
    # restore_snapshot sets subsets through sql_utils: the plain setSubsetString here.
    for name in (".infrastructure", ".infrastructure.database"):
        sys.modules[_PKG + name] = types.ModuleType(_PKG + name)
    sql_utils = types.ModuleType(_PKG + ".infrastructure.database.sql_utils")
    sql_utils.safe_set_subset_string = lambda layer, subset: layer.setSubsetString(subset)
    sys.modules[sql_utils.__name__] = sql_utils
    modules = [importlib.import_module(f"{_PKG}.{name}") for name in (
        "adapters.qgis.coverage_layers.snapshots", "adapters.qgis.coverage_layers.cache",
        "core.services.cross_filter_service", "core.domain.filter_state", "core.domain.layer_kind",
        "core.domain.cross_filter")]
    return modules


snapshots, cache, service_mod, state, kinds, cross = _load()
LayerSnapshot, LayerKind = state.LayerSnapshot, kinds.LayerKind
GEOMETRY = "Polygon ((0 0, 10 0, 10 10, 0 0))"


# --- QGIS stand-ins -------------------------------------------------------------

class FakeSignal:
    def __init__(self):
        self.slots = []

    def connect(self, slot):
        self.slots.append(slot)

    def disconnect(self, slot):
        for index, connected in enumerate(self.slots):
            if connected is slot or connected == slot:
                del self.slots[index]
                return
        raise TypeError("not connected")

    def emit(self, *args):
        for slot in list(self.slots):
            slot(*args)


class FakeResolver:
    """QgsPathResolver of a project saved in ``home`` with relative paths."""

    def __init__(self, home):
        self.home = home

    def writePath(self, path):
        return "./" + path[len(self.home) + 1:] if path.startswith(self.home + "/") else path

    def readPath(self, path):
        return self.home + "/" + path[2:] if path.startswith("./") else path


class FakeProviders:
    """QgsProviderRegistry: ``GPKG:<path>:<table>`` for gdal, a plain path for the others."""

    def decodeUri(self, provider, uri):
        if provider == "gdal" and uri.startswith("GPKG:"):
            path, table = uri[len("GPKG:"):].rsplit(":", 1)
            return {"path": path, "layerName": table}
        return {"path": uri} if provider in ("gdal", "copc", "ept") else {}

    def encodeUri(self, provider, parts):
        if parts.get("layerName"):
            return f"GPKG:{parts['path']}:{parts['layerName']}"
        return parts["path"]


class FakeRenderer:
    def __init__(self, alpha=-1):
        self.alpha = alpha

    def alphaBand(self):
        return self.alpha

    def setAlphaBand(self, band):
        self.alpha = band


class FakeRaster:
    """A raster layer; ``missing`` sources cannot be opened."""

    def __init__(self, layer_id, source, provider="gdal", missing=()):
        self._id, self._source, self._provider = layer_id, source, provider
        self.missing = set(missing)
        self.valid = True
        self.props = {}
        self._renderer = FakeRenderer()

    def id(self):
        return self._id

    def name(self):
        return self._id

    def source(self):
        return self._source

    def providerType(self):
        return self._provider

    def isValid(self):
        return self.valid

    def setDataSource(self, source, name, provider, options, load_default_style=False):
        self._source, self._provider = source, provider
        self.valid = source not in self.missing

    def renderer(self):
        return self._renderer

    def bandCount(self):
        return 3

    def dataProvider(self):
        return types.SimpleNamespace(colorInterpretation=lambda band: 0)

    def customProperty(self, name, default=None):
        return self.props.get(name, default)

    def setCustomProperty(self, name, value):
        self.props[name] = value

    def removeCustomProperty(self, name):
        self.props.pop(name, None)

    def triggerRepaint(self):
        pass

    def clone(self, layer_id):
        copy = type(self).__new__(type(self))
        copy.__dict__.update(self.__dict__, _id=layer_id, props=dict(self.props))
        if isinstance(self._renderer, FakeRenderer):
            copy._renderer = FakeRenderer(self._renderer.alpha)
        return copy


class FakeCloud(FakeRaster):
    """A point cloud layer; its original source has no HeightAboveGround dimension."""

    def __init__(self, layer_id, source, provider="copc", missing=()):
        super().__init__(layer_id, source, provider, missing)
        self._subset = ""
        self._renderer = object()  # point cloud renderer: no alpha band
        self.plain = {source}

    def setDataSource(self, source, name, provider, options, load_default_style=False):
        super().setDataSource(source, name, provider, options, load_default_style)
        self._subset = ""  # a new provider has no subset

    def subsetString(self):
        return self._subset

    def setSubsetString(self, subset):
        if "HeightAboveGround" in subset and self._source in self.plain:
            return False
        self._subset = subset
        return True


class Node:
    """The QDomElement / QDomDocument calls of the hook, over minidom."""

    def __init__(self, node):
        self.node = node

    def isNull(self):
        return self.node is None

    def firstChildElement(self, tag=""):
        if self.node is not None:
            for child in self.node.childNodes:
                if child.nodeType == child.ELEMENT_NODE and (not tag or child.tagName == tag):
                    return Node(child)
        return Node(None)

    def hasChildNodes(self):
        return bool(self.node.childNodes)

    def firstChild(self):
        return Node(self.node.firstChild)

    def removeChild(self, child):
        self.node.removeChild(child.node)

    def appendChild(self, child):
        self.node.appendChild(child.node)

    def setAttribute(self, name, value):
        self.node.setAttribute(name, str(value))

    def attribute(self, name, default=""):
        return self.node.getAttribute(name) if self.node.hasAttribute(name) else default

    def text(self):
        return "".join(child.data for child in self.node.childNodes if child.nodeType == child.TEXT_NODE)

    def toElement(self):
        return self

    def parentNode(self):
        return Node(self.node.parentNode)

    def elementsByTagName(self, tag):
        found = [Node(node) for node in self.node.getElementsByTagName(tag)] if self.node is not None else []
        return types.SimpleNamespace(count=lambda: len(found), at=lambda index: found[index])

    def createTextNode(self, text):
        return Node(self.node.createTextNode(text))

    def createElement(self, tag):
        return Node(self.node.createElement(tag))


class FakeProject:
    def __init__(self, home):
        self.layers = {}
        self.resolver = FakeResolver(home)
        self.writeMapLayer, self.layersWillBeRemoved, self.layersAdded = FakeSignal(), FakeSignal(), FakeSignal()

    def mapLayer(self, layer_id):
        return self.layers.get(layer_id)

    def mapLayers(self):
        return dict(self.layers)

    def pathResolver(self):
        return self.resolver

    def add(self, *layers):
        for layer in layers:
            self.layers[layer.id()] = layer
        self.layersAdded.emit(list(layers))
        return layers[0]

    def write(self):
        """The project XML as QGIS writes it, through the ``writeMapLayer`` hooks; ``{layer id: what was saved}``."""
        doc = minidom.parseString("<qgis><layer-tree-group/><projectlayers/></qgis>")
        tree, projectlayers = (doc.getElementsByTagName(tag)[0] for tag in ("layer-tree-group", "projectlayers"))
        for layer in self.layers.values():
            source = self.resolver.writePath(layer.source())
            node = doc.createElement("layer-tree-layer")
            for name, value in (("id", layer.id()), ("source", source), ("providerKey", layer.providerType())):
                node.setAttribute(name, value)
            tree.appendChild(node)
            element = doc.createElement("maplayer")
            for tag, text in (("id", layer.id()), ("datasource", source), ("provider", layer.providerType())):
                child = doc.createElement(tag)
                child.appendChild(doc.createTextNode(text))
                element.appendChild(child)
            if hasattr(layer, "subsetString"):
                child = doc.createElement("subset")
                child.appendChild(doc.createTextNode(layer.subsetString()))
                element.appendChild(child)
            options = doc.createElement("Option")
            options.setAttribute("type", "Map")
            for name, value in layer.props.items():
                option = doc.createElement("Option")
                option.setAttribute("name", name)
                option.setAttribute("value", value)
                options.appendChild(option)
            properties = doc.createElement("customproperties")
            properties.appendChild(options)
            element.appendChild(properties)
            if isinstance(layer._renderer, FakeRenderer):
                pipe = doc.createElement("pipe")
                renderer = doc.createElement("rasterrenderer")
                renderer.setAttribute("alphaBand", str(layer._renderer.alpha))
                pipe.appendChild(renderer)
                element.appendChild(pipe)
            projectlayers.appendChild(element)
            self.writeMapLayer.emit(layer, Node(element), Node(doc))
        return doc.toxml(), _saved(doc)


def _saved(doc):
    saved = {}
    for element in doc.getElementsByTagName("maplayer"):
        def text(tag):
            found = element.getElementsByTagName(tag)
            return "".join(n.data for n in found[0].childNodes) if found else None
        layer_id = text("id")
        renderer = element.getElementsByTagName("rasterrenderer")
        options = [o for o in element.getElementsByTagName("Option") if o.getAttribute("name") == snapshots.DERIVED_PROPERTY]
        tree = [n for n in doc.getElementsByTagName("layer-tree-layer") if n.getAttribute("id") == layer_id][0]
        markers = element.getElementsByTagName("filtermate_derived")
        saved[layer_id] = types.SimpleNamespace(
            datasource=text("datasource"), provider=text("provider"), subset=text("subset"),
            alpha=renderer[0].getAttribute("alphaBand") if renderer else None,
            stored=json.loads(options[0].getAttribute("value")) if options else None,
            tree=(tree.getAttribute("source"), tree.getAttribute("providerKey")),
            marker=dict(markers[0].attributes.items()) if markers else None)
    return saved


# --- FilterMate operations, as the target jobs / height-above-ground task do them ----

def clip(layer, path, kind, alpha=None):
    """A clipped VRT / COPC replaces the source (target_appliers.*TargetJob.apply)."""
    before = snapshots.take_snapshot(layer, kind)
    own_subset = before.subset
    assert snapshots.swap_source(layer, path, layer.providerType())
    if alpha is not None:
        layer.renderer().setAlphaBand(alpha)  # _sync_alpha_band: the VRT added an alpha band
    if own_subset:
        layer.setSubsetString(own_subset)
    after = LayerSnapshot(layer.id(), kind.value, source=layer.source(), provider=layer.providerType(),
                          subset=layer.subsetString() if hasattr(layer, "subsetString") else "", derived=True,
                          original_source=before.base_source, original_provider=before.base_provider,
                          geometry_wkt=GEOMETRY, side="inside", enriched_source=before.enriched_source,
                          enriched_provider=before.enriched_provider)
    snapshots.registry().record(after, layer)
    return after


def enrich(cloud, path):
    """The cloud becomes its HeightAboveGround copy (hag_task.HeightAboveGroundTask.finished)."""
    before = snapshots.take_snapshot(cloud, LayerKind.POINT_CLOUD)
    assert snapshots.swap_source(cloud, path, "copc")
    after = LayerSnapshot(cloud.id(), "point_cloud", source=cloud.source(), provider="copc", subset=cloud.subsetString(),
                          derived=True, original_source=path, original_provider="copc",
                          enriched_source=before.pristine_source, enriched_provider=before.pristine_provider)
    snapshots.registry().record(after, cloud)
    return after


@pytest.fixture
def env(tmp_path, monkeypatch):
    cache.set_cache_root(str(tmp_path / "cache"))
    session = cache.session_dir()
    home = str(tmp_path / "proj")
    project = FakeProject(home)
    monkeypatch.setattr(snapshots, "QgsProject", types.SimpleNamespace(instance=lambda: project))
    monkeypatch.setattr(snapshots, "QgsProviderRegistry", types.SimpleNamespace(instance=FakeProviders))
    monkeypatch.setattr(snapshots, "_registry", None)
    snapshots.registry().install(project)
    yield types.SimpleNamespace(project=project, session=session, home=home, reg=snapshots.registry())
    snapshots.registry().uninstall()
    cache.set_cache_root(None)


def _raster(env, layer_id="ortho", **kwargs):
    return env.project.add(FakeRaster(layer_id, f"{env.home}/data/{layer_id}.tif", **kwargs))


def _cloud(env, layer_id="lidar", **kwargs):
    return env.project.add(FakeCloud(layer_id, f"{env.home}/data/{layer_id}.copc.laz", **kwargs))


def _unfilter(env, layer, kind):
    return service_mod.CrossFilterService().unfilter("src", [layer.id()], {layer.id(): kind}, project=env.project)


# --- 1. Unfilter keeps a point cloud enriched with HeightAboveGround -------------

class TestUnfilterEnrichedCloud:
    def test_export_protection_keeps_the_pristine_enrichment_source_without_a_stored_selection(self, env):
        cloud = _cloud(env)
        pristine = cloud.source()
        enrich(cloud, f"{env.session}/lidar_hag_1a2b3c4d.copc.laz")
        assert pristine in service_mod.protected_sources()

    def test_enriched_cloud_stays_a_derived_source(self, env):
        cloud = _cloud(env)
        pristine = cloud.source()
        hag = enrich(cloud, f"{env.session}/lidar_hag_1a2b3c4d.copc.laz").source
        clip(cloud, f"{env.session}/lidar_5e6f7a8b.copc.laz", LayerKind.POINT_CLOUD)
        assert _unfilter(env, cloud, LayerKind.POINT_CLOUD) == [cloud.id()]
        assert cloud.source() == hag  # Unfilter keeps the HeightAboveGround dimension
        known = env.reg.get(cloud.id())
        assert known is not None and known.pristine_source == pristine
        assert env.project.write()[1][cloud.id()].datasource == "./data/lidar.copc.laz"
        assert env.reg.restore_all(env.project) == 1 and cloud.source() == pristine

    def test_enriched_cloud_with_a_subset_only(self, env):
        cloud = _cloud(env)
        pristine = cloud.source()
        enrich(cloud, f"{env.session}/lidar_hag_1a2b3c4d.copc.laz")
        assert cloud.setSubsetString("HeightAboveGround >= 2")
        _unfilter(env, cloud, LayerKind.POINT_CLOUD)
        assert cloud.subsetString() == "" and env.reg.get(cloud.id()).pristine_source == pristine

    def test_unfilter_then_undo_then_unload(self, env):
        cloud = _cloud(env)
        pristine = cloud.source()
        enrich(cloud, f"{env.session}/lidar_hag_1a2b3c4d.copc.laz")
        clipped = clip(cloud, f"{env.session}/lidar_5e6f7a8b.copc.laz", LayerKind.POINT_CLOUD).source
        service = service_mod.CrossFilterService()
        service.unfilter("src", [cloud.id()], {cloud.id(): LayerKind.POINT_CLOUD}, project=env.project)
        service.undo("src", project=env.project)
        assert cloud.source() == clipped and env.reg.get(cloud.id()).pristine_source == pristine
        env.reg.restore_all(env.project)
        assert cloud.source() == pristine

    def test_favorite_on_an_enriched_cloud_keeps_it_registered(self, env):
        from fm_derived_sources_test.adapters.qgis.coverage_layers import favorites_bridge
        cloud = _cloud(env)
        pristine = cloud.source()
        enrich(cloud, f"{env.session}/lidar_hag_1a2b3c4d.copc.laz")
        clip(cloud, f"{env.session}/lidar_5e6f7a8b.copc.laz", LayerKind.POINT_CLOUD)
        entry = dict(LayerSnapshot(cloud.id(), "point_cloud", subset="Classification = 2").to_dict(), layer_name="lidar")
        assert favorites_bridge.apply([entry], project=env.project, kind_of=lambda layer: LayerKind.POINT_CLOUD) == 1
        assert cloud.subsetString() == "Classification = 2" and "_hag_" in cloud.source()
        assert env.reg.get(cloud.id()).pristine_source == pristine

    @pytest.mark.parametrize("reason", ["", "remote raster target must run in a worker thread"])
    def test_favorite_clip_run_by_the_caller_reports_its_failure(self, env, reason):
        """2026-10-20: automation clips in its worker; a failed clip is a failure, never "handled"."""
        from fm_derived_sources_test.adapters.qgis.coverage_layers import favorites_bridge
        raster = _raster(env)
        raster.crs = lambda: None  # read by the clip's source job
        entry = dict(LayerSnapshot(raster.id(), "raster", source="/cache/x.vrt", provider="gdal", derived=True,
                                   original_source=raster.source(), original_provider="gdal",
                                   geometry_wkt="POLYGON((0 0,1 0,1 1,0 1,0 0))").to_dict(), layer_name="ortho")
        service = types.SimpleNamespace(run=lambda *args, **kwargs: pytest.fail("queued instead of run"))
        runs, applied, failed = [], [], {}
        previous = clip(raster, f"{env.session}/ortho_1a2b3c4d.vrt", LayerKind.RASTER).source

        def run(clip_service, request, job):
            runs.append((clip_service, request.targets[0].layer_id, job._wkt, raster.source()))
            return reason

        handled = favorites_bridge.apply([entry], service=service, project=env.project,
                                         kind_of=lambda layer: LayerKind.RASTER, applied=applied, run=run, failed=failed)
        # The clip starts from the original source.
        assert runs == [(service, raster.id(), entry["geometry_wkt"], entry["original_source"])]
        if reason:
            assert (handled, applied, failed) == (0, [], {raster.id(): reason})
            assert raster.source() == previous  # a failed clip leaves the layer as it was
        else:
            assert (handled, applied, failed) == (1, [raster.id()], {})

    def test_favorite_canceled_leaves_the_remaining_layers_as_they_are(self, env):
        from fm_derived_sources_test.adapters.qgis.coverage_layers import favorites_bridge
        raster = _raster(env)
        previous = clip(raster, f"{env.session}/ortho_1a2b3c4d.vrt", LayerKind.RASTER).source
        entry = dict(LayerSnapshot(raster.id(), "raster", source="/cache/x.vrt", provider="gdal", derived=True,
                                   original_source=raster.source(), original_provider="gdal",
                                   geometry_wkt="POLYGON((0 0,1 0,1 1,0 1,0 0))").to_dict(), layer_name="ortho")
        failed = {}
        handled = favorites_bridge.apply([entry], project=env.project, kind_of=lambda layer: LayerKind.RASTER,
                                         run=lambda *args: pytest.fail("clipped after cancel"), failed=failed,
                                         canceled=lambda: True)
        assert (handled, failed, raster.source()) == (0, {raster.id(): "canceled"}, previous)

    def test_plain_layer_unfiltered_leaves_the_registry(self, env):
        raster = _raster(env)
        original = raster.source()
        clip(raster, f"{env.session}/ortho_1a2b3c4d.vrt", LayerKind.RASTER)
        _unfilter(env, raster, LayerKind.RASTER)
        assert raster.source() == original and not env.reg.is_derived(raster.id())
        assert snapshots.DERIVED_PROPERTY not in raster.props


# --- 2. Alpha band added by the clipped VRT ------------------------------------------

class TestAlphaBand:

    def test_original_alpha_band_is_saved(self, env):
        raster = _raster(env)
        clip(raster, f"{env.session}/ortho_1a2b3c4d.vrt", LayerKind.RASTER, alpha=4)
        assert raster.renderer().alphaBand() == 4
        assert env.project.write()[1][raster.id()].alpha == "-1"

    def test_second_clip_keeps_the_first_original_alpha(self, env):
        raster = _raster(env)
        raster.renderer().setAlphaBand(2)  # the user's choice on the original
        clip(raster, f"{env.session}/ortho_1a2b3c4d.vrt", LayerKind.RASTER, alpha=4)
        clip(raster, f"{env.session}/ortho_5e6f7a8b.vrt", LayerKind.RASTER, alpha=4)
        assert env.project.write()[1][raster.id()].alpha == "2"

    def test_layer_not_derived_is_saved_as_is(self, env):
        raster = _raster(env)
        raster.renderer().setAlphaBand(4)
        assert env.project.write()[1][raster.id()].alpha == "4"


# --- 3. Copies of a derived layer (duplicate, copy / paste) ----------------------

class TestCopies:

    def test_duplicate_is_registered_like_its_model(self, env):
        raster = _raster(env)
        clip(raster, f"{env.session}/ortho_1a2b3c4d.vrt", LayerKind.RASTER, alpha=4)
        copy = env.project.add(raster.clone("ortho_copy"))
        assert env.reg.is_derived("ortho_copy")
        saved = env.project.write()[1]["ortho_copy"]
        assert (saved.datasource, saved.alpha) == ("./data/ortho.tif", "-1")
        assert _unfilter(env, copy, LayerKind.RASTER) == ["ortho_copy"]
        assert copy.source() == f"{env.home}/data/ortho.tif"

    def test_copy_of_a_layer_no_longer_derived_uses_its_property(self, env):
        raster = _raster(env)
        clip(raster, f"{env.session}/ortho_1a2b3c4d.vrt", LayerKind.RASTER)
        copy = raster.clone("ortho_copy")  # copied, then the model unfiltered, then pasted
        _unfilter(env, raster, LayerKind.RASTER)
        env.project.add(copy)
        assert env.reg.get("ortho_copy").pristine_source == f"{env.home}/data/ortho.tif"

    def test_hook_and_unload_fall_back_on_the_property(self, env):
        raster = _raster(env)
        clip(raster, f"{env.session}/ortho_1a2b3c4d.vrt", LayerKind.RASTER)
        copy = raster.clone("ortho_copy")
        env.project.layers["ortho_copy"] = copy  # added while the hooks were not listening
        env.reg.forget(raster.id())
        assert env.project.write()[1]["ortho_copy"].datasource == "./data/ortho.tif"
        env.project.layers["other_copy"] = raster.clone("other_copy")
        env.reg.restore_all(env.project)
        assert env.project.layers["other_copy"].source() == f"{env.home}/data/ortho.tif"

    def test_unknown_file_outside_the_session_is_left_alone(self, env):
        layer = FakeRaster("vrt", f"{env.home}/data/mosaic.vrt")
        layer.props[snapshots.DERIVED_PROPERTY] = json.dumps(LayerSnapshot(
            "x", "raster", source=f"{env.home}/data/other.vrt", derived=True,
            original_source="/elsewhere.tif", geometry_wkt=GEOMETRY).to_dict())
        env.project.add(layer)
        assert not env.reg.is_derived("vrt")


def test_failed_swap_keeps_the_subset_of_the_cloud(env):
    # 2026-10-18: a derived cloud that cannot be opened (QGIS without the pdal
    # provider) put the layer back on its source WITHOUT its own filter, and no
    # history entry could bring it back.
    cloud = _cloud(env)
    cloud.setSubsetString("Classification = 6")
    broken = f"{env.session}/lidar_1a2b3c4d.laz"
    cloud.missing.add(broken)
    assert not snapshots.swap_source(cloud, broken, "pdal")
    assert cloud.source() == f"{env.home}/data/lidar.copc.laz" and cloud.providerType() == "copc"
    assert cloud.subsetString() == "Classification = 6"


# --- 4. Original source unavailable when the plugin unloads ---------------------

def test_unload_puts_back_an_unavailable_original(env):
    raster = _raster(env)
    original = raster.source()
    clip(raster, f"{env.session}/ortho_1a2b3c4d.vrt", LayerKind.RASTER)
    raster.missing.add(original)  # moved / offline share
    assert env.reg.restore_all(env.project) == 1
    assert raster.source() == original and not raster.isValid()


def test_unavailable_original_keeps_no_filtermate_state(env):
    # QGIS keeps the style of a layer turning invalid, to restore it once
    # repaired: it must not carry the property nor the alpha band of the VRT.
    raster = _raster(env)
    original = raster.source()
    clip(raster, f"{env.session}/ortho_1a2b3c4d.vrt", LayerKind.RASTER, alpha=4)
    raster.missing.add(original)
    styles = []
    real = raster.setDataSource

    def set_data_source(source, *args):
        styles.append((raster.renderer().alphaBand(), snapshots.DERIVED_PROPERTY in raster.props))
        real(source, *args)

    raster.setDataSource = set_data_source
    env.reg.restore_all(env.project)
    assert styles == [(-1, False)]


def test_a_layer_failing_on_unload_does_not_stop_the_others(env):
    first, second = _raster(env, "first"), _raster(env, "second")
    for layer in (first, second):
        clip(layer, f"{env.session}/{layer.id()}_1a2b3c4d.vrt", LayerKind.RASTER)

    def deleted(*args):
        raise RuntimeError("wrapped C/C++ object has been deleted")

    first.setDataSource = deleted
    assert env.reg.restore_all(env.project) == 1
    assert second.source() == f"{env.home}/data/second.tif" and env.reg.layer_ids() == []


# --- 5. Data source changed by the user after a clip ------------------------------

class TestSourceChangedByTheUser:

    def test_saved_with_the_users_source_and_forgotten(self, env):
        raster = _raster(env)
        clip(raster, f"{env.session}/ortho_1a2b3c4d.vrt", LayerKind.RASTER, alpha=4)
        raster.setDataSource(f"{env.home}/data/new.tif", "ortho", "gdal", None)
        text, saved = env.project.write()
        assert saved[raster.id()].datasource == "./data/new.tif"
        assert not env.reg.is_derived(raster.id()) and snapshots.DERIVED_PROPERTY not in raster.props
        # QGIS wrote the custom properties before the hook ran: the written one goes too.
        assert saved[raster.id()].stored is None and "session_" not in text

    def test_changed_back_to_the_original_is_not_replayed(self, env):
        raster = _raster(env)
        original = raster.source()
        clip(raster, f"{env.session}/ortho_1a2b3c4d.vrt", LayerKind.RASTER)
        raster.setDataSource(original, "ortho", "gdal", None)
        saved = env.project.write()[1][raster.id()]
        assert saved.stored is None
        project, _ = _reopen(env, saved, FakeRaster, raster.id(), env.home)
        assert snapshots.pending_replays(project) == []

    def test_layer_still_on_a_session_file_is_not_the_users(self, env):
        raster = _raster(env)
        original = raster.source()
        clip(raster, f"{env.session}/ortho_1a2b3c4d.vrt", LayerKind.RASTER)
        raster._source = f"{env.session}/ortho_9f8e7d6c.vrt"  # stale registry entry
        assert env.project.write()[1][raster.id()].datasource == "./data/ortho.tif"
        assert env.reg.restore_all(env.project) == 1 and raster.source() == original

    def test_unload_leaves_it(self, env):
        raster = _raster(env)
        clip(raster, f"{env.session}/ortho_1a2b3c4d.vrt", LayerKind.RASTER)
        raster.setDataSource(f"{env.home}/data/new.tif", "ortho", "gdal", None)
        assert env.reg.restore_all(env.project) == 0
        assert raster.source() == f"{env.home}/data/new.tif"


# --- 6. Replay on reopen ----------------------------------------------------------------

def _reopen(env, saved, layer_type, layer_id, home):
    """The saved layer read back by a project in ``home`` (paths resolved like QGIS)."""
    project = FakeProject(home)
    layer = layer_type(layer_id, project.resolver.readPath(saved.datasource), saved.provider)
    if saved.stored is not None:
        layer.props[snapshots.DERIVED_PROPERTY] = json.dumps(saved.stored)
    if saved.subset:
        layer.setSubsetString(saved.subset)
    project.layers[layer_id] = layer
    env.reg.forget(layer_id)
    return project, layer


class TestReplay:

    def test_moved_project_is_replayed(self, env, tmp_path):
        raster = _raster(env)
        clip(raster, f"{env.session}/ortho_1a2b3c4d.vrt", LayerKind.RASTER)
        saved = env.project.write()[1][raster.id()]
        project, reopened = _reopen(env, saved, FakeRaster, raster.id(), str(tmp_path / "moved"))
        pending = snapshots.pending_replays(project)
        assert [layer for layer, _ in pending] == [reopened]
        assert pending[0][1].base_source == str(tmp_path / "moved" / "data" / "ortho.tif")
        assert pending[0][1].geometry_wkt == GEOMETRY

    def test_clipped_enriched_cloud_is_replayed_from_its_original(self, env):
        cloud = _cloud(env)
        enrich(cloud, f"{env.session}/lidar_hag_1a2b3c4d.copc.laz")
        clip(cloud, f"{env.session}/lidar_5e6f7a8b.copc.laz", LayerKind.POINT_CLOUD)
        assert cloud.setSubsetString("HeightAboveGround >= 2")
        saved = env.project.write()[1][cloud.id()]
        assert saved.subset == ""  # the original cloud has no HeightAboveGround
        project, reopened = _reopen(env, saved, FakeCloud, cloud.id(), env.home)
        pending = snapshots.pending_replays(project)
        assert [layer for layer, _ in pending] == [reopened]
        assert pending[0][1].base_source == f"{env.home}/data/lidar.copc.laz"

    def test_property_of_an_older_build_absolute_and_enriched(self, env):
        cloud = FakeCloud("lidar", f"{env.home}/data/lidar.copc.laz")
        cloud.props[snapshots.DERIVED_PROPERTY] = json.dumps(LayerSnapshot(
            "lidar", "point_cloud", source=f"{env.session}/lidar_5e6f7a8b.copc.laz", provider="copc", derived=True,
            original_source=f"{env.session}/lidar_hag_1a2b3c4d.copc.laz", original_provider="copc",
            geometry_wkt=GEOMETRY, enriched_source=cloud.source(), enriched_provider="copc").to_dict())
        env.project.layers["lidar"] = cloud
        assert len(snapshots.pending_replays(env.project)) == 1

    def test_source_changed_since_is_not_replayed(self, env):
        raster = _raster(env)
        clip(raster, f"{env.session}/ortho_1a2b3c4d.vrt", LayerKind.RASTER)
        saved = env.project.write()[1][raster.id()]
        project, reopened = _reopen(env, saved, FakeRaster, raster.id(), env.home)
        reopened.setDataSource(f"{env.home}/data/other.tif", "ortho", "gdal", None)
        assert snapshots.pending_replays(project) == []

    def test_own_subset_of_a_cloud_not_enriched_is_saved(self, env):
        cloud = _cloud(env)
        assert cloud.setSubsetString("Classification = 2")
        clip(cloud, f"{env.session}/lidar_5e6f7a8b.copc.laz", LayerKind.POINT_CLOUD)
        assert env.project.write()[1][cloud.id()].subset == "Classification = 2"


# --- 7. Unload keeps the own subset of a point cloud ------------------------------

class TestUnloadSubset:

    def test_own_subset_kept(self, env):
        cloud = _cloud(env)
        original = cloud.source()
        assert cloud.setSubsetString("Classification = 2")
        clip(cloud, f"{env.session}/lidar_5e6f7a8b.copc.laz", LayerKind.POINT_CLOUD)
        env.reg.restore_all(env.project)
        assert (cloud.source(), cloud.subsetString()) == (original, "Classification = 2")

    def test_height_above_ground_subset_dropped(self, env):
        cloud = _cloud(env)
        original = cloud.source()
        enrich(cloud, f"{env.session}/lidar_hag_1a2b3c4d.copc.laz")
        assert cloud.setSubsetString("HeightAboveGround >= 2")
        env.reg.restore_all(env.project)
        assert (cloud.source(), cloud.subsetString()) == (original, "")


# --- 8. No cache path anywhere in the project file --------------------------------

def test_no_cache_path_in_the_project(env):
    raster, cloud = _raster(env), _cloud(env)
    clip(raster, f"{env.session}/ortho_1a2b3c4d.vrt", LayerKind.RASTER, alpha=4)
    enrich(cloud, f"{env.session}/lidar_hag_1a2b3c4d.copc.laz")
    clip(cloud, f"{env.session}/lidar_5e6f7a8b.copc.laz", LayerKind.POINT_CLOUD)
    text, saved = env.project.write()
    assert "session_" not in text
    assert saved[raster.id()].tree == ("./data/ortho.tif", "gdal")
    assert saved[cloud.id()].tree == ("./data/lidar.copc.laz", "copc")
    assert saved[raster.id()].marker == {"kind": "raster"}


# --- 9. Relative paths inside provider URIs -----------------------------------------

def test_geopackage_raster_written_relative(env):
    raster = env.project.add(FakeRaster("dem", f"GPKG:{env.home}/data/x.gpkg:dem"))
    clip(raster, f"{env.session}/dem_1a2b3c4d.vrt", LayerKind.RASTER)
    saved = env.project.write()[1]["dem"]
    assert saved.datasource == "GPKG:./data/x.gpkg:dem"
    assert saved.stored["original_source"] == "GPKG:./data/x.gpkg:dem"


# --- 11. Hooks of another project ------------------------------------------------------

def test_hooks_of_another_project_keep_the_current_ones(env, tmp_path):
    other = FakeProject(str(tmp_path / "other"))
    env.reg.install(other)
    env.reg.install(env.project)  # again: no second connection
    assert len(env.project.writeMapLayer.slots) == 1 and len(other.writeMapLayer.slots) == 1
    raster = _raster(env)
    clip(raster, f"{env.session}/ortho_1a2b3c4d.vrt", LayerKind.RASTER)
    assert env.project.write()[1][raster.id()].datasource == "./data/ortho.tif"
    env.reg.uninstall()
    assert not env.project.writeMapLayer.slots and not other.writeMapLayer.slots
    assert not env.project.layersAdded.slots and not other.layersWillBeRemoved.slots


# --- 12. A target whose job cannot be built is reported -----------------------------

def test_target_whose_job_cannot_be_built_is_reported(env, monkeypatch):
    _raster(env, layer_id="dem")
    appliers = types.ModuleType(f"{_PKG}.adapters.qgis.coverage_layers.target_appliers")

    def make_job(layer, kind, operator, clip_mode):
        raise RuntimeError("raster provider unavailable")

    appliers.make_job = make_job
    task_module = types.ModuleType(f"{_PKG}.adapters.qgis.coverage_layers.cross_filter_task")
    task_module.CrossFilterTask = lambda description, request, source_job, jobs, done, project=None: types.SimpleNamespace(target_jobs=jobs)
    monkeypatch.setitem(sys.modules, appliers.__name__, appliers)
    monkeypatch.setitem(sys.modules, task_module.__name__, task_module)
    request = cross.CrossFilterRequest("zones", LayerKind.VECTOR, targets=(cross.TargetSpec("dem", LayerKind.RASTER),))
    task = service_mod.CrossFilterService().build_task(request, types.SimpleNamespace(layer_name="zones"), project=env.project)
    [job] = task.target_jobs
    job.compute(None, None, None, request, lambda: False)  # nothing to compute
    assert (job.layer_id, job.layer_name, job.kind) == ("dem", "dem", LayerKind.RASTER)
    assert (job.outcome.success, job.outcome.message) == (False, "raster provider unavailable")


# --- 13. Unload lets the canceled tasks close their files ------------------------

class FakeTask:
    def __init__(self, description, clock, runs_for):
        self._description, self.clock, self.runs_for = description, clock, runs_for
        self.canceled, self.waits = False, []

    def description(self):
        return self._description

    def cancel(self):
        self.canceled = True

    def waitForFinished(self, timeout_ms):
        self.waits.append(timeout_ms)
        self.clock[0] += min(self.runs_for, timeout_ms / 1000.0)
        return self.runs_for * 1000.0 <= timeout_ms


def test_unload_waits_a_bounded_time_for_the_canceled_tasks(monkeypatch):
    clock = [100.0]
    tasks = [FakeTask("FilterMate: height above dtm", clock, 0.5), FakeTask("Other plugin", clock, 9.0),
             FakeTask("FilterMate: export", clock, 9.0), FakeTask("FilterMate: lidar", clock, 0.1)]
    manager = types.SimpleNamespace(activeTasks=lambda: tasks)
    monkeypatch.setattr(sys.modules["qgis.core"], "QgsApplication", types.SimpleNamespace(taskManager=lambda: manager))
    monkeypatch.setattr(service_mod.time, "monotonic", lambda: clock[0])
    assert service_mod.stop_filtermate_tasks(wait_seconds=2.0) == 3
    assert [task.canceled for task in tasks] == [True, False, True, True]
    assert tasks[0].waits == [2000] and tasks[2].waits == [1500]
    assert tasks[3].waits == [] and tasks[1].waits == []  # budget spent: never waitForFinished(0)


# --- Review of PR #116 --------------------------------------------------------------

class TestCopiesSpelledDifferently:
    """A copy read back from a .qlr: QgsPathResolver resolves links, writes '/' on Windows."""

    @pytest.mark.parametrize("spelling", ["link", "separators"])
    def test_copy_is_recognized(self, env, tmp_path, spelling):
        raster = _raster(env)
        clip(raster, f"{env.session}/ortho_1a2b3c4d.vrt", LayerKind.RASTER)
        if spelling == "link":
            if os.name == "nt":
                pytest.skip("symbolic links need privileges")
            link = tmp_path / "link"
            os.symlink(os.path.dirname(env.session), str(link))
            source = str(link / os.path.basename(env.session) / "ortho_1a2b3c4d.vrt")
        else:
            source = env.session.replace("/", "\\") + "\\ortho_1a2b3c4d.vrt"
        copy = raster.clone("ortho_copy")
        copy._source = source
        env.project.add(copy)
        assert env.reg.is_derived("ortho_copy") and env.reg.get("ortho_copy").source == source
        assert env.project.write()[1]["ortho_copy"].datasource == "./data/ortho.tif"
        assert _unfilter(env, copy, LayerKind.RASTER) == ["ortho_copy"]
        assert copy.source() == f"{env.home}/data/ortho.tif"

    def test_copy_spelled_differently_adopted_from_its_property(self, env):
        raster = _raster(env)
        clip(raster, f"{env.session}/ortho_1a2b3c4d.vrt", LayerKind.RASTER)
        copy = raster.clone("ortho_copy")
        copy._source = env.session.replace("/", "\\") + "\\ortho_1a2b3c4d.vrt"
        _unfilter(env, raster, LayerKind.RASTER)
        env.project.add(copy)
        assert env.reg.get("ortho_copy").pristine_source == f"{env.home}/data/ortho.tif"


def test_save_as_elsewhere_before_the_replay(env):
    raster = _raster(env)
    clip(raster, f"{env.session}/ortho_1a2b3c4d.vrt", LayerKind.RASTER)
    saved = env.project.write()[1][raster.id()]
    project, reopened = _reopen(env, saved, FakeRaster, raster.id(), env.home)  # replay not run yet
    archive = FakeProject(env.home + "/archive")  # Save As in a sub folder
    archive.layers = project.layers
    copy = archive.write()[1][raster.id()]
    project, reopened = _reopen(env, copy, FakeRaster, raster.id(), env.home + "/archive")
    assert reopened.source() == f"{env.home}/data/ortho.tif"
    assert [layer for layer, _ in snapshots.pending_replays(project)] == [reopened]


class TestOtherProjects:

    def test_unload_restores_the_layers_of_every_hooked_project(self, env, tmp_path):
        other = FakeProject(str(tmp_path / "other"))
        env.reg.install(other)
        layer = other.add(FakeRaster("o", str(tmp_path / "other" / "data" / "o.tif")))
        original = layer.source()
        clip(layer, f"{env.session}/o_1a2b3c4d.vrt", LayerKind.RASTER)
        assert env.reg.restore_all() == 1 and layer.source() == original

    def test_hooks_do_not_keep_a_project_alive(self, env, tmp_path):
        other = FakeProject(str(tmp_path / "other"))
        env.reg.install(other)
        ref = weakref.ref(other)
        del other
        gc.collect()
        assert ref() is None
        env.reg.uninstall()  # a project gone: nothing to disconnect, no error


class TestUserAlphaBand:

    @pytest.mark.parametrize("how", ["unfilter", "unload"])
    def test_alpha_band_chosen_by_the_user_comes_back(self, env, how):
        raster = _raster(env)
        raster.renderer().setAlphaBand(3)
        clip(raster, f"{env.session}/ortho_1a2b3c4d.vrt", LayerKind.RASTER, alpha=5)
        if how == "unfilter":
            _unfilter(env, raster, LayerKind.RASTER)
        else:
            env.reg.restore_all(env.project)
        assert raster.renderer().alphaBand() == 3

    def test_copy_adopted_from_its_property_keeps_the_original_alpha(self, env):
        raster = _raster(env)
        raster.renderer().setAlphaBand(2)
        clip(raster, f"{env.session}/ortho_1a2b3c4d.vrt", LayerKind.RASTER, alpha=4)
        copy = raster.clone("ortho_copy")
        _unfilter(env, raster, LayerKind.RASTER)  # the model and its alpha band are forgotten
        env.project.add(copy)
        assert env.project.write()[1]["ortho_copy"].alpha == "2"


def test_copy_adopted_while_writing_gets_the_property_written(env):
    raster = _raster(env)
    clip(raster, f"{env.session}/ortho_1a2b3c4d.vrt", LayerKind.RASTER)
    copy = raster.clone("ortho_copy")
    copy.props.clear()
    env.project.layers["ortho_copy"] = copy  # added while the hooks were not listening
    stored = env.project.write()[1]["ortho_copy"].stored
    assert stored is not None and stored["geometry_wkt"] == GEOMETRY


class TestHeightAboveGroundTerms:

    @pytest.mark.parametrize("subset, kept", [
        ("Classification = 2 AND HeightAboveGround >= 2", "Classification = 2"),
        ("HeightAboveGround >= 2 and (Classification = 2 OR Classification = 6)",
         "(Classification = 2 OR Classification = 6)"),
        ("Classification = 2 OR HeightAboveGround >= 2", ""),
        ("(Classification = 2 AND HeightAboveGround >= 2)", ""),
        ("\"Name\" = 'x AND y' AND HeightAboveGround >= 2", "\"Name\" = 'x AND y'"),
        ("BAND = 1 AND HeightAboveGround > 2 AND ORDER > 3", "BAND = 1 AND ORDER > 3"),
        ("HeightAboveGround >= 2", ""),
        ("Classification = 2", "Classification = 2"),
    ])
    def test_terms_dropped(self, subset, kept):
        assert snapshots.without_terms(subset, "HeightAboveGround") == kept

    def test_other_terms_kept_in_the_project_and_on_unload(self, env):
        cloud = _cloud(env)
        enrich(cloud, f"{env.session}/lidar_hag_1a2b3c4d.copc.laz")
        clip(cloud, f"{env.session}/lidar_5e6f7a8b.copc.laz", LayerKind.POINT_CLOUD)
        assert cloud.setSubsetString("Classification = 2 AND HeightAboveGround >= 2")
        assert env.project.write()[1][cloud.id()].subset == "Classification = 2"
        env.reg.restore_all(env.project)
        assert cloud.subsetString() == "Classification = 2"


def test_adoption_error_does_not_stop_unload(env):
    raster = _raster(env)
    original = raster.source()
    clip(raster, f"{env.session}/ortho_1a2b3c4d.vrt", LayerKind.RASTER)
    broken = FakeRaster("broken", f"{env.home}/data/broken.tif")

    def source():
        raise ValueError("provider gone")

    broken.source = source
    env.project.layers["broken"] = broken
    assert env.reg.restore_all(env.project) == 1 and raster.source() == original


def test_unload_closes_the_cache_whatever_fails(env, monkeypatch):
    def cancel_all():
        raise RuntimeError("task deleted")

    monkeypatch.setattr(service_mod, "all_services", lambda: [types.SimpleNamespace(cancel_all=cancel_all)])
    monkeypatch.setattr(service_mod, "stop_filtermate_tasks", lambda: 0)
    with pytest.raises(RuntimeError):
        service_mod.release_coverage_layers()
    assert cache.is_closed() and not env.project.writeMapLayer.slots


def test_favorite_of_a_derived_layer_holds_no_cache_path(env, monkeypatch):
    from fm_derived_sources_test.adapters.qgis.coverage_layers import favorites_bridge
    monkeypatch.setattr(favorites_bridge, "_kind",
                        lambda layer: LayerKind.POINT_CLOUD if isinstance(layer, FakeCloud) else LayerKind.RASTER)
    raster, cloud = _raster(env), _cloud(env)
    clip(raster, f"{env.session}/ortho_1a2b3c4d.vrt", LayerKind.RASTER)
    enrich(cloud, f"{env.session}/lidar_hag_1a2b3c4d.copc.laz")
    _unfilter(env, cloud, LayerKind.POINT_CLOUD)  # still on its enriched file
    entries = favorites_bridge.capture(env.project)
    assert len(entries) == 2 and "session_" not in json.dumps(entries)
    by_name = {entry["layer_name"]: LayerSnapshot.from_dict(entry) for entry in entries}
    assert by_name["ortho"].derived and by_name["ortho"].base_source == f"{env.home}/data/ortho.tif"
    assert by_name["ortho"].geometry_wkt == GEOMETRY
    assert by_name["lidar"].base_source == f"{env.home}/data/lidar.copc.laz"
