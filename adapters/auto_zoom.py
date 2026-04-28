"""
Auto-zoom helper.

Single entry point used by both the normal filter completion path
(``FilterResultHandler._handle_auto_zoom``) and the favorites apply path
(``FavoritesController._apply_favorite_subsets_directly``) so both flows
share the same global flag, per-layer ``is_tracking`` override, and union
extent computation.

Resolution rules:
- If the global flag ``APP.OPTIONS.EXPLORATION.auto_zoom_on_filter`` is true,
  zoom to the union extent of all provided layers.
- Otherwise, zoom only to layers whose ``PROJECT_LAYERS[layer_id].exploring.is_tracking``
  is true (per-layer override).
- If neither applies, just refresh the canvas.
"""

from typing import Iterable, Optional, Mapping, Any

from qgis.core import QgsRectangle, QgsVectorLayer
from qgis.utils import iface as default_iface

from ..infrastructure.logging import get_app_logger

logger = get_app_logger()


def _read_global_auto_zoom_flag() -> bool:
    try:
        from ..config.config import ENV_VARS, _get_option_value
        cfg = (
            ENV_VARS.get('CONFIG_DATA', {})
            .get('APP', {})
            .get('OPTIONS', {})
            .get('EXPLORATION', {})
        )
        return bool(_get_option_value(cfg.get('auto_zoom_on_filter'), True))
    except (ImportError, AttributeError, TypeError):
        return True


def _is_tracking(layer_id: str, project_layers: Mapping[str, Any]) -> bool:
    if not layer_id or not project_layers:
        return False
    props = project_layers.get(layer_id)
    if not isinstance(props, Mapping):
        return False
    exploring = props.get("exploring")
    if not isinstance(exploring, Mapping):
        return False
    return bool(exploring.get("is_tracking", False))


def _layer_extent(layer: QgsVectorLayer, dockwidget: Any = None) -> Optional[QgsRectangle]:
    try:
        layer.updateExtents()
    except (RuntimeError, AttributeError):
        return None

    if dockwidget is not None and hasattr(dockwidget, 'get_filtered_layer_extent'):
        try:
            ext = dockwidget.get_filtered_layer_extent(layer)
            if ext is not None and not ext.isEmpty():
                return ext
        except (RuntimeError, AttributeError, TypeError):
            pass

    try:
        ext = layer.extent()
        return ext if ext is not None and not ext.isEmpty() else None
    except (RuntimeError, AttributeError):
        return None


def auto_zoom_to_filtered(
    layers: Iterable[QgsVectorLayer],
    project_layers: Optional[Mapping[str, Any]] = None,
    *,
    dockwidget: Any = None,
    iface_obj: Any = None,
) -> bool:
    """Zoom the map canvas to the union extent of filtered layers.

    Args:
        layers: All layers whose subset was just (re)applied — typically the
            source layer plus every cascade target layer.
        project_layers: ``PROJECT_LAYERS`` mapping (layer_id -> properties)
            used to honour the per-layer ``is_tracking`` override when the
            global flag is off.
        dockwidget: Optional dockwidget — used to call
            ``get_filtered_layer_extent`` for a more accurate (feature-bbox)
            extent when feasible.
        iface_obj: Optional iface override (tests).

    Returns:
        True when a zoom was performed, False when only a refresh was issued
        (or nothing at all).
    """
    iface_obj = iface_obj or default_iface
    if iface_obj is None:
        return False

    canvas = iface_obj.mapCanvas() if hasattr(iface_obj, 'mapCanvas') else None
    if canvas is None:
        return False

    valid_layers = [l for l in layers if l is not None]
    if not valid_layers:
        canvas.refresh()
        return False

    global_enabled = _read_global_auto_zoom_flag()
    project_layers = project_layers or {}

    extents = []
    for layer in valid_layers:
        try:
            layer_id = layer.id()
        except (RuntimeError, AttributeError):
            continue

        if global_enabled or _is_tracking(layer_id, project_layers):
            ext = _layer_extent(layer, dockwidget)
            if ext is not None:
                extents.append(ext)

    if not extents:
        canvas.refresh()
        return False

    union = QgsRectangle(extents[0])
    for ext in extents[1:]:
        union.combineExtentWith(ext)

    if union.isEmpty():
        canvas.refresh()
        return False

    canvas.zoomToFeatureExtent(union)
    logger.debug(
        f"Auto-zoom: combined extent of {len(extents)} layer(s) "
        f"(global={global_enabled})"
    )
    return True
