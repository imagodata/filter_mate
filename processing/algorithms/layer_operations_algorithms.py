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
            self.LAYERS, self.tr("Nuages de points"), layerType=point_cloud_layer_type()))
        self.add_point_cloud_criteria_parameters()
        self.add_operator_parameter(self.tr("Combinaison avec le filtre existant de chaque nuage"))
        self.add_output()

    def processAlgorithm(self, parameters, context, feedback):
        from ...adapters.public_api import operations
        criteria = self.point_cloud_criteria(parameters, context)
        if criteria is None:
            raise QgsProcessingException(self.tr("Donnez des classes, une plage, un numéro de retour ou une expression"))
        feedback.pushInfo(self.tr("Critères : {0}").format(criteria.to_subset_string()))
        report = operations.filter_point_clouds(
            self.parameterAsLayerList(parameters, self.LAYERS, context), criteria,
            operator=OPERATORS[self.parameterAsEnum(parameters, self.OPERATOR, context)], project=context.project())
        return self.finish(report, feedback)

    def name(self):
        return "filter_point_cloud"

    def displayName(self):
        return self.tr("Filtrer des nuages de points par critères")

    def shortHelpString(self):
        return self.tr(
            "Applique les mêmes critères (classes ASPRS, plages Z et intensité, numéro de retour, expression) "
            "à un ou plusieurs nuages de points du projet, par exemple toutes les dalles LiDAR HD d'un chantier. "
            "Le filtre est l'expression du nuage (sous-ensemble) : il est immédiat et annulable depuis FilterMate.")


class ClearFiltersAlgorithm(FilterMateAlgorithm):
    """Rend des couches de tout type à leur source d'origine, sans filtre."""

    LAYERS = "LAYERS"

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterMultipleLayers(
            self.LAYERS, self.tr("Couches à défiltrer"), layerType=QgsProcessing.SourceType.TypeMapLayer))
        self.add_output()

    def processAlgorithm(self, parameters, context, feedback):
        from ...adapters.public_api import operations
        report = operations.clear_filters(self.parameterAsLayerList(parameters, self.LAYERS, context),
                                          project=context.project())
        return self.finish(report, feedback, self.tr("défiltrée"))

    def name(self):
        return "clear_filters"

    def displayName(self):
        return self.tr("Défiltrer des couches de tout type")

    def shortHelpString(self):
        return self.tr(
            "Retire le filtre des couches choisies : sous-ensemble vidé pour les vecteurs et les nuages, "
            "source d'origine rétablie pour les rasters et nuages découpés. Utile en tête d'un modèle pour "
            "repartir des données complètes. Annulable depuis FilterMate.")


class ApplyFavoriteAlgorithm(FilterMateAlgorithm):
    """Rejoue un favori FilterMate."""

    FAVORITE = "FAVORITE"

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterString(self.FAVORITE, self.tr("Nom ou identifiant du favori")))
        self.add_output()

    def processAlgorithm(self, parameters, context, feedback):
        from ...adapters.public_api import operations
        name = self.parameterAsString(parameters, self.FAVORITE, context).strip()
        if not name:
            raise QgsProcessingException(self.tr("Donnez le nom du favori"))
        report = operations.apply_favorite(name, project=context.project())
        favorite = report.details.get("favorite") or {}
        if favorite:
            feedback.pushInfo(self.tr("Favori : {0}").format(favorite.get("name")))
        return self.finish(report, feedback)

    def name(self):
        return "apply_favorite"

    def displayName(self):
        return self.tr("Appliquer un favori FilterMate")

    def shortHelpString(self):
        return self.tr(
            "Rejoue un favori enregistré dans FilterMate (par son nom ou son identifiant) : filtres des couches "
            "vecteur et nuage, découpes des rasters et nuages. Les couches sont retrouvées par signature, "
            "identifiant puis nom. Sans le dock (qgis_process), les favoris sauvegardés dans le projet sont utilisés.")


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
            self.LAYERS, self.tr("Couches à exporter"), layerType=QgsProcessing.SourceType.TypeMapLayer))
        self.addParameter(QgsProcessingParameterEnum(
            self.VECTOR_FORMAT, self.tr("Format vecteur"), options=list(VECTOR_EXPORT_FORMATS), defaultValue=0))
        self.addParameter(QgsProcessingParameterEnum(
            self.RASTER_FORMAT, self.tr("Format raster"), options=list(RASTER_EXPORT_FORMATS), defaultValue=0))
        self.addParameter(QgsProcessingParameterEnum(
            self.POINT_CLOUD_FORMAT, self.tr("Format nuage de points"), options=list(POINT_CLOUD_EXPORT_FORMATS),
            defaultValue=0))
        self.addParameter(QgsProcessingParameterCrs(self.CRS, self.tr("SCR de sortie (vide = celui de la couche)"),
                                                    optional=True))
        self.addParameter(QgsProcessingParameterFolderDestination(self.OUTPUT_FOLDER, self.tr("Dossier de sortie")))
        self.addOutput(QgsProcessingOutputMultipleLayers(self.OUTPUT_FILES, self.tr("Fichiers écrits")))
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
        result = self.finish(report, feedback, self.tr("exportée"))
        result[self.OUTPUT_FOLDER] = folder
        result[self.OUTPUT_FILES] = list(report.outputs.values())
        return result

    def name(self):
        return "export_filtered_layers"

    def displayName(self):
        return self.tr("Exporter les couches filtrées (vecteur, raster, nuage)")

    def shortHelpString(self):
        return self.tr(
            "Écrit chaque couche telle qu'elle est filtrée, un fichier par couche nommé d'après la couche : "
            "entités du sous-ensemble pour les vecteurs, pixels retenus (NoData ailleurs) en GeoTIFF ou COG "
            "pour les rasters, points retenus en LAZ, COPC, LAS, GPKG ou CSV pour les nuages.\n\n"
            "Dans un modèle, branchez « Couches traitées » d'un filtre FilterMate sur « Couches à exporter ». "
            "COPC demande PDAL (livré avec QGIS) ; sans PDAL, un LAZ est écrit à la place.")
