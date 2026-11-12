"""QGIS predicate -> native SQL: variables folded to constants, texts read as numbers, geometric functions.

No QGIS imports: the trees are built by hand as the QGIS adapter builds them
(``@name`` is the function ``var`` with a literal name, ``$geometry`` a
function without argument). What is written was compared with QGIS on real
layers by ``tests/qgis_headless/check_native_translation.py``.
"""
import sqlite3

import pytest

from filtermate_core.filter.expression_sanitizer import sanitize_subset_string
from filtermate_core.filter.native_dialect import (
    GEOPACKAGE, OGR_SQL, POSTGIS, POSTGRESQL, SQLITE, NativeGeometry, referenced_variables, translate_native,
    uses_geometry,
)
from filtermate_core.filter.server_dialect import Node, TranslationStatus

TYPES = {'id': 'int', 'pop': 'int', 'ratio': 'real', 'nom': 'text', 'code': 'text', 'actif': 'bool'}


def col(name):
    return Node('column', name, text='"{}"'.format(name))


def lit(value):
    if value is None:
        text = 'NULL'
    elif isinstance(value, str):
        text = "'" + value.replace("'", "''") + "'"
    else:
        text = repr(value)
    return Node('literal', value, text=text)


def binary(operator, left, right):
    return Node('binary', operator, (left, right), '{} {} {}'.format(left.text, operator, right.text))


def negation(node):
    return Node('unary', 'NOT', (node,), 'NOT ' + node.text)


def between(value, low, high, negated=False):
    return Node('between', negated, (value, low, high), '{} BETWEEN {} AND {}'.format(value.text, low.text, high.text))


def function(name, *arguments):
    return Node('function', name, tuple(arguments), '{}({})'.format(name, ', '.join(a.text for a in arguments)))


def var(name):
    return Node('function', 'var', (lit(name),), "var('{}')".format(name))


def translated(node, dialect, **kwargs):
    result = translate_native(node, dialect, TYPES, **kwargs)
    assert result.status == TranslationStatus.FULL, result.reason
    assert not result.local_expression
    return result.sql


def refused(node, dialect, **kwargs):
    result = translate_native(node, dialect, TYPES, **kwargs)
    assert result.status == TranslationStatus.NONE
    assert not result.sql
    assert result.local_expression == '(' + node.text + ')'
    return result.reason


# -- variables -----------------------------------------------------------------------------

# As QGIS gives them: a project or layer variable is a text, a QGIS one may be a number.
VARIABLES = {'seuil': '5', 'reel': '0.3', 'grand': '1e3', 'nom_cible': 'Route', 'motif': 'Route%', 'vide': '',
             'espace': ' 5', 'entier': 7, 'flottant': 2.5, 'vrai': True, 'rien': None, 'oblique': 'a\\b',
             'liste': ['a'], 'dico': {'a': 1}, 'objet': object()}


def folded(node, dialect, variables=VARIABLES, **kwargs):
    return translated(node, dialect, variables=variables, **kwargs)


def not_folded(node, dialect, variables=VARIABLES):
    return refused(node, dialect, variables=variables)


@pytest.mark.parametrize('dialect', [POSTGRESQL, SQLITE, OGR_SQL])
def test_a_variable_is_written_as_its_value(dialect):
    # '5' compared with a number is compared as the number 5, as QGIS compares it
    assert folded(binary('>', col('pop'), var('seuil')), dialect) == '"pop" > 5'
    assert folded(binary('<', var('seuil'), col('pop')), dialect) == '5 < "pop"'
    assert folded(binary('<', col('pop'), var('entier')), dialect) == '"pop" < 7'
    assert folded(binary('>', col('pop'), var('grand')), dialect) == translated(
        binary('>', col('pop'), lit(1000.0)), dialect)
    assert folded(binary('=', col('ratio'), var('reel')), dialect) == translated(
        binary('=', col('ratio'), lit(0.3)), dialect)
    assert folded(binary('>', col('ratio'), var('flottant')), dialect) == translated(
        binary('>', col('ratio'), lit(2.5)), dialect)


