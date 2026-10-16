# -*- coding: utf-8 -*-
"""FilterMate 5 derived sources: project file hook, copies, Unfilter, unload, replay on reopen."""
import importlib
import json
import pathlib
import sys
import types
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

    def elementsByTagName(self, tag):
        found = [Node(node) for node in self.node.getElementsByTagName(tag)]
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
        assert env.project.write()[1][raster.id()].datasource == "./data/new.tif"
        assert not env.reg.is_derived(raster.id()) and snapshots.DERIVED_PROPERTY not in raster.props

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


