"""
Batch Filter Processing Algorithm.

Expose le filtrage FilterMate dans la Processing Toolbox de QGIS pour
permettre l'application d'une même expression de filtre à plusieurs
couches vectorielles en une seule exécution (utilisable en modèle
Processing / traitement par lot).

Author: FilterMate Team
"""

from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingParameterExpression,
    QgsProcessingParameterMultipleLayers,
)

from ...infrastructure.logging import get_logger

logger = get_logger(__name__)


class BatchFilterAlgorithm(QgsProcessingAlgorithm):
    """Applique une expression de filtre à plusieurs couches vectorielles.

    L'algorithme définit le subset string (`QgsVectorLayer.setSubsetString`)
    de chaque couche sélectionnée avec l'expression fournie. Les couches
    pour lesquelles l'expression est invalide sont ignorées et signalées
    via le feedback, sans interrompre le traitement des autres couches.
    """

    INPUT_LAYERS = "INPUT_LAYERS"
    EXPRESSION = "EXPRESSION"
    LAYERS_FILTERED = "LAYERS_FILTERED"
    LAYERS_FAILED = "LAYERS_FAILED"

    def initAlgorithm(self, config=None):
        """Déclare les paramètres d'entrée de l'algorithme.

        Args:
            config: Configuration optionnelle transmise par QGIS Processing.
        """
        self.addParameter(
            QgsProcessingParameterMultipleLayers(
                self.INPUT_LAYERS,
                self.tr("Couches à filtrer"),
                layerType=QgsProcessing.SourceType.TypeVectorAnyGeometry,
            )
        )
        self.addParameter(
            QgsProcessingParameterExpression(
                self.EXPRESSION,
                self.tr("Expression de filtre"),
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        """Applique l'expression de filtre à chaque couche sélectionnée.

        Args:
            parameters: Valeurs des paramètres résolues par Processing.
            context: Contexte d'exécution Processing.
            feedback: Objet de feedback pour la progression/les messages.

        Returns:
            dict: Nombre de couches filtrées avec succès et en échec.
        """
        layers = self.parameterAsLayerList(parameters, self.INPUT_LAYERS, context)
        expression = self.parameterAsExpression(parameters, self.EXPRESSION, context)

        if not layers:
            raise QgsProcessingException(self.tr("Aucune couche sélectionnée."))

        filtered_count = 0
        failed_count = 0
        total = len(layers)

        for index, layer in enumerate(layers):
            if feedback.isCanceled():
                break

            if layer.setSubsetString(expression):
                filtered_count += 1
            else:
                failed_count += 1
                feedback.pushWarning(
                    self.tr("Expression invalide pour la couche '{0}', ignorée.").format(
                        layer.name()
                    )
                )
                logger.warning(
                    "BatchFilterAlgorithm: expression rejetée par la couche %s",
                    layer.name(),
                )

            feedback.setProgress(int(100 * (index + 1) / total))

        return {
            self.LAYERS_FILTERED: filtered_count,
            self.LAYERS_FAILED: failed_count,
        }

    def name(self):
        """Retourne l'identifiant technique de l'algorithme."""
        return "batch_filter"

    def displayName(self):
        """Retourne le nom affiché dans la Processing Toolbox."""
        return self.tr("Filtrer plusieurs couches (batch)")

    def group(self):
        """Retourne le nom du groupe affiché dans la Processing Toolbox."""
        return self.tr("FilterMate")

    def groupId(self):
        """Retourne l'identifiant technique du groupe."""
        return "filtermate"

    def shortHelpString(self):
        """Retourne le texte d'aide affiché dans le panneau de l'algorithme."""
        return self.tr(
            "Applique la même expression de filtre à plusieurs couches "
            "vectorielles en une seule exécution."
        )

    def createInstance(self):
        """Crée une nouvelle instance de l'algorithme (requis par QGIS)."""
        return BatchFilterAlgorithm()
