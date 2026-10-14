# -*- coding: utf-8 -*-
"""
Build the Processing models shipped with FilterMate (``processing/models/*.model3``).

The models chain the ``filtermate:*`` algorithms (and native ones) for the
common FilterMate 5 recipes. They are generated here rather than drawn in the
modeler so they stay reviewable and reproducible. Run with the QGIS Python::

    "C:\\Program Files\\QGIS 4.2.3\\bin\\python-qgis.bat" build_processing_models.py [<output_dir>]

The default output is ``processing/models`` next to this script. Users can
open a shipped model in the modeler (Model > Open) and save their own copy.
"""
import os
import sys

from qgis.core import QgsApplication

app = QgsApplication([], False)
app.initQgis()
sys.path.append(os.path.join(os.environ.get('QGIS_PREFIX_PATH', ''), 'python', 'plugins'))  # processing

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))  # parent of the plugin folder

from processing.core.Processing import Processing  # noqa: E402
from qgis.core import (  # noqa: E402
    QgsProcessing,
    QgsProcessingModelAlgorithm,
    QgsProcessingModelChildAlgorithm,
    QgsProcessingModelChildParameterSource,
    QgsProcessingModelOutput,
    QgsProcessingModelParameter,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterMultipleLayers,
    QgsProcessingParameterNumber,
    QgsProcessingParameterPointCloudLayer,
    QgsProcessingParameterRasterLayer,
    QgsProcessingParameterString,
    QgsProcessingParameterVectorLayer,
)
from qgis.PyQt.QtCore import QPointF  # noqa: E402

plugin_package = os.path.basename(os.path.dirname(HERE))
provider_module = __import__(f"{plugin_package}.processing.provider", fromlist=['FilterMateProcessingProvider'])

Processing.initialize()
registry = QgsApplication.processingRegistry()
if registry.providerById('filtermate') is None:
    registry.addProvider(provider_module.FilterMateProcessingProvider())

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(HERE), 'processing', 'models')
os.makedirs(OUT, exist_ok=True)
GROUP = "Modèles FilterMate"
DOUBLE = QgsProcessingParameterNumber.Type.Double


def static(value):
    return [QgsProcessingModelChildParameterSource.fromStaticValue(value)]


def model_input(name):
    return [QgsProcessingModelChildParameterSource.fromModelParameter(name)]


def child_output(child_id, output):
    return [QgsProcessingModelChildParameterSource.fromChildOutput(child_id, output)]


class Builder:
    """Small helper over QgsProcessingModelAlgorithm: inputs on the left, children in a column."""

    def __init__(self, name, title, help_text):
        self.model = QgsProcessingModelAlgorithm(title, GROUP)
        self.model.setName(name)
        self.model.setHelpContent({'ALG_DESC': help_text, 'ALG_CREATOR': 'FilterMate',
                                   'ALG_VERSION': '5.0'})
        self._inputs = 0
        self._children = 0

    def add_input(self, parameter):
        component = QgsProcessingModelParameter(parameter.name())
        component.setPosition(QPointF(140, 80 + 90 * self._inputs))
        component.setDescription(parameter.description())
        self.model.addModelParameter(parameter, component)
        self._inputs += 1
        return parameter.name()

    def add_child(self, child_id, algorithm_id, description, sources, outputs=None):
        child = QgsProcessingModelChildAlgorithm(algorithm_id)
        child.setChildId(child_id)
        child.setDescription(description)
        child.setPosition(QPointF(520, 120 + 160 * self._children))
        for parameter, value in sources.items():
            child.addParameterSources(parameter, value)
        if outputs:
            model_outputs = {}
            for index, (child_output_name, (name, title)) in enumerate(outputs.items()):
                output = QgsProcessingModelOutput(name, title)
                output.setChildId(child_id)
                output.setChildOutputName(child_output_name)
                output.setPosition(QPointF(820, 120 + 160 * self._children + 60 * index))
                model_outputs[name] = output
            child.setModelOutputs(model_outputs)
        self.model.addChildAlgorithm(child)
        self._children += 1
        return child_id

    def save(self):
        self.model.updateDestinationParameters()
        path = os.path.join(OUT, f"{self.model.name()}.model3")
        if not self.model.toFile(path):
            raise RuntimeError(f"could not write {path}")
        ok, errors = True, []
        if hasattr(self.model, 'validate'):
            result = self.model.validate()
            ok, errors = result if isinstance(result, tuple) else (bool(result), [])
        print(f"{'OK ' if ok else 'INVALID '} {path} {errors if not ok else ''}", flush=True)
        return ok


