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
GROUP = "FilterMate models"
DOUBLE = QgsProcessingParameterNumber.Type.Double


# QGIS derives the name of a model's output parameter from its (displayed) description. The labels are in English
# but docs/AUTOMATION.md and qgis_process scripts address the French name, so it is pinned after writing.
STABLE_PARAMETER_NAMES = {'output_folder': 'dossier_de_sortie'}


def keep_parameter_names(path):
    """Rename the generated output parameters back to their historical names in the written .model3."""
    with open(path, encoding='utf-8') as handle:
        text = handle.read()
    for generated, stable in STABLE_PARAMETER_NAMES.items():
        if f'"{generated}"' not in text:
            print(f"WARNING: no '{generated}' parameter in {path}; check the output parameter name", flush=True)
        text = text.replace(f'"{generated}"', f'"{stable}"')
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(text)


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
        keep_parameter_names(path)
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
        'extraction_par_emprise', "Extract data by extent (vector, raster, point cloud)",
        "Filters the chosen layers (BD TOPO, DEM, LiDAR...) by the features of an extent layer "
        "(communes, study area), then writes one file per layer: GPKG for vectors, COG for "
        "rasters, LAZ for point clouds.\n\n"
        "In batch mode, iterate over the features of the extent layer (iteration button) to "
        "produce one package per commune.")
    area = b.add_input(QgsProcessingParameterVectorLayer('emprise', "Extent layer",
                                                          [QgsProcessing.SourceType.TypeVectorPolygon]))
    selected = b.add_input(QgsProcessingParameterBoolean('selection_seule', "Selected features only",
                                                         defaultValue=True))
    layers = b.add_input(any_layers('couches', "Layers to extract"))
    buffer = b.add_input(QgsProcessingParameterNumber('tampon', "Buffer around the extent", type=DOUBLE,
                                                      defaultValue=0.0))
    b.add_child('filtre', 'filtermate:cross_filter', "Filter by the extent", {
        'SOURCE': model_input(area), 'SELECTED_ONLY': model_input(selected), 'TARGETS': model_input(layers),
        'PREDICATES': static([0]), 'BUFFER': model_input(buffer), 'COVERAGE': static(0.0), 'OPERATOR': static(0)})
    b.add_child('export', 'filtermate:export_filtered_layers', "Write the filtered layers", {
        'LAYERS': child_output('filtre', 'OUTPUT'), 'VECTOR_FORMAT': static(0), 'RASTER_FORMAT': static(0),
        'POINT_CLOUD_FORMAT': static(0)}, outputs={'OUTPUT_FOLDER': ('dossier', "Output folder")})
    return b.save()


# 2. High vegetation near power lines: classes -> buffer of the lines -> COPC --------------------
def vegetation_near_lines():
    b = Builder(
        'vegetation_pres_des_lignes', "Tall vegetation near lines (LiDAR)",
        "Keeps the vegetation points (ASPRS classes 4 and 5 by default) of the chosen point "
        "clouds, limits the clouds to the corridor around the lines (buffer) and writes the "
        "remaining points as COPC. Starting points for a pruning check: power lines, railways, "
        "roads.")
    lines = b.add_input(QgsProcessingParameterVectorLayer('lignes', "Lines (network)",
                                                           [QgsProcessing.SourceType.TypeVectorLine]))
    clouds = b.add_input(any_layers('nuages', "Point clouds", QgsProcessing.SourceType.TypeMapLayer))
    classes = b.add_input(QgsProcessingParameterString('classes', "Vegetation classes", defaultValue="4,5"))
    corridor = b.add_input(QgsProcessingParameterNumber('couloir', "Corridor half-width", type=DOUBLE,
                                                        defaultValue=10.0, minValue=0.0))
    b.add_child('classes', 'filtermate:filter_point_cloud', "Keep the vegetation", {
        'LAYERS': model_input(clouds), 'CLASSES': model_input(classes), 'OPERATOR': static(0)})
    b.add_child('couloir', 'filtermate:cross_filter', "Limit to the line corridor", {
        'SOURCE': model_input(lines), 'SELECTED_ONLY': static(False), 'TARGETS': child_output('classes', 'OUTPUT'),
        'PREDICATES': static([0]), 'BUFFER': model_input(corridor), 'COVERAGE': static(0.0), 'OPERATOR': static(0)})
    b.add_child('export', 'filtermate:export_filtered_layers', "Write the points as COPC", {
        'LAYERS': child_output('couloir', 'OUTPUT'), 'VECTOR_FORMAT': static(0), 'RASTER_FORMAT': static(0),
        'POINT_CLOUD_FORMAT': static(1)}, outputs={'OUTPUT_FOLDER': ('dossier', "Output folder")})
    return b.save()


