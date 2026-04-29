# -*- coding: utf-8 -*-
"""Edge-case tests for ``FilterParameterBuilder`` — P1-FCB-TESTS.

Background: ``filter_config_builder.py`` was created on 2026-04-29 by
the ``a32026ec`` merge of two prior builder modules and immediately
patched by ``9814bb40`` ("strip stray tool-call tags breaking import").
The 2026-04-29 deep audit (P1-FCB-TESTS) flagged the module as having
zero dedicated test coverage despite the messy birth, and listed 10
edge cases the merge could mishandle. These tests pin the current
behaviour so future refactors notice when an edge changes.

Per project conventions all QGIS imports are mocked by
``tests/conftest.py`` — these tests never instantiate a real
``QgsVectorLayer``.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import types
from unittest.mock import MagicMock

import pytest


# ---------------------------------------------------------------------------
# Module-load shim
# ---------------------------------------------------------------------------
#
# ``filter_config_builder.py`` uses 3-dot relative imports
# (``from ...infrastructure.utils.layer_utils import …``) which only
# resolve when the module is loaded as ``filter_mate.core.services.<X>``.
# In production QGIS that's how it's loaded; in our test harness
# ``PYTHONPATH=.`` puts the plugin root on sys.path so ``core`` is a
# top-level package and the 3-dot import goes "beyond top-level".
#
# Other directory-level conftests (notably ``tests/unit/core/tasks/
# conftest.py``) install MagicMock placeholders for the entire
# ``filter_mate.*`` tree to support handler tests. We can't fight that
# globally without breaking those tests. So instead we sandbox the
# import: spin up a private package hierarchy in sys.modules just long
# enough to load the real file via ``importlib.util.spec_from_file_location``,
# stash the resulting module, and remove the temporary parents so we
# don't leak state to the rest of the suite.
def _load_filter_config_builder():
    plugin_root = os.path.dirname(
        os.path.dirname(
            os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
        )
    )
    fcb_path = os.path.join(
        plugin_root, "core", "services", "filter_config_builder.py"
    )

    # Ephemeral parent chain — never published as ``filter_mate`` so we
    # don't clobber the handler-test MagicMocks.
    sandbox_root_name = "_fcb_sandbox"
    chain = (
        sandbox_root_name,
        f"{sandbox_root_name}.core",
        f"{sandbox_root_name}.core.services",
        f"{sandbox_root_name}.infrastructure",
        f"{sandbox_root_name}.infrastructure.utils",
    )
    chain_dirs = (
        plugin_root,
        os.path.join(plugin_root, "core"),
        os.path.join(plugin_root, "core", "services"),
        os.path.join(plugin_root, "infrastructure"),
        os.path.join(plugin_root, "infrastructure", "utils"),
    )
    for name, dir_path in zip(chain, chain_dirs):
        pkg = types.ModuleType(name)
        pkg.__path__ = [dir_path]
        sys.modules[name] = pkg
        if "." in name:
            parent_name, _, leaf = name.rpartition(".")
            setattr(sys.modules[parent_name], leaf, pkg)

    qualname = f"{sandbox_root_name}.core.services.filter_config_builder"
    spec = importlib.util.spec_from_file_location(qualname, fcb_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[qualname] = module
    spec.loader.exec_module(module)

    # Detach the sandbox parents — keep only the leaf so the test can
    # reference it without the handler-test MagicMocks trampling.
    for name in chain:
        sys.modules.pop(name, None)

    return module


_FCB = _load_filter_config_builder()
PROVIDER_OGR = _FCB.PROVIDER_OGR
PROVIDER_POSTGRES = _FCB.PROVIDER_POSTGRES
PROVIDER_SPATIALITE = _FCB.PROVIDER_SPATIALITE
FilterParameterBuilder = _FCB.FilterParameterBuilder
ParameterBuilderContext = _FCB.ParameterBuilderContext
build_filter_parameters = _FCB.build_filter_parameters


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_layer(
    *,
    name: str = "TestLayer",
    layer_id: str = "test-id",
    fields: list[str] | None = None,
    primary_key_idx: list[int] | None = None,
    source: str = "/tmp/test.gpkg|layername=test",
    subset: str = "",
    provider: str = PROVIDER_OGR,
) -> MagicMock:
    """Build a layer mock that responds to the calls _auto_fill_metadata hits."""
    layer = MagicMock()
    layer.name.return_value = name
    layer.id.return_value = layer_id
    layer.source.return_value = source
    layer.subsetString.return_value = subset
    layer.providerType.return_value = provider

    if fields is None:
        fields = ["fid", "name"]

    field_objs = []
    for fname in fields:
        f = MagicMock()
        f.name.return_value = fname
        field_objs.append(f)

    fields_collection = MagicMock()
    fields_collection.__iter__ = lambda self: iter(field_objs)
    fields_collection.__getitem__ = lambda self, idx: field_objs[idx]
    fields_collection.__len__ = lambda self: len(field_objs)
    fields_collection.__bool__ = lambda self: bool(field_objs)
    layer.fields.return_value = fields_collection

    # ``or`` would treat the explicit empty list ``[]`` as falsy and
    # substitute the default — preserve the caller's exact value.
    layer.primaryKeyAttributes.return_value = (
        [0] if primary_key_idx is None else primary_key_idx
    )
    return layer


def _minimal_infos(**overrides) -> dict:
    """A REQUIRED_INFO_KEYS-complete infos dict."""
    base = {
        "layer_provider_type": PROVIDER_OGR,
        "layer_name": "TestLayer",
        "layer_id": "test-id",
        "layer_geometry_field": "geom",
        "primary_key_name": "fid",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Edge case 1 — infos=None inside task_parameters
# ---------------------------------------------------------------------------


class TestEdgeCase01_InfosNone:
    """Caller passes ``{"infos": None}`` explicitly.

    The builder reads ``task_parameters.get("infos", {}).copy()`` — if
    a caller stores ``None`` under that key the .copy() would
    AttributeError. We pin: either it works (auto-fill recovers) or we
    surface a clear error rather than ``AttributeError``.
    """

    def test_explicit_none_infos_raises_attributeerror_today(self):
        # Document the current (sub-optimal) contract: ``None`` infos
        # is a programmer error and produces AttributeError. Refactors
        # that change this should consciously decide what's better.
        layer = _make_layer()
        ctx = ParameterBuilderContext(
            task_parameters={"infos": None},
            source_layer=layer,
        )
        with pytest.raises(AttributeError):
            FilterParameterBuilder().build(ctx)


# ---------------------------------------------------------------------------
# Edge case 2 — zero-field layer
# ---------------------------------------------------------------------------


class TestEdgeCase02_ZeroFieldLayer:
    """A layer with no fields — primary_key_name falls back to 'id'."""

    def test_zero_field_layer_uses_id_pk_and_empty_field_names(self):
        layer = _make_layer(fields=[], primary_key_idx=[])
        params = build_filter_parameters(
            task_parameters={"infos": {}},
            source_layer=layer,
        )
        # Auto-fill picked 'id' as the fallback PK name.
        assert params.primary_key_name == "id"
        # field_names is filtered to exclude PK; with zero fields it's empty.
        assert params.field_names == []


# ---------------------------------------------------------------------------
# Edge case 3 — subset string is the literal '<NULL>' placeholder
# ---------------------------------------------------------------------------


class TestEdgeCase03_NullPlaceholderSubset:
    """The 2026-04-23 COALESCE bug noted ``is_filter_expression`` false-pos
    on the literal ``<NULL>`` string. When ``sanitize_subset_fn`` is None,
    the raw subset reaches the FilterParameters as-is — the builder is
    not the right layer to second-guess it.
    """

    def test_null_placeholder_subset_passes_through_when_no_sanitizer(self):
        layer = _make_layer(subset="<NULL>")
        params = build_filter_parameters(
            task_parameters={"infos": _minimal_infos()},
            source_layer=layer,
        )
        assert params.old_subset == "<NULL>"

    def test_subset_routes_through_sanitizer_when_provided(self):
        layer = _make_layer(subset="<NULL>")
        captured = []

        def _sanitize(s: str) -> str:
            captured.append(s)
            return ""  # sanitizer drops the placeholder

        params = build_filter_parameters(
            task_parameters={"infos": _minimal_infos()},
            source_layer=layer,
            sanitize_subset_fn=_sanitize,
        )
        assert captured == ["<NULL>"]
        assert params.old_subset == ""


# ---------------------------------------------------------------------------
# Edge case 4 — schema name with embedded quote breaks regex silently
# ---------------------------------------------------------------------------


class TestEdgeCase04_SchemaWithQuote:
    """``_auto_fill_metadata`` parses the layer source via regex
    ``r'table="([^"]+)"\\.'`` — a schema containing ``"`` simply doesn't
    match and we fall through to ``'public'``. Pin the silent fallthrough.
    """

    def test_pg_source_with_quote_in_schema_falls_back_to_public(self):
        # PostgreSQL data source with a malformed table identifier.
        layer = _make_layer(
            source='dbname=x table="weird"schema"."mytable"',
            provider=PROVIDER_POSTGRES,
        )
        # Prevent _validate_schema from re-detecting via QgsDataSourceUri
        # (it returns a MagicMock which is truthy and confuses the
        # mismatch logic). Stub provider detection so the builder
        # treats the layer as PG and takes the auto-fill path.
        params = build_filter_parameters(
            task_parameters={
                "infos": {
                    "layer_provider_type": PROVIDER_POSTGRES,
                    "layer_name": "L",
                    "layer_id": "lid",
                    "layer_geometry_field": "geom",
                    "primary_key_name": "id",
                    # Pre-set schema so _validate_schema doesn't QgsDataSourceUri-detect
                    "layer_schema": "public",
                },
            },
            source_layer=layer,
        )
        # Builder picks up the pre-set schema; auto-fill never touched it.
        assert params.schema in ("public", "")


# ---------------------------------------------------------------------------
# Edge case 5 — provider_type='unknown' fallthrough
# ---------------------------------------------------------------------------


class TestEdgeCase05_ProviderUnknown:
    """No detect_provider_fn AND no layer_provider_type in infos →
    auto-fill stamps 'unknown'. Builder doesn't reject it — downstream
    is the one that crashes."""

    def test_unknown_provider_type_propagates(self):
        layer = _make_layer()
        params = build_filter_parameters(
            task_parameters={"infos": {}},
            source_layer=layer,
            # No detect_provider_fn → 'unknown' fallback
        )
        assert params.provider_type == "unknown"


# ---------------------------------------------------------------------------
# Edge case 6 — forced_backends is a list, not a dict
# ---------------------------------------------------------------------------


class TestEdgeCase06_ForcedBackendsWrongType:
    """``forced_backends.get(...)`` is called blindly — a non-dict caller
    surfaces an AttributeError. Pin the contract: caller must hand a dict.
    """

    def test_list_for_forced_backends_raises_attributeerror(self):
        layer = _make_layer()
        with pytest.raises(AttributeError):
            build_filter_parameters(
                task_parameters={
                    "infos": _minimal_infos(),
                    "forced_backends": [],  # WRONG: should be {}
                },
                source_layer=layer,
            )


# ---------------------------------------------------------------------------
# Edge case 7 — primaryKeyAttributes returns out-of-range index
# ---------------------------------------------------------------------------


class TestEdgeCase07_PrimaryKeyIndexOutOfRange:
    """A layer reports a PK index that's beyond fields() — happens when
    a column is deleted concurrently. ``fields()[bad_idx]`` should raise
    a clear error; the builder doesn't swallow it.
    """

    def test_out_of_range_pk_index_propagates(self):
        layer = _make_layer(fields=["a"], primary_key_idx=[5])
        with pytest.raises((IndexError, AttributeError)):
            build_filter_parameters(
                task_parameters={"infos": {}},
                source_layer=layer,
            )


# ---------------------------------------------------------------------------
# Edge case 8 — REQUIRED_INFO_KEYS missing → KeyError
# ---------------------------------------------------------------------------


class TestEdgeCase08_RequiredKeysMissing:
    """When source_layer is None we can't auto-fill, so any missing
    required key surfaces as a KeyError listing the missing names."""

    def test_no_layer_and_missing_keys_raises_keyerror(self):
        # No source_layer means _auto_fill_metadata short-circuits.
        with pytest.raises(KeyError, match="layer_provider_type"):
            build_filter_parameters(
                task_parameters={"infos": {}},
                source_layer=None,
            )

    def test_no_layer_with_complete_infos_succeeds(self):
        # All five REQUIRED_INFO_KEYS supplied → builder doesn't need
        # the layer at all and produces a coherent FilterParameters.
        params = build_filter_parameters(
            task_parameters={"infos": _minimal_infos()},
            source_layer=None,
        )
        assert params.layer_name == "TestLayer"
        assert params.provider_type == PROVIDER_OGR
        assert params.field_names == []  # no layer → no fields


# ---------------------------------------------------------------------------
# Edge case 9 — combine_operator config defaults
# ---------------------------------------------------------------------------


class TestEdgeCase09_CombineOperatorDefaults:
    """has_combine_operator=False forces both operators back to AND
    regardless of any garbage in the filtering config."""

    def test_combine_operator_false_resets_to_and(self):
        layer = _make_layer()
        params = build_filter_parameters(
            task_parameters={
                "infos": _minimal_infos(),
                "filtering": {
                    "has_combine_operator": False,
                    "source_layer_combine_operator": "OR",  # ignored
                    "other_layers_combine_operator": "OR",  # ignored
                },
            },
            source_layer=layer,
        )
        assert params.has_combine_operator is False
        assert params.source_layer_combine_operator == "AND"
        assert params.other_layers_combine_operator == "AND"

    def test_explicit_or_combine_operator_preserved_when_enabled(self):
        layer = _make_layer()
        params = build_filter_parameters(
            task_parameters={
                "infos": _minimal_infos(),
                "filtering": {
                    "has_combine_operator": True,
                    "source_layer_combine_operator": "OR",
                    "other_layers_combine_operator": "OR",
                },
            },
            source_layer=layer,
        )
        assert params.source_layer_combine_operator == "OR"
        assert params.other_layers_combine_operator == "OR"

    def test_none_operator_falls_back_to_and(self):
        layer = _make_layer()
        params = build_filter_parameters(
            task_parameters={
                "infos": _minimal_infos(),
                "filtering": {
                    "has_combine_operator": True,
                    "source_layer_combine_operator": None,
                    "other_layers_combine_operator": None,
                },
            },
            source_layer=layer,
        )
        assert params.source_layer_combine_operator == "AND"
        assert params.other_layers_combine_operator == "AND"


# ---------------------------------------------------------------------------
# Edge case 10 — table_name fallback chain
# ---------------------------------------------------------------------------


class TestEdgeCase10_TableNameFallback:
    """``table_name = infos.get('layer_table_name') or infos['layer_name']``
    — explicit layer_table_name wins; otherwise layer_name is used."""

    def test_layer_table_name_wins_over_layer_name(self):
        params = build_filter_parameters(
            task_parameters={
                "infos": _minimal_infos(
                    layer_table_name="actual_pg_table",
                    layer_name="display_name",
                ),
            },
            source_layer=None,
        )
        assert params.table_name == "actual_pg_table"

    def test_falls_back_to_layer_name_when_table_name_absent(self):
        params = build_filter_parameters(
            task_parameters={
                "infos": _minimal_infos(layer_name="single_name"),
            },
            source_layer=None,
        )
        assert params.table_name == "single_name"

    def test_empty_layer_table_name_falls_back_to_layer_name(self):
        params = build_filter_parameters(
            task_parameters={
                "infos": _minimal_infos(
                    layer_table_name="",
                    layer_name="fallback_name",
                ),
            },
            source_layer=None,
        )
        # Empty string is falsy so the `or` chain reaches layer_name.
        assert params.table_name == "fallback_name"


# ---------------------------------------------------------------------------
# Bonus — forced backend per layer overrides provider detection
# ---------------------------------------------------------------------------


class TestForcedBackendOverride:
    def test_forced_backend_for_specific_layer_id_wins(self):
        params = build_filter_parameters(
            task_parameters={
                "infos": _minimal_infos(
                    layer_id="lyr-42",
                    layer_provider_type=PROVIDER_OGR,
                ),
                "forced_backends": {"lyr-42": PROVIDER_SPATIALITE},
            },
            source_layer=None,
        )
        assert params.provider_type == PROVIDER_SPATIALITE
        assert params.forced_backend is True

    def test_forced_backend_for_other_layer_id_does_not_apply(self):
        params = build_filter_parameters(
            task_parameters={
                "infos": _minimal_infos(
                    layer_id="lyr-A",
                    layer_provider_type=PROVIDER_OGR,
                ),
                "forced_backends": {"lyr-B": PROVIDER_SPATIALITE},
            },
            source_layer=None,
        )
        assert params.provider_type == PROVIDER_OGR
        assert params.forced_backend is False
