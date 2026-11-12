"""QGIS predicate -> native SQL: written from a tree, no QGIS imports.

The SQLite cases are run in ``sqlite3`` against rows whose expected answer is
the one QGIS gives (case-sensitive LIKE and =, float division, NULL logic,
equality of reals within 4 DBL_EPSILON).
"""
import sqlite3

import pytest

from filtermate_core.filter.expression_combiner import combine_with_old_subset
from filtermate_core.filter.expression_sanitizer import sanitize_subset_string
from filtermate_core.filter.native_dialect import (
    HYBRID_MAX_KEYS, OGR_SQL, POSTGRESQL, SQLITE, hybrid_sql, key_reference, translate_native,
)
from filtermate_core.filter.server_dialect import Node, TranslationStatus, Unsupported

TYPES = {'id': 'int', 'pop': 'int', 'ratio': 'real', 'nom': 'text', 'code': 'text', 'actif': 'bool',
         'jour': 'other'}
EPS = '8.881784197001252e-16'
SQLITE_EPS = '(CAST(1 AS REAL) / 1125899906842624)'  # 2^-50, read exactly by SQLite


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


def in_list(left, values, negated=False):
    return Node('in', negated, (left,) + tuple(lit(v) for v in values), left.text + ' IN (...)')


def between(value, low, high, negated=False):
    return Node('between', negated, (value, low, high), '{} BETWEEN {} AND {}'.format(value.text, low.text, high.text))


def function(name, *arguments):
    return Node('function', name, tuple(arguments), '{}({})'.format(name, ', '.join(a.text for a in arguments)))


def case(*parts, otherwise=None):
    children = tuple(parts) + ((otherwise,) if otherwise is not None else ())
    return Node('condition', otherwise is not None, children, 'CASE ... END')


def full(node, dialect, types=TYPES):
    result = translate_native(node, dialect, types)
    assert result.status == TranslationStatus.FULL, result.reason
    assert not result.local_expression
    return result.sql


def refused(node, dialect, types=TYPES):
    result = translate_native(node, dialect, types)
    assert result.status == TranslationStatus.NONE
    assert not result.sql
    assert result.local_expression == '(' + node.text + ')'
    return result.reason


# -- writing ----------------------------------------------------------------------

@pytest.mark.parametrize('dialect', [POSTGRESQL, SQLITE, OGR_SQL])
def test_number_comparison_is_written_as_is(dialect):
    assert full(binary('>', col('pop'), lit(1000)), dialect) == '"pop" > 1000'


def test_text_equality_quotes_the_value_and_sqlite_ignores_the_column_collation():
    node = binary('=', col('nom'), lit("L'Isle"))
    assert full(node, POSTGRESQL) == '"nom" = \'L\'\'Isle\''
    assert full(node, SQLITE) == '"nom" COLLATE BINARY = \'L\'\'Isle\''


def test_and_is_split_and_the_untranslated_operand_is_kept():
    good = binary('=', col('id'), lit(1))
    bad = binary('=', function('regexp_replace', col('nom'), lit('a'), lit('b')), lit('x'))
    result = translate_native(binary('AND', good, bad), POSTGRESQL, TYPES)
    assert result.status == TranslationStatus.PARTIAL
    assert result.sql == '"id" = 1'
    assert result.local_expression == '(' + bad.text + ')'
    assert 'regexp_replace' in result.reason
    assert result.native_expression == '(' + good.text + ')'
    assert translate_native(good, POSTGRESQL, TYPES).native_expression == '(' + good.text + ')'


def test_or_and_not_are_never_split():
    good = binary('=', col('id'), lit(1))
    bad = binary('=', col('inconnu'), lit(1))
    assert translate_native(binary('OR', good, bad), SQLITE, TYPES).status == TranslationStatus.NONE
    assert translate_native(negation(binary('AND', good, bad)), SQLITE, TYPES).status == TranslationStatus.NONE


def test_several_operands_keep_their_parentheses():
    node = binary('AND', binary('OR', binary('=', col('id'), lit(1)), binary('=', col('id'), lit(2))),
                  binary('>', col('pop'), lit(5)))
    assert full(node, POSTGRESQL) == '(("id" = 1) OR ("id" = 2)) AND ("pop" > 5)'


# -- what is refused ---------------------------------------------------------------

