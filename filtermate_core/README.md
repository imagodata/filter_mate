# filtermate_core

The filtering semantics of FilterMate, free of any host: no QGIS, no Qt, no GDAL.
It is the part of the plugin another GIS (or a plain Python program) can embed.

## Layout

| Package | Contents |
|---|---|
| `domain/` | value objects and criteria: filter expressions and results, layer descriptions, raster and point-cloud criteria, centroid targets; `datasource_uri` reads the geometry column of a QGIS URI as `QgsDataSourceUri` does |
| `filter/` | expression combination (`expression_combiner`), sanitisation, SQL quoting, server dialects, transfer policy |
| `optimization/` | query analysis, combined-query optimiser, performance advisor, backend selection |
| `services/` | host-free application services: filter, expression, buffer, source-subset buffer, point cloud |
| `strategies/` | progressive and multi-step filtering |
| `ports/` | the interfaces a host implements for the core: backend, filter executor, repository, cache, materialized views, point clouds, geometric filter backends, host layer and geometry (`qgis_port`, kept under its historical name) |
| `geometry/` | `IGeometry` on shapely (`ShapelyGeometry`, reprojection with pyproj) and the spatial filter's semantics: `source_union` + `matches` (see below) |
| `sql/postgresql/` | **the PostGIS SQL of the spatial filters** (`PostgreSQLSqlBuilder`, see below), the filter-chain optimiser, QGIS expression → PostGIS (`qgis_expression`), object names (`naming`), SQL safety checks, optimiser, materialized-view reference tracking, driver availability |
| `sql/identifiers.py` | `sanitize_sql_identifier` |
| `sql/spatialite/` | index and temp-table managers, cache, Spatialite connection |
| `tasks/builders/` | subset-string builder shared with the host's task layer |
| `log.py`, `constants.py` | logger access and the constants the SQL generation needs |

## Rules

Checked by `tests/test_filtermate_core_is_host_free.py`:

* no import of `qgis`, `PyQt*`, `osgeo`, `sip` or the QGIS `processing` package,
  not even lazily or inside `try`;
* no import of the plugin's other packages (`core`, `adapters`, `infrastructure`,
  `config`, `ui`, ...): the core is imported by them, never the reverse;
* only relative imports inside the package, so it works both vendored in the
  plugin (`filter_mate.filtermate_core`) and standalone (`import filtermate_core`
  with the repository root on `sys.path`).

A function that receives a host object (a layer, a field) treats it as
duck-typed and documents the methods it calls.

## Compatibility with the former paths

Each module that moved here left an aliasing shim at its former path
(`core/filter/expression_combiner.py`, `adapters/backends/postgresql/sql_safety.py`, ...).
The shim makes `sys.modules[old name]` the moved module, so both spellings
name the same classes and `mock.patch` targets keep working. New code imports
`filtermate_core` directly; the shims go away once no caller is left.

## Standalone use

```python
import sys
sys.path.insert(0, "/path/to/filter_mate")  # the repository root

from filtermate_core.filter.expression_combiner import combine_expressions
```

Everything a host must provide is declared in `ports/`.

## PostGIS SQL for any host

`sql.postgresql.expression_builder.PostgreSQLSqlBuilder` writes the PostGIS
expression of a spatial filter (simple WKT, `EXISTS` against the source
table, filter chaining, union semantics, buffers, reprojection). A host
subclasses it and provides:

| Method | Abstract / default | QGIS (`adapters.backends.postgresql.expression_builder`) |
|---|---|---|
| `supports_layer`, `apply_filter` | abstract | provider check, subset string on the layer |
| `_connection_for_layer(layer)` | `None`: no statement timeout, no pre-computed buffer table (a dynamic buffer is inlined, or `None` is returned in filter chaining, where only the table works) | the layer's psycopg2 connection |
| `_notify_user_warning(message)` | the log | the QGIS message log |
| `_authid_to_srid`, `_srid_is_geographic` | `EPSG:<n>` and known lon/lat SRIDs | the QGIS CRS database, then the defaults |

Layers are duck-typed: `dataProvider().dataSourceUri()`, `crs().postgisSrid()`,
`fields()`. `tests/unit/core/sql/test_postgresql_sql_builder.py` checks that the
core alone writes the SQL the plugin writes in QGIS.

## The spatial filter without a database

`filtermate_core.geometry` (needs `shapely>=2.0`; `pyproj` to reproject)
applies the rule the SQL backends implement: a target is kept when one of the
enabled predicates holds between it and the **union** of the selected source
features, each made valid, the union grown (or eroded) by the buffer. A target
without geometry is never kept.

```python
from filtermate_core.geometry import ShapelyGeometry, matches, source_union

source = source_union([ShapelyGeometry.from_wkt(w) for w in selected_wkts], buffer_distance=50)
kept = [f for f in targets if matches(f.geometry, source, {"intersects": True, "touches": False})]
```

Testing each source feature alone gives other answers for `within`,
`coveredby`, `touches`, `contains`, `covers`, `equals`, `overlaps`, `crosses`
and `disjoint`, and for a negative buffer.
