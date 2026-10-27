# filtermate_core

The filtering semantics of FilterMate, free of any host: no QGIS, no Qt, no GDAL.
It is the part of the plugin another GIS (or a plain Python program) can embed.

## Layout

| Package | Contents |
|---|---|
| `domain/` | value objects and criteria: filter expressions and results, layer descriptions, raster and point-cloud criteria, centroid targets |
| `filter/` | expression combination (`expression_combiner`), sanitisation, SQL quoting, server dialects, transfer policy |
| `optimization/` | query analysis, combined-query optimiser, performance advisor, backend selection |
| `services/` | host-free application services: filter, expression, buffer, source-subset buffer, point cloud |
| `strategies/` | progressive and multi-step filtering |
| `ports/` | the interfaces a host implements for the core: backend, filter executor, repository, cache, materialized views, point clouds, host layer (`qgis_port`, kept under its historical name) |
| `sql/postgresql/` | SQL safety checks, optimiser, materialized-view reference tracking, driver availability |
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