@pytest.mark.parametrize('dialect', [POSTGRESQL, SQLITE, OGR_SQL])
def test_mixed_types_are_left_to_qgis(dialect):
    assert 'same type' in refused(binary('>', col('code'), lit(10)), dialect)
    assert 'same type' in refused(binary('=', col('pop'), lit('10')), dialect)


@pytest.mark.parametrize('dialect', [POSTGRESQL, SQLITE])
def test_text_ordering_is_left_to_qgis(dialect):
    assert 'collation' in refused(binary('<', col('nom'), lit('m')), dialect)


def test_ogr_sql_never_compares_texts():
    assert 'case' in refused(binary('=', col('nom'), lit('Route')), OGR_SQL)
    assert 'case' in refused(in_list(col('nom'), ['a', 'b']), OGR_SQL)
    assert refused(binary('LIKE', col('nom'), lit('R%')), OGR_SQL)
    assert refused(binary('=', function('abs', col('pop')), lit(1)), OGR_SQL)


@pytest.mark.parametrize('dialect', [POSTGRESQL, SQLITE, OGR_SQL])
def test_unknown_field_other_type_null_comparison_and_bare_value(dialect):
    assert 'Not a field' in refused(binary('=', col('joined_x'), lit(1)), dialect)
    assert refused(binary('=', col('jour'), lit('2026-01-01')), dialect)
    assert 'IS NULL' in refused(binary('=', col('pop'), lit(None)), dialect)
    assert refused(col('actif'), dialect)
    assert refused(Node('unsupported', '$area > 3', text='$area > 3'), dialect)


@pytest.mark.parametrize('dialect', [POSTGRESQL, SQLITE, OGR_SQL])
@pytest.mark.parametrize('name', ['a"b', 'x\\', 'x--y', 'a/*b', 'a*/b', 'a\nb'])
def test_field_names_that_cannot_be_written_safely(dialect, name):
    # OGR SQL reads neither "" nor \ in a name; the subset sanitizer reads -- and /* as comments
    assert 'safely' in refused(binary('=', col(name), lit(1)), dialect, {name: 'int'})


@pytest.mark.parametrize('dialect', [POSTGRESQL, SQLITE, OGR_SQL])
def test_backslash_in_a_text_is_refused(dialect):
    # the sanitizer reads \' as an escaped quote and would shift the literals after it
    assert 'backslash' in refused(binary('=', col('nom'), lit('C:\\data\\')), dialect)


@pytest.mark.parametrize('dialect', [POSTGRESQL, SQLITE, OGR_SQL])
def test_integers_beyond_two_to_the_53_are_refused(dialect):
    assert '2^53' in refused(binary('=', col('pop'), lit(2 ** 53 + 1)), dialect)
    assert full(binary('=', col('pop'), lit(2 ** 53)), dialect) == '"pop" = 9007199254740992'


def test_boolean_literal_only_in_postgresql():
    node = binary('=', col('actif'), lit(True))
    assert full(node, POSTGRESQL) == '"actif" = TRUE'
    assert refused(node, SQLITE)


def test_length_and_single_argument_coalesce_are_refused():
    # QGIS counts UTF-16 code units ('😀' is 2), the sources count characters
    assert refused(binary('=', function('length', col('nom')), lit(2)), SQLITE)
    assert refused(binary('=', function('length', col('nom')), lit(2)), POSTGRESQL)
    # SQLite: "wrong number of arguments to function COALESCE()"
    assert refused(binary('=', function('coalesce', col('pop')), lit(5)), SQLITE)


def test_unknown_dialect_is_none():
    assert translate_native(binary('=', col('id'), lit(1)), 'oracle', TYPES).status == TranslationStatus.NONE


# -- equality of reals: qgsDoubleNear ----------------------------------------------------

def test_equality_of_a_real_is_written_with_the_qgis_tolerance():
    node = binary('=', col('ratio'), lit(0.5))
    half = '(CAST(1 AS REAL) / 2)'
    assert full(node, SQLITE) == '("ratio" - {1}) > -{0} AND ("ratio" - {1}) <= {0}'.format(SQLITE_EPS, half)
    assert full(binary('<>', col('ratio'), lit(0.5)), SQLITE) == (
        '("ratio" - {1}) <= -{0} OR ("ratio" - {1}) > {0}'.format(SQLITE_EPS, half))
    assert full(node, POSTGRESQL) == (
        '(CAST("ratio" AS double precision) - 0.5) > -{0} AND (CAST("ratio" AS double precision) - 0.5) <= {0}'
        .format(EPS))


