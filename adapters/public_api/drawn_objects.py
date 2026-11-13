# -*- coding: utf-8 -*-
"""Objects on a raster, for the agent and for automation: those drawn in the dock, SAM run on guide features,
and the objects that look like an example.

Main thread only, plain dicts out. The objects of the dock are read, never changed. SAM adds a
layer of its own to the project and changes no other layer.
"""
from __future__ import annotations

import logging
import math
import statistics
import time
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

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
# Objects like an example, for the agent: only the places whose encoder features look like the example's (no colour,
# so no values of the raster and no panel are needed), with the setting chosen on 10 buildings of the 25 cm Cerdagne
# orthophoto and judged on 10 others (2026-11-11, scripts/sam_similar_candidates.py, "feature" variant): median
# precision 0.55, recall 0.20 there. About half of what it finds is right, a fifth of what is there is found.
SIMILAR_FEATURE_MIN = 0.7
SIMILAR_PER_WINDOW = 40
SIMILAR_APPEARANCE_MIN = 0.8
SIMILAR_RATIO = (0.5, 2.0)
# The area searched is cut in windows of 1024 pixels at the cell of the example; past this many it is refused.
MAX_SEARCH_WINDOWS = 64
# Windows overlap by twice this many pixels, and a place nearer than this to the edge of its window is left to the
# next window (unless the edge is the raster's): an object across an edge is drawn whole by one of them.
WINDOW_MARGIN_PIXELS = 32


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
    a temporary GeoPackage, as the outputs of ``run_algorithm`` (Redo of the turn opens it again), in
    the CRS of the raster, with the attributes of the guide, ``sam_score`` and,
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
    from qgis.core import (
        QgsFillSymbol, QgsProcessingContext, QgsProcessingFeatureSourceDefinition, QgsProcessingUtils, QgsProject,
        QgsVectorLayer,
    )
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
    # A file, as the outputs of run_algorithm: Redo of the turn opens it again (a memory layer would come back empty).
    path = QgsProcessingUtils.generateTempFilename("sam_objects.gpkg")
    begin = time.monotonic()
    # Qt serves events while the windows are drawn: a REST call queued meanwhile is refused, not run nested.
    with running("segment_objects"):
        results, ok = algorithm.run({
            SegmentFromFeaturesAlgorithm.RASTER: image,
            SegmentFromFeaturesAlgorithm.FEATURES: QgsProcessingFeatureSourceDefinition(guide.id(), selected, limit),
            SegmentFromFeaturesAlgorithm.OUTPUT: path,
        }, context, feedback)
    seconds = time.monotonic() - begin
    # The algorithm asks once more after its last window: past the time then, nothing was stopped.
    stopped_early = bool(feedback.timed_out) and feedback.progress() < 100.0
    if feedback.errors:
        logger.warning("segment_objects on %s: %s", image_name, " | ".join(feedback.errors))
    output = (results or {}).get(SegmentFromFeaturesAlgorithm.OUTPUT) if ok else None
    title = (name or '').strip()[:200] or f"{guide_name} (SAM)"
    layer = QgsVectorLayer(output if isinstance(output, str) and output else path, title, 'ogr') if ok else None
    if layer is not None and not layer.isValid():
        layer = None
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


