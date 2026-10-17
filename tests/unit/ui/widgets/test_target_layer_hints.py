# -*- coding: utf-8 -*-
"""
FilterMate 5 hybrid targets: the FILTERING list of layers to filter holds
vector, raster and point cloud layers; each item says what the filter does to
it (mockup "Couches à filtrer · tout type"). Functions extracted with ast so
the Qt widget module is never imported.
"""
import ast
import types
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_MODULE = Path(__file__).resolve().parents[4] / "ui" / "widgets" / "custom_widgets.py"
_TREE = ast.parse(_MODULE.read_text(encoding="utf-8"))


def _module_namespace():
    """``COVERAGE_GEOMETRY_KINDS`` and ``target_kind`` of the module."""
    nodes = [node for node in _TREE.body
             if (isinstance(node, ast.Assign) and any(getattr(t, "id", "") == "COVERAGE_GEOMETRY_KINDS"
                                                       for t in node.targets))
             or (isinstance(node, ast.FunctionDef) and node.name == "target_kind")]
    namespace = {}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(_MODULE), "exec"), namespace)
    return namespace


def _method(name):
    for cls in (n for n in _TREE.body if isinstance(n, ast.ClassDef) and n.name == "QgsCheckableComboBoxLayer"):
        for node in cls.body:
            if isinstance(node, ast.FunctionDef) and node.name == name:
                namespace = {}
                exec(compile(ast.Module(body=[node], type_ignores=[]), str(_MODULE), "exec"), namespace)
                return namespace[name]
    raise AssertionError(f"{name} not found")


target_kind = _module_namespace()["target_kind"]


@pytest.mark.parametrize("geometry_type,kind", [
    ("GeometryType.Raster", "raster"),
    ("GeometryType.PointCloud", "point_cloud"),
    ("GeometryType.Polygon", "vector"),
    ("GeometryType.Line", "vector"),
    (None, "vector"),
])
def test_target_kind_from_the_geometry_type(geometry_type, kind):
    assert target_kind(geometry_type) == kind


def _combo():
    combo = types.SimpleNamespace(tr=lambda text: text)
    combo._target_hint = types.MethodType(_method("_target_hint"), combo)
    combo._target_tooltip = types.MethodType(_method("_target_tooltip"), combo)
    return combo


def test_each_kind_has_its_hint():
    combo = _combo()
    assert combo._target_hint("vector") == "features"
    assert combo._target_hint("raster") == "pixels in the zone"
    assert combo._target_hint("point_cloud") == "points in the zone"


def test_coverage_tooltips_mention_disjoint():
    combo = _combo()
    for kind in ("raster", "point_cloud"):
        assert "Disjoint" in combo._target_tooltip(kind)
    assert "predicate" in combo._target_tooltip("vector")


def test_only_the_filtering_list_shows_hints():
    dock = (_MODULE.parents[2] / "filter_mate_dockwidget.py").read_text(encoding="utf-8")
    assert "checkableComboBoxLayer_filtering_layers_to_filter.set_target_hints(True)" in dock
    assert "checkableComboBoxLayer_exporting_layers.set_target_hints" not in dock


def _paint_centroid_toggle():
    """``ItemDelegate.paint_centroid_toggle`` with stand-ins for its Qt names."""
    delegate = next(n for n in _TREE.body if isinstance(n, ast.ClassDef) and n.name == "ItemDelegate")
    node = next(n for n in delegate.body if isinstance(n, ast.FunctionDef) and n.name == "paint_centroid_toggle")
    node.decorator_list = []

    class QPointF:
        def __init__(self, point):
            self.point = point

    class Anything:
        def __init__(self, *args, **kwargs):
            pass

        def __getattr__(self, name):
            return Anything()

        def __call__(self, *args, **kwargs):
            return Anything()

    namespace = {"QPointF": QPointF, "QColor": Anything, "QBrush": Anything, "QtGui": Anything(), "Qt": Anything()}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(_MODULE), "exec"), namespace)
    return namespace["paint_centroid_toggle"], QPointF


class _Rect:
    def adjusted(self, *_margins):
        return self

    def center(self):
        return "QPoint"


@pytest.mark.parametrize("on", [True, False])
def test_centroid_toggle_paints_with_a_float_centre(on):
    """PyQt6 has no drawEllipse(QPoint, float, float): the glyph raised and the list items were not painted."""
    paint, point_f = _paint_centroid_toggle()
    calls = []

    class Painter:
        def __getattr__(self, name):
            return lambda *args: calls.append((name, args))

        def drawEllipse(self, centre, rx, ry):
            if not isinstance(centre, point_f):
                raise TypeError("drawEllipse(center: QPoint, rx: int, ry: int): argument 2 has unexpected type 'float'")
            calls.append(("drawEllipse", (centre, rx, ry)))

    paint(Painter(), _Rect(), on, "color")
    assert [name for name, _args in calls].count("drawEllipse") == 1
    assert calls[-1][0] == "restore"
