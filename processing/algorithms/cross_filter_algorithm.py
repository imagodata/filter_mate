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

_TARGETS_HELP = (
    "Vecteur : sous-ensemble des entités. Raster : pixels hors zone en NoData (VRT découpé). "
    "Nuage de points : points hors zone retirés (fichier COPC dérivé, PDAL). Disjoint garde l'extérieur.\n\n"
    "Seules les couches du projet sont filtrées. Le filtre est annulable depuis FilterMate et les sources "
    "d'origine sont toujours écrites dans le projet. La sortie « Couches traitées » s'enchaîne dans un modèle, "
    "par exemple vers « Exporter les couches filtrées »."
)


class CrossFilterAlgorithm(FilterMateAlgorithm):
    """Filtre des couches vecteur, raster et nuage de points par une couche vecteur."""

    SOURCE = "SOURCE"
    SELECTED_ONLY = "SELECTED_ONLY"

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterVectorLayer(
            self.SOURCE, self.tr("Couche source"), [QgsProcessing.SourceType.TypeVectorAnyGeometry]))
        self.addParameter(QgsProcessingParameterBoolean(
            self.SELECTED_ONLY, self.tr("Entités sélectionnées uniquement"), defaultValue=True))
        self.add_target_parameters(QgsProcessingParameterDistance(
            self.BUFFER, self.tr("Tampon"), defaultValue=0.0, parentParameterName=self.SOURCE))
        self.add_output()

    def processAlgorithm(self, parameters, context, feedback):
        from ...adapters.public_api import operations
        source = self.parameterAsVectorLayer(parameters, self.SOURCE, context)
        if source is None:
            raise QgsProcessingException(self.tr("Couche source invalide"))
        selected_only = self.parameterAsBoolean(parameters, self.SELECTED_ONLY, context)
        count = source.selectedFeatureCount() if selected_only and source.selectedFeatureCount() else source.featureCount()
        feedback.pushInfo(self.tr("{0} entité(s) source").format(count))
        report = operations.cross_filter(source, self.parameterAsLayerList(parameters, self.TARGETS, context),
                                         selected_only=selected_only, project=context.project(),
                                         **self.target_settings(parameters, context))
        return self.finish(report, feedback)

    def name(self):
        return "cross_filter"

    def displayName(self):
        return self.tr("Filtrer des couches de tout type par une couche vecteur")

    def shortHelpString(self):
        return self.tr(
            "Filtre sur place des couches vecteur, raster et nuage de points par les entités d'une couche "
            "vecteur, avec les prédicats géométriques, un tampon et une couverture minimale.\n\n") + self.tr(_TARGETS_HELP)


