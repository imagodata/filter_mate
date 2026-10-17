# -*- coding: utf-8 -*-
"""
Point cloud capability detection.

Single module that knows about ``QgsPointCloudLayer``: it combines the
feature flag ``APP.OPTIONS.POINT_CLOUD.enabled``, the QGIS version floor
and the availability of the layer class. Every import is deferred and
guarded so the module loads without QGIS and degrades to "vector only"
under test mocks, where ``qgis.core.QgsPointCloudLayer`` is a MagicMock
instance rather than a type and ``Qgis.QGIS_VERSION_INT`` is not an int.

The flag and the version are re-read on every call (the flag can change
live); only the class resolution is cached, see :func:`reset_capability_cache`.
Since FilterMate 5 it also knows about ``QgsRasterLayer`` (flag
``APP.OPTIONS.RASTER.enabled``) and classifies any layer into a
:class:`~core.domain.layer_kind.LayerKind`; the module keeps its historical
name because every caller already imports it.
"""
import functools
import logging
from typing import Any, Optional, Tuple

logger = logging.getLogger(__name__)


def is_point_cloud_filtering_enabled() -> bool:
    """Return the live value of ``APP.OPTIONS.POINT_CLOUD.enabled`` (False by default)."""
    try:
        from ...config.config import ENV_VARS, _get_option_bool
        cfg = (
            ENV_VARS.get('CONFIG_DATA', {})
            .get('APP', {})
            .get('OPTIONS', {})
            .get('POINT_CLOUD', {})
        )
        return _get_option_bool(cfg.get('enabled'), False)
    except (ImportError, AttributeError, TypeError):
        return False


def is_raster_filtering_enabled() -> bool:
    """Return the live value of ``APP.OPTIONS.RASTER.enabled`` (False when unset)."""
    try:
        from ...config.config import ENV_VARS, _get_option_bool
        cfg = (
            ENV_VARS.get('CONFIG_DATA', {})
            .get('APP', {})
            .get('OPTIONS', {})
            .get('RASTER', {})
        )
        return _get_option_bool(cfg.get('enabled'), False)
    except (ImportError, AttributeError, TypeError):
        return False


def get_qgis_version_int() -> int:
    """Return ``Qgis.QGIS_VERSION_INT``, or 0 when QGIS is absent or the value is not an int."""
    try:
        from qgis.core import Qgis
    except Exception:
        return 0
    version = getattr(Qgis, 'QGIS_VERSION_INT', 0)
    if isinstance(version, bool) or not isinstance(version, int):
        return 0
    return version


@functools.lru_cache(maxsize=1)
def _resolve_point_cloud_class() -> Optional[type]:
    """Import ``QgsPointCloudLayer`` once; None when absent, not a real type or without subsets."""
    try:
        from qgis.core import QgsPointCloudLayer
    except Exception:
        return None
    if not isinstance(QgsPointCloudLayer, type):
        return None
    if not hasattr(QgsPointCloudLayer, 'setSubsetString'):
        return None
    return QgsPointCloudLayer


def _supports_point_cloud_filtering(qgis_version_int: int, feature_enabled: bool, has_point_cloud_type: bool) -> bool:
    """Delegate the decision to the domain rule; no domain module means no support."""
    try:
        from ...core.domain.point_cloud_support import supports_point_cloud_filtering
    except Exception as exc:
        logger.debug(f"point_cloud_support unavailable, point cloud filtering disabled: {exc}")
        return False
    return bool(supports_point_cloud_filtering(qgis_version_int, feature_enabled, has_point_cloud_type))


def get_point_cloud_layer_type() -> Optional[type]:
    """Return ``QgsPointCloudLayer`` when point cloud filtering is usable, else None.

    Usable means: flag ON, QGIS version at or above the domain floor, and a
    real ``QgsPointCloudLayer`` class exposing ``setSubsetString``.
    """
    enabled = is_point_cloud_filtering_enabled()
    if not enabled:
        return None
    layer_type = _resolve_point_cloud_class()
    if not _supports_point_cloud_filtering(get_qgis_version_int(), enabled, layer_type is not None):
        return None
    return layer_type


