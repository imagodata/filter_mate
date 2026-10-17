# -*- coding: utf-8 -*-
"""
Source capability of a QGIS layer (see core.domain.source_capability).

:func:`capability_for_layer` classifies ``layer.providerType()`` and
``layer.source()`` once per (layer id, source): a layer whose source
changes (a raster cut to a VRT, a layer repointed) is classified again.
Every QGIS call is guarded: the module loads and answers under test mocks.
"""
import logging
from typing import Any, Dict, Optional, Tuple

try:
    from ...core.domain.source_capability import SourceCapability, classify
except ImportError:  # loaded outside the plugin package (unit tests)
    from core.domain.source_capability import SourceCapability, classify

logger = logging.getLogger(__name__)

_CACHE: Dict[Tuple[str, str], SourceCapability] = {}
_CACHE_MAX = 512


def clear_capability_cache() -> None:
    """Forget every classification (tests, project change)."""
    _CACHE.clear()


def _is_raster(layer: Any) -> bool:
    try:
        from qgis.core import QgsRasterLayer, QgsVectorLayer
    except ImportError:
        return False
    if not isinstance(QgsRasterLayer, type) or QgsRasterLayer is QgsVectorLayer:  # mocked qgis.core
        return False
    try:
        return isinstance(layer, QgsRasterLayer)
    except TypeError:
        return False


def capability_for_layer(layer: Any) -> Optional[SourceCapability]:
    """The :class:`SourceCapability` of ``layer``, None for no layer / a deleted one."""
    if layer is None:
        return None
    try:
        layer_id = layer.id()
        provider_key = layer.providerType()
        source = layer.source()
    except (RuntimeError, AttributeError) as exc:
        logger.debug(f"Source capability unavailable: {exc}")
        return None
    if not isinstance(provider_key, str):
        provider_key = ''
    if not isinstance(source, str):
        source = ''
    key = (str(layer_id), provider_key + '\n' + source)
    capability = _CACHE.get(key)
    if capability is None:
        capability = classify(provider_key, source, _is_raster(layer))
        if len(_CACHE) >= _CACHE_MAX:
            _CACHE.clear()
        _CACHE[key] = capability
    return capability


def is_remote_layer(layer: Any) -> bool:
    """True for a layer read from a web service or a remote file."""
    capability = capability_for_layer(layer)
    return bool(capability and capability.is_remote)


def counts_cheaply(layer: Any) -> bool:
    """Whether ``layer.featureCount()`` may run on the main thread (False for a web service...)."""
    capability = capability_for_layer(layer)
    return capability is None or capability.counts_cheaply


def feature_count_or_none(layer: Any) -> Optional[int]:
    """``layer.featureCount()``, or None when it would be a network request (see counts_cheaply)."""
    if layer is None or not counts_cheaply(layer):
        return None
    try:
        return layer.featureCount()
    except (RuntimeError, AttributeError):
        return None
