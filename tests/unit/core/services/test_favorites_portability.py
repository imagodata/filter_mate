"""Tests for the portable v2 favorites format.

Covers the _strip_project_bindings (export side) and
_rebind_imported_favorite (import side) helpers added in 2026-04-21 to
enable cross-project favorite sharing. The helpers operate on plain dicts,
so these tests avoid requiring a running QGIS environment.
"""

import pytest

from core.services.favorites_service import FavoritesService


class TestStripProjectBindings:
    def test_drops_id_and_project_uuid(self):
        fav = {
            "id": "abc-123",
            "project_uuid": "11111111-1111-1111-1111-111111111111",
            "name": "My favorite",
            "expression": "foo = 1",
            "layer_id": "source-uuid",
        }
        stripped = FavoritesService._strip_project_bindings(fav)
        assert "id" not in stripped
        assert "project_uuid" not in stripped
        assert stripped["layer_id"] is None
        assert stripped["name"] == "My favorite"
        assert stripped["expression"] == "foo = 1"

    def test_rewrites_remote_layers_stripping_uuid_keeping_signature(self):
        fav = {
            "id": "abc",
            "name": "My favorite",
            "expression": "foo = 1",
            "layer_id": "source-uuid",
            "remote_layers": {
                "Points de demande": {
                    "expression": "id in (1,2,3)",
                    "layer_id": "remote-uuid-1",
                    "layer_signature": "postgres::public.points_demande",
                    "provider": "postgres",
                },
                "Parcelles": {
                    "expression": "commune = 'X'",
                    "layer_id": "remote-uuid-2",
                    "layer_signature": "ogr::parcelles",
                    "provider": "ogr",
                },
            },
        }
        stripped = FavoritesService._strip_project_bindings(fav)
        for key, payload in stripped["remote_layers"].items():
            assert payload["layer_id"] is None, key
            assert "layer_signature" in payload, key
            assert "expression" in payload, key

    def test_resets_usage_counters(self):
        fav = {
            "name": "F",
            "expression": "x = 1",
            "use_count": 42,
            "last_used_at": "2026-04-01T10:00:00",
        }
        stripped = FavoritesService._strip_project_bindings(fav)
        assert stripped["use_count"] == 0
        assert stripped["last_used_at"] is None


class TestRebindImportedFavorite:
    def test_untouched_when_no_signatures(self):
        fav = {
            "name": "F",
            "expression": "x = 1",
            "layer_id": None,
            "remote_layers": {
                "Foo": {"expression": "y = 2", "layer_id": None},
            },
        }
        rebound = FavoritesService._rebind_imported_favorite(fav, file_version="1.0")
        assert rebound["layer_id"] is None
        assert rebound["remote_layers"]["Foo"]["layer_id"] is None

    def test_missing_signatures_leave_layer_id_none(self, monkeypatch):
        # Simulate "no layer matches" by forcing the resolver to return None.
        monkeypatch.setattr(
            FavoritesService,
            "_resolve_signature_to_layer_id",
            staticmethod(lambda sig: None),
        )
        fav = {
            "name": "F",
            "expression": "x = 1",
            "layer_id": None,
            "spatial_config": {"source_layer_signature": "postgres::public.nope"},
            "remote_layers": {
                "Foo": {
                    "expression": "y = 2",
                    "layer_id": None,
                    "layer_signature": "postgres::public.foo",
                }
            },
        }
        rebound = FavoritesService._rebind_imported_favorite(fav, file_version="2.0")
        assert rebound["layer_id"] is None
        assert rebound["remote_layers"]["Foo"]["layer_id"] is None

    def test_spatial_config_roundtrips_through_strip_and_rebind(self, monkeypatch):
        """spatial_config (incl. exploring_groupbox added 2026-04-21) must be
        preserved across the portable v2 roundtrip — otherwise imported
        favorites would fire in the wrong selection mode.
        """
        monkeypatch.setattr(
            FavoritesService,
            "_resolve_signature_to_layer_id",
            staticmethod(lambda sig: None),  # no project at test time
        )
        fav = {
            "name": "Fav with spatial config",
            "expression": "x = 1",
            "layer_id": "uuid-source",
            "spatial_config": {
                "exploring_groupbox": "custom_selection",
                "custom_selection_expression": "type = 'A'",
                "source_layer_signature": "postgres::public.points",
                "task_feature_ids": [1, 2, 3],
                "predicates": {"intersects": True},
                "buffer_value": 2.5,
            },
        }

        stripped = FavoritesService._strip_project_bindings(fav)
        # spatial_config is kept as-is (no secret coupling to layer UUIDs)
        assert stripped["spatial_config"]["exploring_groupbox"] == "custom_selection"
        assert stripped["spatial_config"]["custom_selection_expression"] == "type = 'A'"
        assert stripped["spatial_config"]["source_layer_signature"] == "postgres::public.points"
        assert stripped["spatial_config"]["task_feature_ids"] == [1, 2, 3]

        rebound = FavoritesService._rebind_imported_favorite(stripped, file_version="2.0")
        assert rebound["spatial_config"]["exploring_groupbox"] == "custom_selection"
        assert rebound["spatial_config"]["custom_selection_expression"] == "type = 'A'"
        assert rebound["spatial_config"]["task_feature_ids"] == [1, 2, 3]
        assert rebound["spatial_config"]["predicates"] == {"intersects": True}
        assert rebound["spatial_config"]["buffer_value"] == 2.5

    def test_matching_signatures_populate_local_layer_ids(self, monkeypatch):
        mapping = {
            "postgres::public.points_demande": "local-uuid-A",
            "ogr::parcelles": "local-uuid-B",
        }
        monkeypatch.setattr(
            FavoritesService,
            "_resolve_signature_to_layer_id",
            staticmethod(lambda sig: mapping.get(sig)),
        )
        fav = {
            "name": "F",
            "expression": "x = 1",
            "layer_id": None,
            "spatial_config": {"source_layer_signature": "postgres::public.points_demande"},
            "remote_layers": {
                "Parcelles": {
                    "expression": "commune = 'X'",
                    "layer_id": None,
                    "layer_signature": "ogr::parcelles",
                }
            },
        }
        rebound = FavoritesService._rebind_imported_favorite(fav, file_version="2.0")
        assert rebound["layer_id"] == "local-uuid-A"
        assert rebound["remote_layers"]["Parcelles"]["layer_id"] == "local-uuid-B"
