# -*- coding: utf-8 -*-
"""
Processing contexts for the workers of FilterMate's tasks (2026-10-17).

``processing.run()`` without a context builds one from ``QgsProject.instance()``
and ``iface.mapCanvas()``: called from a task's worker thread it read the canvas
and the project while the main thread changed them (QGIS 3.44 crashed in
``createExpressionContext`` when a layer was removed under a running filter).
A bare ``QgsProcessingContext()`` avoids that but loses the user's settings: no
invalid geometry check from the Processing options, an empty transform context
(the project's datum transformations ignored), no ellipsoid, no project scope.

The settings are captured on the main thread when a task is created
(:func:`capture_processing_settings`, from the context Processing itself builds)
and every worker context is a fresh ``QgsProcessingContext`` carrying them
(:func:`worker_processing_context`). A context is never shared between threads.
"""

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger('FilterMate.Infrastructure.ProcessingContext')

# The last settings captured on the main thread: read only by the workers
_CAPTURED: Optional[Dict[str, Any]] = None


def capture_processing_settings() -> Optional[Dict[str, Any]]:
    """Main thread: the settings of the context Processing builds, for the next workers.

    Returns:
        The captured settings, or None when QGIS / Processing are not available.
    """
    global _CAPTURED
    try:
        from qgis.core import QgsExpressionContext
        try:
            from processing.tools import dataobjects
            context = dataobjects.createContext()
        except Exception:  # Processing not loaded (qgis_process, tests): the project's settings
            from qgis.core import QgsProcessingContext, QgsProject
            context = QgsProcessingContext()
            context.setProject(QgsProject.instance())
        settings = {
            'transform_context': context.transformContext(),
            'invalid_geometry_check': context.invalidGeometryCheck(),
            'ellipsoid': context.ellipsoid(),
            'expression_context': QgsExpressionContext(context.expressionContext()),
        }
    except Exception as exc:  # catch-all safety net: a task must start without them
        logger.debug(f"Processing settings not captured: {exc}")
        return None
    _CAPTURED = settings
    return settings


def captured_transform_context():
    """The project's transform context captured on the main thread, None before any capture."""
    return (_CAPTURED or {}).get('transform_context')


def worker_processing_context(settings: Optional[Dict[str, Any]] = None):
    """A new QgsProcessingContext for a worker thread, with the captured settings.

    Args:
        settings: Settings of :func:`capture_processing_settings`; the last captured ones by default.

    Returns:
        QgsProcessingContext, or None when qgis.core has none (test doubles).
    """
    try:
        from qgis.core import QgsExpressionContext, QgsProcessingContext
    except ImportError:
        return None
    context = QgsProcessingContext()
    settings = settings or _CAPTURED
    if settings:
        try:
            context.setTransformContext(settings['transform_context'])
            context.setInvalidGeometryCheck(settings['invalid_geometry_check'])
            context.setEllipsoid(settings['ellipsoid'])
            context.setExpressionContext(QgsExpressionContext(settings['expression_context']))
        except Exception as exc:  # catch-all safety net: the bare context still runs the algorithm
            logger.debug(f"Processing settings not applied: {exc}")
    return context
