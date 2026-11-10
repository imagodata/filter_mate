# -*- coding: utf-8 -*-
"""A filter written by a model is one plain WHERE clause, nothing else.

A model can be steered by what it reads (a layer name, an attribute value) and a
filter reaches the database with the rights of the user. Looking for what is forbidden
is not enough: PostgreSQL alone has E-strings and dollar quoting to hide a ``;``. So this
reads the expression token by token and accepts only what a filter needs. Anything else,
such as a subquery or a function outside the list, is refused.
"""
from __future__ import annotations

from typing import List

FUNCTIONS = frozenset({
    "abs", "cast", "ceil", "ceiling", "char_length", "coalesce", "concat", "extract", "floor", "left", "length",
    "lower", "ltrim", "mod", "nullif", "replace", "right", "round", "rtrim", "strftime", "substr", "substring", "trim",
    "unaccent", "upper",
})
# QGIS expressions can read the environment and the disk, and write to SQLite (env, file_exists, aggregate,
# sqlite_fetch_and_increment...): the same rule, a list of what a selection needs.
EXPRESSION_FUNCTIONS = FUNCTIONS | frozenset({
    "area", "day", "month", "perimeter", "to_date", "to_int", "to_real", "to_string", "x", "y", "year",
})
EXPRESSION_VARIABLES = frozenset({"$area", "$geometry", "$id", "$length", "$perimeter", "$x", "$y"})
# What a Processing formula (field calculator, geometry by expression, extract by expression) needs on top: math,
# text and the geometry functions that only compute. Still nothing that reads another layer, a file, the
# environment, or evaluates text as an expression (eval, aggregate, get_feature, env, load_layer...).
PROCESSING_FUNCTIONS = EXPRESSION_FUNCTIONS | frozenset({
    "acos", "asin", "atan", "atan2", "azimuth", "bounds", "buffer", "centroid", "clamp", "concat", "convex_hull",
    "cos", "degrees", "distance", "exp", "format_number", "geom_from_wkt", "geom_to_wkt", "geometry_type", "if",
    "intersects", "is_valid", "length", "ln", "log", "log10", "lpad", "make_point", "max", "min", "num_points",
    "pi", "point_on_surface", "power", "radians", "rpad", "scale_linear", "simplify", "sin", "sqrt", "tan", "title",
    "to_time", "translate", "x_max", "x_min", "y_max", "y_min", "z", "m",
})
CAST_TYPES = frozenset({
    "bigint", "boolean", "char", "date", "double", "float", "int", "int4", "int8", "integer", "numeric", "precision",
    "real", "smallint", "text", "time", "timestamp", "timestamptz", "varchar",
})
_BEFORE_PARENTHESIS = frozenset({"and", "between", "case", "else", "ilike", "in", "is", "like", "not", "or", "then",
                                 "when"})
_REFUSED_WORDS = frozenset({
    "alter", "call", "copy", "create", "delete", "do", "drop", "except", "execute", "grant", "insert", "intersect",
    "into", "lateral", "merge", "revoke", "select", "table", "truncate", "union", "update", "values", "with",
})
_OPERATORS = ("!~*", "<>", "!=", "<=", ">=", "||", "::", "!~", "~*", "=", "<", ">", "+", "-", "*", "/", "%", "~",
              "(", ")", ",", ".")


def _quoted_end(expression: str, start: int) -> int:
    """Index just after the quoted text opening at ``start``, -1 when it never closes."""
    quote = expression[start]
    index = start + 1
    while index < len(expression):
        if expression[index] == quote:
            if expression[index + 1:index + 2] != quote:
                return index + 1
            index += 1
        index += 1
    return -1


def _next_char(expression: str, index: int) -> str:
    while index < len(expression) and expression[index].isspace():
        index += 1
    return expression[index:index + 1]


def _word_end(expression: str, start: int) -> int:
    index = start
    while index < len(expression) and (expression[index].isalnum() or expression[index] == "_"):
        index += 1
    return index


def _number_end(expression: str, start: int) -> int:
    index = start
    while index < len(expression) and (expression[index].isdigit() or expression[index] == "."):
        index += 1
    if expression[index:index + 1] in ("e", "E") and (
            expression[index + 1:index + 2].isdigit() or expression[index + 1:index + 2] in ("+", "-")):
        index += 2
        while index < len(expression) and expression[index].isdigit():
            index += 1
    return index


def filter_problem(expression: str) -> str:
    """Why ``expression`` cannot be accepted as a filter written by a model; "" when it can."""
    return _problem(expression, FUNCTIONS, frozenset())


def expression_problem(expression: str) -> str:
    """Why ``expression`` cannot be accepted as a QGIS expression written by a model; "" when it can."""
    return _problem(expression, EXPRESSION_FUNCTIONS, EXPRESSION_VARIABLES)


def processing_expression_problem(expression: str) -> str:
    """Why ``expression`` cannot be accepted as a Processing formula written by a model; "" when it can."""
    return _problem(expression, PROCESSING_FUNCTIONS, EXPRESSION_VARIABLES)


def _problem(expression: str, functions: frozenset, variables: frozenset) -> str:
    if not expression.strip():
        return "the expression is empty"
    index, depth, previous = 0, 0, ""
    while index < len(expression):
        char = expression[index]
        if char.isspace():
            index += 1
        elif char == "'" or char == '"':
            end = _quoted_end(expression, index)
            if end < 0:
                return "a quote is never closed"
            if char == "'" and "\\" in expression[index:end]:
                return "a text value cannot hold a backslash"
            if char == '"' and _next_char(expression, end) == "(":
                return "a quoted name cannot be called as a function"
            index, previous = end, "value"
        elif char.isdigit():
            index, previous = _number_end(expression, index), "value"
        elif char == "$" and variables:
            end = _word_end(expression, index + 1)
            if expression[index:end].lower() not in variables:
                return f"the variable {expression[index:end]} is not accepted"
            index, previous = end, "value"
        elif char.isalpha() or char == "_":
            end = _word_end(expression, index)
            word = expression[index:end].lower()
            if expression[end:end + 1] in ("'", '"'):
                return f"the prefix {word} before a quote is not accepted"
            if word in _REFUSED_WORDS:
                return f"{word.upper()} is not accepted in a filter: use plain conditions on the fields of the layer"
            if previous == "::" and word not in CAST_TYPES:
                return f"casting to {word} is not accepted"
            if _next_char(expression, end) == "(" and word not in _BEFORE_PARENTHESIS:
                if word not in functions or previous == ".":
                    return f"the function {word} is not accepted in a filter"
            index, previous = end, "word"
        else:
            operator = next((item for item in _OPERATORS if expression.startswith(item, index)), "")
            if not operator or expression.startswith(("--", "/*"), index):
                return f"the character {char!r} is not accepted in a filter"
            depth += (operator == "(") - (operator == ")")
            if depth < 0:
                return "a parenthesis closes more than was opened"
            index += len(operator)
            previous = operator
    return "" if depth == 0 else "a parenthesis is never closed"


def quoted_identifiers(expression: str) -> List[str]:
    """Names between double quotes in ``expression``, without the table of a ``"table"."field"``."""
    names: List[str] = []
    index = 0
    while index < len(expression):
        char = expression[index]
        if char not in "'\"":
            index += 1
            continue
        end = index + 1
        content: List[str] = []
        while end < len(expression):
            if expression[end] == char:
                if expression[end + 1:end + 2] != char:
                    break
                end += 1  # doubled quote
            content.append(expression[end])
            end += 1
        if char == '"' and expression[end + 1:end + 2] != ".":
            names.append("".join(content))
        index = end + 1
    return names
