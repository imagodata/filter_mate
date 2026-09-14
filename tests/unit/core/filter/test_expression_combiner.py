"""Regression tests for combining a new filter with an existing subset string.

2026-09-14: a GeoPackage layer already filtered as a target carries a subset
of the form ``ROWID IN (SELECT id FROM "rtree_..." WHERE ...) AND
ST_Intersects(..., ST_MakeValid(ST_GeomFromText('...', 2154)))``. When that
layer became the source of the next step, the combiners saw the ``WHERE``
and blindly dropped one trailing ``)`` (legacy handling for malformed
subsets), producing invalid SQL: SQLite answered "incomplete input" and the
source layer showed 0 features.
"""

import importlib.util
import re
from pathlib import Path

import pytest

from core.filter.expression_builder import build_combined_filter_expression
from core.filter.expression_combiner import combine_with_old_subset


def _load_subset_string_builder():
    # Loaded by path: importing the ``core.tasks`` package pulls in
    # filter_task and its QGIS-only relative imports.
    path = (
        Path(__file__).resolve().parents[4]
        / "core" / "tasks" / "builders" / "subset_string_builder.py"
    )
    spec = importlib.util.spec_from_file_location("_subset_string_builder", path)
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
NEW_EXPRESSION = '"importance" in (\'1\', \'2\', \'3\', \'4\')'
# Legacy malformed subset: one closing parenthesis too many after the WHERE.
LEGACY_UNBALANCED_OLD_SUBSET = '"fid" IN (SELECT id FROM t WHERE a = 1))'


def _is_balanced(expression: str) -> bool:
    return expression.count('(') == expression.count(')')


def _squash(expression: str) -> str:
    # The combiners split the old subset at WHERE and re-join with a space;
    # the sanitizer collapses that double space before setSubsetString.
    return re.sub(r'\s+', ' ', expression)


@pytest.mark.parametrize(
    "combine",
    [
        pytest.param(
            lambda new, old: combine_with_old_subset(new, old, 'AND', 'spatialite'),
            id="expression_combiner",
        ),
        pytest.param(
            lambda new, old: build_combined_filter_expression(new, old, 'AND'),
            id="expression_builder",
        ),
        pytest.param(
            lambda new, old: SubsetStringBuilder.__new__(SubsetStringBuilder)._manual_combine(
                new, old, 'AND'
            ),
            id="subset_string_builder",
        ),
    ],
)
class TestCombineKeepsBalancedOldSubset:
    def test_rtree_prefilter_subset_is_kept_verbatim(self, combine):
        assert _is_balanced(RTREE_OLD_SUBSET)

        combined = _squash(combine(NEW_EXPRESSION, RTREE_OLD_SUBSET))

        assert _is_balanced(combined), combined
        assert RTREE_OLD_SUBSET in combined
        assert combined.index(RTREE_OLD_SUBSET) < combined.index(NEW_EXPRESSION)
        assert ' AND ' in combined[len(RTREE_OLD_SUBSET):]

    def test_legacy_excess_parenthesis_is_still_dropped(self, combine):
        combined = _squash(combine(NEW_EXPRESSION, LEGACY_UNBALANCED_OLD_SUBSET))

        assert _is_balanced(combined), combined
        assert '"fid" IN (SELECT id FROM t WHERE a = 1)' in combined
        assert 'a = 1))' not in combined
