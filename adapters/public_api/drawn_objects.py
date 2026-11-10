# -*- coding: utf-8 -*-
"""Objects on a raster, for the agent and for automation: those drawn in the dock, and SAM run on guide features.

Main thread only, plain dicts out. The objects of the dock are read, never changed. SAM adds a
layer of its own to the project and changes no other layer.
"""
from __future__ import annotations

import logging
import math
import statistics
import time
from typing import Any, Dict, List, Mapping, Optional, Sequence

from ...core.domain.layer_kind import LayerKind
from .operations import layer_kind, resolve_layer, running

logger = logging.getLogger('FilterMate.DrawnObjects')

MAX_DRAWN_ROWS = 20
DEFAULT_GUIDE_FEATURES = 50
MAX_GUIDE_FEATURES = 200
# SAM holds the main thread of QGIS while it draws (about 2 s for each window of 1024 pixels on a CPU). Past
# this many seconds the run stops between two windows and answers with what it drew. With the window under way
# (up to 10 s) and the first load of the model, it stays under the 45 s an MCP client waits by default
# (filtermate_api/mcp/settings.py).
BUDGET_SECONDS = 20.0
# Under this overlap with its footprint, an object is one to look at (docs/SEGMENTATION.md).
LOW_OVERLAP = 0.5
SAM_NOT_INSTALLED = ("SAM is not installed. The user installs it from the FilterMate dock: PIPETTE group of a "
                     "raster, Clicked object, then accept the installation (about 160 MB). It cannot be installed "
                     "from here: tell the user, and do not call this again until they say it is done.")
OUTLINE = {'color': '0,0,0,0', 'outline_color': '232,89,12,255', 'outline_width': '0.6'}


def summarize_drawn(objects: Mapping[str, Sequence[str]]) -> List[Dict[str, Any]]:
    """What ``map_context`` says of the objects drawn in the dock: one row per raster still in the project.

    Args:
        objects: WKT polygons in the CRS of their raster, by layer id
            (``CoverageModeController.drawn_objects``).

    Returns:
        ``[{layer_id, name, crs_authid, count, area_m2, extent_wkt}]``: how many objects, their total
        area on the ground (None when unknown) and their bounding box in the CRS of the raster.
        The polygons themselves are not returned: ``dock_objects`` of a raster selection uses them.
    """
    from qgis.core import QgsGeometry, QgsProject, QgsRectangle
    from ..qgis.coverage_layers.segmentation import area_measure
    project = QgsProject.instance()
    rows: List[Dict[str, Any]] = []
    for layer_id, wkts in objects.items():
        layer = project.mapLayer(layer_id)
        if layer is None or not layer.isValid() or layer_kind(layer) is not LayerKind.RASTER:
            continue
        try:
            measure = area_measure(layer.crs())  # once per raster: map_context runs before each request
        except Exception as exc:  # noqa: BLE001 - the objects are told without their area
            logger.debug(f"objects of {layer.name()} not measured: {exc}")
            measure = None
        count, total, measured = 0, 0.0, measure is not None
        box: Optional[List[float]] = None
        for wkt in wkts:
            geometry = QgsGeometry.fromWkt(wkt)
            if geometry is None or geometry.isNull() or geometry.isEmpty():
                continue
            count += 1
            area = measure(geometry) if measure is not None else None
            if area is None or not math.isfinite(area):
                measured = False
            else:
                total += area
            rect = geometry.boundingBox()
            sides = [rect.xMinimum(), rect.yMinimum(), rect.xMaximum(), rect.yMaximum()]
            box = sides if box is None else [min(box[0], sides[0]), min(box[1], sides[1]),
                                             max(box[2], sides[2]), max(box[3], sides[3])]
        if not count or box is None:
            continue
        crs = layer.crs()
        rows.append({'layer_id': layer.id(), 'name': layer.name(), 'crs_authid': crs.authid() if crs is not None else '',
                     'count': count, 'area_m2': round(total, 1) if measured else None,
                     'extent_wkt': QgsRectangle(*box).asWktPolygon()})
    return rows[:MAX_DRAWN_ROWS]