def test_a_text_variable_follows_the_rules_of_a_text_literal():
    assert folded(binary('=', col('nom'), var('nom_cible')), SQLITE) == '"nom" COLLATE BINARY = \'Route\''
    assert folded(binary('=', col('nom'), var('vide')), POSTGRESQL) == '"nom" = \'\''
    assert folded(binary('LIKE', col('nom'), var('motif')), SQLITE) == '"nom" GLOB \'Route*\''
    listed = Node('in', False, (col('nom'), var('nom_cible'), lit('x')), '"nom" IN (@nom_cible, \'x\')')
    assert folded(listed, POSTGRESQL) == '"nom" IN (\'Route\', \'x\')'
    # OGR SQL: a case-sensitive LIKE where the caller allows it, never =
    assert folded(binary('=', col('nom'), var('nom_cible')), OGR_SQL, case_sensitive_like=True) == \
        '"nom" LIKE \'Route\''
    assert 'without their case' in not_folded(binary('=', col('nom'), var('nom_cible')), OGR_SQL)
    assert 'backslash' in not_folded(binary('=', col('nom'), var('oblique')), POSTGRESQL)
    # a number held by a text, compared with a text: two texts
    assert folded(binary('=', col('code'), var('seuil')), POSTGRESQL) == '"code" = \'5\''


def test_a_boolean_or_null_variable_follows_the_rules_of_its_literal():
    assert folded(binary('=', col('actif'), var('vrai')), POSTGRESQL) == '"actif" = TRUE'
    assert 'boolean' in not_folded(binary('=', col('actif'), var('vrai')), SQLITE)
    assert 'IS NULL' in not_folded(binary('=', col('pop'), var('rien')), SQLITE)
    assert folded(binary('IS', col('pop'), var('rien')), SQLITE) == '"pop" IS NULL'


@pytest.mark.parametrize('name', ['row_number', 'geometry', 'feature', 'id', 'parent', 'element', 'value', 'layer',
                                  'layers', 'map_scale', 'canvas_cursor_point', 'atlas_featureid', 'layout_page',
                                  'symbol_color', 'geometry_part_num', 'now', 'today', '_fields_', 'cluster_size',
                                  'current_feature', 'frame_number', 'zoom_level'])
def test_a_variable_of_the_feature_map_layout_or_time_is_never_folded(name):
    # given as a constant by mistake: still refused
    variables = dict(VARIABLES, **{name: '5'})
    for dialect in (POSTGRESQL, SQLITE, OGR_SQL):
        assert 'not a constant' in not_folded(binary('>', col('pop'), var(name)), dialect, variables)


@pytest.mark.parametrize('name', ['inconnue', 'liste', 'dico', 'objet'])
def test_a_variable_unknown_or_of_another_type_is_not_folded(name):
    assert 'not a constant' in not_folded(binary('>', col('pop'), var(name)), SQLITE)


def test_a_variable_named_by_a_value_or_given_another_value_by_a_function_is_not_folded():
    named = Node('function', 'var', (col('nom'),), 'var("nom")')
    assert 'not a constant' in not_folded(binary('>', col('pop'), named), SQLITE)
    scoped = function('with_variable', lit('seuil'), lit(9), binary('>', col('pop'), var('seuil')))
    assert 'with_variable' in not_folded(scoped, SQLITE)
    # folded inside the functions the writer reads
    assert folded(binary('>', function('abs', binary('-', col('pop'), var('entier'))), lit(1)), SQLITE) == \
        '(abs(CAST(("pop" - 7) AS REAL)) > 1)'
    assert 'different types' in not_folded(binary('>', function('coalesce', col('pop'), var('seuil')), lit(1)),
                                           SQLITE)


def test_a_variable_with_spaces_is_left_to_qgis():
    # QGIS reads ' 5' as 5; only the plainest writing of a number is converted
    assert 'same type' in not_folded(binary('>', col('pop'), var('espace')), SQLITE)


