"""
Cross Filter Processing Algorithm (FilterMate 5).

Filtre des couches de tout type (vecteur, raster, nuage de points) par les
entités d'une couche vecteur source, avec les prédicats géométriques, le
tampon et la couverture minimale de l'onglet FILTERING :

* cible vecteur : sous-ensemble des entités qui vérifient le prédicat ;
* cible raster : pixels hors de la géométrie source passés en NoData (VRT découpé) ;
* cible nuage de points : points hors de la géométrie source retirés (COPC dérivé).

Le filtrage est appliqué sur place, comme ``filtermate:batch_filter`` ; il
reste annulable depuis le dock (historique de la couche source) et les
sources dérivées sont rétablies au déchargement du plugin.

Author: FilterMate Team
"""

from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterDistance,
    QgsProcessingParameterEnum,
    QgsProcessingParameterMultipleLayers,
    QgsProcessingParameterNumber,
    QgsProcessingParameterVectorLayer,
    QgsProcessing,
)
from qgis.PyQt.QtCore import QCoreApplication

from ...infrastructure.logging import get_logger

logger = get_logger(__name__)

PREDICATES = ("Intersect", "Contain", "Disjoint", "Equal", "Touch", "Overlap", "Are within", "Cross")
OPERATORS = (None, "AND", "OR", "AND NOT")


def kind_without_flags(layer):
    """Layer kind from its class only (Processing does not depend on the dock options)."""
    from ...adapters.qgis.point_cloud_capability import layer_kind_by_class
    return layer_kind_by_class(layer)