def _example_geometry(image, example_layer: str, example_wkt: str, example_crs: str):
    """The example as a geometry in the CRS of ``image``: one selected feature of a layer, or a WKT."""
    from qgis.core import QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsGeometry, QgsProject
    if example_wkt:
        geometry = QgsGeometry.fromWkt(example_wkt)
        if geometry is None or geometry.isNull() or geometry.isEmpty():
            raise ValueError("the example could not be read")
        source = QgsCoordinateReferenceSystem(example_crs) if example_crs else image.crs()
        if not source.isValid():
            raise ValueError(f"unknown CRS {example_crs!r}")
    elif example_layer:
        layer = _layer_of_kind(example_layer, LayerKind.VECTOR)
        if layer is None or layer_kind(layer) is not LayerKind.VECTOR:
            raise ValueError(f"example layer {example_layer!r} not found among the vector layers")
        selected = list(layer.selectedFeatures())
        if len(selected) != 1:
            raise ValueError(f"'{layer.name()}' has {len(selected)} features selected: select exactly the one example "
                             "with select_features first")
        geometry, source = QgsGeometry(selected[0].geometry()), layer.crs()
    else:
        raise ValueError("give an example: a layer with the one example selected, or an object drawn in the dock")
    if source != image.crs():
        geometry.transform(QgsCoordinateTransform(source, image.crs(), QgsProject.instance()))
    return geometry


def _search_area(image, extent_wkt: str, extent_crs: str, fallback):
    """The rectangle searched, in the CRS of ``image`` and inside it: the extent given, the visible map, or ``fallback``."""
    from qgis.core import QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsGeometry, QgsProject
    area = None
    if extent_wkt:
        geometry = QgsGeometry.fromWkt(extent_wkt)
        if geometry is None or geometry.isNull() or geometry.isEmpty():
            raise ValueError("the extent could not be read")
        source = QgsCoordinateReferenceSystem(extent_crs) if extent_crs else image.crs()
        if not source.isValid():
            raise ValueError(f"unknown CRS {extent_crs!r}")
        area = QgsCoordinateTransform(source, image.crs(), QgsProject.instance()).transformBoundingBox(geometry.boundingBox())
    else:
        try:
            from qgis.utils import iface
            canvas = iface.mapCanvas() if iface is not None else None
        except ImportError:
            canvas = None
        if canvas is not None:
            area = QgsCoordinateTransform(canvas.mapSettings().destinationCrs(), image.crs(), QgsProject.instance()) \
                .transformBoundingBox(canvas.extent())
    if area is None:
        area = fallback
    area = area.intersect(image.extent())
    if area.isEmpty():
        raise ValueError("the area searched does not cross the raster")
    return area


def search_windows(first, area, raster, cell: float, size: int) -> list:
    """Windows of ``size`` pixels of ``cell`` covering ``area``, ``first`` (the example's) first, then nearest first.

    They overlap by twice :data:`WINDOW_MARGIN_PIXELS`; a window equal to ``first`` is not repeated.
    ``raster``: ``(x_min, y_min, x_max, y_max)``.
    """
    from ..qgis.coverage_layers.segmentation import window_at
    side, margin = cell * size, WINDOW_MARGIN_PIXELS * cell
    step = side - 2 * margin

    def centres(low: float, high: float) -> List[float]:
        values, centre = [], low - margin + side / 2.0
        while True:
            values.append(centre)
            if centre + side / 2.0 - margin >= high:
                return values
            centre += step
    windows, seen = [first], {(first.x_min, first.y_max)}
    for y in centres(area.yMinimum(), area.yMaximum()):
        for x in centres(area.xMinimum(), area.xMaximum()):
            window = window_at(x, y, raster, cell, size)
            if (window.x_min, window.y_max) not in seen:
                seen.add((window.x_min, window.y_max))
                windows.append(window)
    fx, fy = first.x_min + first.side / 2.0, first.y_max - first.side / 2.0
    return [first] + sorted(windows[1:], key=lambda w: (w.x_min + w.side / 2.0 - fx) ** 2 + (w.y_max - w.side / 2.0 - fy) ** 2)


def _inside_window(window, x: float, y: float, raster) -> bool:
    """Farther than :data:`WINDOW_MARGIN_PIXELS` from the edges of ``window``, but those on the edge of the raster."""
    from ..qgis.coverage_layers.segmentation import well_inside
    return well_inside(window, x, y, raster, WINDOW_MARGIN_PIXELS)