@functools.lru_cache(maxsize=1)
def _resolve_raster_class() -> Optional[type]:
    """Import ``QgsRasterLayer`` once; None when absent or not a real type."""
    try:
        from qgis.core import QgsRasterLayer
    except Exception:
        return None
    if not isinstance(QgsRasterLayer, type):
        return None
    return QgsRasterLayer


def _supports_raster_filtering(qgis_version_int: int, feature_enabled: bool, has_raster_type: bool) -> bool:
    try:
        from ...core.domain.raster_support import supports_raster_filtering
    except Exception as exc:
        logger.debug(f"raster_support unavailable, raster filtering disabled: {exc}")
        return False
    return bool(supports_raster_filtering(qgis_version_int, feature_enabled, has_raster_type))


def get_raster_layer_type() -> Optional[type]:
    """Return ``QgsRasterLayer`` when raster exploring/filtering is usable, else None."""
    enabled = is_raster_filtering_enabled()
    if not enabled:
        return None
    layer_type = _resolve_raster_class()
    if not _supports_raster_filtering(get_qgis_version_int(), enabled, layer_type is not None):
        return None
    try:
        from qgis.core import QgsVectorLayer
        if layer_type is QgsVectorLayer:
            return None
    except Exception:
        return None
    return layer_type


# Raster providers whose pixels can be read for analysis. Web services (WMS,
# XYZ, WCS, ArcGIS) are rendered images or remote coverages: never sources or
# targets, their statistics would be fetched over the network.
ANALYSIS_RASTER_PROVIDERS = ('gdal', 'virtualraster', 'postgresraster')
# The other raster providers, hidden from the current-layer combo box: a
# basemap (OSM, orthophoto) in the list could be chosen and do nothing.
NON_ANALYSIS_RASTER_PROVIDERS = ('wms', 'wcs', 'arcgismapserver', 'grassraster')


def exclude_non_analysis_rasters(combo: Any) -> None:
    """Hide web / non analysable rasters from a ``QgsMapLayerComboBox``.

    The combo box filters (``RasterLayer``) admit every raster layer, while
    FilterMate only handles :data:`ANALYSIS_RASTER_PROVIDERS`.
    """
    try:
        excluded = list(combo.excludedProviders()) if hasattr(combo, 'excludedProviders') else []
        merged = excluded + [key for key in NON_ANALYSIS_RASTER_PROVIDERS if key not in excluded]
        combo.setExcludedProviders(merged)
    except (AttributeError, TypeError, RuntimeError) as exc:
        logger.debug(f"Web rasters not excluded from the layer combo box: {exc}")


def is_non_analysis_raster(layer: Any) -> bool:
    """True for a raster whose pixels FilterMate cannot read (WMS, XYZ, WCS basemap...).

    ``isinstance(layer, get_filterable_layer_types())`` admits every ``QgsRasterLayer``
    once rasters are on: callers registering layers drop these with this check.
    """
    raster_type = _resolve_raster_class()
    if raster_type is None or layer is None:
        return False
    try:
        from qgis.core import QgsVectorLayer
        if raster_type is QgsVectorLayer:  # mocked qgis.core: one class for both
            return False
        return isinstance(layer, raster_type) and layer.providerType() not in ANALYSIS_RASTER_PROVIDERS
    except (ImportError, TypeError, RuntimeError, AttributeError):
        return False


def is_raster_layer(layer: Any) -> bool:
    """True when ``layer`` is an analysable ``QgsRasterLayer`` and raster filtering is usable."""
    if layer is None:
        return False
    layer_type = get_raster_layer_type()
    if layer_type is None:
        return False
    try:
        if not isinstance(layer, layer_type):
            return False
        return layer.providerType() in ANALYSIS_RASTER_PROVIDERS
    except (TypeError, RuntimeError, AttributeError):
        return False