def test_a_folded_operand_keeps_its_qgis_text_for_the_hybrid_evaluation():
    good = binary('>', col('pop'), var('seuil'))
    bad = binary('=', function('regexp_replace', col('nom'), lit('a'), lit('b')), lit('x'))
    result = translate_native(binary('AND', good, bad), SQLITE, TYPES, variables=VARIABLES)
    assert result.status == TranslationStatus.PARTIAL
    assert result.sql == '"pop" > 5'
    assert result.native_expression == '(' + good.text + ')'
    assert "var('seuil')" in result.native_expression
    assert result.native_columns == frozenset({'pop'})


def test_without_variables_nothing_is_folded():
    assert 'not a constant' in refused(binary('>', col('pop'), var('seuil')), SQLITE)


def test_referenced_variables():
    tree = binary('AND', binary('>', col('pop'), var('seuil')),
                  function('with_variable', lit('x'), lit(1), binary('=', var('x'), var('y'))))
    assert referenced_variables(tree) == frozenset({'seuil', 'x', 'y'})
    assert referenced_variables(binary('>', col('pop'), lit(1))) == frozenset()


# -- texts read as numbers ----------------------------------------------------------------------

@pytest.mark.parametrize('text, written', [('5', '5'), ('+5', '5'), ('007', '7'), ('-4', '-4'), ('2.5', '2.5'),
                                           ('1e3', '1000.0'), ('1E-2', '0.01')])
def test_a_text_constant_compared_with_a_number_is_compared_as_a_number(text, written):
    assert translated(binary('>', col('pop'), lit(text)), POSTGRESQL) == '"pop" > ' + written


@pytest.mark.parametrize('text', [' 5', '5 ', '5.', '.5', '1,5', 'inf', 'nan', '0x10', '٥', '1e999', '',
                                  'cinq', '1' * 20])
def test_other_texts_compared_with_a_number_are_not_written(text):
    assert refused(binary('>', col('pop'), lit(text)), POSTGRESQL)


def test_texts_read_as_numbers_give_the_answer_of_qgis_in_sqlite():
    connection = sqlite3.connect(':memory:')
    connection.execute('CREATE TABLE t (id INTEGER PRIMARY KEY, pop INTEGER, ratio REAL)')
    connection.executemany('INSERT INTO t VALUES (?, ?, ?)', [(1, 10, 0.5), (2, 6, 0.1 * 3), (3, None, 0.3),
                                                               (4, 7, None)])

    def ids(node):
        sql = translated(node, SQLITE)
        return [row[0] for row in connection.execute('SELECT id FROM t WHERE {} ORDER BY id'.format(sql))]  # nosec

    # QGIS compares 6 with 6.0 (not both texts), 0.30000000000000004 with 0.3 within its tolerance
    assert ids(binary('=', col('pop'), lit('6'))) == [2]
    assert ids(binary('>=', col('pop'), lit('6.0'))) == [1, 2, 4]
    assert ids(binary('=', col('ratio'), lit('0.3'))) == [2, 3]
    # IN and BETWEEN still refuse mixed types
    assert refused(Node('in', False, (col('pop'), lit('6')), '"pop" IN (\'6\')'), SQLITE)
    assert refused(between(col('pop'), lit('1'), lit(9)), SQLITE)


# -- geometric functions --------------------------------------------------------------------------

GEOMETRY = Node('function', '$geometry', (), '$geometry')
PG_POINTS = NativeGeometry('geom', 'point', POSTGIS)
PG_LINES = NativeGeometry('geom', 'line', POSTGIS)
PG_CURVES = NativeGeometry('geom', 'polygon', POSTGIS, curved=True)
GPKG_POINTS = NativeGeometry('geom', 'point', GEOPACKAGE)
GPKG_LINES = NativeGeometry('the_geom', 'line', GEOPACKAGE)
GPKG_POLYGONS = NativeGeometry('geom', 'polygon', GEOPACKAGE)
GPKG_CURVES = NativeGeometry('geom', 'line', GEOPACKAGE, curved=True)


