# -*- coding: utf-8 -*-
"""Tests for favorites_sharing.validator."""

import pytest

from extensions.favorites_sharing.validator import validate


# ─── Valid bundles ─────────────────────────────────────────────────────


def test_validate_minimal_v3_bundle():
    data = {
        "schema": "filter_mate.favorites",
        "schema_version": 3,
        "favorites": [
            {"name": "X", "expression": "TRUE"},
        ],
    }
    ok, errors = validate(data)
    assert ok, errors
    assert errors == []


def test_validate_accepts_extra_envelope_fields():
    """Unknown top-level keys don't break validation (forward-compat)."""
    data = {
        "schema": "filter_mate.favorites",
        "schema_version": 3,
        "favorites": [{"name": "A", "expression": "TRUE"}],
        "future_plugin_field": "something",
        "collection": {"name": "Zone Pack", "author": "me"},
    }
    ok, errors = validate(data)
    assert ok, errors


def test_validate_accepts_future_schema_version():
    """Schema v4+ is accepted — loader falls back to v3 reader with _extra."""
    data = {
        "schema": "filter_mate.favorites",
        "schema_version": 42,
        "favorites": [{"name": "Future", "expression": "TRUE"}],
    }
    ok, errors = validate(data)
    assert ok, errors


# ─── Invalid bundles ────────────────────────────────────────────────────


def test_validate_rejects_non_object_root():
    ok, errors = validate(["not", "an", "object"])
    assert not ok
    assert any("object" in e for e in errors)


def test_validate_rejects_wrong_schema_identifier():
    data = {
        "schema": "not_filter_mate",
        "schema_version": 3,
        "favorites": [],
    }
    ok, errors = validate(data)
    assert not ok
    assert any("schema" in e for e in errors)


def test_validate_rejects_missing_favorites():
    data = {"schema": "filter_mate.favorites", "schema_version": 3}
    ok, errors = validate(data)
    assert not ok
    assert any("favorites" in e for e in errors)


def test_validate_rejects_non_list_favorites():
    data = {
        "schema": "filter_mate.favorites",
        "schema_version": 3,
        "favorites": "not a list",
    }
    ok, errors = validate(data)
    assert not ok
    assert any("favorites" in e for e in errors)


def test_validate_rejects_favorite_missing_name():
    data = {
        "schema": "filter_mate.favorites",
        "schema_version": 3,
        "favorites": [
            {"expression": "TRUE"},  # no name
        ],
    }
    ok, errors = validate(data)
    assert not ok
    assert any("name" in e for e in errors)


def test_validate_rejects_favorite_missing_expression():
    data = {
        "schema": "filter_mate.favorites",
        "schema_version": 3,
        "favorites": [
            {"name": "X"},  # no expression
        ],
    }
    ok, errors = validate(data)
    assert not ok
    assert any("expression" in e for e in errors)


def test_validate_rejects_wrong_tags_type():
    data = {
        "schema": "filter_mate.favorites",
        "schema_version": 3,
        "favorites": [
            {"name": "X", "expression": "TRUE", "tags": "not-a-list"},
        ],
    }
    ok, errors = validate(data)
    assert not ok
    assert any("tags" in e for e in errors)


def test_validate_rejects_negative_use_count():
    data = {
        "schema": "filter_mate.favorites",
        "schema_version": 3,
        "favorites": [
            {"name": "X", "expression": "TRUE", "use_count": -1},
        ],
    }
    ok, errors = validate(data)
    assert not ok
    assert any("use_count" in e for e in errors)


def test_validate_reports_all_bad_favorites():
    """Validator surfaces every broken favorite, not just the first."""
    data = {
        "schema": "filter_mate.favorites",
        "schema_version": 3,
        "favorites": [
            {"name": "ok", "expression": "TRUE"},
            {"expression": "TRUE"},        # missing name
            {"name": "X"},                 # missing expression
        ],
    }
    ok, errors = validate(data)
    assert not ok
    assert any("favorites[1]" in e for e in errors)
    assert any("favorites[2]" in e for e in errors)