def get_layer_kind(layer: Any) -> Any:
    """Classify ``layer`` as a :class:`LayerKind` (VECTOR, RASTER, POINT_CLOUD or OTHER).

    Raster and point cloud layers are only recognized when their feature flag
    is on; otherwise they are OTHER, which callers treat as "not handled".
    """
    from ...core.domain.layer_kind import LayerKind
    if layer is None:
        return LayerKind.OTHER
    try:
        from qgis.core import QgsVectorLayer
        if isinstance(QgsVectorLayer, type) and isinstance(layer, QgsVectorLayer):
            return LayerKind.VECTOR
    except Exception as exc:
        logger.debug(f"[FM5] vector layer test failed: {exc}")
    if is_point_cloud_layer(layer):
        return LayerKind.POINT_CLOUD
    if is_raster_layer(layer):
        return LayerKind.RASTER
    return LayerKind.OTHER


def layer_kind_by_class(layer: Any) -> Any:
    """Kind from the layer class only, ignoring the dock options (Processing, REST API).

    Web rasters (WMS, XYZ...) stay OTHER: their pixels cannot be analysed.
    """
    from ...core.domain.layer_kind import LayerKind
    try:
        from qgis.core import QgsRasterLayer, QgsVectorLayer
    except Exception:
        return LayerKind.OTHER
    try:
        if isinstance(QgsVectorLayer, type) and isinstance(layer, QgsVectorLayer):
            return LayerKind.VECTOR
        if isinstance(QgsRasterLayer, type) and isinstance(layer, QgsRasterLayer):
            return LayerKind.RASTER if layer.providerType() in ANALYSIS_RASTER_PROVIDERS else LayerKind.OTHER
        point_cloud_type = _resolve_point_cloud_class()
        if point_cloud_type is not None and isinstance(layer, point_cloud_type):
            return LayerKind.POINT_CLOUD
    except (TypeError, RuntimeError, AttributeError):
        pass
    return LayerKind.OTHER


def is_coverage_layer(layer: Any) -> bool:
    """True for a usable raster or point cloud layer (non-vector FilterMate layer)."""
    return is_point_cloud_layer(layer) or is_raster_layer(layer)


def get_filterable_layer_types() -> Tuple[type, ...]:
    """Return the layer classes FilterMate can filter, as real types only.

    ``(QgsVectorLayer,)`` by default, plus ``QgsPointCloudLayer`` and
    ``QgsRasterLayer`` when their filtering is usable, ``()`` when ``qgis.core`` cannot
    provide a real ``QgsVectorLayer`` type.
    """
    try:
        from qgis.core import QgsVectorLayer
    except Exception:
        return ()
    if not isinstance(QgsVectorLayer, type):
        return ()
    types = [QgsVectorLayer]
    point_cloud_type = get_point_cloud_layer_type()
    if point_cloud_type is not None and point_cloud_type is not QgsVectorLayer:
        types.append(point_cloud_type)
    raster_type = get_raster_layer_type()
    if raster_type is not None and raster_type is not QgsVectorLayer:
        types.append(raster_type)
    return tuple(types)


def is_point_cloud_layer(layer: Any) -> bool:
    """True when ``layer`` is a ``QgsPointCloudLayer`` and point cloud filtering is usable."""
    if layer is None:
        return False
    layer_type = get_point_cloud_layer_type()
    if layer_type is None:
        return False
    try:
        return isinstance(layer, layer_type)
    except TypeError:
        return False


def get_current_layer_combo_filters() -> Optional[Any]:
    """Return the ``QgsMapLayerProxyModel`` filters for the current-layer combo box.

    ``HasGeometry`` alone, or ``HasGeometry | PointCloudLayer`` when point
    cloud filtering is usable; None when the proxy model cannot be imported.
    """
    try:
        try:
            from qgis.gui import QgsMapLayerProxyModel
        except ImportError:
            from qgis.core import QgsMapLayerProxyModel
        flags = QgsMapLayerProxyModel.Filter.HasGeometry
        if get_point_cloud_layer_type() is not None:
            flags = flags | QgsMapLayerProxyModel.Filter.PointCloudLayer
        if get_raster_layer_type() is not None:
            flags = flags | QgsMapLayerProxyModel.Filter.RasterLayer
        return flags
    except (ImportError, AttributeError, TypeError):
        return None


def reset_capability_cache() -> None:
    """Clear the cached class resolution (tests, plugin reload)."""
    _resolve_point_cloud_class.cache_clear()
    _resolve_raster_class.cache_clear()
