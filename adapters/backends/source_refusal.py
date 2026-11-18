# -*- coding: utf-8 -*-
"""
A spatial filter refused for its source, before any target layer is touched.

2026-11-12: when the source filter expression kept no feature (or could not be
read), the SpatiaLite and OGR source preparations fell back to every feature
of the source layer: the source showed 0 features while the targets kept all
that touched the whole source, with a warning in the log only. PostgreSQL
writes the source filter into its EXISTS sub-query, so a source that keeps
nothing never matches there. The file backends now refuse the filter with
this error, shown to the user, instead of using the whole layer; nothing is
filtered, the source keeps its previous filter too.

The message names the selection, which these preparations read
(FilterEngineTask._source_selection_qgis_expression), not the source filter:
under AND NOT the source filter of a selection keeping nothing, NOT (x), keeps
every feature.

The requests that read the features an expression keeps, in the variables of
a layer, are built here too (with_layer_context): by these preparations, the
PostgreSQL source selection, EXPLORING and the public API; and the copy of a
layer without its subset these readings use (unfiltered_copy).
"""
import logging

logger = logging.getLogger('FilterMate.Adapters.Backends.SourceRefusal')

# task_parameters key: the context of the source layer, read on the main thread
# when the filter task is created (FilterEngineTask.__init__).
SOURCE_CONTEXT_KEY = '_source_expression_context'


class SourceSelectionError(ValueError):
    """The source features of a spatial filter cannot be determined.

    The message is translated and meant for the user. The geometry preparation
    lets it through its backend fallbacks (none of them may use the whole
    source layer instead) and the filtering orchestrator shows it.
    """


def source_selection_refusal(layer_name: str, unreadable: bool = False) -> SourceSelectionError:
    """The error for a source selection that keeps no feature, or that cannot be read.

    Args:
        layer_name: Name of the source layer.
        unreadable: True when the expression cannot be parsed or evaluated.

    Returns:
        SourceSelectionError: To raise.
    """
    from qgis.PyQt.QtCore import QCoreApplication
    if unreadable:
        text = QCoreApplication.translate(
            'SourceSelection',
            "The selection of '{0}' cannot be evaluated: nothing was filtered.")
    else:
        text = QCoreApplication.translate(
            'SourceSelection',
            "The selection of '{0}' keeps no feature: nothing was filtered.")
    return SourceSelectionError(text.format(layer_name))


def layer_context(layer):
    """The global, project and layer variables of ``layer`` (QgsExpressionContext), read where it is called.

    The project scope reads the project: call it on the main thread when it
    can be (FilterEngineTask.__init__ keeps the source layer's under
    SOURCE_CONTEXT_KEY).
    """
    from qgis.core import QgsExpressionContext, QgsExpressionContextUtils
    return QgsExpressionContext(QgsExpressionContextUtils.globalProjectLayerScopes(layer))


def with_layer_context(request, layer, context=None):
    """``request`` with the global, project and layer variables of ``layer``.

    A QgsFeatureRequest filtered by an expression has no context of its own:
    ``"pop" > @seuil`` reads the variable as NULL and keeps no feature, and
    ``$area`` is planar, in the units of the layer CRS, where QGIS measures on
    the ellipsoid of the project (2026-11-12).

    ``layer`` is the layer whose variables the expression reads: the source
    layer also when its features are read through a copy without its subset
    (2026-11-13: the copy, out of the project, has none of its layer variables,
    and another @layer_name / @layer_id).

    Args:
        request: A QgsFeatureRequest, changed and returned.
        layer: The layer whose context the expression is evaluated in.
        context: The context of ``layer`` read before (layer_context, on the
            main thread); a copy of it is used. None, or the context of
            another layer: read now.

    Returns:
        QgsFeatureRequest: ``request``.
    """
    from qgis.core import QgsExpressionContext
    if context is not None and context.variable('layer_id') == layer.id():
        request.setExpressionContext(QgsExpressionContext(context))
    else:
        request.setExpressionContext(layer_context(layer))
    return request


