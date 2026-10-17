# -*- coding: utf-8 -*-
"""
One formatter of key literals for every path (2026-10-17).

``repr(fid)`` wrote ``"L'Isle-Jourdain"`` (an identifier in SQL),
``f"'{v}'"`` let a quote end the literal, the numeric branches joined the
values as they came, and a text key made of digits (``'01001'``) was read
as a number because the first ten values were tested before the field type.

Module tested: core.filter.pk_formatter (and its callers)
"""
from unittest.mock import MagicMock

import pytest

from core.filter.expression_builder import build_feature_id_expression
from core.filter.pk_formatter import (
    format_key_literal,
    format_pk_values_for_sql,
    is_pk_numeric,
    key_values_look_numeric,
    sql_string_literal,
)
from infrastructure.database.sql_utils import format_pk_values_for_sql as sql_utils_format

pytestmark = pytest.mark.unit

INJECTION = "1); DROP TABLE communes; --"


def _layer(field_name, numeric, type_name=None):
    """Layer mock with one field ``field_name`` (QgsFields: indexOf + []) ."""
    field = MagicMock()
    field.isNumeric.return_value = numeric
    field.typeName.return_value = type_name or ("Integer" if numeric else "String")
    fields = MagicMock()
    fields.indexOf.side_effect = lambda name: 0 if name == field_name else -1
    fields.__getitem__ = MagicMock(return_value=field)
    layer = MagicMock()
    layer.fields.return_value = fields
    return layer


class TestLiterals:
    def test_quote_is_doubled(self):
        assert sql_string_literal("L'Isle-Jourdain") == "'L''Isle-Jourdain'"
        assert format_key_literal("L'Isle-Jourdain", numeric=False) == "'L''Isle-Jourdain'"

    def test_numeric_values_unquoted(self):
        assert format_key_literal(12, True) == "12"
        assert format_key_literal(2.0, True) == "2"
        assert format_key_literal(1.5, True) == "1.5"
        assert format_key_literal("42", True) == "42"
        assert format_key_literal("-7", True) == "-7"

    def test_numeric_list_never_writes_text_raw(self):
        assert format_key_literal(INJECTION, True) == "'1); DROP TABLE communes; --'"
        assert format_key_literal("L'Isle", True) == "'L''Isle'"

    def test_leading_zero_code_stays_text_even_in_a_numeric_list(self):
        assert format_key_literal("01001", True) == "'01001'"

    def test_null(self):
        assert format_key_literal(None, True) == "NULL"
        assert format_key_literal(None, False) == "NULL"


class TestDetection:
    def test_every_value_is_tested(self):
        values = [str(i) for i in range(1, 11)] + ["abc"]
        assert not key_values_look_numeric(values)

    def test_leading_zero_codes_are_text(self):
        assert not key_values_look_numeric(["01001", "31000"])
        assert key_values_look_numeric(["1001", "31000", 5])

    def test_text_field_wins_over_digit_values(self):
        layer = _layer("insee", numeric=False)
        assert is_pk_numeric(layer, "insee", ["01001", "31555"]) is False
        assert is_pk_numeric(layer, "insee", ["1001", "31555"]) is False

    def test_text_field_holding_real_numbers_is_numeric(self):
        """v4.0.9: a PostgreSQL integer read as text through OGR."""
        assert is_pk_numeric(_layer("id", numeric=False), "id", [1, 2, 3]) is True

    def test_numeric_field(self):
        assert is_pk_numeric(_layer("id", numeric=True), "id", ["1", "2"]) is True