def test_ogr_sql_writes_reals_without_an_exponent():
    assert full(binary('<', col('ratio'), lit(1e-05)), OGR_SQL) == '"ratio" < 0.00001'
    assert full(binary('<', col('ratio'), lit(1e22)), OGR_SQL) == '"ratio" < 10000000000000000000000.0'
    assert full(binary('<', col('ratio'), lit(1e-05)), SQLITE) == (
        '"ratio" < (CAST(5902958103587057 AS REAL) / 4611686018427387904 / 128)')
    assert '0.0000000000000008881784197001252' in full(binary('=', col('ratio'), lit(0.5)), OGR_SQL)


def test_in_on_reals_is_refused():
    assert 'tolerance' in refused(in_list(col('ratio'), [0.5, 1]), SQLITE)
    assert 'tolerance' in refused(in_list(col('pop'), [1, 2.5]), SQLITE)


# -- OGR SQL -------------------------------------------------------------------------

def test_ogr_sql_division_only_by_a_literal_that_is_not_zero():
    assert full(binary('>', binary('/', col('pop'), lit(2)), lit(3)), OGR_SQL) == '("pop" / 2.0) > 3'
    assert full(binary('<', binary('/', col('pop'), lit(-2.5)), lit(-1)), OGR_SQL) == '("pop" / -2.5) < -1'
    assert 'may be 0' in refused(binary('=', binary('/', col('pop'), col('id')), lit(1)), OGR_SQL)
    assert 'may be 0' in refused(binary('=', binary('/', col('pop'), lit(0)), lit(1)), OGR_SQL)


def test_ogr_sql_never_writes_a_not_over_an_and():
    # OGR SQL: TRUE AND NULL is FALSE, NOT makes it TRUE where QGIS keeps NULL
    both = binary('AND', binary('>', col('pop'), lit(5)), binary('<', col('ratio'), lit(2)))
    assert 'NOT over an AND' in refused(negation(both), OGR_SQL)
    assert 'NOT over an AND' in refused(negation(binary('OR', both, binary('=', col('id'), lit(1)))), OGR_SQL)
    # the AND of a real's tolerance too
    assert 'NOT over an AND' in refused(negation(binary('=', col('ratio'), lit(0.5))), OGR_SQL)
    assert full(negation(both), SQLITE) == '(NOT (("pop" > 5) AND ("ratio" < 2)))'
    either = binary('OR', binary('>', col('pop'), lit(5)), binary('<', col('ratio'), lit(2)))
    assert full(negation(either), OGR_SQL) == '(NOT (("pop" > 5) OR ("ratio" < 2)))'
    assert full(binary('<>', col('ratio'), lit(0.5)), OGR_SQL)  # an OR, no NOT


def test_ogr_sql_between_takes_literal_bounds_of_the_value_type():
    assert full(between(col('pop'), lit(3), lit(9)), OGR_SQL) == '"pop" BETWEEN 3 AND 9'
    assert full(between(col('ratio'), lit(1), lit(2)), OGR_SQL) == '"ratio" BETWEEN 1.0 AND 2.0'
    assert refused(between(col('pop'), col('id'), lit(9.5)), OGR_SQL)
    assert refused(between(col('pop'), lit(3), lit(9.5)), OGR_SQL)
    assert refused(between(lit(2), col('pop'), lit(1), negated=True), OGR_SQL)
    assert full(between(col('pop'), col('id'), lit(9.5)), SQLITE) == '"pop" BETWEEN "id" AND (CAST(19 AS REAL) / 2)'


# -- PostgreSQL ---------------------------------------------------------------------

def test_postgresql_division_is_float_and_null_on_zero():
    node = binary('>', binary('/', col('pop'), col('id')), lit(2))
    assert full(node, POSTGRESQL) == '(CAST("pop" AS double precision) / NULLIF("id", 0)) > 2'


def test_postgresql_real_arithmetic_runs_in_double_precision():
    assert full(binary('>', binary('*', col('ratio'), lit(3)), lit(1)), POSTGRESQL) == (
        '(CAST("ratio" AS double precision) * 3) > 1')
    assert full(binary('>', binary('*', col('pop'), lit(3)), lit(1)), POSTGRESQL) == '("pop" * 3) > 1'


