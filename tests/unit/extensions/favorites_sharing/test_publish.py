# -*- coding: utf-8 -*-
"""
Tests for FavoritesSharingService.publish_bundle + related helpers.

Covers:
- happy-path publish into a fresh collection directory (is_new=True)
- publish into an existing collection (manifest merged, not clobbered)
- overwrite safety (refuse by default, accept with overwrite=True)
- filename sanitisation
- allowed_collections config allow-list honoured by scanner
- default_publish_collection pre-selection helper
"""

import json
import os
from unittest.mock import MagicMock

import pytest

from extensions.favorites_sharing.scanner import ResourceSharingScanner
from extensions.favorites_sharing.service import (
    CollectionTarget,
    FavoritesSharingService,
    PublishResult,
)


# ─── Fixtures ────────────────────────────────────────────────────────────


@pytest.fixture
def scanner(tmp_path):
    """Scanner pointed at an empty collections root."""
    root = tmp_path / "collections"
    root.mkdir()
    return ResourceSharingScanner(collections_root=str(root))


@pytest.fixture
def service(scanner):
    return FavoritesSharingService(scanner)


@pytest.fixture
def fake_favorites_service():
    """Minimal stand-in for FavoritesService.export_favorites.

    Writes a small v3 envelope and returns a dict-like result matching
    the FavoriteExportResult shape that PublishBundle checks.
    """
    svc = MagicMock()

    def _export(file_path, favorite_ids=None, collection_metadata=None):
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        envelope = {
            "schema": "filter_mate.favorites",
            "schema_version": 3,
            "favorites": [{"name": f"Fav-{fid}", "expression": "TRUE"}
                          for fid in (favorite_ids or [])],
        }
        if collection_metadata:
            envelope["collection"] = dict(collection_metadata)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(envelope, f)
        result = MagicMock()
        result.success = True
        result.favorites_count = len(favorite_ids or [])
        result.file_path = file_path
        return result

    svc.export_favorites.side_effect = _export
    return svc


# ─── Happy path ─────────────────────────────────────────────────────────


def test_publish_into_new_collection_creates_tree(tmp_path, service, fake_favorites_service):
    target = CollectionTarget(
        collection_dir=str(tmp_path / "collections" / "brand-new"),
        display_name="Brand New",
        is_new=True,
    )
    result = service.publish_bundle(
        favorites_service=fake_favorites_service,
        target=target,
        bundle_filename="zones",
        favorite_ids=["a", "b", "c"],
        collection_metadata={"author": "me", "license": "MIT"},
    )
    assert isinstance(result, PublishResult)
    assert result.success, result.error_message
    assert result.favorites_count == 3
    assert os.path.isfile(result.bundle_path)
    assert result.bundle_path.endswith("zones.fmfav-pack.json")
    assert os.path.isfile(result.collection_manifest_path)

    # Manifest contents
    with open(result.collection_manifest_path, 'r', encoding='utf-8') as f:
        manifest = json.load(f)
    assert manifest["author"] == "me"
    assert manifest["license"] == "MIT"
    assert manifest["name"]  # derived from target.display_name

    # Bundle carries the collection block
    with open(result.bundle_path, 'r', encoding='utf-8') as f:
        bundle = json.load(f)
    assert bundle["collection"]["author"] == "me"
    assert bundle["schema_version"] == 3


def test_publish_refuses_overwrite_by_default(tmp_path, service, fake_favorites_service):
    target = CollectionTarget(
        collection_dir=str(tmp_path / "collections" / "c1"),
        display_name="c1",
        is_new=True,
    )
    # First publish succeeds
    r1 = service.publish_bundle(
        favorites_service=fake_favorites_service, target=target,
        bundle_filename="x", favorite_ids=["a"], collection_metadata={},
    )
    assert r1.success

    # Second publish with same name must fail without overwrite=True
    r2 = service.publish_bundle(
        favorites_service=fake_favorites_service, target=target,
        bundle_filename="x", favorite_ids=["a"], collection_metadata={},
    )
    assert not r2.success
    assert "already exists" in r2.error_message


