# -*- coding: utf-8 -*-
"""
QGIS adapters of FilterMate 5 coverage layers (raster and point cloud).

* :mod:`.cache` - folder of derived files (clipped VRT, clipped point clouds).
* :mod:`.pdal_cli` - detection and execution of the ``pdal`` executable.
* :mod:`.geometry_tools` - mask grid -> polygons, buffer, CRS transforms.
* :mod:`.raster_adapter` - raster summary, histogram, pixel values, selection geometry, preview.
* :mod:`.point_cloud_footprint` - footprint of the points kept by a point cloud selection.
* :mod:`.snapshots` - capture / restore the filter state of any layer, derived source registry.
* :mod:`.target_appliers` - apply a source geometry to vector, raster and point cloud targets.
* :mod:`.exporters` - export raster and point cloud layers as they are filtered.

Every module imports QGIS lazily or at module level only; they are exercised
for real by ``scripts/fm5_scenarios.py`` inside QGIS and by unit tests with fakes.
"""