def test_postgresql_like_functions_and_case():
    assert full(binary('NOT ILIKE', col('nom'), lit('r%')), POSTGRESQL) == '"nom" NOT ILIKE \'r%\''
    # parentheses kept before a function: the sanitizer reads "COALESCE(...) GLOB" as a display expression
    assert full(binary('=', function('upper', col('nom')), lit('ROUTE')), POSTGRESQL) == '(upper("nom") = \'ROUTE\')'
    node = binary('=', function('if', binary('>', col('pop'), lit(5)), lit('a'), col('nom')), lit('a'))
    assert full(node, POSTGRESQL) == '(CASE WHEN ("pop" > 5) THEN \'a\' ELSE "nom" END) = \'a\''
    assert refused(binary('=', function('upper', col('nom')), lit('X')), SQLITE)


def test_case_branches_must_share_a_type():
    node = binary('=', case(binary('>', col('pop'), lit(5)), lit('a'), otherwise=lit(1)), lit('a'))
    assert 'different types' in refused(node, POSTGRESQL)


# -- SQLite, run for real ---------------------------------------------------------------

ROWS = [
    # id, pop, ratio, nom
    (1, 10, 0.5, 'Route'),
    (2, 0, 1.5, 'route'),
    (3, 7, None, 'ROUTE du Sud'),
    (4, None, 2.0, None),
    (5, 3, 3.0, "l'Ariège"),
    (6, 9, 4.5, 'r*ute'),
    (7, 2, 0.1, 'Éte'),
    (8, 1, 0.2, 'ſaint'),          # long s
    (9, 4, 0.7, 'Kelvin \u212a'),   # Kelvin sign
    (10, 6, 0.3, 'Route\nNord'),
]


@pytest.fixture(scope='module')
def table():
    connection = sqlite3.connect(':memory:')
    connection.execute('CREATE TABLE t (id INTEGER PRIMARY KEY, pop INTEGER, ratio REAL, nom TEXT COLLATE NOCASE)')
    connection.executemany('INSERT INTO t VALUES (?, ?, ?, ?)', ROWS)
    yield connection
    connection.close()


def ids(table, node):
    sql = full(node, SQLITE)
    return [row[0] for row in table.execute('SELECT id FROM t WHERE {} ORDER BY id'.format(sql))]  # nosec B608


def test_sqlite_like_is_case_sensitive_as_in_qgis(table):
    # SQLite's own LIKE would return 1, 2, 3 and 10
    assert ids(table, binary('LIKE', col('nom'), lit('Route%'))) == [1, 10]  # % spans a newline
    assert ids(table, binary('LIKE', col('nom'), lit('_oute'))) == [1, 2]
    assert ids(table, binary('NOT LIKE', col('nom'), lit('Route%'))) == [2, 3, 5, 6, 7, 8, 9]  # NULL stays out


def test_sqlite_ilike_ignores_case_with_the_other_cases_of_k_and_s(table):
    assert ids(table, binary('ILIKE', col('nom'), lit('route%'))) == [1, 2, 3, 10]
    assert ids(table, binary('NOT ILIKE', col('nom'), lit('route%'))) == [5, 6, 7, 8, 9]
    assert ids(table, binary('ILIKE', col('nom'), lit('saint'))) == [8]
    assert ids(table, binary('ILIKE', col('nom'), lit('% k'))) == [9]
    assert full(binary('ILIKE', col('nom'), lit('Ks_1%')), SQLITE) == (
        '"nom" GLOB \'[kK\u212a][sS\u017f]?1*\'')


def test_sqlite_like_patterns_that_are_refused():
    assert refused(binary('LIKE', col('nom'), lit('r*%')), SQLITE)        # GLOB wildcard
    assert refused(binary('ILIKE', col('nom'), lit('a[b%')), SQLITE)      # GLOB class
    assert refused(binary('ILIKE', col('nom'), lit('ét%')), SQLITE)       # not ASCII
    assert refused(binary('LIKE', col('nom'), lit('50\\%')), SQLITE)      # escape
    assert refused(binary('LIKE', col('pop'), lit('1%')), SQLITE)         # not a text


