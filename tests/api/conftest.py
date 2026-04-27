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

from filtermate_api.accessor import InMemoryAccessor, LayerSummary  # noqa: E402
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
def accessor(sample_layers) -> InMemoryAccessor:
    return InMemoryAccessor(layers=list(sample_layers))


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
