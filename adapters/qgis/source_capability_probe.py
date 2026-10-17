# -*- coding: utf-8 -*-
"""
Source capability of a QGIS layer (see core.domain.source_capability).

:func:`capability_for_layer` classifies ``layer.providerType()`` and
``layer.source()`` once per (layer id, source): a layer whose source
changes (a raster cut to a VRT, a layer repointed) is classified again.
Every QGIS call is guarded: the module loads and answers under test mocks.

It also proves the stable key of a local layer (core.domain.stable_key):
:func:`key_field_is_unique` reads one field of every feature (in a task,
never on the main thread) and :func:`stable_key_for_layer` picks the key.
"""
import logging
from typing import Any, Dict, Optional, Tuple

try:
    from ...core.domain.source_capability import SourceCapability, classify
    from ...core.domain.stable_key import FEATURE_ID, FEATURE_ID_KEY, NONE, KeyChoice, choose_key
    from ...core.filter.pk_formatter import is_null_value
except ImportError:  # loaded outside the plugin package (unit tests)
    from core.domain.source_capability import SourceCapability, classify
    from core.domain.stable_key import FEATURE_ID, FEATURE_ID_KEY, NONE, KeyChoice, choose_key
    from core.filter.pk_formatter import is_null_value

logger = logging.getLogger(__name__)

_CACHE: Dict[Tuple[str, str], SourceCapability] = {}
_CACHE_MAX = 512
# Proving a key unique reads one attribute of every feature: above this many features the
# field stays unproven (the layer is then keyed by its feature id).
UNIQUE_SCAN_MAX_FEATURES = 500000
_UNIQUE_CACHE: Dict[Tuple[str, str, str], Optional[bool]] = {}


def clear_capability_cache() -> None:
    """Forget every classification and key verdict (tests, project change)."""
    _CACHE.clear()
    _UNIQUE_CACHE.clear()


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


def _data_key(layer: Any) -> Tuple[str, str]:
    """(layer id, source without its OGR subset): the data a key verdict is about."""
    source = layer.source()
    source = source if isinstance(source, str) else ''
    return str(layer.id()), source.split('|subset=', 1)[0]


def key_field_is_unique(layer: Any, name: str, scan: bool = True) -> Optional[bool]:
    """Whether every feature has a value of ``name``, all different: True, False or None (unknown).

    Read in a task (layer registration, filter), never on the main thread;
    the verdict is cached per layer data. A web service / remote file is
    never scanned (None). A scan through a subset string only proves
    duplicates (a value unique inside the subset may repeat outside it):
    True is then reported as None. ``scan=False`` answers from the cache only.
    """
    try:
        layer_id, source = _data_key(layer)
        subset = layer.subsetString() or ''
    except (RuntimeError, AttributeError):
        return None
    cache_key = (layer_id, source, name)
    if cache_key in _UNIQUE_CACHE:
        return _UNIQUE_CACHE[cache_key]
    if not scan:
        return None
    capability = capability_for_layer(layer)
    if capability is None or not capability.counts_cheaply:
        return None
    try:
        from qgis.core import QgsFeatureRequest
        fields = layer.fields()
        if fields.indexOf(name) < 0:
            return None
        request = QgsFeatureRequest()
        no_geometry = getattr(getattr(QgsFeatureRequest, 'Flag', None), 'NoGeometry', None)
        if no_geometry is not None:
            request.setFlags(no_geometry)
        request.setSubsetOfAttributes([name], fields)
        request.setLimit(UNIQUE_SCAN_MAX_FEATURES + 1)
        seen = set()
        verdict: Optional[bool] = True
        for count, feature in enumerate(layer.getFeatures(request), start=1):
            if count > UNIQUE_SCAN_MAX_FEATURES:
                verdict = None
                break
            value = feature[name]
            if is_null_value(value):
                verdict = False
                break
            try:
                marker = value if not isinstance(value, float) or value == value else repr(value)
                hash(marker)
            except TypeError:
                marker = repr(value)
            if marker in seen:
                verdict = False
                break
            seen.add(marker)
    except Exception as exc:  # nosec B110 - an unreadable field is no proven key
        logger.debug(f"Key scan of '{name}' failed: {exc}")
        return None
    if verdict is True and subset.strip():
        verdict = None
    if len(_UNIQUE_CACHE) >= _CACHE_MAX:
        _UNIQUE_CACHE.clear()
    _UNIQUE_CACHE[cache_key] = verdict
    return verdict


def stable_key_for_layer(layer: Any, scan: bool = True) -> KeyChoice:
    """The stable key of ``layer`` (core.domain.stable_key), its capability applied.

    A local layer without a proven key is keyed by its feature id, except
    where a subset cannot list feature ids (virtual layer, web service):
    there the choice is ``none`` (no key list).
    """
    capability = capability_for_layer(layer)
    try:
        fields = layer.fields()
        names = [field.name() for field in fields]
        try:
            declared = [fields.at(index).name() for index in layer.primaryKeyAttributes()]
        except (RuntimeError, AttributeError, IndexError, TypeError):
            declared = []
    except (RuntimeError, AttributeError, TypeError):
        names, declared = [], []
    local = capability is None or not capability.is_remote
    choice = choose_key(names, declared, local=local,
                        is_unique=lambda name: key_field_is_unique(layer, name, scan))
    lists_ids = capability is None or capability.lists_feature_ids
    if choice.origin == FEATURE_ID and not lists_ids:
        return KeyChoice(None, NONE)
    if choice.origin == NONE and lists_ids:
        return KeyChoice(FEATURE_ID_KEY, FEATURE_ID)
    return choice


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