def test_publish_overwrite_true_replaces_bundle(tmp_path, service, fake_favorites_service):
    target = CollectionTarget(
        collection_dir=str(tmp_path / "collections" / "c2"),
        display_name="c2",
        is_new=True,
    )
    r1 = service.publish_bundle(
        favorites_service=fake_favorites_service, target=target,
        bundle_filename="x", favorite_ids=["a"], collection_metadata={},
    )
    assert r1.success

    r2 = service.publish_bundle(
        favorites_service=fake_favorites_service, target=target,
        bundle_filename="x", favorite_ids=["b", "c"], collection_metadata={},
        overwrite=True,
    )
    assert r2.success
    assert r2.favorites_count == 2

    # Bundle now reflects the newer export
    with open(r2.bundle_path, 'r', encoding='utf-8') as f:
        bundle = json.load(f)
    names = {fav["name"] for fav in bundle["favorites"]}
    assert names == {"Fav-b", "Fav-c"}


def test_publish_merges_existing_manifest_keys(tmp_path, service, fake_favorites_service):
    """Keys already present in collection.json (e.g. qgis_min, tags) must
    survive a publish that doesn't set them.
    """
    col_dir = tmp_path / "collections" / "c3"
    col_dir.mkdir(parents=True)
    manifest_path = col_dir / "collection.json"
    manifest_path.write_text(json.dumps({
        "name": "C3",
        "qgis_min": "3.28",
        "tags": ["preset"],
        "homepage": "https://c3.example",
    }))

    target = CollectionTarget(
        collection_dir=str(col_dir),
        display_name="C3",
        existing_metadata={"name": "C3"},
    )
    result = service.publish_bundle(
        favorites_service=fake_favorites_service, target=target,
        bundle_filename="x", favorite_ids=["a"],
        collection_metadata={"author": "new-author"},
    )
    assert result.success
    with open(manifest_path, 'r', encoding='utf-8') as f:
        merged = json.load(f)
    # New key added
    assert merged["author"] == "new-author"
    # Pre-existing keys preserved
    assert merged["qgis_min"] == "3.28"
    assert merged["tags"] == ["preset"]
    assert merged["homepage"] == "https://c3.example"


def test_publish_rejects_empty_favorite_list(tmp_path, service, fake_favorites_service):
    target = CollectionTarget(
        collection_dir=str(tmp_path / "collections" / "c4"),
        display_name="c4",
        is_new=True,
    )
    result = service.publish_bundle(
        favorites_service=fake_favorites_service, target=target,
        bundle_filename="x", favorite_ids=[], collection_metadata={},
    )
    assert not result.success
    assert "No favorites" in result.error_message


# ─── Filename sanitisation ───────────────────────────────────────────────


@pytest.mark.parametrize("raw, expected", [
    ("zones", "zones.fmfav-pack.json"),
    ("Zone Bruxelles", "Zone_Bruxelles.fmfav-pack.json"),
    # "../../etc/passwd" has 6 non-alnum chars ('..', '/', '..', '/') before
    # "etc", plus one more '/' before "passwd" — so 6 leading underscores,
    # then "etc_passwd" (the '/' between etc and passwd also becomes '_').
    ("../../etc/passwd", "______etc_passwd.fmfav-pack.json"),
    # User-typed extensions are stripped BEFORE sanitising — no double
    # suffix, no mid-word underscores from the '.' in ".fmfav-pack.json".
    ("my.bundle.fmfav-pack.json", "my_bundle.fmfav-pack.json"),
    ("my.bundle.fmfav.json", "my_bundle.fmfav-pack.json"),
    ("", "favorites.fmfav-pack.json"),
    ("   ", "favorites.fmfav-pack.json"),
])
def test_sanitize_bundle_filename(raw, expected):
    assert FavoritesSharingService._sanitize_bundle_filename(raw) == expected


