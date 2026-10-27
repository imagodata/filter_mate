"""
FilterMate Core Domain Module.

Domain models and entities for filter operations.
This module contains pure Python value objects and entities
with NO QGIS dependencies.

Value Objects (immutable, equality by value):
- FilterExpression: Validated filter expression with SQL conversion
- FilterResult: Result of a filter operation
- OptimizationConfig: Backend optimization settings

Entities (identity-based):
- LayerInfo: Layer metadata without QGIS dependency

Enums:
- ProviderType: Supported data provider types
- SpatialPredicate: Spatial filter predicates
- FilterStatus: Filter operation status
- GeometryType: Geometry types
"""
from .filter_expression import (  # noqa: F401
    FilterExpression,
    ProviderType,
    SpatialPredicate,
)
from .filter_result import (  # noqa: F401
    FilterResult,
    FilterStatus,
)
from .layer_info import (  # noqa: F401
    LayerInfo,
    GeometryType,
)
from .optimization_config import (  # noqa: F401
    OptimizationConfig,
)
from .point_cloud_filter_criteria import (  # noqa: F401
    AttributeRange,
    PointCloudAttributeSummary,
    PointCloudFilterCriteria,
    PointCloudFilterResult,
    PointCloudLayerSummary,
)
from .point_cloud_support import (  # noqa: F401
    ASPRS_CLASS_NAMES,
    POINT_CLOUD_GEOMETRY_TYPE,
    POINT_CLOUD_MIN_QGIS_VERSION_INT,
    POINT_CLOUD_PROVIDER_TYPE,
    asprs_class_label,
    build_point_cloud_layer_properties,
    ensure_point_cloud_layer_properties,
    is_point_cloud_layer_props,
    supports_point_cloud_filtering,
)

__all__ = [
    # Value Objects
    'FilterExpression',
    'FilterResult',
    'OptimizationConfig',
    'AttributeRange',
    'PointCloudFilterCriteria',
    'PointCloudAttributeSummary',
    'PointCloudLayerSummary',
    'PointCloudFilterResult',
    # Entities
    'LayerInfo',
    # Enums
    'ProviderType',
    'SpatialPredicate',
    'FilterStatus',
    'GeometryType',
    # Point cloud support
    'ASPRS_CLASS_NAMES',
    'POINT_CLOUD_GEOMETRY_TYPE',
    'POINT_CLOUD_MIN_QGIS_VERSION_INT',
    'POINT_CLOUD_PROVIDER_TYPE',
    'asprs_class_label',
    'build_point_cloud_layer_properties',
    'ensure_point_cloud_layer_properties',
    'is_point_cloud_layer_props',
    'supports_point_cloud_filtering',
]
