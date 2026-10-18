"""
Cross Filter Processing Algorithms (FilterMate 5).

Filtre des couches de tout type (vecteur, raster, nuage de points) par une
sélection faite sur une source, avec les prédicats géométriques, le tampon et
la couverture minimale de l'onglet FILTERING :

* cible vecteur : sous-ensemble des entités qui vérifient le prédicat ;
* cible raster : pixels hors de la géométrie source passés en NoData (VRT découpé) ;
* cible nuage de points : points hors de la géométrie source retirés (COPC dérivé).

Une source par algorithme, pour que chacun n'affiche que ses paramètres :

* ``filtermate:cross_filter`` - entités d'une couche vecteur ;
* ``filtermate:cross_filter_from_raster`` - pixels d'une plage de valeurs, de classes ou d'une expression ;
* ``filtermate:cross_filter_from_point_cloud`` - points gardés par des classes, plages ou une expression ;
* ``filtermate:cross_filter_from_geometry`` - une emprise ou une géométrie saisie.

Le filtrage est appliqué sur place ; il reste annulable depuis le dock
(historique de la couche source) et les sources dérivées sont rétablies au
déchargement du plugin. La sortie ``OUTPUT`` liste les couches filtrées.

Author: FilterMate Team
"""

from qgis.core import (
    QgsProcessing,
    QgsProcessingException,
    QgsProcessingParameterBand,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterDistance,
    QgsProcessingParameterEnum,
    QgsProcessingParameterExtent,
    QgsProcessingParameterGeometry,
    QgsProcessingParameterNumber,
    QgsProcessingParameterRasterLayer,
    QgsProcessingParameterString,
    QgsProcessingParameterVectorLayer,
)

from ...core.domain.api_requests import OPERATORS, PREDICATES  # noqa: F401 - re-exported for scripts
from .common import FilterMateAlgorithm, QgsProcessingParameterPointCloudLayer, advanced


class CrossFilterAlgorithm(FilterMateAlgorithm):
    """Filtre des couches vecteur, raster et nuage de points par une couche vecteur."""

    SOURCE = "SOURCE"
    SELECTED_ONLY = "SELECTED_ONLY"

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterVectorLayer(
            self.SOURCE, self.tr("Source layer"), [QgsProcessing.SourceType.TypeVectorAnyGeometry]))
        self.addParameter(QgsProcessingParameterBoolean(
            self.SELECTED_ONLY, self.tr("Selected features only"), defaultValue=True))
        self.add_target_parameters(QgsProcessingParameterDistance(
            self.BUFFER, self.tr("Buffer"), defaultValue=0.0, parentParameterName=self.SOURCE))
        self.add_output()

    def processAlgorithm(self, parameters, context, feedback):
        from ...adapters.public_api import operations
        source = self.parameterAsVectorLayer(parameters, self.SOURCE, context)
        if source is None:
            raise QgsProcessingException(self.tr("Invalid source layer"))
        selected_only = self.parameterAsBoolean(parameters, self.SELECTED_ONLY, context)
        count = source.selectedFeatureCount() if selected_only and source.selectedFeatureCount() else source.featureCount()
        feedback.pushInfo(self.tr("{0} source feature(s)").format(count))
        report = operations.cross_filter(source, self.parameterAsLayerList(parameters, self.TARGETS, context),
                                         selected_only=selected_only, project=context.project(), feedback=feedback,
                                         **self.target_settings(parameters, context))
        return self.finish(report, feedback)

    def name(self):
        return "cross_filter"

    def displayName(self):
        return self.tr("Filter layers of any type by a vector layer")

    def shortHelpString(self):
        return self.tr(
            "Filters vector, raster and point cloud layers in place by the features of a vector layer, "
            "with the geometric predicates, a buffer and a minimum coverage.\n\n") + self.targets_help()