class TestFormatters:
    def test_core_formatter_text_codes(self):
        layer = _layer("insee", numeric=False)
        assert format_pk_values_for_sql(["01001", "L'Isle"], layer=layer, pk_field="insee") == "'01001', 'L''Isle'"

    def test_sql_utils_reads_the_schema_before_the_values(self):
        layer = _layer("insee", numeric=False)
        assert sql_utils_format(["01001", "31000"], pk_field="insee", layer=layer) == "'01001', '31000'"

    def test_sql_utils_tests_all_values_without_schema(self):
        values = [str(i) for i in range(1, 11)] + ["abc"]
        result = sql_utils_format(values, pk_field="code")
        assert result.startswith("'1', '2'") and result.endswith("'abc'")

    def test_sql_utils_never_writes_text_raw_for_a_numeric_name(self):
        """``id`` used to be assumed numeric whatever its values."""
        assert sql_utils_format(["abc", INJECTION], pk_field="id") == "'abc', '1); DROP TABLE communes; --'"

    def test_sql_utils_uuid_cast_escapes(self):
        layer = _layer("uid", numeric=False, type_name="uuid")
        assert sql_utils_format(["a'b"], pk_field="uid", layer=layer) == "'a''b'::uuid"


class TestFeatureIdExpression:
    @pytest.mark.parametrize("provider", ["ogr", "spatialite", "postgresql"])
    def test_text_key_with_a_quote_is_a_string_literal(self, provider):
        expression = build_feature_id_expression(["L'Isle-Jourdain"], "nom", None, provider, is_numeric=False)
        assert expression == "\"nom\" IN ('L''Isle-Jourdain')"

    def test_numeric_list_quotes_a_non_numeric_value(self):
        expression = build_feature_id_expression(["1", INJECTION], "id", "t", "postgresql", is_numeric=True)
        assert expression == '"t"."id" IN (1, \'1); DROP TABLE communes; --\')'


def _feature_collector_class():
    """Load feature_collector.py alone (core.tasks/__init__ needs the plugin package)."""
    import importlib.util
    from pathlib import Path
    path = Path(__file__).resolve().parents[4] / "core" / "tasks" / "collectors" / "feature_collector.py"
    spec = importlib.util.spec_from_file_location("core.tasks.collectors._fm_test_feature_collector", path)
    module = importlib.util.module_from_spec(spec)
    module.__package__ = "core.tasks.collectors"
    spec.loader.exec_module(module)
    return module.FeatureCollector


def test_feature_collector_formats_with_the_shared_formatter():
    FeatureCollector = _feature_collector_class()
    assert FeatureCollector.format_ids_for_sql(["L'Isle", "01001"], is_numeric=False) == "'L''Isle', '01001'"
    assert FeatureCollector.format_ids_for_sql([1, INJECTION], is_numeric=True) == "1, '1); DROP TABLE communes; --'"


class _NullVariant:
    """QGIS 3 / PyQt5: a NULL attribute is a null QVariant, not None."""

    def isNull(self):
        return True


class TestNullAndQgisDialect:
    def test_null_qvariant_is_null(self):
        from core.filter.pk_formatter import is_null_value
        assert is_null_value(None) and is_null_value(_NullVariant())
        assert not is_null_value(0) and not is_null_value('') and not is_null_value('NULL')
        assert format_key_literal(_NullVariant(), True) == 'NULL'
        assert format_key_literal(_NullVariant(), False) == 'NULL'

    def test_null_qvariants_do_not_make_keys_text(self):
        assert key_values_look_numeric([10, _NullVariant(), 20])
        assert format_pk_values_for_sql([10, _NullVariant()]) == '10, NULL'

    def test_qgis_expression_literal_escapes_backslashes(self):
        from core.filter.pk_formatter import QGIS_EXPRESSION, qgis_string_literal
        backslash = "\\"
        assert qgis_string_literal("b" + backslash + "c") == "'b" + backslash * 2 + "c'"
        assert qgis_string_literal("L'Isle") == "'L''Isle'"
        assert format_key_literal("b" + backslash + "c", False, QGIS_EXPRESSION) == "'b" + backslash * 2 + "c'"
        assert format_key_literal("b" + backslash + "c", False) == "'b" + backslash + "c'"   # SQL: unchanged
