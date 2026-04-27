# -*- coding: utf-8 -*-
"""
Round-trip tests for FilterFavorite to_dict / from_dict.

Covers the v3 format promises:
- signature-keyed ``remote_layers`` canonicalisation
- ``_extra`` preservation of unknown keys (forward compat)
- legacy v1/v2 favorites still load without loss
- ``display_name`` populated from original layer name when missing
- timestamps preserved on round-trip through from_dict/to_dict
"""

import importlib.util
import os

import pytest


def _load_favorites_module():
    """Load core/domain/favorites_manager directly.

    We avoid importing via the ``core`` package because that triggers
    ``core/__init__.py`` -> QGIS imports which aren't available in the
    pure-Python test environment.
    """
    import sys as _sys
    import types

    plugin_root = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )))

    # favorites_manager.py uses relative imports (from .schema_constants).
    # Register a stand-in parent package so those imports resolve when the
    # module is loaded outside the real plugin namespace.
    pkg_name = "_fm_favorites_for_tests_pkg"
    if pkg_name not in _sys.modules:
        pkg = types.ModuleType(pkg_name)
        pkg.__path__ = [os.path.join(plugin_root, "core", "domain")]
        _sys.modules[pkg_name] = pkg

    sc_full = f"{pkg_name}.schema_constants"
    if sc_full not in _sys.modules:
        sc_path = os.path.join(plugin_root, "core", "domain", "schema_constants.py")
        sc_spec = importlib.util.spec_from_file_location(sc_full, sc_path)
        sc_module = importlib.util.module_from_spec(sc_spec)
        _sys.modules[sc_full] = sc_module
        sc_spec.loader.exec_module(sc_module)

    fm_full = f"{pkg_name}.favorites_manager"
    path = os.path.join(plugin_root, "core", "domain", "favorites_manager.py")
    spec = importlib.util.spec_from_file_location(fm_full, path)
    module = importlib.util.module_from_spec(spec)
    _sys.modules[fm_full] = module
    _sys.modules["_fm_favorites_for_tests"] = module  # legacy alias
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def FilterFavorite():
    return _load_favorites_module().FilterFavorite


@pytest.fixture(scope="module")
def normalize_remote_layers_keys():
    return _load_favorites_module().normalize_remote_layers_keys


# ─── Signature canonicalisation ──────────────────────────────────────────


def test_remote_layers_normalized_to_signature_keys(FilterFavorite):
    raw = {
        "name": "pg",
        "expression": "TRUE",
        "remote_layers": {
            "Buildings": {
                "expression": "x=1",
                "layer_signature": "postgres::public.buildings",
            },
        },
    }
    fav = FilterFavorite.from_dict(raw)
    assert "postgres::public.buildings" in fav.remote_layers
    assert fav.remote_layers["postgres::public.buildings"]["display_name"] == "Buildings"


def test_remote_layers_without_signature_kept_as_is(FilterFavorite):
    raw = {
        "name": "legacy",
        "expression": "TRUE",
        "remote_layers": {
            "Old Layer": {"expression": "x=1"},
        },
    }
    fav = FilterFavorite.from_dict(raw)
    assert "Old Layer" in fav.remote_layers
    assert fav.remote_layers["Old Layer"]["display_name"] == "Old Layer"


def test_signature_collision_collapses_to_first(normalize_remote_layers_keys):
    remote = {
        "alpha": {"expression": "a", "layer_signature": "postgres::public.dups"},
        "beta": {"expression": "b", "layer_signature": "postgres::public.dups"},
    }
    normalized = normalize_remote_layers_keys(remote)
    assert list(normalized.keys()) == ["postgres::public.dups"]
    assert normalized["postgres::public.dups"]["display_name"] == "alpha"


def test_empty_remote_layers_kept_none(FilterFavorite):
    """None remote_layers must stay None (not {}) so downstream checks work."""
    fav = FilterFavorite.from_dict({"name": "n", "expression": "TRUE", "remote_layers": None})
    assert fav.remote_layers is None


