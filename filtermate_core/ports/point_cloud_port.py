"""
Point Cloud Ports.

Abstract interfaces for point cloud layer access and subset filtering.
They mirror ``LayerRepositoryPort`` for ``QgsPointCloudLayer`` without
touching the vector contract.

This is a PURE PYTHON module with NO QGIS dependencies.
"""
from abc import ABC, abstractmethod
from typing import Any, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..domain.point_cloud_filter_criteria import PointCloudLayerSummary


class PointCloudRepositoryPort(ABC):
    """Access to the point cloud layers of the current project."""

    @abstractmethod
    def get_point_cloud_layer(self, layer_id: str) -> Optional[Any]:
        """Return the point cloud layer with ``layer_id``, None when absent or not a point cloud."""

    @abstractmethod
    def get_all_point_cloud_layers(self) -> List[Any]:
        """Return every point cloud layer of the project."""


class PointCloudFilterPort(ABC):
    """Subset application and inspection for one point cloud layer."""

    @abstractmethod
    def apply_subset(self, layer: Any, subset_string: str) -> bool:
        """Apply ``subset_string`` (empty clears the filter); True on success."""

    @abstractmethod
    def read_subset(self, layer: Any) -> str:
        """Return the current subset string, ``""`` when none."""

    @abstractmethod
    def read_summary(self, layer: Any) -> 'PointCloudLayerSummary':
        """Return the attributes, classes and ranges of the layer."""
