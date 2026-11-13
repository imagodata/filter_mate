# -*- coding: utf-8 -*-
"""Which Processing algorithms a model may run (core/agent/processing_policy.py) and what its formulas may hold."""
import pytest

from core.agent.processing_policy import DENIED, VALUE_ALGORITHMS, matches, refusal
from core.agent.sql_guard import expression_problem, processing_expression_problem

pytestmark = pytest.mark.unit

BUFFER = [("INPUT", "source", False), ("DISTANCE", "distance", False), ("OUTPUT", "sink", False)]


def test_an_algorithm_of_qgis_that_makes_a_layer_runs():
    assert refusal("native:buffer", "native", BUFFER) == ""
    assert refusal("qgis:regularpoints", "qgis", [("EXTENT", "extent", False), ("OUTPUT", "sink", False)]) == ""
    assert refusal("native:rastercalc", "native", [("LAYERS", "multilayer", False), ("OUTPUT", "rasterDestination", False)]) == ""


@pytest.mark.parametrize("provider", ["gdal", "grass", "saga", "pdal", "script", "model", "filtermate", ""])
def test_other_providers_are_refused(provider):
    assert "only the algorithms of QGIS" in refusal(f"{provider}:x", provider, BUFFER)


def test_what_makes_no_layer_is_refused():
    # truncate, selection, projection, index, import into a database: they act in place
    for algorithm, parameters in (("native:truncatetable", [("INPUT", "vector", False)]),
                                  ("native:selectbyexpression", [("INPUT", "vector", False), ("EXPRESSION", "expression", False)]),
                                  ("native:definecurrentprojection", [("INPUT", "vector", False), ("CRS", "crs", False)]),
                                  ("native:createspatialindex", [("INPUT", "vector", False)])):
        assert "makes no layer" in refusal(algorithm, "native", parameters), algorithm


def test_values_algorithms_run_without_a_layer():
    assert refusal("native:rasterlayerproperties", "native", [("INPUT", "raster", False)]) == ""
    assert "native:basicstatisticsforfields" in VALUE_ALGORITHMS


def test_code_sql_and_network_are_refused_by_name():
    for algorithm in ("qgis:executesql", "qgis:advancedpythonfieldcalculator", "native:postgisexecuteandloadsql",
                      "native:httprequest", "native:zonalstatistics"):
        assert algorithm in DENIED
        assert "code, SQL or a network request" in refusal(algorithm, algorithm.split(":")[0], BUFFER)


def test_files_connections_and_layouts():
    assert "writes a file" in refusal("native:package", "native", [("LAYERS", "multilayer", False),
                                                                    ("OUTPUT", "fileDestination", False)])
    # an optional file output stays unset: the algorithm runs
    assert refusal("native:listuniquevalues", "native", [("INPUT", "source", False),
                                                         ("OUTPUT_HTML_FILE", "fileDestination", True)]) == ""
    for kind in ("file", "providerconnection", "layout", "fields_mapping", "aggregates", "execute_sql"):
        assert kind in refusal("native:x", "native", [(kind.upper(), kind, False), ("OUTPUT", "sink", False)]), kind
        assert refusal("native:x", "native", [(kind.upper(), kind, True), ("OUTPUT", "sink", False)]) == "", kind


# Types of the parameters of the algorithms allowed in QGIS 3.44.6, besides layers, extents, points, CRS, formulas,
# options and destinations; then simple ones that exist in other versions.
PLAIN = ["number", "field", "string", "boolean", "distance", "band", "area", "scale", "matrix", "duration",
         "raster_calc_expression", "relief_colors", "meshdatasetgroups", "meshdatasettime", "color", "datetime", "range",
         "geometry", "volume", "attribute", "pointcloudattribute"]


@pytest.mark.parametrize("kind", PLAIN + ["idw_interpolation_data", "source", "multilayer", "extent", "point", "crs",
                                          "expression", "enum"])
def test_known_types_are_given(kind):
    assert refusal("native:x", "native", [("P", kind, False), ("OUTPUT", "sink", False)]) == ""


@pytest.mark.parametrize("kind", ["coordinateoperation", "alignrasterlayers", "annotation", "a_type_of_tomorrow",
                                  "dxflayers", "tininputlayers", "vectortilewriterlayers"])
def test_a_type_not_known_as_safe_is_refused_when_required_and_left_unset_when_optional(kind):
    # A PROJ operation names a grid by path or URL; other types carry paths or layers outside the project.
    assert kind in refusal("native:x", "native", [("P", kind, False), ("OUTPUT", "sink", False)])
    assert refusal("native:x", "native", [("P", kind, True), ("OUTPUT", "sink", False)]) == ""


def test_interpolations_run_their_rows_are_rewritten_by_the_adapter():
    idw = [("INTERPOLATION_DATA", "idw_interpolation_data", False), ("DISTANCE_COEFFICIENT", "number", False),
           ("EXTENT", "extent", False), ("PIXEL_SIZE", "number", False), ("OUTPUT", "rasterDestination", False)]
    assert refusal("qgis:idwinterpolation", "qgis", idw) == ""


def test_what_sends_data_out_is_refused_by_name():
    for algorithm in ("native:batchnominatimgeocoder", "native:openurl"):
        assert algorithm in DENIED
        assert refusal(algorithm, "native", BUFFER)


def test_the_sources_of_the_layers_are_not_made_a_layer_the_model_reads():
    """native:exportlayersinformation makes a layer (so the rule alone let it run) of the source of each layer."""
    parameters = [("LAYERS", "multilayer", False), ("OUTPUT", "sink", False)]
    assert refusal("native:exportlayersinformation", "native", parameters) != ""
    assert refusal("native:buffer", "native", BUFFER) == ""


def test_deprecated():
    assert "deprecated" in refusal("native:old", "native", BUFFER, deprecated=True)


def test_search_words():
    assert matches("join location", ["native:joinattributesbylocation", "Join attributes by location"])
    assert matches("BUFFER", ["native:buffer"]) and not matches("buffer voronoi", ["native:buffer"])


@pytest.mark.parametrize("formula", ['"pop" * 2', "sqrt($area) / 10", "round(\"surface\" / 10000, 2)",
                                     "buffer($geometry, 10)", "if(\"pop\" > 5, 'big', 'small')", "x(centroid($geometry))"])
def test_formulas_that_compute(formula):
    assert processing_expression_problem(formula) == ""


@pytest.mark.parametrize("formula", ["env('HOME')", "eval('1')", "file_exists('/etc/passwd')",
                                     "aggregate('communes', 'sum', \"pop\")", "get_feature('a', 'b', 1)",
                                     "sqlite_fetch_and_increment('/tmp/x', 't', 'id', 'k', 'a', map('s', '1'))",
                                     "load_layer('/tmp/a.shp', 'ogr')", "\"a\"(1)"])
def test_formulas_that_read_or_write_elsewhere(formula):
    assert processing_expression_problem(formula)


def test_the_selection_list_stays_narrower():
    assert expression_problem("sqrt($area)") and not processing_expression_problem("sqrt($area)")
