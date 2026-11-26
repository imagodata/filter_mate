# -*- coding: utf-8 -*-
"""What the user watches while the agent works: designer, highlights, active layer, messages, atlas pages.

Same harness as test_project_control_crs.py: the module loads for real, QGIS stays mocked, the layer resolver
and the window are stand-ins. What needs a real canvas or designer (the blink itself, the opened window) is
checked in tests/qgis_headless/check_agent_gui.py.
"""
import importlib
import pathlib
import sys
import types
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

_ROOT = pathlib.Path(__file__).resolve().parents[4]
_PKG = "fm_gui_control_test"


def _load():
    for name, path in (("", _ROOT), (".core", _ROOT / "core"), (".core.agent", _ROOT / "core" / "agent"),
                       (".core.domain", _ROOT / "core" / "domain"), (".adapters", _ROOT / "adapters"),
                       (".adapters.qgis", _ROOT / "adapters" / "qgis"),
                       (".adapters.public_api", _ROOT / "adapters" / "public_api")):
        package = types.ModuleType(_PKG + name)
        package.__path__ = [str(path)]
        sys.modules[_PKG + name] = package
    stubbed = "qgis.PyQt.QtNetwork" not in sys.modules
    if stubbed:
        sys.modules["qgis.PyQt.QtNetwork"] = MagicMock()
    try:
        importlib.import_module(f"{_PKG}.adapters.public_api.introspection")
        return importlib.import_module(f"{_PKG}.adapters.public_api.gui_control")
    finally:
        if stubbed:
            sys.modules.pop("qgis.PyQt.QtNetwork", None)


gui_control = _load()

from filtermate_core.domain.layer_kind import LayerKind  # noqa: E402


class _Feature:
    def __init__(self, fid):
        self._fid = fid

    def id(self):
        return self._fid


class _Request:
    def __init__(self):
        self.expression = ""
        self.limit = 10 ** 9

    def setFilterExpression(self, expression):
        self.expression = expression
        return self

    def setNoAttributes(self):
        return self

    def setLimit(self, limit):
        self.limit = limit
        return self


class _Layer:
    def __init__(self, name="communes", fids=()):
        self._name = name
        self._fids = list(fids)

    def name(self):
        return self._name

    def id(self):
        return "L1"

    def getFeatures(self, request):
        return [_Feature(fid) for fid in self._fids[:request.limit]]


class _Layouts:
    def __init__(self, layouts=()):
        self._layouts = list(layouts)

    def layoutByName(self, name):
        return next((item for item in self._layouts if item.name() == name), None)

    def printLayouts(self):
        return list(self._layouts)


class _Project:
    layouts = _Layouts()

    @classmethod
    def instance(cls):
        return cls()

    def layoutManager(self):
        return self.layouts

    def layerTreeRoot(self):
        return _Tree()


class _Canvas:
    def __init__(self):
        self.flashed = []

    def flashFeatureIds(self, layer, fids):
        self.flashed.append((layer, list(fids)))


class _Bar:
    def __init__(self):
        self.messages = []

    def pushMessage(self, title, text, level, duration):
        self.messages.append((title, text, level, duration))


class _Model:
    def __init__(self, indexed=True):
        self.expanded = []
        self.indexed = indexed

    def node2index(self, node):
        if not self.indexed:
            raise AttributeError("no node2index")
        return ("index", id(node))


class _View:
    def __init__(self, model=None):
        self.current = None
        self.scrolled = []
        self._model = model if model is not None else _Model()

    def setCurrentLayer(self, layer):
        self.current = layer

    def model(self):
        return self._model

    def setExpanded(self, index, expanded):
        self._model.expanded.append((index, expanded))

    def scrollTo(self, index):
        self.scrolled.append(index)


class _Face:
    def __init__(self, canvas=None, bar=None, view=None, designers=()):
        self._canvas = canvas
        self._bar = bar
        self._view = view
        self._designers = list(designers)
        self.active = None
        self.opened = []

    def mapCanvas(self):
        return self._canvas

    def messageBar(self):
        return self._bar

    def layerTreeView(self):
        return self._view

    def setActiveLayer(self, layer):
        self.active = layer

    def openLayoutDesigner(self, layout):
        self.opened.append(layout)

    def openLayoutDesigners(self):
        return list(self._designers)


