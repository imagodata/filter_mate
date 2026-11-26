"""Verify the Processing model API used by the processing-models skill in a real QGIS."""
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from qgis.core import (
    Qgis, QgsApplication, QgsFeature, QgsGeometry, QgsPointXY, QgsProcessingModelAlgorithm,
    QgsProcessingModelChildAlgorithm, QgsProcessingModelChildParameterSource, QgsProcessingModelOutput,
    QgsProcessingModelParameter, QgsProcessingParameterFeatureSource, QgsProcessingParameterNumber, QgsVectorLayer,
)


def build_model():
    model = QgsProcessingModelAlgorithm()
    model.setName("buffer_centroids")
    model.setGroup("FilterMate")
    for definition in (QgsProcessingParameterFeatureSource("INPUT", "Input layer"),
                       QgsProcessingParameterNumber("DISTANCE", "Distance", defaultValue=500)):
        component = QgsProcessingModelParameter()
        component.setParameterName(definition.name())
        model.addModelParameter(definition, component)
    source = QgsProcessingModelChildParameterSource
    buffer = QgsProcessingModelChildAlgorithm("native:buffer")
    buffer.setChildId("buffer")
    sources = {
        "INPUT": [source.fromModelParameter("INPUT")],
        "DISTANCE": [source.fromModelParameter("DISTANCE")],
        "SEGMENTS": [source.fromStaticValue(5)],
        "END_CAP_STYLE": [source.fromStaticValue(0)],
        "JOIN_STYLE": [source.fromStaticValue(0)],
        "MITER_LIMIT": [source.fromStaticValue(2)],
        "DISSOLVE": [source.fromStaticValue(False)],
        "OUTPUT": [source.fromStaticValue("TEMPORARY_OUTPUT")],
    }
    for parameter, values in sources.items():
        buffer.addParameterSources(parameter, values)
    assert model.addChildAlgorithm(buffer) == "buffer"
    centroids = QgsProcessingModelChildAlgorithm("native:centroids")
    centroids.setChildId("centroids")
    centroids.addParameterSources("INPUT", [source.fromChildOutput("buffer", "OUTPUT")])
    centroids.addParameterSources("ALL_PARTS", [source.fromStaticValue(False)])
    output = QgsProcessingModelOutput()
    output.setName("RESULT")
    output.setDescription("Centroids of buffers")
    output.setChildId("centroids")
    output.setChildOutputName("OUTPUT")
    centroids.setModelOutputs({"RESULT": output})
    assert model.addChildAlgorithm(centroids) == "centroids"
    model.updateDestinationParameters()
    return model


def main():
    sys.path.insert(0, "/usr/share/qgis/python/plugins")
    from processing.core.Processing import Processing
    import processing

    Processing.initialize()
    model = build_model()
    valid, issues = model.validate()
    assert valid, issues
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "buffer_centroids.model3"
        assert not path.exists()
        assert model.toFile(str(path))
        restored = QgsProcessingModelAlgorithm()
        assert restored.fromFile(str(path))
        valid, issues = restored.validate()
        assert valid, issues
        children = restored.childAlgorithms()
        assert {name: child.algorithmId() for name, child in children.items()} == {
            "buffer": "native:buffer", "centroids": "native:centroids"}
        connection = children["centroids"].parameterSources()["INPUT"][0]
        assert connection.outputChildId() == "buffer" and connection.outputName() == "OUTPUT"
        assert restored.parameterDefinition("DISTANCE").defaultValue() == 500
        layer = QgsVectorLayer("Point?crs=EPSG:2154", "Input", "memory")
        features = []
        for number in range(2):
            feature = QgsFeature()
            feature.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(600000 + number * 2000, 6280000)))
            features.append(feature)
        layer.dataProvider().addFeatures(features)
        destinations = restored.destinationParameterDefinitions()
        assert len(destinations) == 1
        destination = destinations[0].name()
        result = processing.run(restored, {"INPUT": layer, "DISTANCE": 500, destination: "TEMPORARY_OUTPUT"})
        assert result[destination].featureCount() == 2
        print("PASS .model3 saved, reloaded, validated and executed: buffer -> centroids, 2 features")


if __name__ == "__main__":
    application = QgsApplication([], False)
    application.initQgis()
    print(f"QGIS {Qgis.QGIS_VERSION}", flush=True)
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        sys.stdout.flush()
        os._exit(1)
    sys.stdout.flush()
    os._exit(0)
