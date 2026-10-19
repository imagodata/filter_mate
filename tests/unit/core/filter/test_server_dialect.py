"""Dialect rules use a small, explicit tree, with no QGIS imports."""
import pytest

from core.filter.server_dialect import (
    Node, TranslationStatus, translate_node,
)


def column(name):
    return Node('column', name, text='"{}"'.format(name))


def literal(value):
    return Node('literal', value, text=repr(value))


def binary(operator, left, right):
    return Node('binary', operator, (left, right), '{} {} {}'.format(left.text, operator, right.text))


@pytest.mark.parametrize('dialect', ['oracle', 'hana', 'wfs'])
def test_basic_comparison_quotes_text(dialect):
    result = translate_node(binary('=', column('nom'), literal("L'Isle-Jourdain")), dialect, ['nom'])
    assert result.status == TranslationStatus.FULL
    assert "'L''Isle-Jourdain'" in result.server_expression
    assert not result.local_expression


def test_and_splits_but_never_splits_or_or_not():
    good = binary('=', column('id'), literal(1))
    bad = Node('unsupported', 'left', text='left("nom", 3) = \'Sai\'')
    result = translate_node(binary('AND', good, bad), 'arcgis', ['id', 'nom'])
    assert result.status == TranslationStatus.PARTIAL
    assert '"id" = 1' in result.server_expression
    assert result.local_expression == '(' + bad.text + ')'
    for tree in (binary('OR', good, bad), Node('unary', 'NOT', (bad,), 'NOT (' + bad.text + ')')):
        result = translate_node(tree, 'arcgis', ['id', 'nom'])
        assert result.status == TranslationStatus.NONE
        assert not result.server_expression


def test_unknown_field_and_functions_are_refused():
    for tree in (binary('=', column('missing'), literal(1)),
                 binary('>', Node('unsupported', '$area', text='$area'), literal(1e6))):
        result = translate_node(tree, 'oracle', ['nom'])
        assert result.status == TranslationStatus.NONE
        assert result.reason


def test_ilike_requires_proven_case_semantics():
    tree = binary('ILIKE', column('nom'), literal('saint%'))
    assert translate_node(tree, 'mssql', ['nom']).status == TranslationStatus.NONE
    result = translate_node(tree, 'mssql', ['nom'], ilike_exact=True, text_semantics_exact=True)
    assert result.server_expression == '(UPPER("nom") LIKE UPPER(N\'saint%\'))'


def test_in_null_and_not():
    tree = Node('in', False, (column('id'), literal(1), literal(None)), '"id" IN (1, NULL)')
    assert translate_node(tree, 'oracle', ['id']).server_expression == '("id" IN (1, NULL))'
    null = binary('IS', column('id'), literal(None))
    assert translate_node(null, 'hana', ['id']).status == TranslationStatus.FULL
    assert translate_node(binary('IS', column('id'), literal(1)), 'hana', ['id']).status == TranslationStatus.NONE


def test_oapif_requires_evidence_instead_of_assuming_cql2():
    result = translate_node(binary('=', column('id'), literal(1)), 'oapif', ['id'])
    assert result.status == TranslationStatus.NONE
    assert 'provider' in result.reason.lower()


def test_oracle_in_limit_and_non_finite_numbers():
    tree = Node('in', False, (column('id'),) + tuple(literal(i) for i in range(1001)), 'large IN list')
    assert translate_node(tree, 'oracle', ['id']).status == TranslationStatus.NONE
    result = translate_node(binary('=', column('id'), literal(float('nan'))), 'arcgis', ['id'])
    assert result.status == TranslationStatus.NONE


@pytest.mark.parametrize('dialect', ['arcgis', 'mssql'])
def test_unknown_text_collation_is_refused(dialect):
    tree = binary('=', column('nom'), literal('a'))
    assert translate_node(tree, dialect, ['nom']).status == TranslationStatus.NONE


@pytest.mark.parametrize('operator', ['<>', 'NOT LIKE', 'NOT ILIKE'])
def test_wfs_nullable_negations_are_refused(operator):
    tree = binary(operator, column('nom'), literal('a'))
    assert translate_node(tree, 'wfs', ['nom']).status == TranslationStatus.NONE


@pytest.mark.parametrize('tree, fields', [
    (binary('=', column('nom'), literal(1)), {'nom': 'text'}),
    (binary('=', column('id'), literal('1')), {'id': 'numeric'}),
    (binary('>', column('date'), literal('2020-01-02')), {'date': 'date'}),
    (binary('LIKE', column('id'), literal('1%')), {'id': 'numeric'}),
    (binary('=', column('id'), literal(None)), {'id': 'numeric'}),
    (binary('=', literal(1), literal(0)), {}),
    (binary('>', column('nom'), literal('a')), {'nom': 'text'}),
    (Node('in', False, (literal(1), literal(1)), '1 IN (1)'), {}),
])
def test_nonportable_types_and_tree_shapes_are_refused(tree, fields):
    assert translate_node(tree, 'wfs', fields).status == TranslationStatus.NONE


def test_aggregate_remote_in_budget_cannot_be_evaded_by_or():
    part = Node('in', False, (column('id'),) + tuple(literal(i) for i in range(300)), 'id IN (...)')
    assert translate_node(binary('OR', part, part), 'wfs', ['id']).status == TranslationStatus.NONE


def test_empty_wfs_selection_uses_a_portable_field_contradiction():
    result = translate_node(binary('=', literal(1), literal(0)), 'wfs', ['id'])
    assert result.status == TranslationStatus.FULL
    assert result.server_expression == '(("id" IS NULL) AND ("id" IS NOT NULL))'


@pytest.mark.parametrize('dialect, operator', [('arcgis', '='), ('mssql', '='), ('oracle', '<'), ('hana', '>')])
def test_column_comparisons_do_not_bypass_text_semantics(dialect, operator):
    result = translate_node(binary(operator, column('a'), column('b')), dialect, {'a': 'text', 'b': 'text'})
    assert result.status == TranslationStatus.NONE