def geo(name, *arguments):
    if name.startswith('$'):
        return Node('function', name, (), name)
    return function(name, *(arguments or (GEOMETRY,)))


def test_bounds_are_written_for_postgis_points_and_lines_arcs_included():
    for geometry in (PG_POINTS, PG_LINES, NativeGeometry('geom', 'line', POSTGIS, curved=True)):
        assert translated(binary('>', geo('x_min'), lit(700000)), POSTGRESQL, geometry=geometry) == \
            '(ST_XMin(CAST("geom" AS geometry)) > 700000)'
    assert translated(binary('<=', geo('y_max'), lit(5.5)), POSTGRESQL, geometry=PG_LINES) == \
        '(ST_YMax(CAST("geom" AS geometry)) <= 5.5)'


def test_bounds_are_written_for_geopackage_points():
    points = NativeGeometry('the_geom', 'point', GEOPACKAGE)
    assert translated(binary('<', geo('y_max'), lit(1)), SQLITE, geometry=points) == '(ST_MaxY("the_geom") < 1)'
    assert translated(binary('<', geo('x_max'), lit(1)), SQLITE, geometry=points) == '(ST_MaxX("the_geom") < 1)'
    assert translated(binary('<', geo('y_min'), lit(1)), SQLITE, geometry=points) == '(ST_MinY("the_geom") < 1)'


def test_coordinates_of_points_are_written_for_postgis_only():
    shape = 'CAST("geom" AS geometry)'
    assert translated(binary('>', geo('x'), lit(1)), POSTGRESQL, geometry=PG_POINTS) == (
        "(CASE WHEN ST_IsEmpty({0}) AND ST_GeometryType({0}) <> 'ST_Point' THEN CAST(0 AS double precision) "
        "WHEN ST_NumGeometries({0}) = ST_NPoints({0}) THEN ST_X(ST_Centroid({0})) END) > 1").format(shape)
    assert 'ST_Y(ST_Centroid(' in translated(binary('>', geo('y'), lit(1)), POSTGRESQL, geometry=PG_POINTS)
    assert translated(binary('>', geo('$x'), lit(1)), POSTGRESQL, geometry=PG_POINTS) == (
        "(CASE WHEN ST_IsEmpty({0}) AND ST_GeometryType({0}) <> 'ST_Point' THEN CAST(0 AS double precision) "
        "ELSE ST_X(ST_GeometryN({0}, 1)) END) > 1").format(shape)
    assert 'ELSE ST_Y(ST_GeometryN(' in translated(binary('>', geo('$y'), lit(1)), POSTGRESQL, geometry=PG_POINTS)
    assert 'points only' in refused(binary('>', geo('x'), lit(1)), POSTGRESQL, geometry=PG_LINES)
    assert 'points only' in refused(binary('>', geo('x'), lit(1)), SQLITE, geometry=GPKG_POINTS)
    assert 'points only' in refused(binary('>', geo('$y'), lit(1)), SQLITE, geometry=GPKG_POINTS)


def test_geometric_functions_need_the_geometry_of_the_feature_and_a_column():
    assert 'No geometry column' in refused(binary('>', geo('x_min'), lit(1)), SQLITE)
    assert 'OGR SQL' in refused(binary('>', geo('x_min'), lit(1)), OGR_SQL, geometry=GPKG_POINTS)
    other = function('geom_from_wkt', lit('POINT(1 2)'))
    assert '$geometry only' in refused(binary('>', geo('x_min', other), lit(1)), POSTGRESQL, geometry=PG_POINTS)
    assert '$geometry only' in refused(binary('>', function('x_min', col('pop')), lit(1)), POSTGRESQL,
                                       geometry=PG_POINTS)
    assert '$geometry only' in refused(binary('>', function('x', GEOMETRY, lit(1)), lit(1)), POSTGRESQL,
                                       geometry=PG_POINTS)
    dollar = Node('function', '$x', (lit(1),), '$x(1)')
    assert 'Not a geometric function' in refused(binary('>', dollar, lit(1)), POSTGRESQL, geometry=PG_POINTS)
    for name in ('a"b', "l'geom", 'geom--x', ''):
        assert 'safely' in refused(binary('>', geo('x_min'), lit(1)), POSTGRESQL,
                                   geometry=NativeGeometry(name, 'point', POSTGIS))
    assert 'not written for this source' in refused(binary('>', geo('x_min'), lit(1)), SQLITE,
                                                    geometry=NativeGeometry('geom', 'point', 'spatialite'))
    assert refused(binary('=', GEOMETRY, lit(1)), POSTGRESQL, geometry=PG_POINTS)


