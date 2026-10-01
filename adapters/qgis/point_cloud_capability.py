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
"""
import functools
import logging
from typing import Any, Optional, Tuple

logger = logging.getLogger(__name__)


def is_point_cloud_filtering_enabled() -> bool:
    """Return the live value of ``APP.OPTIONS.POINT_CLOUD.enabled`` (False by default)."""
    try:
        from ...config.config import ENV_VARS, _get_option_value
        cfg = (
            ENV_VARS.get('CONFIG_DATA', {})
            .get('APP', {})
            .get('OPTIONS', {})
            .get('POINT_CLOUD', {})
        )
        return bool(_get_option_value(cfg.get('enabled'), False))
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


def get_filterable_layer_types() -> Tuple[type, ...]:
    """Return the layer classes FilterMate can filter, as real types only.

    ``(QgsVectorLayer,)`` by default, ``(QgsVectorLayer, QgsPointCloudLayer)``
    when point cloud filtering is usable, ``()`` when ``qgis.core`` cannot
    provide a real ``QgsVectorLayer`` type.
    """
    try:
        from qgis.core import QgsVectorLayer
    except Exception:
        return ()
    if not isinstance(QgsVectorLayer, type):
        return ()
    point_cloud_type = get_point_cloud_layer_type()
    if point_cloud_type is None or point_cloud_type is QgsVectorLayer:
        return (QgsVectorLayer,)
    return (QgsVectorLayer, point_cloud_type)


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
        return flags
    except (ImportError, AttributeError, TypeError):
        return None


def reset_capability_cache() -> None:
    """Clear the cached class resolution (tests, plugin reload)."""
    _resolve_point_cloud_class.cache_clear()