def _write_objects(objects, crs, path: str, area) -> None:
    """The objects as a GeoPackage at ``path``: one multipolygon each, numbered, with its appearance and area."""
    from qgis.core import QgsFeature, QgsProject, QgsVectorFileWriter, QgsVectorLayer
    memory = QgsVectorLayer('MultiPolygon?field=object:integer&field=appearance:double&field=area_m2:double', 'objects',
                            'memory')
    memory.setCrs(crs)
    features = []
    for index, (geometry, appearance) in enumerate(objects, start=1):
        geometry.convertToMultiType()
        feature = QgsFeature(memory.fields())
        measured = area(geometry)
        feature.setAttributes([index, None if appearance is None else round(appearance, 4),
                               None if measured is None else round(measured, 2)])
        feature.setGeometry(geometry)
        features.append(feature)
    memory.dataProvider().addFeatures(features)
    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName = 'GPKG'
    options.layerName = 'objects'
    result = QgsVectorFileWriter.writeAsVectorFormatV3(memory, path, QgsProject.instance().transformContext(), options)
    if result[0] != QgsVectorFileWriter.WriterError.NoError:
        raise RuntimeError(f"the objects could not be written: {result[-1]}")


def _rounded(value: Optional[float]) -> Optional[float]:
    return None if value is None or not math.isfinite(value) else round(value, 1)