@pytest.mark.parametrize('name, reason', [('area', 'another order'), ('length', 'arc'), ('perimeter', 'arc'),
                                          ('num_points', 'counted'), ('$area', 'ellipsoidal'),
                                          ('$length', 'ellipsoidal'), ('$perimeter', 'ellipsoidal')])
def test_measures_are_left_to_qgis(name, reason):
    for dialect, geometry in ((POSTGRESQL, PG_LINES), (SQLITE, GPKG_POINTS)):
        assert reason in refused(binary('>', geo(name), lit(1)), dialect, geometry=geometry)


def test_a_geometric_value_is_never_rescued_by_an_or_a_case_or_a_negated_and():
    # an empty geometry: QGIS stops on an evaluation error (not kept), SQL goes on with NULL
    above = binary('>', geo('x_min'), lit(1))
    other = binary('>', col('pop'), lit(6))
    for node in (binary('OR', above, other), binary('OR', other, above),
                 binary('=', function('if', above, lit(1), lit(2)), lit(2)),
                 binary('=', Node('condition', True, (above, lit(1), lit(2)), 'CASE'), lit(2)),
                 binary('>', Node('condition', True, (other, geo('x_min'), lit(0)), 'CASE'), lit(5)),
                 negation(binary('AND', above, other)), negation(binary('AND', other, above))):
        assert 'under OR, CASE' in refused(node, POSTGRESQL, geometry=PG_POINTS)
    # a top-level AND is split, an AND not under NOT is the same NULL
    assert translated(binary('AND', above, other), POSTGRESQL, geometry=PG_POINTS) == \
        '(ST_XMin(CAST("geom" AS geometry)) > 1) AND ("pop" > 6)'
    assert translated(negation(negation(above)), SQLITE, geometry=GPKG_POINTS) == '(NOT (NOT (ST_MinX("geom") > 1)))'
    # OR without a geometric value is still written
    assert translated(binary('OR', other, binary('<', col('pop'), lit(2))), POSTGRESQL, geometry=PG_POINTS)


def test_a_geometric_value_is_nan_in_qgis_and_null_in_the_source():
    # not kept on both sides: comparisons, NOT, BETWEEN, arithmetic and abs are written
    assert translated(negation(binary('>', geo('x_min'), lit(1))), POSTGRESQL, geometry=PG_POINTS) == \
        '(NOT (ST_XMin(CAST("geom" AS geometry)) > 1))'
    assert translated(between(geo('x_min'), lit(1), lit(2), negated=True), POSTGRESQL, geometry=PG_POINTS)
    assert translated(binary('>', binary('/', geo('x_min'), lit(1000)), lit(700)), SQLITE, geometry=GPKG_POINTS)
    assert translated(binary('<>', geo('x_min'), lit(0.5)), POSTGRESQL, geometry=PG_POINTS)
    assert translated(binary('>', function('abs', geo('y_max')), lit(1)), POSTGRESQL, geometry=PG_POINTS)
    # not under IS NULL nor coalesce: NaN is not NULL in QGIS
    assert 'IS NULL' in refused(binary('IS', geo('x_min'), lit(None)), POSTGRESQL, geometry=PG_POINTS)
    assert 'IS NULL' in refused(binary('IS NOT', binary('*', geo('x'), lit(2)), lit(None)), POSTGRESQL,
                                geometry=PG_POINTS)
    assert 'coalesce' in refused(binary('<', function('coalesce', geo('x_min'), lit(0)), lit(5)), POSTGRESQL,
                                 geometry=PG_POINTS)


