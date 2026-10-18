# -*- coding: utf-8 -*-
"""Similar features of a vector layer: click a feature, every feature with the same value is selected.

The vector counterpart of the raster similar objects tool (2026-10-18): the value compared is
the one of the group's expression (the display expression of the single / multiple selection),
read on the clicked feature; the selection is made with ``selectByExpression`` so the usual
map → panel synchronisation ("Select" mode) brings the features into the lists.
"""
import logging
from typing import Any, Optional

logger = logging.getLogger('FilterMate.ui.tools.similar_features')


def quoted_value(value: Any) -> str:
    """A QGIS expression literal for ``value`` (``NULL``, a number, a boolean or a quoted string)."""
    if value is None:
        return 'NULL'
    if isinstance(value, bool):
        return 'TRUE' if value else 'FALSE'
    if isinstance(value, (int, float)):
        return repr(value)
    try:
        from qgis.PyQt.QtCore import QVariant
        if isinstance(QVariant, type) and isinstance(value, QVariant):
            if value.isNull():
                return 'NULL'
            return quoted_value(value.value())
    except (ImportError, TypeError):
        pass
    text = str(value).replace("'", "''")
    return f"'{text}'"


def equality_expression(expression: str, value: Any) -> str:
    """The expression selecting the features whose ``expression`` has ``value``.

    Args:
        expression: A field name (quoted or not) or any QGIS expression.
        value: The value read on the clicked feature.

    Returns:
        ``(expression) = value``, or ``(expression) IS NULL`` for a missing value.
    """
    expression = (expression or '').strip()
    if not expression:
        return ''
    if value is None:
        return f"({expression}) IS NULL"
    literal = quoted_value(value)
    if literal == 'NULL':
        return f"({expression}) IS NULL"
    return f"({expression}) = {literal}"


def expression_value(layer: Any, expression: str, feature: Any) -> Any:
    """Evaluate ``expression`` on ``feature`` of ``layer``; None when it cannot be evaluated."""
    try:
        from qgis.core import QgsExpression, QgsExpressionContext, QgsExpressionContextUtils
        exp = QgsExpression(expression)
        context = QgsExpressionContext(QgsExpressionContextUtils.globalProjectLayerScopes(layer))
        context.setFeature(feature)
        exp.prepare(context)
        value = exp.evaluate(context)
        if exp.hasEvalError():
            logger.debug(f"[FM5] similar features: '{expression}' not evaluated: {exp.evalErrorString()}")
            return None
        return value
    except Exception as exc:
        logger.debug(f"[FM5] similar features: '{expression}' not evaluated: {exc}")
        return None


def feature_at(canvas: Any, layer: Any, position: Any) -> Optional[Any]:
    """The topmost feature of ``layer`` under the device ``position`` of the canvas, None without one."""
    try:
        from qgis.gui import QgsMapToolIdentify
        modes = getattr(QgsMapToolIdentify, 'IdentifyMode', QgsMapToolIdentify)
        results = QgsMapToolIdentify(canvas).identify(int(position.x()), int(position.y()), [layer],
                                                      modes.TopDownStopAtFirst)
    except Exception as exc:
        logger.debug(f"[FM5] similar features: nothing identified: {exc}")
        return None
    for result in results:
        feature = getattr(result, 'mFeature', None)
        if feature is not None and feature.isValid():
            return feature
    return None


try:
    from qgis.PyQt.QtCore import Qt, pyqtSignal
    from qgis.gui import QgsMapTool
except ImportError:  # unit tests without QGIS: the pure helpers above stay importable
    QgsMapTool = None  # type: ignore[assignment,misc]

if QgsMapTool is not None:
    class SimilarFeaturesTool(QgsMapTool):
        """Click a feature of the current vector layer: ``featureClicked(feature, extend)`` (Ctrl extends)."""

        featureClicked = pyqtSignal(object, bool)

        def __init__(self, canvas: Any, layer_getter: Any) -> None:
            super().__init__(canvas)
            self._layer_getter = layer_getter
            try:
                self.setCursor(Qt.CursorShape.CrossCursor)
            except Exception:
                pass

        def canvasReleaseEvent(self, event: Any) -> None:  # noqa: N802 - Qt override
            if event.button() != Qt.MouseButton.LeftButton:
                return
            layer = self._layer_getter()
            if layer is None:
                return
            feature = feature_at(self.canvas(), layer, event.pos())
            if feature is None:
                return
            extend = bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier)
            self.featureClicked.emit(feature, extend)