class CrossFilterFromRasterAlgorithm(FilterMateAlgorithm):
    """Filtre des couches de tout type par les pixels retenus d'un raster."""

    SOURCE = "SOURCE"
    BAND = "BAND"
    MODE = "MODE"
    MINIMUM = "MINIMUM"
    MAXIMUM = "MAXIMUM"
    CLASSES = "CLASSES"
    EXPRESSION = "EXPRESSION"
    FILTER_SOURCE = "FILTER_SOURCE"
    MAX_PIXELS = "MAX_PIXELS"

    def targets_optional(self):
        return True  # sans cible : masque la source seule (avec FILTER_SOURCE)

    def initAlgorithm(self, config=None):
        number = QgsProcessingParameterNumber.Type.Double
        self.addParameter(QgsProcessingParameterRasterLayer(self.SOURCE, self.tr("Raster source")))
        self.addParameter(QgsProcessingParameterBand(self.BAND, self.tr("Bande"), 1, self.SOURCE))
        self.addParameter(QgsProcessingParameterEnum(
            self.MODE, self.tr("Pixels retenus"),
            options=[self.tr("Plage de valeurs"), self.tr("Classes"), self.tr("Expression raster")], defaultValue=0))
        self.addParameter(QgsProcessingParameterNumber(self.MINIMUM, self.tr("Valeur minimum (plage)"),
                                                       type=number, optional=True))
        self.addParameter(QgsProcessingParameterNumber(self.MAXIMUM, self.tr("Valeur maximum (plage)"),
                                                       type=number, optional=True))
        self.addParameter(QgsProcessingParameterString(
            self.CLASSES, self.tr("Valeurs de classes (ex. 6,7)"), optional=True))
        self.addParameter(QgsProcessingParameterString(
            self.EXPRESSION, self.tr("Expression raster, pixel gardé si non nul (ex. \"mnt@1\" > 1200)"),
            optional=True))
        self.addParameter(QgsProcessingParameterBoolean(
            self.FILTER_SOURCE, self.tr("Masquer aussi le raster source hors sélection"), defaultValue=False))
        self.add_target_parameters(QgsProcessingParameterDistance(
            self.BUFFER, self.tr("Tampon"), defaultValue=0.0, parentParameterName=self.SOURCE))
        self.addParameter(advanced(QgsProcessingParameterNumber(
            self.MAX_PIXELS, self.tr("Pixels lus au maximum (au-delà : rééchantillonnage)"),
            type=QgsProcessingParameterNumber.Type.Integer, defaultValue=4000000, minValue=10000)))
        self.add_output()

    def processAlgorithm(self, parameters, context, feedback):
        from ...adapters.public_api import operations
        from ...core.domain.api_requests import raster_selection_from_values
        source = self.parameterAsRasterLayer(parameters, self.SOURCE, context)
        if source is None:
            raise QgsProcessingException(self.tr("Raster source invalide"))
        try:
            selection = raster_selection_from_values(
                band=self.parameterAsInt(parameters, self.BAND, context) or 1,
                mode=self.parameterAsEnum(parameters, self.MODE, context),
                minimum=self.optional_number(self, parameters, self.MINIMUM, context),
                maximum=self.optional_number(self, parameters, self.MAXIMUM, context),
                classes=self.parameterAsString(parameters, self.CLASSES, context),
                expression=self.parameterAsString(parameters, self.EXPRESSION, context))
        except ValueError as exc:
            raise QgsProcessingException(str(exc))
        feedback.pushInfo(self.tr("Sélection : {0}").format(selection.describe()))
        report = operations.cross_filter(
            source, self.parameterAsLayerList(parameters, self.TARGETS, context) or [],
            raster_selection=selection, filter_source=self.parameterAsBoolean(parameters, self.FILTER_SOURCE, context),
            max_pixels=self.parameterAsInt(parameters, self.MAX_PIXELS, context), project=context.project(),
            **self.target_settings(parameters, context))
        self._log_source(report, feedback)
        return self.finish(report, feedback)

    def _log_source(self, report, feedback):
        details = report.details.get("source") or {}
        if details.get("kept_pixels") is not None:
            feedback.pushInfo(self.tr("{0} pixel(s) retenu(s) sur {1}").format(
                details["kept_pixels"], details.get("total_pixels", "?")))

    def name(self):
        return "cross_filter_from_raster"

    def displayName(self):
        return self.tr("Filtrer des couches de tout type par les pixels d'un raster")

    def shortHelpString(self):
        return self.tr(
            "Retient les pixels d'un raster (plage de valeurs d'une bande, classes d'un raster catégorisé ou "
            "expression raster), les vectorise à la taille du pixel et filtre les couches cibles par cette zone.\n\n"
            "Exemples : parcelles contenues dans la zone 1200–1300 m avec une couverture de 50 % ; MNT limité "
            "aux classes forêt ; points LiDAR des zones de pente < 15 % (pente calculée par « Pente » juste avant "
            "dans un modèle).\n\n"
            "Le raster source peut être une sortie de modèle : il est lu sans être modifié. Avec « Masquer aussi "
            "le raster source » et une source du projet, la source est elle-même filtrée.\n\n") + self.tr(_TARGETS_HELP)


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
            self.addParameter(QgsProcessingParameterMapLayer(self.SOURCE, self.tr("Nuage de points source")))
        else:
            self.addParameter(QgsProcessingParameterPointCloudLayer(self.SOURCE, self.tr("Nuage de points source")))
        self.add_point_cloud_criteria_parameters()
        self.add_operator_parameter(self.tr("Combinaison des critères avec le filtre existant de la source"),
                                    self.SOURCE_OPERATOR)
        self.add_target_parameters()
        self.addParameter(advanced(QgsProcessingParameterNumber(
            self.RESOLUTION, self.tr("Résolution de l'empreinte des points (unités du nuage)"),
            type=QgsProcessingParameterNumber.Type.Double, defaultValue=2.0, minValue=0.1)))
        self.add_output()

    def processAlgorithm(self, parameters, context, feedback):
        from ...adapters.public_api import operations
        source = self.parameterAsLayer(parameters, self.SOURCE, context)
        if source is None:
            raise QgsProcessingException(self.tr("Nuage de points source invalide"))
        criteria = self.point_cloud_criteria(parameters, context)
        if criteria is not None:
            feedback.pushInfo(self.tr("Critères : {0}").format(criteria.to_subset_string()))
        report = operations.cross_filter(
            source, self.parameterAsLayerList(parameters, self.TARGETS, context) or [],
            point_cloud_criteria=criteria,
            source_operator=OPERATORS[self.parameterAsEnum(parameters, self.SOURCE_OPERATOR, context)],
            footprint_resolution=self.parameterAsDouble(parameters, self.RESOLUTION, context),
            project=context.project(), **self.target_settings(parameters, context))
        details = report.details.get("source") or {}
        if details.get("truncated"):
            feedback.pushWarning(self.tr("Empreinte calculée sur un nombre de points limité : augmentez la résolution"))
        return self.finish(report, feedback)

    def name(self):
        return "cross_filter_from_point_cloud"

    def displayName(self):
        return self.tr("Filtrer des couches de tout type par les points d'un nuage")

    def shortHelpString(self):
        return self.tr(
            "Applique des critères au nuage source (classes ASPRS, plages Z et intensité, numéro de retour, "
            "expression), calcule l'empreinte des points retenus et filtre les couches cibles par cette zone.\n\n"
            "Exemples : bâtiments recoupant des points de classe 6 (couverture ≥ 10 %) ; Disjoint = bâtiments "
            "absents du nuage ; MNT limité à l'emprise des points eau (classe 9).\n\n"
            "Sans critère, l'empreinte porte sur les points affichés par le nuage.\n\n") + self.tr(_TARGETS_HELP)