def test_a_translation_says_whether_it_holds_a_coordinate_of_the_geometry():
    # the caller must not negate a geometric translation with AND / OR / NOT (AND NOT)
    above = binary('>', geo('x_min'), lit(1))
    alone = translate_native(above, POSTGRESQL, TYPES, geometry=PG_POINTS)
    assert alone.geometric and not alone.composite
    both = translate_native(binary('AND', above, binary('>', col('pop'), lit(3))), POSTGRESQL, TYPES,
                            geometry=PG_POINTS)
    assert both.geometric and both.composite
    assert not translate_native(binary('>', col('pop'), lit(3)), POSTGRESQL, TYPES, geometry=PG_POINTS).geometric
    refusal = translate_native(binary('AND', binary('>', geo('area'), lit(1)), binary('>', col('pop'), lit(3))),
                               POSTGRESQL, TYPES, geometry=PG_POINTS)
    assert refusal.status == TranslationStatus.PARTIAL and not refusal.geometric


def test_a_geometric_operand_does_not_read_a_field():
    result = translate_native(binary('AND', binary('>', geo('x_min'), lit(1)), binary('>', col('pop'), lit(2))),
                              POSTGRESQL, TYPES, geometry=PG_POINTS)
    assert result.native_columns == frozenset({'pop'})  # as QGIS's referencedColumns()


def test_uses_geometry():
    assert uses_geometry(binary('>', geo('x_min'), lit(1)))
    assert uses_geometry(negation(binary('>', geo('$x'), lit(1))))
    assert not uses_geometry(binary('>', geo('area'), lit(1)))
    assert not uses_geometry(binary('>', col('pop'), lit(1)))


def _geometric_written():
    nodes = [(binary('>', geo('x_min'), lit(700000.5)), POSTGRESQL, PG_POINTS),
             (binary('=', geo('y_max'), lit(6600000)), POSTGRESQL, PG_LINES),
             (negation(binary('>', geo('x'), lit(1))), POSTGRESQL, PG_POINTS),
             (binary('<', geo('$y'), lit(1)), POSTGRESQL, PG_POINTS),
             (binary('>', geo('x_min'), lit(700000.5)), SQLITE, GPKG_POINTS),
             (between(geo('y_min'), lit(1), lit(2)), SQLITE, GPKG_POINTS),
             (binary('=', geo('x_max'), lit(0.3)), SQLITE, GPKG_POINTS)]
    return [translated(node, dialect, geometry=geometry) for node, dialect, geometry in nodes]


@pytest.mark.parametrize('sql', _geometric_written())
def test_the_subset_sanitizer_leaves_a_geometric_translation_unchanged(sql):
    assert sanitize_subset_string(sql, text_fields={'nom', 'code'}) == sql


def test_a_geometric_value_is_never_a_between_bound():
    # BETWEEN is a hidden AND: "pop" NOT BETWEEN NULL AND 10 is TRUE for pop = 20 (20 > 10), QGIS stops on
    # the NaN of an empty geometry and keeps nothing; AND NOT negates a plain BETWEEN the same way
    for negated in (False, True):
        node = between(col('pop'), geo('x_min'), lit(10), negated=negated)
        assert 'BETWEEN bound' in refused(node, POSTGRESQL, geometry=PG_POINTS)
        node = between(col('pop'), lit(1), binary('+', geo('y_max'), lit(1)), negated=negated)
        assert 'BETWEEN bound' in refused(node, SQLITE, geometry=GPKG_POINTS)
    # the geometric value BETWEEN two bounds: NULL on both sides, written
    assert translated(between(geo('x_min'), lit(1), lit(2), negated=True), POSTGRESQL, geometry=PG_POINTS)