class _Designer:
    def __init__(self, layout):
        self._layout = layout
        self.previewed = []

    def layout(self):
        return self._layout

    def setAtlasPreviewEnabled(self, enabled):
        self.previewed.append(enabled)


class _Layout:
    def __init__(self, name="Carte", atlas=None):
        self._name = name
        self._atlas = atlas
        self.refreshed = 0

    def name(self):
        return self._name

    def atlas(self):
        return self._atlas

    def refresh(self):
        self.refreshed += 1


class QgsReport(_Layout):
    """A report, not a print layout: refused like an unknown name."""


class _Node:
    def __init__(self, parent=None):
        self._parent = parent

    def parent(self):
        return self._parent


_TOP = _Node(None)
_GROUP = _Node(_TOP)
_LEAF = _Node(_GROUP)


class _Tree:
    def findLayer(self, _layer_id):
        return _LEAF


class _Atlas:
    def __init__(self, pages=4, enabled=True, coverage=True):
        self._pages = pages
        self._enabled = enabled
        self._coverage = object() if coverage else None
        self.current = 0
        self.rendered = 0
        self.ended = 0

    def enabled(self):
        return self._enabled

    def coverageLayer(self):
        return self._coverage

    def updateFeatures(self):
        self.current = -1
        return self._pages

    def seekTo(self, page):
        if not 0 <= page < self._pages:
            return False
        self.current = page
        return True

    def beginRender(self):
        self.rendered += 1
        return True

    def endRender(self):
        self.ended += 1

    def currentFeatureNumber(self):
        return self.current

    def first(self):
        self.current = 0
        return self._pages > 0

    def previous(self):
        if self.current <= 0:
            return False
        self.current -= 1
        return True

    def next(self):
        if self.current + 1 >= self._pages:
            return False
        self.current += 1
        return True

    def last(self):
        if self._pages <= 0:
            return False
        self.current = self._pages - 1
        return True


class _Qgis:
    Info, Success, Warning, Critical = "info", "success", "warning", "critical"


@pytest.fixture(autouse=True)
def fake_qgis(monkeypatch):
    core = sys.modules["qgis.core"]
    monkeypatch.setattr(core, "QgsProject", _Project, raising=False)
    monkeypatch.setattr(core, "QgsFeatureRequest", _Request, raising=False)
    monkeypatch.setattr(core, "Qgis", _Qgis, raising=False)
    monkeypatch.setattr(sys.modules["qgis.utils"], "iface", None, raising=False)


@pytest.fixture(autouse=True)
def layers(monkeypatch):
    layer = _Layer(fids=[1, 2, 3])
    # The shim of LayerKind under the test package may hold its own copy: pin the module to the real one.
    monkeypatch.setattr(gui_control, "LayerKind", LayerKind)
    monkeypatch.setattr(gui_control, "resolve_layer", lambda reference: layer if reference == "communes" else None)
    monkeypatch.setattr(gui_control, "layer_kind", lambda found: LayerKind.VECTOR)
    module = sys.modules[_PKG + ".adapters.public_api.introspection"]
    monkeypatch.setattr(module, "_checked_expression", lambda found, expression: expression)
    return layer


def test_open_layout_opens_in_front():
    layout = _Layout()
    _Project.layouts = _Layouts([layout])
    face = _Face()
    assert gui_control.open_layout("Carte", iface_obj=face) == {"name": "Carte", "opened": True}
    assert face.opened == [layout]


def test_open_layout_refuses_an_unknown_layout_or_a_report():
    _Project.layouts = _Layouts([_Layout("Carte")])
    with pytest.raises(ValueError, match="no print layout 'nope'"):
        gui_control.open_layout("nope", iface_obj=_Face())
    _Project.layouts = _Layouts([QgsReport("Rapport")])
    with pytest.raises(ValueError, match="no print layout 'Rapport'"):
        gui_control.open_layout("Rapport", iface_obj=_Face())


def test_open_layout_needs_a_window():
    _Project.layouts = _Layouts([_Layout("Carte")])
    with pytest.raises(ValueError, match="no window"):
        gui_control.open_layout("Carte")


