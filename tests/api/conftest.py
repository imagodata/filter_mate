# -*- coding: utf-8 -*-
"""Shared fixtures for the FilterMate REST API tests.

Skips the entire suite when ``fastapi`` isn't installed so the rest of
the unit tests still run on environments that haven't pulled in the API
extras (``pip install -r requirements-api.txt``).
"""
from __future__ import annotations

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from filtermate_api.accessor import (  # noqa: E402
    Favorite,
    InMemoryAccessor,
    LayerSummary,
)
from filtermate_api.server import create_app  # noqa: E402


@pytest.fixture
def sample_layers() -> list[LayerSummary]:
    return [
        LayerSummary(
            layer_id="L1",
            name="communes",
            provider_type="postgresql",
            feature_count=35000,
            geometry_type="MultiPolygon",
            crs_authid="EPSG:2154",
        ),
        LayerSummary(
            layer_id="L2",
            name="roads",
            provider_type="ogr",
            feature_count=12000,
            geometry_type="LineString",
            crs_authid="EPSG:2154",
        ),
    ]


@pytest.fixture
def sample_favorites() -> list[Favorite]:
    return [
        Favorite(
            favorite_id="fav-communes-large",
            name="Large communes",
            description="Communes >10k pop",
            layer_name="communes",
            expression='"population" > 10000',
        ),
        Favorite(
            favorite_id="fav-roads-major",
            name="Major roads",
            layer_name="roads",
            expression='"class" = \'major\'',
        ),
        # Intentionally has no layer_name — represents a malformed favorite
        # so we can exercise the 404 path.
        Favorite(favorite_id="fav-orphan", name="Orphan"),
    ]


@pytest.fixture
def accessor(sample_layers, sample_favorites) -> InMemoryAccessor:
    return InMemoryAccessor(
        layers=list(sample_layers),
        favorites=list(sample_favorites),
    )


@pytest.fixture
def client(accessor) -> TestClient:
    return TestClient(create_app(accessor=accessor))


@pytest.fixture
def client_factory():
    """Build a TestClient bound to a custom layer set.

    Useful for tests that need an empty/specific accessor without paying
    for the default fixture chain.
    """
    def _make(layers: list[LayerSummary] | None = None) -> TestClient:
        return TestClient(
            create_app(accessor=InMemoryAccessor(layers=list(layers or [])))
        )
    return _make