def similar_objects(raster: str, example_layer: str = '', use_dock_object: bool = False,
                    dock_objects: Optional[Mapping[str, Sequence[str]]] = None, example_wkt: str = '',
                    example_crs: str = '', extent_wkt: str = '', extent_crs: str = '', same_shape: bool = True,
                    name: str = '') -> Dict[str, Any]:
    """SAM finds on ``raster`` the objects that look like an example, as a new polygon layer of the project.

    The examples (one selected feature of ``example_layer``; with ``use_dock_object`` every object
    drawn on this raster in the dock, from ``dock_objects`` by layer id; or ``example_wkt``) are drawn
    by SAM; then, window by window over the area searched (the extent given, or the visible map), the
    places whose encoder features look like one of them are drawn, and those of an area within
    :data:`SIMILAR_RATIO` of the examples' (and of their shape with ``same_shape``) that look like one
    of them are kept: with several examples, resembling the nearest of them is what counts, in the
    candidates as in the appearance. One drawn object taken alone decided everything before
    2026-11-13: the last one drawn, a small pool of a 25 cm orthophoto (two to four cells of the
    coarsest feature map), left almost no place over :data:`SIMILAR_FEATURE_MIN` anywhere and the
    search answered nothing (``examined`` 0 to 2 over the whole orthophoto); with the six pools the
    user had drawn as examples together, the held-out pools are found at the same thresholds. The
    layer is a temporary GeoPackage with ``appearance`` (cosine of the features with the nearest
    example's, 0 to 1) and ``area_m2``. About half of what it finds is right (see
    :data:`SIMILAR_FEATURE_MIN`).

    Returns:
        ``{layer, objects, examined, windows, windows_planned, stopped_early, seconds, examples,
        appearance}``; ``layer`` is None when nothing was found (no layer is added then).

    Raises:
        ValueError: A layer or an example that does not fit, an area too large, SAM not installed.
    """
    import numpy as np
    from qgis.core import QgsFillSymbol, QgsGeometry, QgsMapSettings, QgsPointXY, QgsProcessingUtils, QgsProject, \
        QgsVectorLayer
    from qgis.PyQt.QtGui import QColor
    from ...processing.algorithms.segmentation_algorithm import _metres_to_units
    from ..qgis.coverage_layers import segmentation as seg
    from ..qgis.coverage_layers.geometry_tools import compactness
    from .project_control import _summary

    project = QgsProject.instance()
    image = _layer_of_kind(raster, LayerKind.RASTER)
    if image is None:
        raise ValueError(f"raster layer {raster!r} not found")
    if layer_kind(image) is not LayerKind.RASTER or not image.isValid():
        raise ValueError(f"'{image.name()}' is not a raster layer that can be read")
    image_name = image.name()
    if use_dock_object:
        if example_layer:
            raise ValueError("give either an example layer or use_dock_object, not both")
        drawn_here = [wkt for wkt in ((dock_objects or {}).get(image.id()) or ()) if wkt]
        if not drawn_here:
            raise ValueError(f"no object is drawn on '{image_name}' in the FilterMate dock: map_context lists the "
                             "rasters that have some (drawn_objects)")
        geometries = [_example_geometry(image, '', wkt, '') for wkt in drawn_here]  # in the CRS of the raster
    else:
        geometries = [_example_geometry(image, example_layer, example_wkt, example_crs)]
    prompts = [prompt for prompt in (seg.prompt_of(geometry) for geometry in geometries) if prompt is not None]
    if not prompts:
        raise ValueError("the example is neither a point nor a polygon")
    extent = image.extent()
    raster_bounds = (extent.xMinimum(), extent.yMinimum(), extent.xMaximum(), extent.yMaximum())
    prompts = [prompt for prompt in prompts if extent.contains(QgsPointXY(prompt.x, prompt.y))]
    if not prompts:
        raise ValueError(f"the example does not lie on '{image_name}'")
    if not seg.model_state().ready:
        raise ValueError(SAM_NOT_INSTALLED)
    model = seg.find_provider()
    if model is None:
        raise ValueError(SAM_NOT_INSTALLED)
    size = int(model.input_size)
    cells = [side / count for side, count in ((extent.width(), image.width()), (extent.height(), image.height()))
             if count > 0 and side > 0]
    native = min(cells) if len(cells) == 2 else 0.0
    planned = seg.plan_prompts(prompts, raster_bounds, native, size,
                               seg.PROMPT_POINT_VIEW_METRES * _metres_to_units(image.crs()))
    first = planned[0][0]
    area = _search_area(image, extent_wkt, extent_crs, first.rectangle())
    windows = search_windows(first, area, raster_bounds, first.cell, size)
    if len(windows) > MAX_SEARCH_WINDOWS:
        raise ValueError(f"the area searched needs {len(windows)} windows of {first.side:.0f} m at the scale of the "
                         f"example, at most {MAX_SEARCH_WINDOWS}: give a smaller extent or zoom in")

    settings = QgsMapSettings()
    settings.setDestinationCrs(image.crs())
    settings.setTransformContext(project.transformContext())
    settings.setBackgroundColor(QColor(0, 0, 0, 255))
    crs_wkt = image.crs().toWkt()
    bounds = QgsGeometry.fromRect(extent)
    begin = time.monotonic()
    found, examined, done, stopped_early = [], 0, 0, False
    # Qt serves events while the windows are drawn: a REST call queued meanwhile is refused, not run nested.
    with running("similar_objects"):
        embeddings: Dict[Tuple[float, float, float, int], Any] = {}

        def embedded(window):
            key = (window.x_min, window.y_max, window.cell, window.size)
            if key not in embeddings:
                embeddings[key] = model.embed(seg.image_to_rgb(seg.render_window(settings, image, window, lambda: False)))
            return embeddings[key]

        references = []  # (geometry as SAM drew it, its pooled features, its score), one per example drawn
        for window, indexes in planned:
            embedding = embedded(window)
            for index in indexes:
                reference, score, mask = seg.prompt_object_mask(model, embedding, window, prompts[index], crs_wkt)
                reference = reference.intersection(bounds) if reference is not None else None
                features = seg.pooled_features(embedding, mask)
                if reference is None or reference.isEmpty() or features is None:
                    continue
                references.append((reference, features, float(score)))
        if not references:
            raise ValueError("SAM drew no object under the example")
        reference_areas = [reference.area() for reference, _features, _score in references]
        reference_shapes = [compactness(reference) for reference, _features, _score in references]
        kept = [reference for reference, _features, _score in references]
        for index, window in enumerate(windows):
            if index and time.monotonic() - begin > BUDGET_SECONDS:
                stopped_early = True
                break
            embedding = embedded(window)
            done += 1
            coarse = seg.coarse_features(embedding)
            if coarse is None:
                continue
            step = window.size / coarse.shape[1]
            peaks: Dict[Tuple[int, int], float] = {}  # (row, column) -> its best cosine over the examples
            for _reference, features, _score in references:
                for cosine, row, column in seg.similarity_peaks(coarse, features, SIMILAR_FEATURE_MIN):
                    if cosine > peaks.get((row, column), -1.0):
                        peaks[(row, column)] = cosine
            candidates = []
            for (row, column), _cosine in sorted(peaks.items(), key=lambda item: (-item[1], item[0])):
                x, y = window.to_map((column + 0.5) * step, (row + 0.5) * step)
                if area.contains(QgsPointXY(x, y)) and _inside_window(window, x, y, raster_bounds) \
                        and not any(reference.contains(QgsGeometry.fromPointXY(QgsPointXY(x, y)))
                                    for reference, _features, _score in references):
                    candidates.append((x, y))
                    if len(candidates) >= SIMILAR_PER_WINDOW:
                        break
            for x, y in candidates:
                where = QgsGeometry.fromPointXY(QgsPointXY(x, y))
                if any(other.contains(where) for other in kept):
                    continue
                examined += 1
                drawn, drawn_mask = seg.point_object(model, embedding, window, x, y, crs_wkt)
                drawn = drawn.intersection(bounds) if drawn is not None and not drawn.isEmpty() else None
                if drawn is None or drawn.isEmpty() or any(seg.overlap(drawn, other) >= seg.SAME_OBJECT_IOU
                                                           for other in kept):
                    continue
                if not seg.is_similar(drawn, reference_areas, reference_shapes, SIMILAR_RATIO, bool(same_shape)):
                    continue
                kept.append(drawn)
                pooled = seg.pooled_features(embedding, drawn_mask)
                appearance = max((float(np.dot(pooled, features)) for _reference, features, _score in references),
                                 default=None) if pooled is not None else None
                if appearance is None or appearance >= SIMILAR_APPEARANCE_MIN:
                    found.append((drawn, appearance))
    seconds = time.monotonic() - begin
    measure = seg.area_measure(image.crs())
    scores = [score for _reference, _features, score in references]
    measured = [value for reference, _features, _score in references
                if (value := _rounded(measure(reference))) is not None]
    answer: Dict[str, Any] = {
        'layer': None, 'objects': len(found), 'examined': examined, 'windows': done, 'windows_planned': len(windows),
        'stopped_early': stopped_early, 'seconds': round(seconds, 1),
        'examples': {'count': len(references),
                     'sam_score': {'median': round(statistics.median(scores), 3), 'minimum': round(min(scores), 3)},
                     'area_m2': {'minimum': min(measured), 'maximum': max(measured)} if measured else {}},
    }
    if not found:
        return answer
    path = QgsProcessingUtils.generateTempFilename("similar_objects.gpkg")
    _write_objects(found, image.crs(), path, measure)
    layer = QgsVectorLayer(path, (name or '').strip()[:200] or f"{image_name} (similar objects)", 'ogr')
    if not layer.isValid():
        raise RuntimeError("the objects found could not be opened again")
    try:
        layer.renderer().setSymbol(QgsFillSymbol.createSimple(dict(OUTLINE)))  # outlined: the raster stays visible
    except (AttributeError, RuntimeError) as exc:
        logger.debug(f"similar objects left with their default style: {exc}")
    project.addMapLayer(layer)
    answer['layer'] = _summary(layer)
    appearances = [value for _geometry, value in found if value is not None]
    if appearances:
        answer['appearance'] = {'median': round(statistics.median(appearances), 3), 'minimum': round(min(appearances), 3)}
    return answer
