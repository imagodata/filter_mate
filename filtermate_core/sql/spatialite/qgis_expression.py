# -*- coding: utf-8 -*-
"""QGIS expression syntax to SpatiaLite SQL.

Moved from ``adapters/backends/spatialite/filter_executor.py`` (2026-10-28),
which re-exports it. Pure text rewriting: every rewrite runs outside string
literals and identifiers (``filter.sql_quotes``).
"""


def qgis_expression_to_spatialite(expression: str, geom_col: str = 'geometry') -> str:
    """
    Convert QGIS expression to Spatialite SQL.

    EPIC-1 Phase E4-S1: Extracted from filter_task.py line 3526 (58 lines)
    FIX v4.2.12: Aligned with qgis_expression_to_postgis() for full buffer expression support

    Spatialite spatial functions are ~90% compatible with PostGIS, but differences:
    - Type casting: PostgreSQL uses :: operator, Spatialite uses CAST() function
    - String comparison is case-sensitive by default
    - No ILIKE operator (use LOWER() + LIKE instead)
    - Spatial functions: ST_Buffer (same), ST_Area (same), etc.

    2026-10-17: same rules as qgis_expression_to_postgis. Every rewrite runs
    outside string literals and identifiers (``"buffer_m"`` became
    ``"Buffer_m"``), only calls are converted, length() only for the geometry,
    ``CAST(... AS REAL)`` only when the other side is a number (a text
    compared with a text became 0 compared with a text), and ILIKE keeps its
    column whole (``"nom" ILIKE 'a%'`` gave ``"LOWER(nom" LIKE LOWER('a%'``).

    Args:
        expression: QGIS expression string
        geom_col: Geometry column name (default: 'geometry')

    Returns:
        str: Spatialite SQL expression
    """
    import re

    if not expression:
        return expression

    from ...filter.sql_quotes import (
        IDENTIFIER_PLACEHOLDER, LITERAL_PLACEHOLDER, cast_numeric_operands, map_geometry_length, mask_quoted,
        qgis_literals_to_sql, unmask_quoted,
    )

    sql, parts = mask_quoted(expression)

    # 1. Convert QGIS spatial functions to Spatialite
    # FIX v4.2.12: Added spatial function conversions (missing in previous version)
    sql = map_geometry_length(sql, parts, geom_col, 'ST_Length')
    spatial_conversions = {
        r'\$area\b': f'ST_Area("{geom_col}")',
        r'\$length\b': f'ST_Length("{geom_col}")',
        r'\$perimeter\b': f'ST_Perimeter("{geom_col}")',
        r'\$x\b': f'ST_X("{geom_col}")',
        r'\$y\b': f'ST_Y("{geom_col}")',
        r'\$geometry\b': f'"{geom_col}"',
        r'\bbuffer\s*\(': 'Buffer(',  # Spatialite uses Buffer() not ST_Buffer()
        r'\barea\s*\(': 'ST_Area(',
        r'\bperimeter\s*\(': 'ST_Perimeter(',
    }

    for pattern, replacement in spatial_conversions.items():
        sql = re.sub(pattern, replacement, sql, flags=re.IGNORECASE)

    # 2. Convert IF statements to CASE WHEN
    # FIX v4.2.12: Added IF conversion (missing in previous version)
    sql = re.sub(
        r'\bif\s*\(\s*([^,]+),\s*([^,]+),\s*([^)]+)\)',
        r'CASE WHEN \1 THEN \2 ELSE \3 END',
        sql,
        flags=re.IGNORECASE
    )

    # 3. Add type casting for numeric operations
    # FIX v4.2.12: Spatialite uses CAST() instead of :: operator
    # Pattern: "field" > value → CAST("field" AS REAL) > value
    sql = cast_numeric_operands(sql, r'CAST(\1 AS REAL)', arithmetic=True)

    # 4. Handle CASE expressions
    sql = re.sub(r'\bcase\b', ' CASE ', sql, flags=re.IGNORECASE)
    sql = re.sub(r'\bwhen\b', ' WHEN ', sql, flags=re.IGNORECASE)
    sql = re.sub(r'\bis\b', ' IS ', sql, flags=re.IGNORECASE)
    sql = re.sub(r'\bthen\b', ' THEN ', sql, flags=re.IGNORECASE)
    sql = re.sub(r'\belse\b', ' ELSE ', sql, flags=re.IGNORECASE)
    sql = re.sub(r'\bend\b', ' END ', sql, flags=re.IGNORECASE)

    # 5. Handle LIKE/ILIKE - Spatialite doesn't have ILIKE, use LIKE with LOWER()
    # IMPORTANT: Process ILIKE first, before processing LIKE, to avoid double-replacement
    sql = re.sub(
        rf'({IDENTIFIER_PLACEHOLDER})\s+(NOT\s+)?ILIKE\s+({LITERAL_PLACEHOLDER})',
        r'LOWER(\1) \2LIKE LOWER(\3)',
        sql,
        flags=re.IGNORECASE
    )
    sql = re.sub(r'\bNOT\b', ' NOT ', sql, flags=re.IGNORECASE)
    sql = re.sub(r'\bLIKE\b', ' LIKE ', sql, flags=re.IGNORECASE)

    # 6. Convert PostgreSQL :: type casting to Spatialite CAST() function (if any remaining)
    sql = re.sub(rf'({IDENTIFIER_PLACEHOLDER})::numeric', r'CAST(\1 AS REAL)', sql)
    sql = re.sub(rf'({IDENTIFIER_PLACEHOLDER})::integer', r'CAST(\1 AS INTEGER)', sql)
    sql = re.sub(rf'({IDENTIFIER_PLACEHOLDER})::text', r'CAST(\1 AS TEXT)', sql)
    sql = re.sub(rf'({IDENTIFIER_PLACEHOLDER})::double', r'CAST(\1 AS REAL)', sql)

    # 7. Clean up multiple spaces
    sql = re.sub(r'\s+', ' ', sql).strip()

    return unmask_quoted(sql, qgis_literals_to_sql(parts))


__all__ = ['qgis_expression_to_spatialite']