def test_flash_flashes_without_selecting():
    face = _Face(canvas=_Canvas())
    answer = gui_control.flash_features("communes", '"pop" > 100', iface_obj=face)
    assert answer == {"layer": "communes", "flashed": 3}
    assert face._canvas.flashed[0][1] == [1, 2, 3]


def test_flash_is_bounded_and_says_so(layers):
    layers._fids = list(range(502))
    answer = gui_control.flash_features("communes", '"pop" > 0', iface_obj=_Face(canvas=_Canvas()))
    assert answer["flashed"] == 500 and "first 500" in answer["note"]


def test_flash_refuses_an_unknown_layer_an_empty_expression_and_no_match(layers):
    face = _Face(canvas=_Canvas())
    with pytest.raises(ValueError, match="not found"):
        gui_control.flash_features("absente", '"pop" > 0', iface_obj=face)
    with pytest.raises(ValueError, match="an expression is needed"):
        gui_control.flash_features("communes", "  ", iface_obj=face)
    layers._fids = []
    with pytest.raises(ValueError, match="no feature"):
        gui_control.flash_features("communes", '"pop" > 0', iface_obj=face)
    assert face._canvas.flashed == []


def test_flash_refuses_a_non_vector_layer(monkeypatch):
    monkeypatch.setattr(gui_control, "layer_kind", lambda found: LayerKind.RASTER)
    with pytest.raises(ValueError, match="not a vector layer"):
        gui_control.flash_features("communes", '"pop" > 0', iface_obj=_Face(canvas=_Canvas()))


def test_set_active_layer_reveals_in_the_tree(layers):
    view = _View()
    face = _Face(view=view)
    answer = gui_control.set_active_layer("communes", iface_obj=face)
    assert answer == {"layer": "communes", "active": True, "revealed": True}
    assert face.active is layers and view.current is layers
    assert view._model.expanded and view.scrolled  # groups unfolded, scrolled into view


def test_layer_tree_navigation_uses_view_indexes_instead_of_source_model_indexes(layers):
    view = _View()
    view.node2index = lambda node: ('view-index', id(node))
    gui_control.set_active_layer('communes', iface_obj=_Face(view=view))
    assert view._model.expanded and view.scrolled
    assert all(index[0] == 'view-index' for index, _expanded in view._model.expanded)
    assert all(index[0] == 'view-index' for index in view.scrolled)


def test_set_active_layer_without_reveal_leaves_the_tree_alone():
    face = _Face(view=_View())
    answer = gui_control.set_active_layer("communes", reveal=False, iface_obj=face)
    assert answer == {"layer": "communes", "active": True, "revealed": False}
    assert face._view.current is None


def test_set_active_layer_refuses_an_unknown_layer_and_no_window():
    with pytest.raises(ValueError, match="not found"):
        gui_control.set_active_layer("absente", iface_obj=_Face())
    with pytest.raises(ValueError, match="no window"):
        gui_control.set_active_layer("communes")


def test_show_message_goes_to_the_bar():
    face = _Face(bar=_Bar())
    assert gui_control.show_message("Filtre appliqué.", level="success", duration=7, iface_obj=face) == {
        "shown": True, "level": "success"}
    assert face._bar.messages == [("FilterMate", "Filtre appliqué.", "success", 7)]


def test_show_message_refuses_an_empty_text_a_long_one_a_bad_level_and_no_window():
    face = _Face(bar=_Bar())
    with pytest.raises(ValueError, match="a message is needed"):
        gui_control.show_message("  ", iface_obj=face)
    with pytest.raises(ValueError, match="at most 500 characters"):
        gui_control.show_message("x" * 501, iface_obj=face)
    with pytest.raises(ValueError, match="level is one of"):
        gui_control.show_message("hello", level="loud", iface_obj=face)
    with pytest.raises(ValueError, match="no window"):
        gui_control.show_message("hello")
    assert face._bar.messages == []


