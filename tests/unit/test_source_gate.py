# -*- coding: utf-8 -*-
"""The Sources tab enforced on the REST API (audit of 2026-11-24, decided with the user).

The chat does not offer the tools of the sources the user did not tick; the REST API (and through it the MCP
server) reached Overpass, Copernicus and Meta anyway. Pure gate, no QGIS.
"""
import pytest

pytestmark = pytest.mark.unit

from filtermate_api.source_gate import refused_for


@pytest.mark.parametrize("kinds", [{"overpass"}, {"overpass", "elevation"}])
def test_ticked_kind_allowed(kinds):
    assert refused_for(kinds, "overpass", "Overpass") is None


@pytest.mark.parametrize("kinds", [set(), {"elevation"}, {"xyz"}])
def test_unticked_kind_refused_with_the_tab(kinds):
    refused = refused_for(kinds, "overpass", "Overpass")
    assert refused is not None and "Sources tab" in refused
