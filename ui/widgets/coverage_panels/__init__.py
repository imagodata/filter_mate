"""
FilterMate 5 coverage widgets.

EXPLORING panels shown in place of the vector groups when the current layer
is a raster or a point cloud, and the range histogram they use.
"""
from .histogram_widget import RangeHistogramWidget  # noqa: F401
from .point_cloud_exploring_panel import PointCloudExploringPanel  # noqa: F401
from .raster_exploring_panel import RasterExploringPanel  # noqa: F401

__all__ = [
    'PointCloudExploringPanel',
    'RangeHistogramWidget',
    'RasterExploringPanel',
]