def test_preview_atlas_turns_a_page_and_previews_it():
    layout = _Layout(atlas=_Atlas(pages=4))
    _Project.layouts = _Layouts([layout])
    face = _Face(designers=[_Designer(layout)])
    answer = gui_control.preview_atlas("Carte", action="next", iface_obj=face)
    assert answer == {"layout": "Carte", "action": "next", "page": 2, "pages": 4, "preview": True}
    assert layout._atlas.rendered == layout._atlas.ended == 0 and layout.refreshed == 1


def test_preview_atlas_keeps_its_position_across_calls_and_refusals():
    layout = _Layout(atlas=_Atlas(pages=4))
    _Project.layouts = _Layouts([layout])
    face = _Face(designers=[_Designer(layout)])
    assert gui_control.preview_atlas("Carte", action="next", iface_obj=face)["page"] == 2
    assert gui_control.preview_atlas("Carte", action="next", iface_obj=face)["page"] == 3
    assert gui_control.preview_atlas("Carte", action="last", iface_obj=face)["page"] == 4
    with pytest.raises(ValueError, match="no next page"):
        gui_control.preview_atlas("Carte", action="next", iface_obj=face)
    assert layout._atlas.currentFeatureNumber() == 3
    assert gui_control.preview_atlas("Carte", action="previous", iface_obj=face)["page"] == 3


@pytest.mark.parametrize("preview", [True, False])
def test_preview_atlas_needs_a_window_before_changing_the_page(preview):
    layout = _Layout(atlas=_Atlas(pages=4))
    _Project.layouts = _Layouts([layout])
    with pytest.raises(ValueError, match="no window"):
        gui_control.preview_atlas("Carte", preview=preview)
    assert layout._atlas.currentFeatureNumber() == 0


def test_flash_needs_a_window():
    with pytest.raises(ValueError, match="no window"):
        gui_control.flash_features("communes", '"pop" > 100')


def test_chat_dispatch_translates_window_refusals(monkeypatch):
    error_module = importlib.import_module(_PKG + ".core.agent.tool_executor")
    handlers = gui_control.chat_handlers()
    expected = {"open_layout", "preview_atlas", "flash_features", "set_active_layer", "show_message"}
    assert set(handlers) == expected

    def refused(*arguments, **keywords):
        raise ValueError("QGIS has no window")

    for name, arguments in (
        ("open_layout", {"name": "Carte"}), ("preview_atlas", {"layout": "Carte"}),
        ("flash_features", {"layer": "communes", "expression": '"pop" > 0'}),
        ("set_active_layer", {"layer": "communes"}), ("show_message", {"text": "hello"}),
    ):
        monkeypatch.setattr(gui_control, name, refused)
        with pytest.raises(error_module.ToolFailure, match="no window"):
            handlers[name](arguments)


def test_preview_atlas_without_a_designer_still_turns():
    layout = _Layout(atlas=_Atlas(pages=4))
    _Project.layouts = _Layouts([layout])
    answer = gui_control.preview_atlas("Carte", action="last", iface_obj=_Face())
    assert (answer["page"], answer["pages"], answer["preview"]) == (4, 4, False)


def test_preview_atlas_refuses_no_atlas_no_page_and_no_further_page():
    _Project.layouts = _Layouts([_Layout("Carte")])
    with pytest.raises(ValueError, match="no atlas: set_atlas first"):
        gui_control.preview_atlas("Carte", iface_obj=_Face())
    _Project.layouts = _Layouts([_Layout("Carte", _Atlas(pages=4, enabled=False))])
    with pytest.raises(ValueError, match="no atlas: set_atlas first"):
        gui_control.preview_atlas("Carte", iface_obj=_Face())
    _Project.layouts = _Layouts([_Layout("Carte", _Atlas(pages=0))])
    with pytest.raises(ValueError, match="no page"):
        gui_control.preview_atlas("Carte", iface_obj=_Face())
    _Project.layouts = _Layouts([_Layout("Carte", _Atlas(pages=4))])
    with pytest.raises(ValueError, match="action is one of"):
        gui_control.preview_atlas("Carte", action="back", iface_obj=_Face())
    layout = _Layout("Carte", _Atlas(pages=1))
    _Project.layouts = _Layouts([layout])
    with pytest.raises(ValueError, match="no next page"):
        gui_control.preview_atlas("Carte", action="next", iface_obj=_Face())