# ─── Target enumeration & suggest_new ───────────────────────────────────


def test_list_publish_targets_enumerates_existing(tmp_path, service):
    root = service._scanner.get_collections_root()
    assert root is not None

    (tmp_path / "collections" / "alpha").mkdir(parents=True)
    (tmp_path / "collections" / "beta").mkdir(parents=True)
    with open(os.path.join(root, "alpha", "collection.json"), 'w') as f:
        json.dump({"name": "Alpha (pretty)"}, f)

    targets = service.list_publish_targets()
    names = {t.display_name for t in targets}
    assert "Alpha (pretty)" in names, "manifest name should win over dirname"
    assert "beta" in names
    # existing metadata preserved for the form prefill
    alpha = next(t for t in targets if t.display_name == "Alpha (pretty)")
    assert alpha.existing_metadata.get("name") == "Alpha (pretty)"


def test_suggest_new_collection_dir_sanitises(tmp_path, service):
    root = service._scanner.get_collections_root()
    path = service.suggest_new_collection_dir("Zones Urbanisation")
    assert path is not None
    assert path.startswith(root)
    assert os.path.basename(path) == "Zones_Urbanisation"


def test_suggest_new_collection_dir_returns_none_without_root(tmp_path):
    scanner = ResourceSharingScanner(collections_root=str(tmp_path / "does-not-exist"))
    service = FavoritesSharingService(scanner)
    assert service.suggest_new_collection_dir("Whatever") is None


# ─── Scanner allow-list ─────────────────────────────────────────────────


def test_scanner_allow_list_filters_collections(tmp_path, monkeypatch):
    """When allowed_collections is non-empty, non-whitelisted collections
    are skipped by the scanner.
    """
    root = tmp_path / "collections"
    root.mkdir()
    # Two collections, only one allowed
    for name in ("kept", "filtered"):
        favdir = root / name / "filter_mate" / "favorites"
        favdir.mkdir(parents=True)
        (favdir / "x.fmfav.json").write_text(json.dumps({
            "name": f"from-{name}", "expression": "TRUE"
        }))

    # Point the scanner at our fake root
    scanner = ResourceSharingScanner(collections_root=str(root))

    # Stub the config reader to advertise an allow-list of one
    monkeypatch.setattr(
        ResourceSharingScanner,
        "_read_allowed_collections",
        lambda self: ["kept"],
    )

    items = scanner.scan()
    names = {f.name for f in items}
    assert "from-kept" in names
    assert "from-filtered" not in names


def test_scanner_empty_allow_list_scans_everything(tmp_path, monkeypatch):
    root = tmp_path / "collections"
    root.mkdir()
    favdir = root / "anyone" / "filter_mate" / "favorites"
    favdir.mkdir(parents=True)
    (favdir / "x.fmfav.json").write_text(json.dumps({
        "name": "Anyone", "expression": "TRUE"
    }))
    scanner = ResourceSharingScanner(collections_root=str(root))
    monkeypatch.setattr(
        ResourceSharingScanner,
        "_read_allowed_collections",
        lambda self: [],
    )
    items = scanner.scan()
    assert any(f.name == "Anyone" for f in items)


def test_scanner_uses_config_root_override(tmp_path, monkeypatch):
    """resource_sharing_root in config overrides the auto-detected path."""
    real_root = tmp_path / "custom_location" / "collections"
    real_root.mkdir(parents=True)
    (real_root / "c1" / "filter_mate" / "favorites").mkdir(parents=True)
    (real_root / "c1" / "filter_mate" / "favorites" / "x.fmfav.json").write_text(
        json.dumps({"name": "From Config Root", "expression": "TRUE"})
    )

    scanner = ResourceSharingScanner()  # no explicit root
    monkeypatch.setattr(
        ResourceSharingScanner,
        "_read_configured_root",
        lambda self: str(real_root),
    )
    assert scanner.get_collections_root() == str(real_root)
    items = scanner.scan()
    assert any(f.name == "From Config Root" for f in items)