class CrossFilterFromGeometryAlgorithm(FilterMateAlgorithm):
    """Filtre des couches de tout type par une emprise ou une géométrie."""

    EXTENT = "EXTENT"
    GEOMETRY = "GEOMETRY"

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterExtent(self.EXTENT, self.tr("Emprise"), optional=True))
        self.addParameter(QgsProcessingParameterGeometry(
            self.GEOMETRY, self.tr("Géométrie (WKT, prioritaire sur l'emprise)"), optional=True))
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
            raise QgsProcessingException(self.tr("Donnez une emprise ou une géométrie"))
        if crs is None or not crs.isValid():
            crs = context.project().crs() if context.project() else None
        report = operations.cross_filter_by_geometry(
            geometry, crs, self.parameterAsLayerList(parameters, self.TARGETS, context),
            project=context.project(), **self.target_settings(parameters, context))
        return self.finish(report, feedback)

    def name(self):
        return "cross_filter_from_geometry"

    def displayName(self):
        return self.tr("Filtrer des couches de tout type par une emprise ou une géométrie")

    def shortHelpString(self):
        return self.tr(
            "Filtre les couches cibles par une emprise (couche, canevas, saisie) ou une géométrie WKT, avec les "
            "mêmes prédicats, tampon et couverture que l'onglet FILTERING. L'opération est inscrite dans "
            "l'historique de la première couche cible.\n\n") + self.tr(_TARGETS_HELP)
