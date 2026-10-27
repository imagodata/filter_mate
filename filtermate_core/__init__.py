# -*- coding: utf-8 -*-
"""FilterMate core: the filtering semantics, free of any host (QGIS, Qt, GDAL).

What lives here
    domain/        value objects and criteria (filter expressions, results, raster
                   and point-cloud criteria, layer descriptions)
    filter/        expression combination, sanitisation, quoting, server dialects
    optimization/  query analysis and combined-query optimisation
    services/      host-free application services
    strategies/    progressive and multi-step filtering
    ports/         the interfaces a host implements for the core
    geometry/      IGeometry on shapely and the union semantics of the
                   spatial filter, for hosts other than QGIS (optional deps)
    sql/           PostgreSQL and Spatialite helpers that need no host
    tasks/         builders shared with the host's task layer

Rules (checked by tests/test_filtermate_core_is_host_free.py)
    * no import of qgis, PyQt, osgeo, sip or the QGIS ``processing`` package,
      not even lazily or inside ``try``;
    * no import of the plugin's other packages (core, adapters, infrastructure,
      config, ui, ...): the core is imported by them, never the reverse;
    * only relative imports inside the package, so it works both vendored in
      the plugin (``filter_mate.filtermate_core``) and standalone
      (``import filtermate_core`` with the repository root on ``sys.path``).

The plugin's former module paths (``core.filter.expression_combiner`` and the
like) remain as aliasing shims, so both spellings name the same objects.
"""
