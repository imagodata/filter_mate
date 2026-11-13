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
PostgreSQL source selection, EXPLORING and the public API.
"""

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