def test_sqlite_text_equality_ignores_a_nocase_column(table):
    # the column is COLLATE NOCASE: a bare = would also return 2 (and IN 1)
    assert ids(table, binary('=', col('nom'), lit('Route'))) == [1]
    assert ids(table, binary('<>', col('nom'), lit('Route'))) == [2, 3, 5, 6, 7, 8, 9, 10]
    assert ids(table, binary('=', lit('Route'), col('nom'))) == [1]
    assert ids(table, in_list(col('nom'), ['route', "l'Ariège"])) == [2, 5]
    assert ids(table, in_list(col('id'), [1, 4], negated=True)) == [2, 3, 5, 6, 7, 8, 9, 10]


def test_sqlite_equality_of_reals_has_the_qgis_tolerance(table):
    # 0.1 * 3 is 0.30000000000000004: equal for QGIS (qgsDoubleNear), not for SQL's =
    times_three = binary('*', col('ratio'), lit(3))
    assert ids(table, binary('=', times_three, lit(0.3))) == [7]
    assert 7 not in ids(table, binary('<>', times_three, lit(0.3)))
    assert ids(table, binary('=', col('ratio'), lit(0.5))) == [1]
    assert ids(table, binary('<>', col('ratio'), lit(0.5))) == [2, 4, 5, 6, 7, 8, 9, 10]  # 3 (NULL) stays out


def test_sqlite_division_is_float_and_null_on_zero(table):
    # 7 / 2 is 3.5 in QGIS (3 in SQLite's integer division); x / 0 is NULL
    assert ids(table, binary('>', binary('/', col('pop'), lit(2)), lit(3))) == [1, 3, 6]
    assert ids(table, binary('=', binary('/', col('pop'), lit(2)), lit(3.5))) == [3]
    assert ids(table, binary('>', binary('/', col('id'), col('pop')), lit(0))) == [1, 3, 5, 6, 7, 8, 9, 10]


def test_sqlite_null_logic_between_case_and_functions(table):
    assert ids(table, binary('IS', col('pop'), lit(None))) == [4]
    assert ids(table, binary('IS NOT', col('nom'), lit(None))) == [1, 2, 3, 5, 6, 7, 8, 9, 10]
    assert ids(table, negation(binary('>', col('pop'), lit(5)))) == [2, 5, 7, 8, 9]  # NULL stays out
    assert ids(table, negation(binary('AND', binary('>', col('pop'), lit(5)), binary('<', col('ratio'), lit(2))))) == [
        2, 4, 5, 6, 7, 8, 9]  # 3: pop 7, ratio NULL -> NULL, out
    assert ids(table, between(col('pop'), lit(3), lit(9))) == [3, 5, 6, 9, 10]
    assert ids(table, between(col('pop'), lit(3), lit(9), negated=True)) == [1, 2, 7, 8]
    assert ids(table, binary('>', function('coalesce', col('pop'), lit(100)), lit(50))) == [4]
    assert ids(table, binary('=', function('abs', binary('-', col('pop'), lit(10))), lit(1))) == [6]
    node = binary('=', case(binary('>', col('pop'), lit(5)), lit('grand'), otherwise=lit('petit')), lit('petit'))
    assert ids(table, node) == [2, 4, 5, 7, 8, 9]  # a NULL condition takes ELSE, as in QGIS
    assert ids(table, binary('=', binary('||', col('nom'), lit('!')), lit('Route!'))) == [1]
    # QGIS: -NULL of an integer field is 0, the sources give NULL: only the sign of a literal is written
    assert 'may be NULL' in refused(binary('<', Node('unary', '-', (col('pop'),), '-"pop"'), lit(-8)), SQLITE)
    assert ids(table, binary('<', Node('unary', '-', (lit(-4),), '--4'), col('pop'))) == [1, 3, 6, 10]


def test_abs_of_the_smallest_integer_does_not_overflow():
    connection = sqlite3.connect(':memory:')
    connection.execute('CREATE TABLE t (id INTEGER, pop INTEGER)')
    connection.execute('INSERT INTO t VALUES (1, -9223372036854775808)')
    sql = full(binary('>', function('abs', col('pop')), lit(0)), SQLITE)
    assert [row[0] for row in connection.execute('SELECT id FROM t WHERE ' + sql)] == [1]  # nosec B608


# -- what happens downstream --------------------------------------------------------------

