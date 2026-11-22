# -*- coding: utf-8 -*-
"""Which projection for which map (core/agent/projections.py, 2026-11-22)."""
import pytest

from core.agent import projections
from core.agent.projections import ProjectionError, suggest

pytestmark = pytest.mark.unit


def crs_of(result):
    return [row["crs"] for row in result["suggestions"]]


def test_a_french_department_gets_lambert93_its_cc_zone_and_utm():
    result = suggest([1.0, 43.2, 1.9, 43.9])  # around Toulouse
    assert result["scale"] == "local"
    assert crs_of(result)[:3] == ["EPSG:2154", "EPSG:3943", "EPSG:25831"]


def test_areas_put_an_equal_area_projection_first():
    result = suggest([-5.0, 42.0, 8.0, 51.0], purpose="areas")  # France
    first = result["suggestions"][0]
    assert first["keeps"] == "equal-area" and first["crs"] in ("EPSG:3035",) + tuple(
        row["crs"] for row in result["suggestions"] if row["crs"].startswith("PROJ:+proj=aea"))


def test_a_country_comes_before_its_continent():
    rows = crs_of(suggest([3.0, 50.0, 6.0, 51.4]))
    assert rows.index("EPSG:3812") < rows.index("EPSG:3034")


def test_overseas_territories_have_their_own_system():
    assert crs_of(suggest([55.2, -21.4, 55.8, -20.9]))[0] == "EPSG:2975"  # Réunion
    assert crs_of(suggest([-54.5, 3.0, -52.0, 5.5]))[0] == "EPSG:2972"  # Guyane


def test_the_world_gets_world_projections_and_web_mercator_last():
    result = suggest([-180, -60, 180, 80])
    assert result["scale"] == "world" and crs_of(result)[0] == "ESRI:54030"
    assert crs_of(suggest([-180, -60, 180, 80], purpose="areas"))[0] == "EPSG:8857"
    assert crs_of(result)[-1] == "EPSG:3857"
    assert crs_of(suggest([2, 48, 3, 49], purpose="web"))[0] == "EPSG:3857"


def test_polar_data_get_a_polar_projection():
    assert "EPSG:3413" in crs_of(suggest([-180, 66, 180, 90]))
    assert "EPSG:3031" in crs_of(suggest([-180, -90, 180, -60]))


def test_a_projection_is_made_for_data_nobody_made_one_for():
    result = suggest([30.0, 40.0, 60.0, 55.0], purpose="areas")  # from the Black Sea to the Caspian
    first = result["suggestions"][0]
    assert first["crs"].startswith("PROJ:+proj=aea") and "+lat_1=42.5" in first["crs"] and "+lat_2=52.5" in first["crs"]
    distances = suggest([30.0, 40.0, 60.0, 55.0], purpose="distances")["suggestions"][0]
    assert distances["crs"].startswith("PROJ:+proj=aeqd") and "+lon_0=45.0" in distances["crs"]


def test_a_tall_extent_gets_a_transverse_mercator_and_the_equator_an_azimuthal_one():
    crs, _, _ = projections.custom((10.0, -30.0, 14.0, 5.0), "conformal")
    assert crs.startswith("PROJ:+proj=tmerc") and "+lon_0=12.0" in crs
    crs, _, _ = projections.custom((10.0, -5.0, 30.0, 5.0), "equal-area")
    assert crs.startswith("PROJ:+proj=laea")


def test_the_antimeridian_is_crossed_eastwards():
    result = suggest([170.0, -20.0, -170.0, -10.0], purpose="areas")  # Fiji, Samoa
    centred = [row["crs"] for row in result["suggestions"] if "+lon_0=" in row["crs"]][0]
    assert "+lon_0=180.0" in centred or "+lon_0=-180.0" in centred


def test_utm_zones_north_south_and_in_europe():
    assert projections.utm(2.3, 48.8)[0] == "EPSG:25831"
    assert projections.utm(-74.0, 40.7)[0] == "EPSG:32618"
    assert projections.utm(151.2, -33.9)[0] == "EPSG:32756"


@pytest.mark.parametrize("bounds", [[0, 0, 1], [0, 50, 1, 40], [0, 0, 1, 95], [float("nan"), 0, 1, 1],
                                    [0, 0, "a", 1]])
def test_an_extent_that_cannot_be_read_is_refused(bounds):
    with pytest.raises(ProjectionError):
        suggest(bounds)
    with pytest.raises(ProjectionError):
        suggest([0, 0, 1, 1], purpose="beauty")
