"""The combiners always mean ``(old) <operator> (new)``.

2026-10-17, wrong results found by audit:

- substring shortcuts: ``"id" = 1`` is a substring of ``"id" = 12``, so
  AND returned ``"id" = 12`` alone; any textual inclusion returned one side
  whatever the operator; identical expressions under AND NOT returned X
  instead of nothing;
- an old subset containing WHERE (subquery, or a value) was not
  parenthesized: ``a IN (SELECT .. WHERE ..) OR b`` AND ``c`` was evaluated
  ``a OR (b AND c)``, and SubsetStringBuilder left the new side bare
  (``old AND NOT x OR y``);
- OGR: an old subset with FROM in a value was dropped, and an R-tree
  subset was cut after its first WHERE (unbalanced SQL).

The 4.9.2 fixes (R-tree subset kept verbatim, combination unchecked =
replace) are covered by test_expression_combiner.py.
"""

import importlib.util
import sqlite3
from pathlib import Path

import pytest

from core.filter.expression_builder import build_combined_filter_expression
from core.filter.expression_combiner import combine_with_old_subset


def _load_subset_string_builder():
    path = Path(__file__).resolve().parents[4] / "core" / "tasks" / "builders" / "subset_string_builder.py"
    # Named inside the plain ``core`` package so its relative imports of
    # core.filter resolve, without importing core.tasks (QGIS-only).
    spec = importlib.util.spec_from_file_location("core.tasks.builders._ssb_by_path", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.SubsetStringBuilder


SubsetStringBuilder = _load_subset_string_builder()

RTREE_OLD_SUBSET = (
    'ROWID IN (SELECT id FROM "rtree_troncon_de_route_geometrie" '
    'WHERE minx <= 584218.8 AND maxx >= 551572.5) '
    'AND ST_Intersects(ST_PointOnSurface("geometrie"), '
    "ST_MakeValid(ST_GeomFromText('Polygon ((0 0, 1 0, 1 1, 0 0))', 2154)))"
)

COMBINERS = [
    pytest.param(lambda new, old, op: combine_with_old_subset(new, old, op, 'spatialite'), id="expression_combiner"),
    pytest.param(lambda new, old, op: combine_with_old_subset(new, old, op, 'ogr'), id="expression_combiner_ogr"),
    pytest.param(build_combined_filter_expression, id="expression_builder"),
    pytest.param(
        lambda new, old, op: SubsetStringBuilder.__new__(SubsetStringBuilder)._manual_combine(new, old, op),
        id="subset_string_builder",
    ),
]


@pytest.fixture(scope="module")
def table():
    connection = sqlite3.connect(":memory:")
    connection.execute('CREATE TABLE t ("fid" INTEGER PRIMARY KEY, "id" INTEGER, "a" INTEGER, "b" INTEGER, "note" TEXT)')
    rows = [(fid, fid % 20, fid % 3, fid % 5, "WHERE x" if fid % 7 == 0 else "Paris from above") for fid in range(1, 101)]
    connection.executemany('INSERT INTO t VALUES (?, ?, ?, ?, ?)', rows)
    yield connection
    connection.close()


def _fids(table, where):
    return {row[0] for row in table.execute(f'SELECT "fid" FROM t WHERE {where}')}  # nosec B608 - test data


def _expected(table, old, op, new):
    old_set, new_set = _fids(table, old), _fids(table, new)
    return {"AND": old_set & new_set, "OR": old_set | new_set, "AND NOT": old_set - new_set}[op]


CASES = [
    ('"id" = 12', '"id" = 1'),                      # new is a substring of old
    ('"id" = 1', '"id" = 12'),                      # old is a substring of new
    ('"a" = 1 AND "b" = 2', '"b" = 2'),             # new contained in old
    ('"a" = 1', '"a" = 1 OR "b" = 3'),              # old contained in new
    ('"a" = 1', '"a" = 1'),                         # identical
    ('"a" = 1', '( "a" = 1 )'),                     # identical once parenthesized
    ('"fid" IN (SELECT "fid" FROM t WHERE "a" = 0) OR "b" = 1', '"a" = 2'),
    ('"note" = \'WHERE x\' OR "b" = 1', '"a" = 2'),
    ('"note" = \'Paris from above\'', '"b" = 1'),
]


@pytest.mark.parametrize("combine", COMBINERS)
@pytest.mark.parametrize("operator", ["AND", "OR", "AND NOT"])
@pytest.mark.parametrize("old, new", CASES)
def test_combined_subset_selects_old_operator_new(table, combine, operator, old, new):
    combined = combine(new, old, operator)
    assert _fids(table, combined) == _expected(table, old, operator, new), combined


@pytest.mark.parametrize("operator", ["AND", "OR"])
def test_combiner_keeps_one_copy_of_an_identical_expression(operator):
    assert combine_with_old_subset('"a" = 1', ' ( "a"  = 1 ) ', operator, 'spatialite') == '"a" = 1'


def test_identical_expressions_under_and_not_select_nothing():
    combined = combine_with_old_subset('"a" = 1', '"a" = 1', 'AND NOT', 'spatialite')
    assert combined == '( "a" = 1 ) AND NOT ( "a" = 1 )'


def test_spaces_inside_values_make_expressions_different():
    combined = combine_with_old_subset("\"n\" = 'a b'", "\"n\" = 'a  b'", 'AND', 'spatialite')
    assert combined == "( \"n\" = 'a  b' ) AND ( \"n\" = 'a b' )"


class TestOgrOldSubset:
    def test_from_inside_a_value_keeps_the_old_filter(self):
        old = "\"titre\" = 'Paris from above'"
        assert combine_with_old_subset('"b" = 1', old, 'AND', 'ogr') == f'( {old} ) AND ( "b" = 1 )'

    def test_rtree_subset_is_kept_whole(self):
        combined = combine_with_old_subset('"b" = 1', RTREE_OLD_SUBSET, 'AND', 'ogr')
        assert combined == f'( {RTREE_OLD_SUBSET} ) AND ( "b" = 1 )'

    def test_full_select_statement_keeps_its_where_body(self):
        old = 'SELECT * FROM "troncon" WHERE "nature" = \'Route\' AND ("a" = 1 OR "b" = 2)'
        combined = combine_with_old_subset('"c" = 3', old, 'OR', 'ogr')
        assert combined == '( "nature" = \'Route\' AND ("a" = 1 OR "b" = 2) ) OR ( "c" = 3 )'

    def test_select_statement_without_where_is_the_whole_layer(self):
        assert combine_with_old_subset('"c" = 3', 'SELECT * FROM "troncon"', 'OR', 'ogr') == '( 1 = 1 ) OR ( "c" = 3 )'
