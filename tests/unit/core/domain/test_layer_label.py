# -*- coding: utf-8 -*-
"""The text of a layer in the lists of the panel (core/domain/layer_label.py, 2026-11-24)."""
import pytest

from core.domain.layer_label import layer_label

pytestmark = pytest.mark.unit


def test_a_layer_and_its_crs():
    assert layer_label("communes", "EPSG:2154") == "communes [EPSG:2154]"


@pytest.mark.parametrize("authid", ["", None, "  "])
def test_a_crs_without_an_authority_id_gives_no_empty_brackets(authid):
    assert layer_label("lhd_vegetation", authid) == "lhd_vegetation"
