# -*- coding: utf-8 -*-
"""QGIS expression syntax to PostGIS SQL.

Moved from ``adapters/backends/postgresql/filter_executor.py`` (2026-10-27),
which re-exports it. Pure text rewriting: every rewrite runs outside string
literals and identifiers (``filter.sql_quotes``).
"""


def qgis_expression_to_postgis(expression: str, geom_col: str = 'geometry') -> str:
    """
    Convert QGIS expression to PostGIS SQL.

    EPIC-1 Phase E4-S1: Extracted from filter_task.py line 3451 (68 lines)
    FIX v4.2.12: Added END keyword, * and / operators, multiple spaces cleanup

    Converts QGIS expression syntax to PostgreSQL/PostGIS SQL:
    - Spatial functions ($area, $length, etc.) → ST_Area, ST_Length
    - IF statements → CASE WHEN
    - Type casting for numeric/text operations

    2026-10-17: every rewrite runs outside string literals and identifiers.
    The function names were replaced with str.replace anywhere (``"buffer_m"``
    became ``"ST_Buffer_m"``, ``"area_ha"`` ``"ST_Area_ha"``): only calls
    (``name(``) are converted now, and length() only for the geometry
    (length(string) is a string function in QGIS). ``::numeric`` is added
    only when the other side is a number (``"nature" <> 'Route'`` became
    ``"nature"::numeric <> 'Route'``).

    Args:
        expression: QGIS expression string
        geom_col: Geometry column name (default: 'geometry')

    Returns:
        str: PostGIS SQL expression
    """
    import re

    if not expression:
        return expression

    from ...filter.sql_quotes import (
        IDENTIFIER_PLACEHOLDER, cast_numeric_operands, map_geometry_length, mask_quoted,
        qgis_literals_to_sql, unmask_quoted,
    )

    sql, parts = mask_quoted(expression)

    # 1. Convert QGIS spatial functions to PostGIS
    sql = map_geometry_length(sql, parts, geom_col, 'ST_Length')
    spatial_conversions = {
        r'\$area\b': f'ST_Area("{geom_col}")',
        r'\$length\b': f'ST_Length("{geom_col}")',
        r'\$perimeter\b': f'ST_Perimeter("{geom_col}")',
        r'\$x\b': f'ST_X("{geom_col}")',
        r'\$y\b': f'ST_Y("{geom_col}")',
        r'\$geometry\b': f'"{geom_col}"',
        r'\bbuffer\s*\(': 'ST_Buffer(',
        r'\barea\s*\(': 'ST_Area(',
        r'\bperimeter\s*\(': 'ST_Perimeter(',
    }

    for pattern, replacement in spatial_conversions.items():
        sql = re.sub(pattern, replacement, sql, flags=re.IGNORECASE)

    # 2. Convert IF statements to CASE WHEN
    sql = re.sub(
        r'\bif\s*\(\s*([^,]+),\s*([^,]+),\s*([^)]+)\)',
        r'CASE WHEN \1 THEN \2 ELSE \3 END',
        sql,
        flags=re.IGNORECASE
    )

    # 3. Add type casting for numeric operations
    # FIX v4.2.12: Added * and / operators
    sql = cast_numeric_operands(sql, r'\1::numeric', arithmetic=True)

    # 4. Normalize SQL keywords (case-insensitive replacements)
    sql = re.sub(r'\bcase\b', ' CASE ', sql, flags=re.IGNORECASE)
    sql = re.sub(r'\bwhen\b', ' WHEN ', sql, flags=re.IGNORECASE)
    sql = re.sub(r'\bis\b', ' IS ', sql, flags=re.IGNORECASE)
    sql = re.sub(r'\bthen\b', ' THEN ', sql, flags=re.IGNORECASE)
    sql = re.sub(r'\belse\b', ' ELSE ', sql, flags=re.IGNORECASE)
    sql = re.sub(r'\bend\b', ' END ', sql, flags=re.IGNORECASE)  # FIX v4.2.12: Added END
    sql = re.sub(r'\bilike\b', ' ILIKE ', sql, flags=re.IGNORECASE)
    sql = re.sub(r'\blike\b', ' LIKE ', sql, flags=re.IGNORECASE)
    sql = re.sub(r'\bnot\b', ' NOT ', sql, flags=re.IGNORECASE)

    # 5. Add type casting for text operations
    sql = re.sub(rf'({IDENTIFIER_PLACEHOLDER})\s+(NOT\s+)?(I?LIKE)\b', r'\1::text \2\3', sql)

    # 6. Clean up multiple spaces (FIX v4.2.12)
    sql = re.sub(r'\s+', ' ', sql).strip()

    return unmask_quoted(sql, qgis_literals_to_sql(parts))


__all__ = ['qgis_expression_to_postgis']
