"""
Layer Operations Processing Algorithms (FilterMate 5).

* ``filtermate:filter_point_cloud`` - mêmes critères sur plusieurs nuages (dalles LiDAR HD) ;
* ``filtermate:clear_filters`` - couches de tout type rendues à leur source d'origine, sans filtre ;
* ``filtermate:apply_favorite`` - rejoue un favori FilterMate (sous-ensembles et découpes raster / nuage) ;
* ``filtermate:export_filtered_layers`` - écrit les couches telles qu'elles sont filtrées (GPKG,
  GeoTIFF / COG, LAZ / COPC...), une par fichier.

Les trois premiers modifient les couches du projet sur place (annulable depuis
le dock) et renvoient ``OUTPUT`` (couches traitées) pour les modèles.

Author: FilterMate Team
"""

from qgis.core import (
    QgsProcessing,
    QgsProcessingException,
    QgsProcessingOutputMultipleLayers,
    QgsProcessingParameterCrs,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFolderDestination,
    QgsProcessingParameterMultipleLayers,
    QgsProcessingParameterString,
)

from ...core.domain.api_requests import (
    OPERATORS,
    POINT_CLOUD_EXPORT_FORMATS,
    RASTER_EXPORT_FORMATS,
    VECTOR_EXPORT_FORMATS,
)
from .common import FilterMateAlgorithm, point_cloud_layer_type


class FilterPointCloudAlgorithm(FilterMateAlgorithm):
    """Applique les mêmes critères à plusieurs nuages de points."""

    LAYERS = "LAYERS"

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterMultipleLayers(
            self.LAYERS, self.tr("Point clouds"), layerType=point_cloud_layer_type()))
        self.add_point_cloud_criteria_parameters()
        self.add_operator_parameter(self.tr("Combine with the existing filter of each point cloud"))
        self.add_output()

    def processAlgorithm(self, parameters, context, feedback):
        from ...adapters.public_api import operations
        criteria = self.point_cloud_criteria(parameters, context)
        if criteria is None:
            raise QgsProcessingException(self.tr("Provide classes, a range, a return number or an expression"))
        feedback.pushInfo(self.tr("Criteria: {0}").format(criteria.to_subset_string()))
        report = operations.filter_point_clouds(
            self.parameterAsLayerList(parameters, self.LAYERS, context), criteria,
            operator=OPERATORS[self.parameterAsEnum(parameters, self.OPERATOR, context)], project=context.project(),
            feedback=feedback)
        return self.finish(report, feedback)

    def name(self):
        return "filter_point_cloud"

    def displayName(self):
        return self.tr("Filter point clouds by criteria")

    def shortHelpString(self):
        return self.tr(
            "Applies the same criteria (ASPRS classes, Z and intensity ranges, return number, expression) "
            "to one or more point clouds of the project, for example all the LiDAR HD tiles of a work site. "
            "The filter is the point cloud expression (subset): it is immediate and can be undone from FilterMate.")


class ClearFiltersAlgorithm(FilterMateAlgorithm):
    """Rend des couches de tout type à leur source d'origine, sans filtre."""

    LAYERS = "LAYERS"

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterMultipleLayers(
            self.LAYERS, self.tr("Layers to clear"), layerType=QgsProcessing.SourceType.TypeMapLayer))
        self.add_output()

    def processAlgorithm(self, parameters, context, feedback):
        from ...adapters.public_api import operations
        report = operations.clear_filters(self.parameterAsLayerList(parameters, self.LAYERS, context),
                                          project=context.project())
        return self.finish(report, feedback, self.tr("cleared"))

    def name(self):
        return "clear_filters"

    def displayName(self):
        return self.tr("Clear the filters of layers of any type")

    def shortHelpString(self):
        return self.tr(
            "Removes the filter from the chosen layers: subset cleared for vectors and point clouds, "
            "original source restored for clipped rasters and point clouds. Useful at the start of a model to "
            "start again from the complete data. Can be undone from FilterMate.")


class ApplyFavoriteAlgorithm(FilterMateAlgorithm):
    """Rejoue un favori FilterMate."""

    FAVORITE = "FAVORITE"

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterString(self.FAVORITE, self.tr("Favorite name or identifier")))
        self.add_output()

    def processAlgorithm(self, parameters, context, feedback):
        from ...adapters.public_api import operations
        name = self.parameterAsString(parameters, self.FAVORITE, context).strip()
        if not name:
            raise QgsProcessingException(self.tr("Provide the name of the favorite"))
        report = operations.apply_favorite(name, project=context.project(), feedback=feedback)
        favorite = report.details.get("favorite") or {}
        if favorite:
            feedback.pushInfo(self.tr("Favorite: {0}").format(favorite.get("name")))
        return self.finish(report, feedback)

    def name(self):
        return "apply_favorite"

    def displayName(self):
        return self.tr("Apply a FilterMate favorite")

    def shortHelpString(self):
        return self.tr(
            "Replays a favorite saved in FilterMate (by name or identifier): filters of the vector and point "
            "cloud layers, clips of the rasters and point clouds. Layers are found by signature, then identifier, "
            "then name. Without the dock (qgis_process), the favorites saved in the project are used.")