def _all_written():
    nodes = [
        binary('LIKE', col('nom'), lit('Route%')),
        binary('NOT ILIKE', col('nom'), lit('saint%')),
        binary('=', col('nom'), lit('Route')),
        in_list(col('nom'), ['a', "l'b"]),
        binary('=', binary('*', col('ratio'), lit(3)), lit(0.3)),
        binary('<>', col('ratio'), lit(0.5)),
        binary('>', function('coalesce', col('pop'), lit(100)), lit(50)),
        binary('=', case(binary('>', col('pop'), lit(5)), lit('grand'), otherwise=lit('petit')), lit('petit')),
        binary('=', function('if', binary('>', col('pop'), lit(5)), lit(1), lit(2)), lit(2)),
        binary('=', function('abs', binary('-', col('pop'), lit(10))), lit(1)),
        binary('<', Node('unary', '-', (lit(-4),), '--4'), col('pop')),
        negation(binary('AND', binary('>', col('pop'), lit(5)), binary('<', col('ratio'), lit(2)))),
        between(col('pop'), lit(3), lit(9), negated=True),
        binary('>', binary('/', col('pop'), lit(2)), lit(3)),
    ]
    written = []
    for node in nodes:
        for dialect in (SQLITE, OGR_SQL):
            result = translate_native(node, dialect, TYPES)
            if result.status == TranslationStatus.FULL:
                written.append(result.sql)
    return written


@pytest.mark.parametrize('sql', _all_written())
def test_the_subset_sanitizer_leaves_a_translation_unchanged(sql):
    assert sanitize_subset_string(sql, text_fields={'nom', 'code'}) == sql


def test_translated_sql_survives_the_combination_with_an_old_subset(table):
    new = full(binary('LIKE', col('nom'), lit('Route%')), SQLITE)
    combined = combine_with_old_subset(new, '"id" < 5', 'OR', provider_type='spatialite')
    rows = [row[0] for row in table.execute('SELECT id FROM t WHERE {} ORDER BY id'.format(combined))]  # nosec B608
    assert rows == [1, 2, 3, 4, 10]


# -- writings the subset sanitizer and SQLite read as written ---------------------------

def test_negated_globs_are_written_not_glob():
    assert full(binary('NOT LIKE', col('nom'), lit('A%')), SQLITE) == '"nom" NOT GLOB \'A*\''
    assert full(binary('NOT ILIKE', col('nom'), lit('a%')), SQLITE) == '"nom" NOT GLOB \'[aA]*\''


def test_field_names_with_an_apostrophe_are_refused():
    # the sanitizer took 'usage" GLOB ' for a literal and erased the subset
    assert 'safely' in refused(binary('=', col("nom d'usage"), lit('x')), SQLITE, {"nom d'usage": 'text'})


def test_sqlite_reals_are_written_exactly():
    connection = sqlite3.connect(':memory:')
    for value in (0.3, -737867.403628, 6656395.210250434, 1e-05, 2.5, 3.0, -4.0, 2.0 ** 62, 0.1 * 3):
        node = binary('=', col('ratio'), lit(value))
        sql = full(binary('<', col('ratio'), lit(value)), SQLITE).split(' < ', 1)[1]
        assert connection.execute('SELECT ' + sql).fetchone()[0] == value  # nosec B608
        assert 'e' not in sql.replace('CAST', '').replace('REAL', '')
        assert full(node, SQLITE)
    assert refused(binary('<', col('ratio'), lit(1e300)), SQLITE)
    assert refused(binary('<', col('ratio'), lit(1e22)), SQLITE)
    assert refused(binary('<', col('ratio'), lit(1e-300)), SQLITE)
    assert full(binary('<', col('ratio'), lit(1e300)), POSTGRESQL) == '"ratio" < 1e+300'


def test_translation_reports_its_columns_and_whether_it_is_a_condition():
    good = binary('>', col('pop'), lit(5))
    bad = binary('=', function('regexp_replace', col('nom'), lit('a'), lit('b')), lit('x'))
    result = translate_native(binary('AND', good, bad), SQLITE, TYPES)
    assert result.native_columns == frozenset({'pop'})
    assert result.predicate
    assert not translate_native(function('regexp_match', col('nom'), lit('a')), SQLITE, TYPES).predicate
    assert translate_native(negation(good), SQLITE, TYPES).predicate
    assert translate_native(between(col('pop'), lit(1), lit(2)), SQLITE, TYPES).predicate


