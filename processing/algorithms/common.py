"""
Base commune des algorithmes Processing FilterMate 5.

Tous les algorithmes délèguent à ``adapters.public_api.operations`` (le même
code que l'API Python et l'API REST) et :

* s'exécutent dans le fil principal (``FlagNoThreading``) : ils modifient les
  couches du projet sur place, comme le dock ;
* déclarent la sortie ``OUTPUT`` (couches traitées) pour pouvoir être
  enchaînés dans le modeleur graphique, par exemple filtre croisé → export ;
* transmettent le ``feedback`` : progression et bouton Annuler ;
* ignorent, avec un avertissement, les couches hors projet : un filtre posé
  sur une couche temporaire chargée depuis un chemin serait perdu.

Les opérations restent annulables depuis le dock (historique FilterMate).
"""

from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingOutputMultipleLayers,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterDefinition,
    QgsProcessingParameterEnum,
    QgsProcessingParameterMultipleLayers,
    QgsProcessingParameterNumber,
    QgsProcessingParameterString,
)
from qgis.PyQt.QtCore import QCoreApplication

from ...core.domain.api_requests import OPERATORS, PREDICATES

try:  # QGIS 3.22+
    from qgis.core import QgsProcessingParameterPointCloudLayer
except ImportError:  # pragma: no cover - older QGIS
    QgsProcessingParameterPointCloudLayer = None

try:  # QGIS 3.28+: listes de noms déclarées comme sorties
    from qgis.core import QgsProcessingOutputVariant
except ImportError:  # pragma: no cover - older QGIS
    QgsProcessingOutputVariant = None


def point_cloud_layer_type():
    """Type de couche « nuage de points » des paramètres multi-couches (repli : toute couche)."""
    from qgis.core import Qgis
    for owner, name in ((getattr(Qgis, "ProcessingSourceType", None), "PointCloud"),
                        (getattr(QgsProcessing, "SourceType", None), "TypePointCloud"),
                        (QgsProcessing, "TypePointCloud")):
        value = getattr(owner, name, None) if owner is not None else None
        if value is not None:
            return value
    return QgsProcessing.SourceType.TypeMapLayer


