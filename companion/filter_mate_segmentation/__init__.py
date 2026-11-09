# -*- coding: utf-8 -*-
"""FilterMate Segmentation: the optional model behind the Segment target of FilterMate."""


def classFactory(iface):  # noqa: N802 - QGIS plugin interface
    from .plugin import FilterMateSegmentationPlugin
    return FilterMateSegmentationPlugin(iface)