# -- hybrid subsets (SQLite): the native part plus the keys QGIS evaluated --------------------

def test_key_reference():
    assert key_reference('fid') == '"fid"'
    assert key_reference('code_insee') == '"code_insee"'
    for name in ('a"b', "l'id", '', None):
        with pytest.raises(Unsupported):
            key_reference(name)


def test_hybrid_keeps_the_native_part_alone_when_qgis_excludes_nothing_from_it():
    assert hybrid_sql('"pop" > 5', [1, 3], [], '"id"', True) == '"pop" > 5'


def test_hybrid_lists_the_shorter_side():
    assert hybrid_sql('"pop" > 5', [1, 3, 6], [9], '"id"', True) == (
        '"id" IS NOT NULL AND ("pop" > 5) AND NOT ("id" IN (9))')
    assert hybrid_sql('"pop" > 5', [1], [3, 6], '"id"', True) == '"id" IS NOT NULL AND "id" IN (1)'
    assert hybrid_sql('', [2, 5], None, '"fid"', True) == '"fid" IS NOT NULL AND "fid" IN (2, 5)'


def test_hybrid_keeps_nothing_with_a_contradiction():
    assert hybrid_sql('"pop" > 5', [], [1, 3], '"id"', True) == '"id" <> "id"'
    assert hybrid_sql('', [], None, '"fid"', True) == '"fid" <> "fid"'


def test_hybrid_text_keys_are_compared_with_their_case():
    assert hybrid_sql('', ["l'Isle", '01001'], None, '"code"', False) == (
        '"code" IS NOT NULL AND "code" COLLATE BINARY IN (\'l\'\'Isle\', \'01001\')')
    connection = sqlite3.connect(':memory:')
    connection.execute('CREATE TABLE t (code TEXT COLLATE NOCASE)')
    connection.executemany('INSERT INTO t VALUES (?)', [('a1',), ('A1',), ('b2',)])
    sql = hybrid_sql('', ['a1'], None, '"code"', False)
    assert [row[0] for row in connection.execute('SELECT code FROM t WHERE ' + sql)] == ['a1']  # nosec B608


def test_hybrid_refuses_null_keys_and_too_long_lists():
    with pytest.raises(Unsupported):
        hybrid_sql('', [1, None], None, '"id"', True)
    with pytest.raises(Unsupported):
        hybrid_sql('', list(range(HYBRID_MAX_KEYS + 1)), None, '"id"', True)


def test_hybrid_subset_keeps_what_the_expression_keeps(table):
    # "pop" > 2 AND <something QGIS alone evaluates, here: an id parity>
    translation = translate_native(binary('>', col('pop'), lit(2)), SQLITE, TYPES)
    native_rows = [row[0] for row in table.execute('SELECT id FROM t WHERE ' + translation.sql)]  # nosec B608
    kept = sorted(key for key in native_rows if key % 2 == 0)
    excluded = [key for key in native_rows if key % 2]
    for failing, expected in ((excluded, kept), ([], sorted(native_rows))):
        sql = hybrid_sql(translation.sql, kept if failing else native_rows, failing, '"id"', True)
        rows = [row[0] for row in table.execute('SELECT id FROM t WHERE {} ORDER BY id'.format(sql))]  # nosec B608
        assert rows == expected
    assert list(table.execute('SELECT id FROM t WHERE ' + hybrid_sql('', [], None, '"id"', True))) == []  # nosec B608


def test_translation_reports_whether_it_holds_a_connective():
    # OGR SQL: TRUE AND NULL is FALSE, so a negated AND / OR is left to the former conversion
    assert not translate_native(binary('>', col('pop'), lit(5)), OGR_SQL, TYPES).composite
    assert not translate_native(in_list(col('id'), [1, 2], negated=True), OGR_SQL, TYPES).composite
    assert translate_native(binary('AND', binary('>', col('pop'), lit(5)), binary('<', col('ratio'), lit(2))),
                            OGR_SQL, TYPES).composite
    assert translate_native(binary('OR', binary('>', col('pop'), lit(5)), binary('<', col('ratio'), lit(2))),
                            OGR_SQL, TYPES).composite
    assert translate_native(negation(binary('>', col('pop'), lit(5))), OGR_SQL, TYPES).composite
    assert translate_native(binary('=', col('ratio'), lit(0.5)), OGR_SQL, TYPES).composite  # its tolerance