def unfiltered_copy(layer):
    """A second layer on the data source of ``layer``, without its subset; None when it cannot be opened.

    The subset is removed from the URI (as OGRExpressionBuilder._unfiltered_target
    does). The layer of the project is never touched: its subset stays on the
    map, and nothing is left without a filter when the reading fails. The copy
    is made in the thread that reads it, out of the project, and is never kept
    (a layer made in a worker must not outlive it); it has none of the layer's
    variables (with_layer_context). No default style is read and no CRS is
    asked for: only its features are read. A memory layer opened again is a
    new, empty one: None.

    Read by the SpatiaLite source preparation (spatialite/filter_executor) and,
    since 2026-11-18, by the hybrid subsets of a filter that replaces the
    subset or is ORed with it (native_filter_translation._hybrid_subset).
    """
    try:
        from qgis.core import QgsProviderRegistry, QgsVectorLayer
        provider = layer.providerType()
        if provider == 'memory':
            return None
        registry = QgsProviderRegistry.instance()
        parts = dict(registry.decodeUri(provider, layer.source()))
        for key in ('subset', 'sql', 'filter'):
            parts.pop(key, None)
        uri = registry.encodeUri(provider, parts) if parts else layer.source()
        if provider == 'postgres':
            uri = _with_key_check_of(layer.source(), uri)
        options = QgsVectorLayer.LayerOptions(False, False)
        options.skipCrsValidation = True
        clone = QgsVectorLayer(uri, f"{layer.name()} (unfiltered)", provider, options)
        if clone.isValid() and clone.subsetString():
            clone.setSubsetString('')
        if clone.isValid() and not clone.subsetString():
            return clone
    except Exception as exc:  # nosec B110 - read through the layer instead, or not at all
        logger.debug(f"Unfiltered reading of {layer.name()} unavailable: {exc}")
    logger.warning(f"{layer.name()} cannot be read without its current filter")
    return None


def _with_key_check_of(source, uri):
    """``uri`` with the ``checkPrimaryKeyUnicity`` of the PostgreSQL URI ``source``.

    QGIS 3.22 drops it when it reads the URI back (3.44 keeps it): on a view
    whose layer says ``checkPrimaryKeyUnicity='0'``, each copy would count the
    distinct keys of the whole view again (review of 2026-11-18).
    """
    from qgis.core import QgsDataSourceUri
    name = 'checkPrimaryKeyUnicity'
    original, copy = QgsDataSourceUri(source), QgsDataSourceUri(uri)
    if not original.hasParam(name) or copy.hasParam(name):
        return uri
    copy.setParam(name, original.param(name))
    return copy.uri(False)  # an authcfg stays a reference, never expanded


def selection_request(expression, layer, context=None):
    """The request that reads the features ``expression`` keeps, in the variables of ``layer``.

    The QGIS text of a native subset may read ``@variables`` (folded into the
    subset with the global, project and layer values): the source features
    are read in the same values (with_layer_context).

    Args:
        expression: A parsed QgsExpression.
        layer: The source layer (not a copy of it: see with_layer_context).
        context: Its context read on the main thread (SOURCE_CONTEXT_KEY), if any.

    Returns:
        QgsFeatureRequest: Filtered by ``expression`` in the layer's context.
    """
    from qgis.core import QgsFeatureRequest
    return with_layer_context(QgsFeatureRequest(expression), layer, context)


def variable_values(expression, layer):
    """The values of the variables ``expression`` reads in the context of ``layer``: part of a cache key.

    2026-11-13: the features of an EXPLORING expression were cached by its
    text; after a change of @seuil the selection stayed that of the former
    value until the cache expired. Empty when the expression reads none.
    """
    from qgis.core import QgsExpression
    names = sorted(QgsExpression(expression or '').referencedVariables())
    if not names:
        return ()
    context = layer_context(layer)
    return tuple((name, repr(context.variable(name))) for name in names)