# ─── _extra preservation ─────────────────────────────────────────────────


def test_extra_preserves_unknown_top_level_fields(FilterFavorite):
    raw = {
        "name": "x",
        "expression": "TRUE",
        "future_plugin_field": "from-v99",
        "nested_extra": {"key": "value"},
    }
    fav = FilterFavorite.from_dict(raw)
    assert fav._extra == {"future_plugin_field": "from-v99", "nested_extra": {"key": "value"}}


def test_extra_roundtrip_via_to_dict(FilterFavorite):
    raw = {
        "name": "x",
        "expression": "TRUE",
        "custom_field": "value",
    }
    fav = FilterFavorite.from_dict(raw)
    out = fav.to_dict()
    # Unknown key is re-emitted at the top level, not hidden under _extra
    assert out.get("custom_field") == "value"
    assert "_extra" not in out


def test_extra_never_shadows_known_fields(FilterFavorite):
    """If _extra somehow contains a key that later becomes a dataclass
    field, the real field wins at serialisation time.
    """
    fav = FilterFavorite(name="real-name", expression="TRUE")
    fav._extra = {"name": "shadow-name"}
    out = fav.to_dict()
    assert out["name"] == "real-name"


def test_project_uuid_dropped_from_extra(FilterFavorite):
    """project_uuid is intentionally discarded on import — it's rebound
    by the caller, never round-tripped.
    """
    raw = {
        "name": "x",
        "expression": "TRUE",
        "project_uuid": "some-project-uuid",
    }
    fav = FilterFavorite.from_dict(raw)
    assert "project_uuid" not in fav._extra


# ─── Full round-trip ─────────────────────────────────────────────────────


def test_full_roundtrip_preserves_all_content(FilterFavorite):
    raw = {
        "name": "Zone Molenbeek",
        "expression": "\"commune\" = 'Molenbeek'",
        "layer_name": "zones",
        "layer_provider": "postgres",
        "description": "Zone urbanisme",
        "tags": ["urban", "bxl"],
        "created_at": "2025-01-15T10:00:00",
        "updated_at": "2025-01-20T12:00:00",
        "use_count": 7,
        "last_used_at": "2025-04-01T09:00:00",
        "remote_layers": {
            "postgres::public.bat": {
                "expression": "TRUE",
                "layer_signature": "postgres::public.bat",
                "display_name": "Bâtiments",
                "provider": "postgres",
            },
        },
        "spatial_config": {
            "source_layer_signature": "postgres::public.zones",
            "predicates": {"INTERSECT": True},
        },
        "extra_custom": 42,
    }
    fav = FilterFavorite.from_dict(raw)
    out = fav.to_dict()

    # Ensure content didn't drift
    assert out["name"] == "Zone Molenbeek"
    assert out["description"] == "Zone urbanisme"
    assert out["tags"] == ["urban", "bxl"]
    assert out["use_count"] == 7
    assert out["created_at"] == "2025-01-15T10:00:00"
    assert out["updated_at"] == "2025-01-20T12:00:00"
    assert out["extra_custom"] == 42
    assert "postgres::public.bat" in out["remote_layers"]
    assert out["remote_layers"]["postgres::public.bat"]["display_name"] == "Bâtiments"
    assert out["spatial_config"]["source_layer_signature"] == "postgres::public.zones"


def test_from_dict_handles_string_tags_payload(FilterFavorite):
    """Legacy SQLite rows store tags as JSON string; from_dict parses them."""
    fav = FilterFavorite.from_dict({
        "name": "x",
        "expression": "TRUE",
        "tags": '["a", "b"]',
    })
    assert fav.tags == ["a", "b"]


def test_from_dict_handles_corrupt_string_tags(FilterFavorite):
    """A non-JSON string tags value falls back to empty list, not a crash."""
    fav = FilterFavorite.from_dict({
        "name": "x",
        "expression": "TRUE",
        "tags": "not-json-at-all",
    })
    assert fav.tags == []
