"""
``filtermate:segment_from_features`` - SAM draws on a raster the objects that the features of a layer point at.

Each feature is a prompt: a point is a click on the object, a polygon gives its bounding box and a point
inside it (a building footprint, a parcel, a field). The raster is drawn as on the map, window by window,
and SAM 2.1 tiny (installed from the PIPETTE group of the dock) draws one polygon per feature, in the CRS
of the raster, with the attributes of the feature, the score of SAM and, for a polygon, its overlap
with the drawn object. Unlike the other FilterMate algorithms, it runs in the background: it changes
no layer of the project.

Author: FilterMate Team
"""

import time

from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterRasterLayer,
)

from .common import FilterMateAlgorithm


def _double_field(name):
    """A double field: ``QMetaType`` (QGIS 3.38+), ``QVariant`` before."""
    from qgis.core import QgsField
    try:
        from qgis.PyQt.QtCore import QMetaType
        return QgsField(name, QMetaType.Type.Double)
    except (ImportError, AttributeError, TypeError):
        from qgis.PyQt.QtCore import QVariant
        return QgsField(name, QVariant.Double)


def _multipolygon():
    """``Qgis.WkbType`` (3.30+), ``QgsWkbTypes.Type`` before."""
    from qgis.core import Qgis, QgsWkbTypes
    kinds = getattr(Qgis, 'WkbType', None)
    return kinds.MultiPolygon if kinds is not None else QgsWkbTypes.Type.MultiPolygon


