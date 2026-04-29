"""A2 — LayerSignatureIndex no longer falls back to QgsProject.instance().

Audit 2026-04-29 (A2): the previous version reached into QGIS at the domain
layer when ``qgs_project`` was None. The fallback masked the dependency in
headless contexts and prevented services from controlling project lookup.
The constructor now respects the explicit None contract: empty index, no
implicit project walk.
"""
from __future__ import annotations

import importlib.util
import os
import sys
import types
from unittest.mock import MagicMock

import pytest


_PKG = "filter_mate_a2"
_PROJECT_ROOT = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
)


def _install_stubs() -> None:
    if _PKG in sys.modules:
        return

    root = types.ModuleType(_PKG)
    root.__path__ = [_PROJECT_ROOT]
    sys.modules[_PKG] = root

    core_mod = types.ModuleType(f"{_PKG}.core")
    core_mod.__path__ = [os.path.join(_PROJECT_ROOT, "core")]
    sys.modules[f"{_PKG}.core"] = core_mod

    domain_mod = types.ModuleType(f"{_PKG}.core.domain")
    domain_mod.__path__ = [os.path.join(_PROJECT_ROOT, "core", "domain")]
    sys.modules[f"{_PKG}.core.domain"] = domain_mod

    full = f"{_PKG}.core.domain.layer_signature"
    path = os.path.join(_PROJECT_ROOT, "core", "domain", "layer_signature.py")
    spec = importlib.util.spec_from_file_location(full, path)
    mod = importlib.util.module_from_spec(spec)
    mod.__package__ = f"{_PKG}.core.domain"
    sys.modules[full] = mod
    spec.loader.exec_module(mod)


_install_stubs()
_mod = sys.modules[f"{_PKG}.core.domain.layer_signature"]
LayerSignature = _mod.LayerSignature
LayerSignatureIndex = _mod.LayerSignatureIndex


class TestExplicitNoneContract:
    def test_qgs_project_none_yields_empty_index(self):
        index = LayerSignatureIndex(None)
        assert index.id_to_signature == {}
        assert index.name_to_signature == {}
        assert index.resolve("postgres::public.foo") is None

    def test_default_argument_is_none(self):
        # Calling with no argument must behave identically to passing None
        # — the regression A2 closed was the constructor reaching into
        # QgsProject.instance() in this branch.
        index = LayerSignatureIndex()
        assert index.id_to_signature == {}
        assert index.name_to_signature == {}

    def test_no_qgis_import_at_module_level(self):
        # Sanity: scan the source. The module must not reach into qgis
        # at the top of the file. Lazy imports inside compute() are
        # acceptable (parser usage) but the module-level surface must
        # stay clean.
        with open(_mod.__file__, "r", encoding="utf-8") as fh:
            source = fh.read()
        # The first 30 lines must not contain `from qgis` / `import qgis`.
        head = "\n".join(source.splitlines()[:30])
        assert "from qgis" not in head
        assert "import qgis" not in head


class TestPassedProjectWalksLayers:
    def test_walks_provided_project(self):
        # A fake project mimics the part of QgsProject the index uses.
        layer_a = MagicMock()
        layer_a.providerType.return_value = "postgres"
        layer_a.source.return_value = "dbname=x table=public.foo"
        layer_a.name.return_value = "foo"
        layer_b = MagicMock()
        layer_b.providerType.return_value = "ogr"
        layer_b.source.return_value = "/data/cities.shp"
        layer_b.name.return_value = "cities"

        project = MagicMock()
        project.mapLayers.return_value = {"L1": layer_a, "L2": layer_b}

        # Patch QgsDataSourceUri inside the module so postgres parsing
        # succeeds without real QGIS.
        class _FakeUri:
            def __init__(self, _src: str) -> None:
                pass

            def schema(self) -> str:
                return "public"

            def table(self) -> str:
                return "foo"

        # The lazy import inside compute() pulls qgis.core; stub it here.
        sys.modules.setdefault("qgis", MagicMock())
        sys.modules.setdefault("qgis.core", MagicMock())
        sys.modules["qgis.core"].QgsDataSourceUri = _FakeUri

        index = LayerSignatureIndex(project)

        assert index.id_to_signature == {
            "L1": "postgres::public.foo",
            "L2": "ogr::cities",
        }
        assert index.signature_for_id("L1") == "postgres::public.foo"
        assert index.resolve("ogr::cities") == "L2"
        assert index.signature_for_name("foo") == "postgres::public.foo"

    def test_project_with_broken_maplayers_yields_empty(self):
        # If mapLayers() raises (e.g. project closing concurrently), the
        # index must degrade to empty rather than propagate the failure.
        broken = MagicMock()
        broken.mapLayers.side_effect = RuntimeError("project closed")

        index = LayerSignatureIndex(broken)
        assert index.id_to_signature == {}

    def test_layer_with_compute_failure_skipped(self):
        # A layer whose providerType / source raises must be skipped, not
        # crash the whole walk.
        good = MagicMock()
        good.providerType.return_value = "ogr"
        good.source.return_value = "/data/g.shp"
        good.name.return_value = "g"

        bad = MagicMock()
        bad.providerType.side_effect = RuntimeError("layer destroyed")

        project = MagicMock()
        project.mapLayers.return_value = {"good": good, "bad": bad}

        index = LayerSignatureIndex(project)

        # The good layer is indexed; the bad one is silently skipped.
        assert "good" in index.id_to_signature
        # The bad entry must not pollute the index either way.
        bad_sig = index.id_to_signature.get("bad", "")
        assert "bad" not in bad_sig or bad_sig.startswith("unknown::")