class ExportFilteredLayersAlgorithm(FilterMateAlgorithm):
    """Écrit des couches de tout type telles qu'elles sont filtrées."""

    LAYERS = "LAYERS"
    VECTOR_FORMAT = "VECTOR_FORMAT"
    RASTER_FORMAT = "RASTER_FORMAT"
    POINT_CLOUD_FORMAT = "POINT_CLOUD_FORMAT"
    CRS = "CRS"
    OUTPUT_FOLDER = "OUTPUT_FOLDER"
    OUTPUT_FILES = "OUTPUT_FILES"

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterMultipleLayers(
            self.LAYERS, self.tr("Layers to export"), layerType=QgsProcessing.SourceType.TypeMapLayer))
        self.addParameter(QgsProcessingParameterEnum(
            self.VECTOR_FORMAT, self.tr("Vector format"), options=list(VECTOR_EXPORT_FORMATS), defaultValue=0))
        self.addParameter(QgsProcessingParameterEnum(
            self.RASTER_FORMAT, self.tr("Raster format"), options=list(RASTER_EXPORT_FORMATS), defaultValue=0))
        self.addParameter(QgsProcessingParameterEnum(
            self.POINT_CLOUD_FORMAT, self.tr("Point cloud format"), options=list(POINT_CLOUD_EXPORT_FORMATS),
            defaultValue=0))
        self.addParameter(QgsProcessingParameterCrs(self.CRS, self.tr("Output CRS (empty = the layer's CRS)"),
                                                    optional=True))
        self.addParameter(QgsProcessingParameterFolderDestination(self.OUTPUT_FOLDER, self.tr("Output folder")))
        self.addOutput(QgsProcessingOutputMultipleLayers(self.OUTPUT_FILES, self.tr("Files written")))
        self.add_output()

    def processAlgorithm(self, parameters, context, feedback):
        from ...adapters.public_api import operations
        # parameterAsFileOutput resolves "temporary folder" (TEMPORARY_OUTPUT) to a real path.
        folder = self.parameterAsFileOutput(parameters, self.OUTPUT_FOLDER, context)
        if not folder or folder == "TEMPORARY_OUTPUT":
            from qgis.core import QgsProcessingUtils
            folder = QgsProcessingUtils.generateTempFilename("filtermate_export", context)
        crs = self.parameterAsCrs(parameters, self.CRS, context) if parameters.get(self.CRS) else None
        report = operations.export_layers(
            self.parameterAsLayerList(parameters, self.LAYERS, context), folder,
            vector_format=list(VECTOR_EXPORT_FORMATS)[self.parameterAsEnum(parameters, self.VECTOR_FORMAT, context)],
            raster_format=RASTER_EXPORT_FORMATS[self.parameterAsEnum(parameters, self.RASTER_FORMAT, context)],
            point_cloud_format=POINT_CLOUD_EXPORT_FORMATS[
                self.parameterAsEnum(parameters, self.POINT_CLOUD_FORMAT, context)],
            crs=crs if crs is not None and crs.isValid() else None, feedback=feedback, project=context.project())
        for name, note in (report.details.get("notes") or {}).items():
            feedback.pushWarning(f"{name} : {note}")
        result = self.finish(report, feedback, self.tr("exported"))
        result[self.OUTPUT_FOLDER] = folder
        result[self.OUTPUT_FILES] = list(report.outputs.values())
        return result

    def name(self):
        return "export_filtered_layers"

    def displayName(self):
        return self.tr("Export filtered layers (vector, raster, point cloud)")

    def shortHelpString(self):
        return self.tr(
            "Writes each layer as it is filtered, one file per layer named after the layer: subset features "
            "for vectors, retained pixels (NoData elsewhere) as GeoTIFF or COG for rasters, retained points as "
            "LAZ, COPC, LAS, GPKG or CSV for point clouds.\n\n"
            "In a model, connect \"Processed layers\" of a FilterMate filter to \"Layers to export\". "
            "COPC requires PDAL (shipped with QGIS); without PDAL, a LAZ is written instead.")