def any_layers(name, description, layer_type=QgsProcessing.SourceType.TypeMapLayer):
    return QgsProcessingParameterMultipleLayers(name, description, layerType=layer_type)


# 1. Delivery package for an area: area -> any layers -> files ---------------------------------
def delivery_package():
    b = Builder(
        'extraction_par_emprise', "Extraction de données par emprise (vecteur, raster, nuage)",
        "Filtre les couches choisies (BD TOPO, MNT, LiDAR...) par les entités d'une couche d'emprise "
        "(communes, zone d'étude), puis écrit un fichier par couche : GPKG pour les vecteurs, COG pour "
        "les rasters, LAZ pour les nuages.\n\nEn traitement par lot, itérez sur les entités de l'emprise "
        "(bouton d'itération) pour produire un paquet par commune.")
    area = b.add_input(QgsProcessingParameterVectorLayer('emprise', "Couche d'emprise",
                                                          [QgsProcessing.SourceType.TypeVectorPolygon]))
    selected = b.add_input(QgsProcessingParameterBoolean('selection_seule', "Entités sélectionnées uniquement",
                                                         defaultValue=True))
    layers = b.add_input(any_layers('couches', "Couches à extraire"))
    buffer = b.add_input(QgsProcessingParameterNumber('tampon', "Tampon autour de l'emprise", type=DOUBLE,
                                                      defaultValue=0.0))
    b.add_child('filtre', 'filtermate:cross_filter', "Filtrer par l'emprise", {
        'SOURCE': model_input(area), 'SELECTED_ONLY': model_input(selected), 'TARGETS': model_input(layers),
        'PREDICATES': static([0]), 'BUFFER': model_input(buffer), 'COVERAGE': static(0.0), 'OPERATOR': static(0)})
    b.add_child('export', 'filtermate:export_filtered_layers', "Écrire les couches filtrées", {
        'LAYERS': child_output('filtre', 'OUTPUT'), 'VECTOR_FORMAT': static(0), 'RASTER_FORMAT': static(0),
        'POINT_CLOUD_FORMAT': static(0)}, outputs={'OUTPUT_FOLDER': ('dossier', "Dossier de sortie")})
    return b.save()


# 2. High vegetation near power lines: classes -> buffer of the lines -> COPC --------------------
def vegetation_near_lines():
    b = Builder(
        'vegetation_pres_des_lignes', "Végétation haute près des lignes (LiDAR)",
        "Garde les points de végétation (classes ASPRS 4 et 5 par défaut) des nuages choisis, limite les "
        "nuages au couloir autour des lignes (tampon) et écrit les points restants en COPC. Points de départ "
        "d'un contrôle d'élagage : lignes électriques, voies ferrées, routes.")
    lines = b.add_input(QgsProcessingParameterVectorLayer('lignes', "Lignes (réseau)",
                                                           [QgsProcessing.SourceType.TypeVectorLine]))
    clouds = b.add_input(any_layers('nuages', "Nuages de points", QgsProcessing.SourceType.TypeMapLayer))
    classes = b.add_input(QgsProcessingParameterString('classes', "Classes de végétation", defaultValue="4,5"))
    corridor = b.add_input(QgsProcessingParameterNumber('couloir', "Demi-largeur du couloir", type=DOUBLE,
                                                        defaultValue=10.0, minValue=0.0))
    b.add_child('classes', 'filtermate:filter_point_cloud', "Garder la végétation", {
        'LAYERS': model_input(clouds), 'CLASSES': model_input(classes), 'OPERATOR': static(0)})
    b.add_child('couloir', 'filtermate:cross_filter', "Limiter au couloir des lignes", {
        'SOURCE': model_input(lines), 'SELECTED_ONLY': static(False), 'TARGETS': child_output('classes', 'OUTPUT'),
        'PREDICATES': static([0]), 'BUFFER': model_input(corridor), 'COVERAGE': static(0.0), 'OPERATOR': static(0)})
    b.add_child('export', 'filtermate:export_filtered_layers', "Écrire les points en COPC", {
        'LAYERS': child_output('couloir', 'OUTPUT'), 'VECTOR_FORMAT': static(0), 'RASTER_FORMAT': static(0),
        'POINT_CLOUD_FORMAT': static(1)}, outputs={'OUTPUT_FOLDER': ('dossier', "Dossier de sortie")})
    return b.save()


