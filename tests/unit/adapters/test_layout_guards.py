# -*- coding: utf-8 -*-
"""Layouts, lot 6 (audit of 2026-11-24): texts without scripts, a fingerprint that sees frames, layer sets,
backgrounds and fonts, and atlas pages always named inside the folder.

Pure helpers read off ``adapters/public_api/layouts.py`` by AST (no QGIS).
"""
import ast
import html as html_module
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

pytestmark = pytest.mark.unit

PATH = Path(__file__).resolve().parents[3] / 'adapters' / 'public_api' / 'layouts.py'


def _methods(*names):
    tree = ast.parse(PATH.read_text())
    wanted = [node for node in tree.body
              if isinstance(node, (ast.FunctionDef, ast.Assign)) and (
                  (isinstance(node, ast.FunctionDef) and node.name in names)
                  or (isinstance(node, ast.Assign) and any(
                      getattr(target, 'id', '') in ('_EXPRESSION_PART', '_WINDOWS_RESERVED')
                      for target in node.targets)))]
    namespace = {'__name__': 'filter_mate.adapters.public_api.layouts',
                 '__package__': 'filter_mate.adapters.public_api',
                 'html': html_module, 're': re}
    exec(compile(ast.Module(body=wanted, type_ignores=[]), str(PATH), 'exec'), namespace)
    return namespace


FUNCS = _methods('_label_text', '_finger_map', '_finger_text', '_atlas_filename_expression', '_safe')


def test_set_text_on_an_html_label_keeps_scripts_literal():
    """setText reads HTML (scripts included, run under QGIS 3.22) in a label in HTML mode."""
    item = SimpleNamespace(mode=lambda: 1)
    text = '<script src="http://evil.example/x.js"></script><b>hi</b> [% "nom" %]'
    out = FUNCS['_label_text'](item, text)
    assert "evil.example" in out and "<script" not in out and "<b>" not in out
    assert '[% "nom" %]' in out


def test_set_text_on_a_plain_label_goes_as_it_is():
    item = SimpleNamespace(mode=lambda: 0)
    text = '<b>hi</b> [% "nom" %]'
    assert FUNCS['_label_text'](item, text) == text


def test_set_text_without_a_mode_reads_plain():
    assert FUNCS['_label_text'](object(), '<b>hi</b>') == '<b>hi</b>'


class Map:
    def __init__(self, layers=(), extent=None, frame=True, background=None, driven=False, keep=True):
        self._layers, self._extent, self._frame = list(layers), extent, frame
        self._background, self._driven, self._keep = background, driven, keep

    def keepLayerSet(self):
        return self._keep

    def layers(self):
        return [SimpleNamespace(id=lambda lid=lid: lid) for lid in self._layers]

    def atlasDriven(self):
        return self._driven

    def extent(self):
        return SimpleNamespace(xMinimum=lambda: self._extent[0], yMinimum=lambda: self._extent[1],
                               xMaximum=lambda: self._extent[2], yMaximum=lambda: self._extent[3])

    def frameEnabled(self):
        return self._frame

    def backgroundEnabled(self):
        return self._background is not None

    def backgroundColor(self):
        return SimpleNamespace(name=lambda: self._background)


def test_fingerprint_sees_layers_extent_frame_and_background():
    shown = FUNCS['_finger_map'](Map(layers=["b", "a"], extent=(1.0, 2.0, 3.0, 4.0), background="#ff0000"))
    assert shown[0] == ["a", "b"] and shown[1] == [1.0, 2.0, 3.0, 4.0]
    assert shown[2] is True and shown[3] == "#ff0000"


def test_fingerprint_ignores_the_tree_and_a_driven_extent():
    shown = FUNCS['_finger_map'](Map(keep=False, driven=True, background=None))
    assert shown == ["tree", True, False]


def test_fingerprint_sees_mode_and_font_of_a_text():
    font = SimpleNamespace(family=lambda: "Arial", pointSizeF=lambda: 12.0, bold=lambda: True,
                           italic=lambda: False, underline=lambda: False)
    assert FUNCS['_finger_text'](SimpleNamespace(mode=lambda: 1, font=lambda: font)) == [1, ["Arial", 12.0, True,
                                                                                            False, False]]


def test_reserved_windows_names_get_a_suffix():
    """Audit of 2026-11-24: CON, NUL and friends are no file anywhere."""
    assert FUNCS['_safe']("CON", "layout") == "CON_"
    assert FUNCS['_safe']("nul", "layout") == "nul_"
    assert FUNCS['_safe']("com9 plans", "layout") == "com9 plans"
    assert FUNCS['_safe']("Carte", "layout") == "Carte"
    assert FUNCS['_safe']("  ", "layout") == "layout"


def test_atlas_page_without_a_name_falls_back_to_its_number():
    expression = FUNCS['_atlas_filename_expression']("", "atlas")
    assert "coalesce(nullif(trim(" in expression and "@atlas_featurenumber" in expression
    named = FUNCS['_atlas_filename_expression']('"nom"', "atlas")
    assert '"nom"' in named and "'atlas_'" in named
    quoted = FUNCS['_atlas_filename_expression']("", "l'atlas")
    assert "l_atlas_" in quoted and "l'atlas" not in quoted
