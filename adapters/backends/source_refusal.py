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
"""


class SourceSelectionError(ValueError):
    """The source features of a spatial filter cannot be determined.

    The message is translated and meant for the user. The geometry preparation
    lets it through its backend fallbacks (none of them may use the whole
    source layer instead) and the filtering orchestrator shows it.
    """


def source_selection_refusal(layer_name: str, unreadable: bool = False) -> SourceSelectionError:
    """The error for a source filter that keeps no feature, or that cannot be read.

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
            "The source filter of '{0}' cannot be evaluated: nothing was filtered.")
    else:
        text = QCoreApplication.translate(
            'SourceSelection',
            "The source filter of '{0}' keeps no feature: nothing was filtered.")
    return SourceSelectionError(text.format(layer_name))