class CrossFilterFromRasterAlgorithm(FilterMateAlgorithm):
    """Filtre des couches de tout type par les pixels retenus d'un raster."""

    SOURCE = "SOURCE"
    BAND = "BAND"
    MODE = "MODE"
    MINIMUM = "MINIMUM"
    MAXIMUM = "MAXIMUM"
    CLASSES = "CLASSES"
    EXPRESSION = "EXPRESSION"
    DERIVATIVE = "DERIVATIVE"
    FILTER_SOURCE = "FILTER_SOURCE"
    MAX_PIXELS = "MAX_PIXELS"

    def targets_optional(self):
        return True  # sans cible : masque la source seule (avec FILTER_SOURCE)

    def initAlgorithm(self, config=None):
        number = QgsProcessingParameterNumber.Type.Double
        self.addParameter(QgsProcessingParameterRasterLayer(self.SOURCE, self.tr("Source raster")))
        self.addParameter(QgsProcessingParameterBand(self.BAND, self.tr("Band"), 1, self.SOURCE))
        self.addParameter(QgsProcessingParameterEnum(
            self.MODE, self.tr("Pixels to keep"),
            options=[self.tr("Value range"), self.tr("Classes"), self.tr("Raster expression")], defaultValue=0))
        self.addParameter(QgsProcessingParameterEnum(
            self.DERIVATIVE, self.tr("Range applies to (band read as a DTM for slope, aspect...)"),
            options=[self.tr("Pixel value"), self.tr("Slope (degrees)"), self.tr("Slope (%)"),
                     self.tr("Aspect (degrees)"), self.tr("Hillshade (0-255)"), self.tr("Roughness (TRI)")],
            defaultValue=0))
        self.addParameter(QgsProcessingParameterNumber(self.MINIMUM, self.tr("Minimum value (range)"),
                                                       type=number, optional=True))
        self.addParameter(QgsProcessingParameterNumber(self.MAXIMUM, self.tr("Maximum value (range)"),
                                                       type=number, optional=True))
        self.addParameter(QgsProcessingParameterString(
            self.CLASSES, self.tr("Class values (e.g. 6,7)"), optional=True))
        self.addParameter(QgsProcessingParameterString(
            self.EXPRESSION, self.tr("Raster expression, pixel kept if non-zero (e.g. \"dem@1\" > 1200)"),
            optional=True))
        self.addParameter(QgsProcessingParameterBoolean(
            self.FILTER_SOURCE, self.tr("Also hide the source raster outside the selection"), defaultValue=False))
        self.add_target_parameters(QgsProcessingParameterDistance(
            self.BUFFER, self.tr("Buffer"), defaultValue=0.0, parentParameterName=self.SOURCE))
        # Sans valeur : réglage CROSS_FILTER.raster_source_max_pixels (400 000 000 par défaut).
        self.addParameter(advanced(QgsProcessingParameterNumber(
            self.MAX_PIXELS, self.tr("Maximum pixels read (beyond: resampling)"),
            type=QgsProcessingParameterNumber.Type.Integer, optional=True, minValue=10000)))
        self.add_output()

    def processAlgorithm(self, parameters, context, feedback):
        from ...adapters.public_api import operations
        from ...core.domain.api_requests import raster_selection_from_values
        source = self.parameterAsRasterLayer(parameters, self.SOURCE, context)
        if source is None:
            raise QgsProcessingException(self.tr("Invalid source raster"))
        try:
            selection = raster_selection_from_values(
                band=self.parameterAsInt(parameters, self.BAND, context) or 1,
                mode=self.parameterAsEnum(parameters, self.MODE, context),
                minimum=self.optional_number(self, parameters, self.MINIMUM, context),
                maximum=self.optional_number(self, parameters, self.MAXIMUM, context),
                classes=self.parameterAsString(parameters, self.CLASSES, context),
                expression=self.parameterAsString(parameters, self.EXPRESSION, context),
                derivative=self.parameterAsEnum(parameters, self.DERIVATIVE, context))
        except ValueError as exc:
            raise QgsProcessingException(str(exc))
        feedback.pushInfo(self.tr("Selection: {0}").format(selection.describe()))
        report = operations.cross_filter(
            source, self.parameterAsLayerList(parameters, self.TARGETS, context) or [],
            raster_selection=selection, filter_source=self.parameterAsBoolean(parameters, self.FILTER_SOURCE, context),
            max_pixels=self.optional_number(self, parameters, self.MAX_PIXELS, context, integer=True),
            project=context.project(), feedback=feedback, **self.target_settings(parameters, context))
        self._log_source(report, feedback)
        return self.finish(report, feedback)

    def _log_source(self, report, feedback):
        details = report.details.get("source") or {}
        if details.get("kept_pixels") is not None:
            feedback.pushInfo(self.tr("{0} of {1} pixel(s) kept").format(
                details["kept_pixels"], details.get("total_pixels", "?")))

    def name(self):
        return "cross_filter_from_raster"

    def displayName(self):
        return self.tr("Filter layers of any type by the pixels of a raster")

    def shortHelpString(self):
        return self.tr(
            "Keeps the pixels of a raster (value range of a band, classes of a categorized raster or "
            "raster expression), vectorizes them at the pixel size and filters the target layers by this area.\n\n"
            "Examples: parcels contained in the 1200–1300 m zone with a coverage of 50%; a DEM limited "
            "to the forest classes; LiDAR points of the areas with a slope < 15% (choose \"Slope (%)\" in "
            "\"Range applies to\" with a DEM as the source: no \"Slope\" step needed before).\n\n"
            "The source raster can be a model output: it is read without being modified. With \"Also hide the "
            "source raster outside the selection\" and a project source, the source itself is filtered.\n\n") + self.targets_help()


