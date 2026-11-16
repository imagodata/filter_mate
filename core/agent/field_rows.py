# -*- coding: utf-8 -*-
"""The row of one field in describe_layer, as short as it can be (token diet, lot 3, 2026-11-16)."""
from typing import Any, Dict


def field_row(name: str, type_name: str, alias: str, filterable: bool) -> Dict[str, Any]:
    """Return {name, type}, plus the alias only when there is one and filterable only when it is false.

    Args:
        name: the field name.
        type_name: the type of the field, as QGIS names it.
        alias: the alias of the field, empty when it has none.
        filterable: false for a virtual or joined field, which the SQL of the source cannot test.
    """
    row: Dict[str, Any] = {"name": name, "type": type_name}
    if alias:
        row["alias"] = alias
    if not filterable:
        row["filterable"] = False
    return row