class SegmentFromFeaturesAlgorithm(FilterMateAlgorithm):
    """One polygon drawn by SAM per point or polygon of a guide layer."""

    RASTER = "RASTER"
    FEATURES = "FEATURES"
    OUTPUT = "OUTPUT"
    SCORE_FIELD = "sam_score"
    IOU_FIELD = "sam_iou"

    def flags(self):
        """Nothing of the project is changed: it may run in the background, the dock stays usable."""
        return QgsProcessingAlgorithm.flags(self)

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterRasterLayer(self.RASTER, self.tr("Raster to draw on (e.g. an orthophoto)")))
        self.addParameter(QgsProcessingParameterFeatureSource(
            self.FEATURES, self.tr("Guide features (points or polygons)"),
            [QgsProcessing.SourceType.TypeVectorPoint, QgsProcessing.SourceType.TypeVectorPolygon]))
        self.addParameter(QgsProcessingParameterFeatureSink(
            self.OUTPUT, self.tr("Objects drawn by SAM"), QgsProcessing.SourceType.TypeVectorPolygon))

    def prepareAlgorithm(self, parameters, context, feedback):
        """What the background needs of the raster (its source, CRS and how it is drawn) and the model.

        From the toolbox it runs on the main thread; in a model, on the thread of the model.
        """
        from ...adapters.qgis.coverage_layers.segmentation import find_provider, model_state, raster_look
        layer = self.parameterAsRasterLayer(parameters, self.RASTER, context)
        if layer is None or not layer.isValid():
            raise QgsProcessingException(self.tr("The raster cannot be read"))
        state = model_state()
        model = find_provider() if state.ready else None
        if model is None:
            raise QgsProcessingException(self.tr(
                "SAM is not installed: choose Clicked object in the PIPETTE group of a raster in the FilterMate "
                "dock, and accept the installation"))
        extent = layer.extent()
        cells = [side / count for side, count in ((extent.width(), layer.width()), (extent.height(), layer.height()))
                 if count > 0 and side > 0]
        self._raster = dict(source=layer.source(), provider=layer.providerType(), crs=layer.crs(), look=raster_look(layer),
                            bounds=(extent.xMinimum(), extent.yMinimum(), extent.xMaximum(), extent.yMaximum()),
                            native=min(cells) if len(cells) == 2 else 0.0)
        self._model = model
        return True

    def processAlgorithm(self, parameters, context, feedback):
        from qgis.core import QgsCoordinateTransform, QgsFeature, QgsFeatureSink, QgsGeometry, QgsRectangle
        from ...adapters.qgis.coverage_layers import segmentation
        raster, model = self._raster, self._model
        source = self.parameterAsSource(parameters, self.FEATURES, context)
        if source is None:
            raise QgsProcessingException(self.tr("The guide features cannot be read"))
        fields, kept = _output_fields(source.fields(), (self.SCORE_FIELD, self.IOU_FIELD))
        sink, sink_id = self.parameterAsSink(parameters, self.OUTPUT, context, fields,
                                             _multipolygon(), raster['crs'])
        if sink is None:
            raise QgsProcessingException(self.invalidSinkError(parameters, self.OUTPUT))

        transform = QgsCoordinateTransform(source.sourceCrs(), raster['crs'], context.transformContext())
        bounds = QgsGeometry.fromRect(QgsRectangle(*raster['bounds']))
        point_view = segmentation.PROMPT_POINT_VIEW_METRES * _metres_to_units(raster['crs'])
        features, prompts, guides, skipped = [], [], [], 0
        for feature in source.getFeatures():
            if feedback.isCanceled():
                return {self.OUTPUT: sink_id}
            geometry = QgsGeometry(feature.geometry())
            try:
                geometry.transform(transform)
            except Exception:  # noqa: BLE001 - a feature that cannot be reprojected is skipped and counted
                skipped += 1
                continue
            prompt = segmentation.prompt_of(geometry)
            if prompt is None or not bounds.contains(QgsGeometry.fromPointXY(_point(prompt))):
                skipped += 1
                continue
            features.append(feature)
            prompts.append(prompt)
            guides.append(_guide(geometry, bounds) if prompt.box is not None else None)
        if not prompts:
            raise QgsProcessingException(self.tr("No point or polygon of the guide layer lies on the raster"))

        size = int(model.input_size)
        windows = segmentation.plan_prompts(prompts, raster['bounds'], raster['native'], size, point_view,
                                            is_canceled=feedback.isCanceled)
        if feedback.isCanceled():
            return {self.OUTPUT: sink_id}
        feedback.pushInfo(self.tr("{0} feature(s) on the raster, {1} window(s) to prepare").format(len(prompts), len(windows)))
        # A provider of its own, not a layer: no statistics of the whole coverage, the CRS of the project layer.
        pipe = segmentation.open_drawing(raster['source'], raster['provider'], raster['look'])
        if pipe is None:
            raise QgsProcessingException(self.tr("The raster cannot be read"))
        crs_wkt = raster['crs'].toWkt()
        drawn = [None] * len(prompts)
        begin, prepared, failed, error = time.time(), 0, 0, ''
        try:
            for window, members in windows:
                if feedback.isCanceled():
                    break
                try:  # one window that cannot be drawn (a tile of a service) loses its objects, not the run
                    image = segmentation.render_drawing(pipe, window, feedback.isCanceled)
                    if feedback.isCanceled():
                        break
                    embedding = model.embed(segmentation.image_to_rgb(image))
                    for index in members:
                        geometry, score = segmentation.prompt_object(model, embedding, window, prompts[index], crs_wkt)
                        geometry = _polygons(geometry.intersection(bounds)) if geometry is not None else None
                        if geometry is not None:  # past the raster the window is black: nothing was drawn there
                            drawn[index] = (geometry, score)
                except Exception as exc:  # noqa: BLE001 - told, counted, the next windows still run
                    failed += 1
                    error = str(exc) or type(exc).__name__
                    feedback.pushWarning(self.tr("A window could not be prepared: {0}").format(error))
                prepared += 1
                feedback.setProgress(100.0 * prepared / len(windows))
        finally:
            pipe = None  # noqa: F841 - its provider goes in the thread that made it
        if failed and failed == prepared:
            raise QgsProcessingException(self.tr("No window could be prepared: {0}").format(error))
        written = refused = 0
        for feature, guide, result in zip(features, guides, drawn):
            if result is None:
                continue
            geometry, score = result
            values = feature.attributes()
            out = QgsFeature(fields)
            out.setAttributes([values[i] for i in kept] + [round(score, 4),
                              round(segmentation.overlap(geometry, guide), 4) if guide is not None else None])
            out.setGeometry(geometry)
            if sink.addFeature(out, QgsFeatureSink.Flag.FastInsert):
                written += 1
            else:
                refused += 1
        if feedback.isCanceled():
            feedback.pushWarning(self.tr("Canceled: {0} of {1} window(s) prepared").format(prepared, len(windows)))
        prompted = {index for _window, members in windows[:prepared] for index in members}
        missing = sum(1 for index in prompted if drawn[index] is None)
        feedback.pushInfo(self.tr("{0} object(s) drawn, {1} feature(s) without an object, {2} skipped, in {3:.0f} s").format(
            written, missing + refused, skipped, time.time() - begin))
        return {self.OUTPUT: sink_id}

    def told_reason(self, errors):
        """Why nothing was drawn, as a caller may tell it further: this algorithm's own words, never a traceback.

        An unexpected exception reaches the feedback as a whole Python traceback, and a window that
        could not be drawn carries the text of its exception (the path of the model in the profile, for
        one): they stay in the log. ``errors`` are the messages the feedback was given, last one last.
        """
        own = {
            self.tr("No point or polygon of the guide layer lies on the raster"):
                "no point or polygon of the guide layer lies on the raster",
            self.tr("The raster cannot be read"): "the raster cannot be read",
            self.tr("The guide features cannot be read"): "the guide features cannot be read",
        }
        window = self.tr("No window could be prepared: {0}").split("{0}")[0].strip()
        for error in reversed(list(errors)):
            text = (error or "").strip()
            if text in own:
                return own[text]
            if window and text.startswith(window):
                return "no window of the raster could be drawn (the reason is in the FilterMate log)"
        return "SAM could not draw these objects (the reason is in the FilterMate log)"

    def name(self):
        return "segment_from_features"

    def displayName(self):
        return self.tr("Draw objects on a raster with SAM from points or polygons")

    def shortHelpString(self):
        return self.tr(
            "SAM 2.1 tiny draws on the raster the object each feature of the guide layer points at: a point is a "
            "click on the object, a polygon gives its bounding box and a point inside it. One polygon per feature, "
            "in the CRS of the raster, with the attributes of the feature, the score of SAM (sam_score) and, for a "
            "polygon, its overlap with the drawn object (sam_iou, from 0 to 1).\n\n"
            "Examples: building footprints redrawn on a recent orthophoto (a low sam_iou flags a building that "
            "changed); points of trees or ponds turned into outlines.\n\n"
            "The raster is drawn as in the map, with its style. SAM is installed once from the PIPETTE group of the "
            "FilterMate dock; it runs on the CPU, a few seconds for each window of 1024 pixels.")