def _layer_of_kind(reference: str, kind: LayerKind):
    """Project layer for an id or a name; among layers of one name, the one of ``kind``. None when absent."""
    from qgis.core import QgsProject
    layer = resolve_layer(reference)
    if layer is None or layer.id() == reference or layer_kind(layer) is kind:
        return layer
    same_kind = [item for item in QgsProject.instance().mapLayersByName(reference) if layer_kind(item) is kind]
    return same_kind[0] if same_kind else layer


def _number(value: Any) -> Optional[float]:
    """A field value as a finite float; None for NULL and anything else."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _budget_feedback(seconds: float):
    """A feedback that cancels itself once ``seconds`` are spent, and keeps the errors it is told."""
    from qgis.core import QgsProcessingFeedback

    class BudgetFeedback(QgsProcessingFeedback):
        def __init__(self) -> None:
            super().__init__()
            self._deadline = time.monotonic() + seconds
            self.timed_out = False
            self.errors: List[str] = []

        def isCanceled(self) -> bool:  # noqa: N802 - Qt name; read by the algorithm between two windows
            if not self.timed_out and time.monotonic() > self._deadline:
                self.timed_out = True
            return self.timed_out or super().isCanceled()

        def reportError(self, error, fatalError=False):  # noqa: N802,N803 - Qt names
            self.errors.append(str(error))
            super().reportError(error, fatalError)

    return BudgetFeedback()


def _guide_count(guide, selected: bool) -> int:
    """Features the guide gives; -1 for a web service, which is not asked (one more request, out of reach of Stop)."""
    if selected:
        return int(guide.selectedFeatureCount())
    from ..qgis.source_capability_probe import capability_for_layer
    try:
        capability = capability_for_layer(guide)
    except Exception:  # noqa: BLE001 - an unknown source is counted as any other
        capability = None
    if capability is not None and capability.is_remote_service:
        return -1
    count = guide.featureCount()
    return int(count) if isinstance(count, int) and count >= 0 else -1


def segment_objects(raster: str, guide_layer: str, selected_only: bool = True, limit: int = DEFAULT_GUIDE_FEATURES,
                    name: str = '') -> Dict[str, Any]:
    """SAM draws on ``raster`` the object each guide feature points at, as a new polygon layer of the project.

    ``filtermate:segment_from_features`` run here, on the main thread as the other tools: a point is
    a click on the object, a polygon gives its bounding box and a point inside it. The layer added is
    held in memory, in the CRS of the raster, with the attributes of the guide, ``sam_score`` and,
    for a polygon guide, ``sam_iou`` (overlap of the footprint with the drawn object).

    Args:
        raster: Raster layer id or name, drawn as on the map (a web service too).
        guide_layer: Vector layer id or name, points or polygons.
        selected_only: Use the selected features of the guide; with none selected, the features it shows.
        limit: The most guide features taken in one call (at most :data:`MAX_GUIDE_FEATURES`).
        name: Name of the layer added; by default the name of the guide followed by ``(SAM)``.

    Returns:
        ``{layer, guide_features, drawn, without_object, stopped_early, seconds, sam_score, sam_iou}``:
        the summary of the layer added and what was drawn. ``stopped_early`` is True when the time
        allowed (:data:`BUDGET_SECONDS`) ran out before every window was drawn; ``without_object`` then
        also counts the features never tried.

    Raises:
        ValueError: A layer that does not fit, too many guide features, SAM not installed, nothing drawn.
    """
    from qgis.core import QgsFillSymbol, QgsProcessingContext, QgsProcessingFeatureSourceDefinition, QgsProject
    from ...processing.algorithms.segmentation_algorithm import SegmentFromFeaturesAlgorithm
    from ..qgis.coverage_layers.segmentation import _geometry_kinds, model_state
    from .project_control import _summary

    project = QgsProject.instance()
    image = _layer_of_kind(raster, LayerKind.RASTER)
    if image is None:
        raise ValueError(f"raster layer {raster!r} not found")
    if layer_kind(image) is not LayerKind.RASTER:
        raise ValueError(f"'{image.name()}' is not a raster layer")
    guide = _layer_of_kind(guide_layer, LayerKind.VECTOR)
    if guide is None:
        raise ValueError(f"guide layer {guide_layer!r} not found")
    if layer_kind(guide) is not LayerKind.VECTOR:
        raise ValueError(f"'{guide.name()}' is not a vector layer")
    if not image.isValid() or not guide.isValid():
        raise ValueError("a layer is not available: its data source could not be opened")
    if guide.geometryType() not in _geometry_kinds():
        raise ValueError(f"'{guide.name()}' holds neither points nor polygons: a line frames no object")
    image_name, guide_name = image.name(), guide.name()  # the layers may be gone once the run is over
    limit = max(1, min(int(limit), MAX_GUIDE_FEATURES))
    selected = bool(selected_only) and guide.selectedFeatureCount() > 0
    count = _guide_count(guide, selected)
    if count < 0:
        raise ValueError(f"the features of '{guide_name}' cannot be counted (a web service): select the ones meant "
                         "with select_features first")
    if count == 0 and (selected or guide.providerType() != 'postgres'):  # PostGIS may only estimate its count
        raise ValueError(f"'{guide_name}' gives no guide feature: its selection or its filter keeps nothing")
    if count > limit:
        raise ValueError(
            f"'{guide_name}' gives {count} guide features and at most {limit} are taken in one call (limit, up to "
            f"{MAX_GUIDE_FEATURES}): select fewer with select_features, for example those of the visible map")
    if not model_state().ready:
        raise ValueError(SAM_NOT_INSTALLED)

    algorithm = SegmentFromFeaturesAlgorithm().create()
    context = QgsProcessingContext()
    context.setProject(project)
    feedback = _budget_feedback(BUDGET_SECONDS)
    begin = time.monotonic()
    # Qt serves events while the windows are drawn: a REST call queued meanwhile is refused, not run nested.
    with running("segment_objects"):
        results, ok = algorithm.run({
            SegmentFromFeaturesAlgorithm.RASTER: image,
            SegmentFromFeaturesAlgorithm.FEATURES: QgsProcessingFeatureSourceDefinition(guide.id(), selected, limit),
            SegmentFromFeaturesAlgorithm.OUTPUT: 'memory:',
        }, context, feedback)
    seconds = time.monotonic() - begin
    # The algorithm asks once more after its last window: past the time then, nothing was stopped.
    stopped_early = bool(feedback.timed_out) and feedback.progress() < 100.0
    if feedback.errors:
        logger.warning("segment_objects on %s: %s", image_name, " | ".join(feedback.errors))
    output = (results or {}).get(SegmentFromFeaturesAlgorithm.OUTPUT) if ok else None
    layer = context.takeResultLayer(output) if output else None
    drawn = int(layer.featureCount()) if layer is not None else 0
    if drawn <= 0:
        if stopped_early:
            reason = f"the {BUDGET_SECONDS:.0f} s allowed ran out before an object was drawn: give fewer features"
        elif feedback.errors:
            reason = algorithm.told_reason(feedback.errors)  # its own words: the detail stays in the log
        else:
            reason = "SAM found no object under these features"
        raise ValueError(f"nothing was drawn on '{image_name}': {reason}")

    scores, overlaps = [], []
    score_index = layer.fields().lookupField(SegmentFromFeaturesAlgorithm.SCORE_FIELD)
    overlap_index = layer.fields().lookupField(SegmentFromFeaturesAlgorithm.IOU_FIELD)
    for feature in layer.getFeatures():
        values = feature.attributes()
        score = _number(values[score_index]) if score_index >= 0 else None
        overlap = _number(values[overlap_index]) if overlap_index >= 0 else None
        if score is not None:
            scores.append(score)
        if overlap is not None:
            overlaps.append(overlap)

    layer.setName((name or '').strip()[:200] or f"{guide_name} (SAM)")
    try:
        layer.renderer().setSymbol(QgsFillSymbol.createSimple(dict(OUTLINE)))  # outlined: the raster stays visible
    except (AttributeError, RuntimeError) as exc:
        logger.debug(f"objects layer left with its default style: {exc}")
    project.addMapLayer(layer)
    answer: Dict[str, Any] = {
        'layer': _summary(layer), 'guide_features': count, 'drawn': drawn,
        'without_object': max(count - drawn, 0), 'stopped_early': stopped_early, 'seconds': round(seconds, 1),
    }
    if scores:
        answer['sam_score'] = {'median': round(statistics.median(scores), 3), 'minimum': round(min(scores), 3)}
    if overlaps:
        answer['sam_iou'] = {'median': round(statistics.median(overlaps), 3), 'minimum': round(min(overlaps), 3),
                             'below_half': sum(1 for value in overlaps if value < LOW_OVERLAP)}
    return answer