class FilterMateAlgorithm(QgsProcessingAlgorithm):
    """Algorithme FilterMate : fil principal, sortie OUTPUT, rapport d'opération."""

    TARGETS = "TARGETS"
    PREDICATES = "PREDICATES"
    BUFFER = "BUFFER"
    COVERAGE = "COVERAGE"
    OPERATOR = "OPERATOR"
    OUTPUT = "OUTPUT"
    LAYERS_FILTERED = "LAYERS_FILTERED"
    LAYERS_FAILED = "LAYERS_FAILED"

    def tr(self, string):
        """Traduit une chaîne via le contexte Processing."""
        return QCoreApplication.translate("Processing", string)

    def flags(self):
        """Les couches sont modifiées sur place : exécution dans le fil principal."""
        return super().flags() | QgsProcessingAlgorithm.Flag.FlagNoThreading

    def group(self):
        return self.tr("FilterMate")

    def groupId(self):
        return "filtermate"

    def createInstance(self):
        return type(self)()

    # --- paramètres partagés ---------------------------------------------------

    def add_target_parameters(self, buffer_parameter=None):
        """Couches cibles, prédicats, tampon, couverture minimale et combinaison."""
        self.addParameter(QgsProcessingParameterMultipleLayers(
            self.TARGETS, self.tr("Layers to filter (vector, raster, point cloud)"),
            layerType=QgsProcessing.SourceType.TypeMapLayer, optional=self.targets_optional()))
        self.addParameter(QgsProcessingParameterEnum(
            self.PREDICATES, self.tr("Geometric predicates"), options=list(PREDICATES),
            allowMultiple=True, defaultValue=[0]))
        self.addParameter(buffer_parameter or QgsProcessingParameterNumber(
            self.BUFFER, self.tr("Buffer (source units)"),
            type=QgsProcessingParameterNumber.Type.Double, defaultValue=0.0))
        self.addParameter(QgsProcessingParameterNumber(
            self.COVERAGE, self.tr("Minimum coverage of the target polygons (%)"),
            type=QgsProcessingParameterNumber.Type.Double, defaultValue=0.0, minValue=0.0, maxValue=100.0))
        self.add_operator_parameter(self.tr("Combine with the existing filter of the targets"))

    def targets_optional(self) -> bool:
        return False

    def targets_help(self):
        """Help paragraph shared by the cross filters (what each kind of target becomes)."""
        return self.tr(
            "Vector: subset of the features. Raster: pixels outside the area set to NoData (clipped VRT). "
            "Point cloud: points outside the area removed (derived COPC file, PDAL). Disjoint keeps the outside.\n\n"
            "Only project layers are filtered. The filter can be undone from FilterMate and the original sources "
            "are always recorded in the project. The \"Processed layers\" output can be chained in a model, "
            "for example into \"Export filtered layers\".")

    def add_operator_parameter(self, label, name=None):
        self.addParameter(QgsProcessingParameterEnum(
            name or self.OPERATOR, label, options=[self.tr("Replace"), "AND", "OR", "AND NOT"], defaultValue=0))

    def add_point_cloud_criteria_parameters(self, prefix=""):
        """Classes ASPRS, plages Z et intensité, numéro de retour, expression."""
        number = QgsProcessingParameterNumber.Type.Double
        self.addParameter(QgsProcessingParameterString(
            prefix + "CLASSES", self.tr("ASPRS classes to keep (e.g. 3,4,5; empty = all)"), optional=True))
        for name, label in (("Z_MIN", self.tr("Minimum Z")), ("Z_MAX", self.tr("Maximum Z")),
                            ("INTENSITY_MIN", self.tr("Minimum intensity")),
                            ("INTENSITY_MAX", self.tr("Maximum intensity"))):
            self.addParameter(QgsProcessingParameterNumber(prefix + name, label, type=number, optional=True))
        self.addParameter(QgsProcessingParameterNumber(
            prefix + "RETURN_NUMBER", self.tr("Return number (empty = all)"),
            type=QgsProcessingParameterNumber.Type.Integer, optional=True, minValue=1, maxValue=15))
        self.addParameter(QgsProcessingParameterString(
            prefix + "EXPRESSION", self.tr("Point cloud expression (e.g. ReturnNumber = NumberOfReturns)"),
            optional=True, multiLine=False))

    def add_output(self):
        self.addOutput(QgsProcessingOutputMultipleLayers(self.OUTPUT, self.tr("Processed layers")))
        # Noms des couches traitées / en échec (résultats de processing.run) : déclarés quand
        # QGIS sait décrire une liste (QGIS 3.28+), sans libellé traduit de plus.
        if QgsProcessingOutputVariant is not None:
            self.addOutput(QgsProcessingOutputVariant(self.LAYERS_FILTERED, self.LAYERS_FILTERED))
            self.addOutput(QgsProcessingOutputVariant(self.LAYERS_FAILED, self.LAYERS_FAILED))

    # --- lecture des paramètres --------------------------------------------------

    @staticmethod
    def optional_number(algorithm, parameters, name, context, integer=False):
        """Valeur d'un nombre optionnel, None quand il n'est pas renseigné."""
        value = parameters.get(name)
        if value is None or value == "":
            return None
        if integer:
            return algorithm.parameterAsInt(parameters, name, context)
        return algorithm.parameterAsDouble(parameters, name, context)

    def point_cloud_criteria(self, parameters, context, prefix=""):
        """PointCloudFilterCriteria lus depuis les paramètres (None quand ils sont vides)."""
        from ...core.domain.api_requests import point_cloud_criteria_from_values
        number = lambda name: self.optional_number(self, parameters, prefix + name, context)  # noqa: E731
        try:
            criteria = point_cloud_criteria_from_values(
                classes=self.parameterAsString(parameters, prefix + "CLASSES", context),
                z_min=number("Z_MIN"), z_max=number("Z_MAX"),
                intensity_min=number("INTENSITY_MIN"), intensity_max=number("INTENSITY_MAX"),
                return_number=self.optional_number(self, parameters, prefix + "RETURN_NUMBER", context, integer=True),
                expression=self.parameterAsString(parameters, prefix + "EXPRESSION", context))
        except ValueError as exc:
            raise QgsProcessingException(str(exc))
        return None if criteria.is_empty else criteria

    def target_settings(self, parameters, context):
        """Arguments communs des opérations de filtre croisé."""
        predicates = tuple(PREDICATES[i] for i in self.parameterAsEnums(parameters, self.PREDICATES, context))
        return dict(
            predicates=predicates or ("Intersect",),
            buffer=self.parameterAsDouble(parameters, self.BUFFER, context),
            coverage_min=self.parameterAsDouble(parameters, self.COVERAGE, context),
            operator=OPERATORS[self.parameterAsEnum(parameters, self.OPERATOR, context)])

    # --- rapport -----------------------------------------------------------------

    def finish(self, report, feedback, verb=None):
        """Journal du rapport d'opération et dictionnaire de résultats Processing."""
        for name, reason in report.skipped.items():
            feedback.pushWarning(self.tr("Layer skipped: {0} ({1})").format(name, reason))
        if report.error:
            raise QgsProcessingException(report.error)
        verb = verb or self.tr("filtered")
        layers = report.details.get("layers", {})
        for layer_id, name in report.done.items():
            info = layers.get(name) or {}
            suffix = ""
            if info.get("seconds") is not None:
                suffix = self.tr(" ({0:.1f} s)").format(info["seconds"])
            if name in report.outputs:
                suffix = " → " + report.outputs[name]
            feedback.pushInfo(self.tr("{0}: {1}{2}").format(name, verb, suffix))
        for name, message in report.failed.items():
            feedback.reportError(self.tr("{0}: failed — {1}").format(name, message))
        return {
            self.OUTPUT: report.done_ids,
            self.LAYERS_FILTERED: report.done_names,
            self.LAYERS_FAILED: list(report.failed),
        }


def advanced(parameter):
    """Range un paramètre dans les « paramètres avancés »."""
    from qgis.core import Qgis
    flag = getattr(getattr(Qgis, "ProcessingParameterFlag", None), "Advanced", None)
    if flag is None:
        flag = QgsProcessingParameterDefinition.FlagAdvanced
    parameter.setFlags(parameter.flags() | flag)
    return parameter


__all__ = ["FilterMateAlgorithm", "QgsProcessingParameterPointCloudLayer", "QgsProcessingParameterBoolean",
           "advanced", "point_cloud_layer_type"]