def _point(prompt):
    from qgis.core import QgsPointXY
    return QgsPointXY(prompt.x, prompt.y)


def _output_fields(source_fields, added):
    """The fields of the source but those named like ``added`` (any case), then ``added`` as doubles.

    Returns:
        ``(fields, indexes of the source fields kept)``: a source ``SAM_IOU`` would collide in a
        GeoPackage or a shapefile, a source ``sam_score`` of integers would round the score.
    """
    from qgis.core import QgsFields
    names = {name.lower() for name in added}
    fields, kept = QgsFields(), []
    for index in range(source_fields.count()):
        field = source_fields.at(index)
        if field.name().lower() not in names:
            fields.append(field)
            kept.append(index)
    for name in added:
        fields.append(_double_field(name))
    return fields, kept


def _guide(geometry, bounds):
    """The footprint compared with the drawn object: valid, and inside the raster as the object is."""
    if not geometry.isGeosValid():
        geometry = geometry.makeValid()
    return geometry.intersection(bounds)


def _polygons(geometry):
    """The polygons of ``geometry`` as one multipolygon; None without any (a line along the edge of the raster)."""
    from qgis.core import QgsGeometry
    from ...adapters.qgis.coverage_layers.raster_adapter import geometry_parts
    from ...adapters.qgis.coverage_layers.segmentation import _geometry_kinds
    if geometry is None or geometry.isEmpty():
        return None
    polygon = _geometry_kinds()[1]
    parts = [part for part in geometry_parts(geometry) if part.type() == polygon and part.area() > 0]
    if not parts:
        return None
    merged = QgsGeometry.collectGeometry(parts)
    merged.convertToMultiType()
    return merged


def _metres_to_units(crs):
    """Map units of ``crs`` in one metre (degrees at the equator for a geographic CRS)."""
    from qgis.core import Qgis, QgsUnitTypes
    units = getattr(Qgis, 'DistanceUnit', None)
    metres = units.Meters if units is not None else QgsUnitTypes.DistanceUnit.DistanceMeters
    try:
        factor = QgsUnitTypes.fromUnitToUnitFactor(metres, crs.mapUnits())
    except Exception:  # noqa: BLE001 - an unknown unit: metres
        return 1.0
    return factor if factor and factor > 0 else 1.0
