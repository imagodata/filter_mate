#!/usr/bin/env python3
"""Create a portable Kathmandu QGIS project for the FilterMate walkthrough."""

import os
import sys

from qgis.core import (
    Qgis,
    QgsApplication,
    QgsColorRampShader,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsProject,
    QgsReferencedRectangle,
    QgsRasterLayer,
    QgsRasterShader,
    QgsRectangle,
    QgsSingleBandPseudoColorRenderer,
    QgsVectorLayer,
)
from qgis.PyQt.QtGui import QColor


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage: create_project.py <demo-directory>")

    demo_dir = os.path.abspath(sys.argv[1])
    data_dir = os.path.join(demo_dir, "data")
    app = QgsApplication([], False)
    app.initQgis()

    project = QgsProject.instance()
    project.setTitle("Kathmandu terrain and mapped services | FilterMate")
    project.setCrs(QgsCoordinateReferenceSystem("EPSG:32645"))

    slope = QgsRasterLayer(
        os.path.join(data_dir, "slope-percent.tif"),
        "SRTM slope (%)",
    )
    roads = QgsVectorLayer(
        os.path.join(data_dir, "roads.gpkg") + "|layername=roads",
        "OSM roads",
        "ogr",
    )
    schools = QgsVectorLayer(
        os.path.join(data_dir, "schools.gpkg") + "|layername=schools",
        "OSM schools",
        "ogr",
    )
    layers = (slope, roads, schools)
    invalid = [layer.name() for layer in layers if not layer.isValid()]
    if invalid:
        raise RuntimeError("Invalid project layers: " + ", ".join(invalid))

    ramp = QgsColorRampShader()
    ramp.setColorRampType(QgsColorRampShader.Interpolated)
    ramp.setMinimumValue(0)
    ramp.setMaximumValue(24)
    ramp.setColorRampItemList(
        [
            QgsColorRampShader.ColorRampItem(0, QColor("#173b57"), "0%"),
            QgsColorRampShader.ColorRampItem(10, QColor("#36a98a"), "10%"),
            QgsColorRampShader.ColorRampItem(20, QColor("#f2c14e"), "20%"),
            QgsColorRampShader.ColorRampItem(24, QColor("#d1495b"), "24%"),
        ]
    )
    shader = QgsRasterShader()
    shader.setRasterShaderFunction(ramp)
    renderer = QgsSingleBandPseudoColorRenderer(
        slope.dataProvider(), 1, shader
    )
    renderer.setClassificationMin(0)
    renderer.setClassificationMax(24)
    slope.setRenderer(renderer)

    roads.renderer().symbol().setColor(QColor("#f8f6f0"))
    roads.renderer().symbol().setWidth(0.45)
    schools.renderer().symbol().setColor(QColor("#e45756"))
    schools.renderer().symbol().setSize(2.2)

    for layer in layers:
        project.addMapLayer(layer)

    source_crs = QgsCoordinateReferenceSystem("EPSG:4326")
    project_crs = project.crs()
    transform = QgsCoordinateTransform(
        source_crs, project_crs, project.transformContext()
    )
    extent = transform.transformBoundingBox(
        QgsRectangle(85.3, 27.71, 85.31, 27.72)
    )
    extent.scale(1.12)
    project.viewSettings().setDefaultViewExtent(
        QgsReferencedRectangle(extent, project_crs)
    )

    output_path = os.path.join(demo_dir, "Kathmandu_FilterMate.qgz")
    project.setFileName(output_path)
    if not project.write():
        raise RuntimeError("Could not save " + output_path)
    print(f"Project: {output_path}")
    print(f"QGIS: {Qgis.QGIS_VERSION}")
    for layer in layers:
        print(f"{layer.name()}: {layer.featureCount() if isinstance(layer, QgsVectorLayer) else layer.width() * layer.height()}")
    app.exitQgis()


if __name__ == "__main__":
    main()