class CrossFilterAlgorithm(QgsProcessingAlgorithm):
    """Filtre des couches vecteur, raster et nuage de points par une couche vecteur."""

    SOURCE = "SOURCE"
    SELECTED_ONLY = "SELECTED_ONLY"
    TARGETS = "TARGETS"
    PREDICATES = "PREDICATES"
    BUFFER = "BUFFER"
    COVERAGE = "COVERAGE"
    OPERATOR = "OPERATOR"
    LAYERS_FILTERED = "LAYERS_FILTERED"
    LAYERS_FAILED = "LAYERS_FAILED"

    def tr(self, string):
        """Traduit une chaîne via le contexte Processing."""
        return QCoreApplication.translate("Processing", string)

    def flags(self):
        """Les couches sont modifiées sur place : exécution dans le fil principal."""
        return super().flags() | QgsProcessingAlgorithm.Flag.FlagNoThreading

    def initAlgorithm(self, config=None):
        """Déclare les paramètres d'entrée de l'algorithme."""
        self.addParameter(QgsProcessingParameterVectorLayer(
            self.SOURCE, self.tr("Couche source"), [QgsProcessing.SourceType.TypeVectorAnyGeometry]))
        self.addParameter(QgsProcessingParameterBoolean(
            self.SELECTED_ONLY, self.tr("Entités sélectionnées uniquement"), defaultValue=True))
        self.addParameter(QgsProcessingParameterMultipleLayers(
            self.TARGETS, self.tr("Couches à filtrer (vecteur, raster, nuage de points)"),
            layerType=QgsProcessing.SourceType.TypeMapLayer))
        self.addParameter(QgsProcessingParameterEnum(
            self.PREDICATES, self.tr("Prédicats géométriques"), options=list(PREDICATES),
            allowMultiple=True, defaultValue=[0]))
        self.addParameter(QgsProcessingParameterDistance(
            self.BUFFER, self.tr("Tampon"), defaultValue=0.0, parentParameterName=self.SOURCE))
        self.addParameter(QgsProcessingParameterNumber(
            self.COVERAGE, self.tr("Couverture minimale des polygones cibles (%)"),
            type=QgsProcessingParameterNumber.Type.Double, defaultValue=0.0, minValue=0.0, maxValue=100.0))
        self.addParameter(QgsProcessingParameterEnum(
            self.OPERATOR, self.tr("Combinaison avec le filtre existant des cibles"),
            options=[self.tr("Remplacer"), "AND", "OR", "AND NOT"], defaultValue=0))

    def processAlgorithm(self, parameters, context, feedback):
        """Applique la géométrie source aux couches cibles."""
        from ...core.domain.cross_filter import CrossFilterRequest, TargetSpec
        from ...core.domain.layer_kind import LayerKind
        from ...core.services.cross_filter_service import get_cross_filter_service
        from ...adapters.qgis.coverage_layers.source_jobs import VectorSourceJob

        source = self.parameterAsVectorLayer(parameters, self.SOURCE, context)
        if source is None:
            raise QgsProcessingException(self.tr("Couche source invalide"))
        selected_only = self.parameterAsBoolean(parameters, self.SELECTED_ONLY, context)
        features = list(source.getSelectedFeatures() if selected_only and source.selectedFeatureCount() else source.getFeatures())
        if not features:
            raise QgsProcessingException(self.tr("La couche source n'a aucune entité à utiliser"))
        targets = []
        for layer in self.parameterAsLayerList(parameters, self.TARGETS, context):
            kind = kind_without_flags(layer)
            if layer.id() == source.id() or kind is LayerKind.OTHER:
                feedback.reportError(self.tr("Couche ignorée : {0}").format(layer.name()))
                continue
            targets.append(TargetSpec(layer.id(), kind))
        if not targets:
            raise QgsProcessingException(self.tr("Aucune couche cible exploitable"))
        predicates = tuple(PREDICATES[i] for i in self.parameterAsEnums(parameters, self.PREDICATES, context)) or ("Intersect",)
        request = CrossFilterRequest(
            source_layer_id=source.id(), source_kind=LayerKind.VECTOR, targets=tuple(targets),
            predicates=predicates,
            buffer_value=self.parameterAsDouble(parameters, self.BUFFER, context),
            coverage_min=self.parameterAsDouble(parameters, self.COVERAGE, context),
            other_layers_combine_operator=OPERATORS[self.parameterAsEnum(parameters, self.OPERATOR, context)])
        feedback.pushInfo(self.tr("{0} entité(s) source, {1} cible(s)").format(len(features), len(targets)))
        task = get_cross_filter_service().run(request, VectorSourceJob(source, features), synchronous=True)
        if task.error:
            raise QgsProcessingException(task.error)
        filtered, failed = [], []
        for outcome in task.outcomes:
            name = context.project().mapLayer(outcome.layer_id).name() if context.project() and context.project().mapLayer(outcome.layer_id) else outcome.layer_id
            if outcome.success:
                filtered.append(name)
                feedback.pushInfo(self.tr("{0} : filtrée ({1:.1f} s)").format(name, outcome.elapsed))
            else:
                failed.append(name)
                feedback.reportError(self.tr("{0} : échec — {1}").format(name, outcome.message))
        return {self.LAYERS_FILTERED: filtered, self.LAYERS_FAILED: failed}

    def name(self):
        return "cross_filter"

    def displayName(self):
        return self.tr("Filtrer des couches de tout type par une couche vecteur")

    def group(self):
        return self.tr("FilterMate")

    def groupId(self):
        return "filtermate"

    def shortHelpString(self):
        return self.tr(
            "Filtre sur place des couches vecteur, raster et nuage de points par les entités d'une couche "
            "vecteur, avec les prédicats géométriques, un tampon et une couverture minimale.\n\n"
            "Vecteur : sous-ensemble des entités. Raster : pixels hors zone en NoData (VRT découpé). "
            "Nuage de points : points hors zone retirés (fichier COPC dérivé, PDAL). Disjoint garde l'extérieur.\n\n"
            "Le filtre est annulable depuis FilterMate et les sources d'origine sont toujours écrites dans le projet.")

    def createInstance(self):
        return CrossFilterAlgorithm()