@pytest.mark.parametrize('text', ['1e-400', '2.4e-324', '-5e-330', '0.1e-323'])
def test_a_text_that_underflows_is_compared_as_a_text_by_qgis(text):
    # QString::toDouble fails on an underflow: QGIS compares the texts ('1' > '1e-400' is FALSE), Python reads 0.0
    assert 'same type' in refused(binary('>', col('pop'), lit(text)), POSTGRESQL)


@pytest.mark.parametrize('text, written', [('3e-324', '5e-324'), ('1e-310', '1e-310'), ('0e5', '0.0'),
                                           ('0.000', '0.0')])
def test_a_subnormal_or_a_zero_text_is_a_number_for_qgis(text, written):
    # measured: 1 > '3e-324' and 1 > '1e-310' are TRUE in QGIS (numbers), 1 > '0e5' too
    assert translated(binary('>', col('pop'), lit(text)), POSTGRESQL) == '"pop" > ' + written


def test_postgis_bounds_are_not_written_for_polygons():
    # PostGIS builds the box of a CURVEPOLYGON / MULTISURFACE from every ring, QGIS from the shell (x_max 10
    # against 30 with a hole outside); a generic column read as polygons holds them, whatever the layer type
    for geometry in (NativeGeometry('geom', 'polygon', POSTGIS), PG_CURVES):
        assert 'polygon' in refused(binary('>', geo('x_min'), lit(1)), POSTGRESQL, geometry=geometry)
    assert translated(binary('>', geo('x_min'), lit(1)), POSTGRESQL, geometry=NativeGeometry(
        'geom', 'line', POSTGIS, curved=True))


def test_geopackage_bounds_are_written_for_points_only():
    # GDAL's envelope of an arc differs in the last bits, and a layer of lines may store a polygon whose hole
    # lies outside its shell: only the envelope of points is exact (a header written by another tool is not
    # checked)
    assert translated(binary('>', geo('x_min'), lit(1)), SQLITE, geometry=GPKG_POINTS) == '(ST_MinX("geom") > 1)'
    for geometry in (GPKG_LINES, GPKG_POLYGONS, GPKG_CURVES):
        assert 'points only' in refused(binary('>', geo('x_min'), lit(1)), SQLITE, geometry=geometry)


def test_the_qgis_text_of_a_native_part_must_give_back_its_numbers():
    # node.dump() writes 1e-30 as '0' and -1e-30 as '- 0' (measured): a hybrid subset evaluating that text
    # in QGIS would not evaluate what the SQL holds
    tiny = Node('literal', 1e-30, (), '0')
    other = binary('=', function('regexp_replace', col('nom'), lit('a'), lit('b')), lit('x'))
    result = translate_native(binary('AND', binary('>', col('ratio'), tiny), other), POSTGRESQL, TYPES)
    assert result.status == TranslationStatus.PARTIAL and not result.native_exact
    negative = Node('literal', -1e-30, (), '- 0')
    assert not translate_native(binary('>', col('ratio'), negative), POSTGRESQL, TYPES).native_exact
    for value, text in ((0.3, '0.29999999999999999'), (-1.5, '- 1.5'), (2.5e-10, '0.00000000025'), (-4, '- 4'),
                        (123456789012, '123456789012'), (6656395.210250434, '6656395.21025043353438377')):
        result = translate_native(binary('>', col('ratio'), Node('literal', value, (), text)), POSTGRESQL, TYPES)
        assert result.native_exact, (value, text)
    # an operand left to QGIS does not count; a folded variable keeps its QGIS text (same context)
    assert translate_native(binary('AND', binary('>', col('pop'), lit(1)), binary('>', function('round', col('ratio')),
                                                                                   tiny)), SQLITE, TYPES).native_exact
    assert translate_native(binary('>', col('pop'), var('seuil')), SQLITE, TYPES,
                            variables={'seuil': '5'}).native_exact