# 3. Gentle slopes: DTM -> slope -> range -> parcels with a minimum coverage ----------------------
def gentle_slopes():
    b = Builder(
        'parcelles_en_pente_faible', "Parcelles en pente faible (MNT)",
        "Calcule la pente du MNT (native:slope), retient les pixels sous la pente maximale et garde les "
        "couches cibles (parcelles, bâtiments...) dont au moins la part choisie de la surface est dans cette "
        "zone, puis écrit le résultat en GPKG.")
    dtm = b.add_input(QgsProcessingParameterRasterLayer('mnt', "MNT"))
    slope_max = b.add_input(QgsProcessingParameterNumber('pente_max', "Pente maximale (degrés)", type=DOUBLE,
                                                         defaultValue=15.0, minValue=0.0, maxValue=90.0))
    targets = b.add_input(any_layers('cibles', "Couches à filtrer (parcelles...)",
                                     QgsProcessing.SourceType.TypeVectorPolygon))
    coverage = b.add_input(QgsProcessingParameterNumber('couverture', "Part minimale en pente faible (%)",
                                                        type=DOUBLE, defaultValue=50.0, minValue=0.0,
                                                        maxValue=100.0))
    b.add_child('pente', 'native:slope', "Pente du MNT", {
        'INPUT': model_input(dtm), 'Z_FACTOR': static(1.0),
        'OUTPUT': static(QgsProcessing.TEMPORARY_OUTPUT)})
    b.add_child('zone', 'filtermate:cross_filter_from_raster', "Parcelles dans la zone de pente faible", {
        'SOURCE': child_output('pente', 'OUTPUT'), 'BAND': static(1), 'MODE': static(0),
        'MINIMUM': static(0.0), 'MAXIMUM': model_input(slope_max), 'FILTER_SOURCE': static(False),
        'TARGETS': model_input(targets), 'PREDICATES': static([0]), 'BUFFER': static(0.0),
        'COVERAGE': model_input(coverage), 'OPERATOR': static(0)})
    b.add_child('export', 'filtermate:export_filtered_layers', "Écrire les couches filtrées", {
        'LAYERS': child_output('zone', 'OUTPUT'), 'VECTOR_FORMAT': static(0), 'RASTER_FORMAT': static(0),
        'POINT_CLOUD_FORMAT': static(0)}, outputs={'OUTPUT_FOLDER': ('dossier', "Dossier de sortie")})
    return b.save()


# 4. Buildings missing from the point cloud: class 6 footprint, Disjoint ---------------------------
def buildings_missing_from_lidar():
    b = Builder(
        'batiments_absents_du_lidar', "Bâtiments absents du nuage LiDAR (contrôle)",
        "Calcule l'empreinte des points de classe bâtiment (6) du nuage et garde les bâtiments qui ne la "
        "touchent pas (prédicat Disjoint) : bâtiments démolis, non relevés ou mal classés. Le nuage source "
        "reste filtré sur la classe choisie (annulable depuis FilterMate).")
    cloud = b.add_input(QgsProcessingParameterPointCloudLayer('nuage', "Nuage de points"))
    classes = b.add_input(QgsProcessingParameterString('classes', "Classes bâtiment", defaultValue="6"))
    buildings = b.add_input(any_layers('batiments', "Bâtiments", QgsProcessing.SourceType.TypeVectorPolygon))
    b.add_child('absents', 'filtermate:cross_filter_from_point_cloud', "Bâtiments sans point de la classe", {
        'SOURCE': model_input(cloud), 'CLASSES': model_input(classes), 'SOURCE_OPERATOR': static(0),
        'TARGETS': model_input(buildings), 'PREDICATES': static([2]), 'BUFFER': static(0.0),
        'COVERAGE': static(0.0), 'OPERATOR': static(0), 'RESOLUTION': static(2.0)})
    b.add_child('export', 'filtermate:export_filtered_layers', "Écrire les bâtiments retenus", {
        'LAYERS': child_output('absents', 'OUTPUT'), 'VECTOR_FORMAT': static(0), 'RASTER_FORMAT': static(0),
        'POINT_CLOUD_FORMAT': static(0)}, outputs={'OUTPUT_FOLDER': ('dossier', "Dossier de sortie")})
    return b.save()


results = [delivery_package(), vegetation_near_lines(), gentle_slopes(), buildings_missing_from_lidar()]
print(f"{sum(results)}/{len(results)} models valid", flush=True)