class CrossFilterFromPointCloudAlgorithm(FilterMateAlgorithm):
    """Filtre des couches de tout type par l'empreinte des points retenus d'un nuage."""

    SOURCE = "SOURCE"
    SOURCE_OPERATOR = "SOURCE_OPERATOR"
    RESOLUTION = "RESOLUTION"

    def targets_optional(self):
        return True  # sans cible : filtre le nuage source seul

    def initAlgorithm(self, config=None):
        if QgsProcessingParameterPointCloudLayer is None:
            from qgis.core import QgsProcessingParameterMapLayer
            self.addParameter(QgsProcessingParameterMapLayer(self.SOURCE, self.tr("Source point cloud")))
        else:
            self.addParameter(QgsProcessingParameterPointCloudLayer(self.SOURCE, self.tr("Source point cloud")))
        self.add_point_cloud_criteria_parameters()
        self.add_operator_parameter(self.tr("Combine the criteria with the existing filter of the source"),
                                    self.SOURCE_OPERATOR)
        self.add_target_parameters()
        # Sans valeur : réglage CROSS_FILTER.point_cloud_footprint_resolution (2 par défaut).
        self.addParameter(advanced(QgsProcessingParameterNumber(
            self.RESOLUTION, self.tr("Point footprint resolution (point cloud units)"),
            type=QgsProcessingParameterNumber.Type.Double, optional=True, minValue=0.1)))
        self.add_output()

    def processAlgorithm(self, parameters, context, feedback):
        from ...adapters.public_api import operations
        source = self.parameterAsLayer(parameters, self.SOURCE, context)
        if source is None:
            raise QgsProcessingException(self.tr("Invalid source point cloud"))
        criteria = self.point_cloud_criteria(parameters, context)
        if criteria is not None:
            feedback.pushInfo(self.tr("Criteria: {0}").format(criteria.to_subset_string()))
        report = operations.cross_filter(
            source, self.parameterAsLayerList(parameters, self.TARGETS, context) or [],
            point_cloud_criteria=criteria,
            source_operator=OPERATORS[self.parameterAsEnum(parameters, self.SOURCE_OPERATOR, context)],
            footprint_resolution=self.optional_number(self, parameters, self.RESOLUTION, context),
            project=context.project(), feedback=feedback, **self.target_settings(parameters, context))
        details = report.details.get("source") or {}
        if details.get("truncated"):
            feedback.pushWarning(self.tr("Footprint computed from a limited number of points: increase the resolution"))
        return self.finish(report, feedback)

    def name(self):
        return "cross_filter_from_point_cloud"

    def displayName(self):
        return self.tr("Filter layers of any type by the points of a point cloud")

    def shortHelpString(self):
        return self.tr(
            "Applies criteria to the source point cloud (ASPRS classes, Z and intensity ranges, return number, "
            "expression), computes the footprint of the retained points and filters the target layers by this "
            "area.\n\n"
            "Examples: buildings intersecting class 6 points (coverage ≥ 10%); Disjoint = buildings "
            "absent from the point cloud; a DEM limited to the extent of the water points (class 9).\n\n"
            "Without criteria, the footprint covers the points displayed by the point cloud.\n\n") + self.targets_help()


class CrossFilterFromGeometryAlgorithm(FilterMateAlgorithm):
    """Filtre des couches de tout type par une emprise ou une géométrie."""

    EXTENT = "EXTENT"
    GEOMETRY = "GEOMETRY"

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterExtent(self.EXTENT, self.tr("Extent"), optional=True))
        self.addParameter(QgsProcessingParameterGeometry(
            self.GEOMETRY, self.tr("Geometry (WKT, takes precedence over the extent)"), optional=True))
        self.add_target_parameters()
        self.add_output()

    def processAlgorithm(self, parameters, context, feedback):
        from qgis.core import QgsGeometry
        from ...adapters.public_api import operations
        geometry, crs = None, None
        if parameters.get(self.GEOMETRY):
            geometry = self.parameterAsGeometry(parameters, self.GEOMETRY, context)
            crs = self.parameterAsGeometryCrs(parameters, self.GEOMETRY, context)
        if (geometry is None or geometry.isEmpty()) and parameters.get(self.EXTENT):
            geometry = QgsGeometry.fromRect(self.parameterAsExtent(parameters, self.EXTENT, context))
            crs = self.parameterAsExtentCrs(parameters, self.EXTENT, context)
        if geometry is None or geometry.isEmpty():
            raise QgsProcessingException(self.tr("Provide an extent or a geometry"))
        if crs is None or not crs.isValid():
            crs = context.project().crs() if context.project() else None
        report = operations.cross_filter_by_geometry(
            geometry, crs, self.parameterAsLayerList(parameters, self.TARGETS, context),
            project=context.project(), feedback=feedback, **self.target_settings(parameters, context))
        return self.finish(report, feedback)

    def name(self):
        return "cross_filter_from_geometry"

    def displayName(self):
        return self.tr("Filter layers of any type by an extent or a geometry")

    def shortHelpString(self):
        return self.tr(
            "Filters the target layers by an extent (layer, canvas, typed in) or a WKT geometry, with the "
            "same predicates, buffer and coverage as the FILTERING tab. The operation is recorded in the "
            "history of the first target layer.\n\n") + self.targets_help()