# 3. Gentle slopes: DTM -> slope -> range -> parcels with a minimum coverage ----------------------
def gentle_slopes():
    b = Builder(
        'parcelles_en_pente_faible', "Parcels on gentle slopes (DTM)",
        "Computes the slope of the DTM (native:slope), keeps the pixels under the maximum slope "
        "and keeps the target layers (parcels, buildings...) of which at least the chosen share "
        "of the area is in this zone, then writes the result as GPKG.")
    dtm = b.add_input(QgsProcessingParameterRasterLayer('mnt', "DTM"))
    slope_max = b.add_input(QgsProcessingParameterNumber('pente_max', "Maximum slope (degrees)", type=DOUBLE,
                                                         defaultValue=15.0, minValue=0.0, maxValue=90.0))
    targets = b.add_input(any_layers('cibles', "Layers to filter (parcels...)",
                                     QgsProcessing.SourceType.TypeVectorPolygon))
    coverage = b.add_input(QgsProcessingParameterNumber('couverture', "Minimum share on a gentle slope (%)",
                                                        type=DOUBLE, defaultValue=50.0, minValue=0.0,
                                                        maxValue=100.0))
    b.add_child('pente', 'native:slope', "DTM slope", {
        'INPUT': model_input(dtm), 'Z_FACTOR': static(1.0),
        'OUTPUT': static(QgsProcessing.TEMPORARY_OUTPUT)})
    b.add_child('zone', 'filtermate:cross_filter_from_raster', "Parcels in the gentle slope zone", {
        'SOURCE': child_output('pente', 'OUTPUT'), 'BAND': static(1), 'MODE': static(0),
        'MINIMUM': static(0.0), 'MAXIMUM': model_input(slope_max), 'FILTER_SOURCE': static(False),
        'TARGETS': model_input(targets), 'PREDICATES': static([0]), 'BUFFER': static(0.0),
        'COVERAGE': model_input(coverage), 'OPERATOR': static(0)})
    b.add_child('export', 'filtermate:export_filtered_layers', "Write the filtered layers", {
        'LAYERS': child_output('zone', 'OUTPUT'), 'VECTOR_FORMAT': static(0), 'RASTER_FORMAT': static(0),
        'POINT_CLOUD_FORMAT': static(0)}, outputs={'OUTPUT_FOLDER': ('dossier', "Output folder")})
    return b.save()


# 4. Buildings missing from the point cloud: class 6 footprint, Disjoint ---------------------------
def buildings_missing_from_lidar():
    b = Builder(
        'batiments_absents_du_lidar', "Buildings missing from the LiDAR point cloud (check)",
        "Computes the footprint of the building class (6) points of the point cloud and keeps the "
        "buildings that do not touch it (Disjoint predicate): demolished, unsurveyed or "
        "misclassified buildings. The source cloud stays filtered on the chosen class (can be "
        "undone from FilterMate).")
    cloud = b.add_input(QgsProcessingParameterPointCloudLayer('nuage', "Point cloud"))
    classes = b.add_input(QgsProcessingParameterString('classes', "Building classes", defaultValue="6"))
    buildings = b.add_input(any_layers('batiments', "Buildings", QgsProcessing.SourceType.TypeVectorPolygon))
    b.add_child('absents', 'filtermate:cross_filter_from_point_cloud', "Buildings without a point of the class", {
        'SOURCE': model_input(cloud), 'CLASSES': model_input(classes), 'SOURCE_OPERATOR': static(0),
        'TARGETS': model_input(buildings), 'PREDICATES': static([2]), 'BUFFER': static(0.0),
        'COVERAGE': static(0.0), 'OPERATOR': static(0), 'RESOLUTION': static(2.0)})
    b.add_child('export', 'filtermate:export_filtered_layers', "Write the kept buildings", {
        'LAYERS': child_output('absents', 'OUTPUT'), 'VECTOR_FORMAT': static(0), 'RASTER_FORMAT': static(0),
        'POINT_CLOUD_FORMAT': static(0)}, outputs={'OUTPUT_FOLDER': ('dossier', "Output folder")})
    return b.save()


results = [delivery_package(), vegetation_near_lines(), gentle_slopes(), buildings_missing_from_lidar()]
print(f"{sum(results)}/{len(results)} models valid", flush=True)
