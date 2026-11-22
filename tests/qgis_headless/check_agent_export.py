"""export_layers in a real (headless) QGIS: style files beside the files (QML, SLD), every vector layer in one
GeoPackage, everything in one zip never overwritten, and the formats KML, XLSX and GeoParquet (refused when GDAL
lacks the driver). Each file is opened again to check what it holds.

    docker run --rm -v "$PWD":/src -e QT_QPA_PLATFORM=offscreen qgis/qgis:ltr \\
        sh -c 'cd /tmp && xvfb-run -a python3 /src/tests/qgis_headless/check_agent_export.py'

Prints one PASS / FAIL line per check; exits with 1 when one failed.
"""
import json
import os
import sqlite3
import sys
import tempfile
import zipfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from qgis.core import (  # noqa: E402
    QgsApplication, QgsFeature, QgsField, QgsFields, QgsGeometry, QgsPointXY, QgsProject, QgsRasterLayer,
    QgsRectangle, QgsVectorFileWriter, QgsVectorLayer,
)
from qgis.PyQt.QtCore import QVariant  # noqa: E402
from qgis.PyQt.QtGui import QColor  # noqa: E402

RESULTS = []
RED = QColor(255, 0, 0)


def check(label, condition, detail=""):
    RESULTS.append(bool(condition))
    print(f"{'PASS' if condition else 'FAIL'} {label}" + (f" -- {str(detail)[:400]}" if not condition else ""))


def write_vector(path, geometry, rows):
    fields = QgsFields()
    fields.append(QgsField("nom", QVariant.String))
    fields.append(QgsField("dept", QVariant.String))
    fields.append(QgsField("pop", QVariant.Int))
    memory = QgsVectorLayer(f"{geometry}?crs=EPSG:2154", "memory", "memory")
    memory.dataProvider().addAttributes(fields.toList())
    memory.updateFields()
    features = []
    for index, shape in enumerate(rows):
        feature = QgsFeature(memory.fields())
        feature.setGeometry(shape)
        feature.setAttributes([f"Item {index + 1:02d}", "31" if index < 7 else "32", 100 * (index + 1)])
        features.append(feature)
    memory.dataProvider().addFeatures(features)
    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName = "GPKG"
    QgsVectorFileWriter.writeAsVectorFormatV2(memory, path, QgsProject.instance().transformContext(), options)


def write_raster(path):
    from osgeo import gdal, osr
    dataset = gdal.GetDriverByName("GTiff").Create(path, 10, 10, 1, gdal.GDT_Float32)
    dataset.SetGeoTransform((600000, 100, 0, 6290000, 0, -100))
    reference = osr.SpatialReference()
    reference.ImportFromEPSG(2154)
    dataset.SetProjection(reference.ExportToWkt())
    dataset.GetRasterBand(1).WriteArray(__import__("numpy").arange(100, dtype="float32").reshape(10, 10))
    dataset = None


def symbol_color(layer):
    symbol = layer.renderer().symbol() if hasattr(layer.renderer(), "symbol") else None
    return symbol.color() if symbol is not None else None


def tables_of(path):
    with sqlite3.connect(path) as connection:
        return sorted(row[0] for row in connection.execute("SELECT table_name FROM gpkg_contents"))


def styles_in(path):
    with sqlite3.connect(path) as connection:
        return sorted(row[0] for row in connection.execute("SELECT f_table_name FROM layer_styles"))


def main():
    from filter_mate.adapters.public_api import operations
    work = tempfile.mkdtemp()
    data = os.path.join(work, "data")
    os.makedirs(data)
    squares = [QgsGeometry.fromRect(QgsRectangle(600000 + (i % 4) * 5000, 6280000 + (i // 4) * 5000,
                                                 604000 + (i % 4) * 5000, 6284000 + (i // 4) * 5000))
               for i in range(12)]
    write_vector(os.path.join(data, "communes.gpkg"), "Polygon", squares)
    lines = [QgsGeometry.fromPolylineXY([QgsPointXY(600000 + i * 1000, 6280000),
                                         QgsPointXY(601000 + i * 1000, 6285000)]) for i in range(3)]
    write_vector(os.path.join(data, "routes.gpkg"), "LineString", lines)
    write_raster(os.path.join(data, "mnt.tif"))
    project = QgsProject.instance()
    communes = QgsVectorLayer(os.path.join(data, "communes.gpkg"), "communes", "ogr")
    routes = QgsVectorLayer(os.path.join(data, "routes.gpkg"), "routes", "ogr")
    twin = QgsVectorLayer(os.path.join(data, "communes.gpkg"), "COMMUNES", "ogr")
    mnt = QgsRasterLayer(os.path.join(data, "mnt.tif"), "mnt")
    for layer in (communes, routes, twin, mnt):
        project.addMapLayer(layer)
    communes.setSubsetString("\"dept\" = '31'")
    communes.renderer().symbol().setColor(RED)
    check("fixture valid", communes.featureCount() == 7 and routes.featureCount() == 3 and twin.featureCount() == 12
          and mnt.isValid())

    def export(name, layers, **options):
        folder = os.path.join(work, "out", name)
        return folder, operations.export_layers(layers, folder, project=project, **options)

    # --- as before: one file each, nothing more
    folder, report = export("plain", [communes, routes])
    check("default: one GeoPackage per layer, as before", report.ok and sorted(report.outputs) == ["communes", "routes"]
          and not report.package and not report.styles and not report.tables
          and sorted(os.listdir(folder)) == ["communes.gpkg", "routes.gpkg"], (report, os.listdir(folder)))
    check("default: the filter kept", QgsVectorLayer(report.outputs["communes"], "x", "ogr").featureCount() == 7)

    # --- styles beside the files
    folder, report = export("qml", [communes, mnt], vector_format="GeoJSON", styles="qml")
    check("qml: a .qml beside the GeoJSON and the raster", report.ok and sorted(os.listdir(folder)) ==
          ["communes.geojson", "communes.qml", "mnt.qml", "mnt.tif"] and report.styles == {
              "communes": os.path.join(folder, "communes.qml"), "mnt": os.path.join(folder, "mnt.qml")},
          (report, os.listdir(folder)))
    reopened = QgsVectorLayer(os.path.join(folder, "communes.geojson"), "again", "ogr")
    check("qml: QGIS opens the file with the style of the layer", reopened.featureCount() == 7
          and symbol_color(reopened) == RED, symbol_color(reopened))
    folder, report = export("sld", [communes], vector_format="ESRI Shapefile", styles="sld")
    sld = os.path.join(folder, "communes.sld")
    text = open(sld, encoding="utf-8").read() if os.path.isfile(sld) else ""
    check("sld: an SLD file beside the Shapefile", report.ok and "StyledLayerDescriptor" in text
          and "#ff0000" in text.lower(), (report, os.listdir(folder)))
    folder, report = export("csv", [communes], vector_format="CSV", styles="qml")
    check("styles: none beside a CSV", report.ok and os.listdir(folder) == ["communes.csv"] and not report.styles,
          os.listdir(folder))

    from filter_mate.core.export.style_exporter import StyleExporter, StyleFormat
    dock = os.path.join(work, "dock")
    os.makedirs(dock)
    StyleExporter().save_style(communes, os.path.join(dock, "communes.shp"), StyleFormat.SLD)
    check("dock: its SLD export writes the file (it went to the style database)",
          os.listdir(dock) == ["communes.sld"], os.listdir(dock))

    # --- every vector layer in one GeoPackage
    folder, report = export("single", [communes, routes, twin, mnt], single_file=True, styles="qml",
                            package_name="livraison.gpkg")
    gpkg = os.path.join(folder, "livraison.gpkg")
    check("single_file: one GeoPackage, the raster beside it", report.ok and report.package == gpkg
          and sorted(os.listdir(folder)) == ["livraison.gpkg", "mnt.qml", "mnt.tif"], (report, os.listdir(folder)))
    check("single_file: one table each, names unique ignoring case",
          report.tables == {"communes": "communes", "routes": "routes", "COMMUNES": "COMMUNES_2"}
          and tables_of(gpkg) == ["COMMUNES_2", "communes", "routes"], (report.tables, tables_of(gpkg)))
    check("single_file: each table holds its layer as filtered",
          QgsVectorLayer(f"{gpkg}|layername=communes", "x", "ogr").featureCount() == 7
          and QgsVectorLayer(f"{gpkg}|layername=COMMUNES_2", "x", "ogr").featureCount() == 12)
    inside = QgsVectorLayer(f"{gpkg}|layername=communes", "styled", "ogr")
    check("single_file: the styles inside, read by QGIS", styles_in(gpkg) == ["COMMUNES_2", "communes", "routes"]
          and symbol_color(inside) == RED and report.styles["communes"] == gpkg, (styles_in(gpkg), report.styles))
    folder, report = export("single_geojson", [communes], vector_format="GeoJSON", single_file=True)
    check("single_file: refused with another format", "GPKG" in report.error and not os.path.exists(folder), report)

    # --- one zip, never overwritten
    folder = os.path.join(work, "out", "zip")
    os.makedirs(folder)
    with open(os.path.join(folder, "communes.geojson"), "w") as handle:
        handle.write("keep")
    _, report = export("zip", [communes, routes, mnt], vector_format="GeoJSON", styles="qml", zip_archive=True)
    archive = os.path.join(folder, "export.zip")
    names = sorted(zipfile.ZipFile(archive).namelist()) if os.path.isfile(archive) else []
    check("zip: every file and style in export.zip", report.ok and report.package == archive and names ==
          ["communes.geojson", "communes.qml", "mnt.qml", "mnt.tif", "routes.geojson", "routes.qml"], (report, names))
    check("zip: outputs and styles name the files in it", report.outputs == {
        "communes": "communes.geojson", "routes": "routes.geojson", "mnt": "mnt.tif"}
        and report.styles["mnt"] == "mnt.qml", report)
    check("zip: a file of the folder is neither overwritten nor removed, nothing left beside",
          sorted(os.listdir(folder)) == ["communes.geojson", "export.zip"]
          and open(os.path.join(folder, "communes.geojson")).read() == "keep", os.listdir(folder))
    size = os.path.getsize(archive)
    _, again = export("zip", [routes], zip_archive=True)
    check("zip: a second one is export_2.zip, the first kept", again.package == os.path.join(folder, "export_2.zip")
          and os.path.getsize(archive) == size and zipfile.ZipFile(again.package).namelist() == ["routes.gpkg"],
          (again, os.listdir(folder)))
    extracted = tempfile.mkdtemp()
    zipfile.ZipFile(archive).extractall(extracted)
    check("zip: its files open", QgsVectorLayer(os.path.join(extracted, "communes.geojson"), "x", "ogr")
          .featureCount() == 7 and QgsRasterLayer(os.path.join(extracted, "mnt.tif"), "x").isValid())
    folder, report = export("zip_single", [communes, routes], single_file=True, zip_archive=True,
                            package_name="livraison")
    check("zip + single_file: the GeoPackage in livraison.zip",
          report.package == os.path.join(folder, "livraison.zip") and os.listdir(folder) == ["livraison.zip"]
          and zipfile.ZipFile(report.package).namelist() == ["livraison.gpkg"]
          and report.tables == {"communes": "communes", "routes": "routes"}, (report, os.listdir(folder)))

    # --- more formats
    folder, report = export("kml", [communes], vector_format="KML", crs=communes.crs())
    kml = QgsVectorLayer(report.outputs.get("communes", ""), "kml", "ogr")
    extent = kml.extent() if kml.isValid() else None
    check("KML: written and read again, in WGS 84 longitudes and latitudes", report.ok and kml.featureCount() == 7
          and extent is not None and -10 < extent.xMinimum() < 10 and 40 < extent.yMinimum() < 52,
          (report, extent.toString() if extent else None))
    folder, report = export("xlsx", [communes], vector_format="XLSX")
    sheet = QgsVectorLayer(report.outputs.get("communes", ""), "xlsx", "ogr")
    check("XLSX: a sheet of the features kept, with their fields", report.ok and sheet.featureCount() == 7
          and {"nom", "dept", "pop"} <= set(sheet.fields().names()), (report, sheet.fields().names()))
    has_parquet = "Parquet" in {item.driverName for item in QgsVectorFileWriter.supportedFiltersAndFormats()}
    folder, report = export("parquet", [communes], vector_format="GeoParquet")
    if has_parquet:
        parquet = QgsVectorLayer(report.outputs.get("communes", ""), "parquet", "ogr")
        check("GeoParquet: written and read again", report.ok and parquet.featureCount() == 7, report)
    else:
        check("GeoParquet: refused in words, nothing written (no Parquet driver here)",
              "no Parquet driver" in report.error and not os.listdir(folder), (report, os.listdir(folder)))

    # --- through the tool of the agent: paths from the sub-folder only
    from filter_mate.core.agent.messages import ToolCallPart
    from filter_mate.core.agent.tool_catalog import chat_tools
    from filter_mate.core.agent.tool_executor import ToolExecutor
    from filter_mate.filtermate_api.agent_tools import build_handlers
    from filter_mate.filtermate_api.qgis_accessor import QGISFilterMateAccessor
    root = os.path.join(work, "exports")
    executor = ToolExecutor(chat_tools(), build_handlers(QGISFilterMateAccessor(None, None), root))
    result = executor.execute(ToolCallPart("c", "export_layers", {
        "layers": ["communes", "mnt"], "subfolder": "envoi", "styles": "qml", "zip": True, "package_name": "envoi"}))
    answer = json.loads(result.content) if not result.is_error else {}
    check("tool: the zip and its files named from the sub-folder, no path of the machine",
          answer.get("package") == "envoi.zip" and answer.get("outputs") == {"communes": "communes.gpkg",
                                                                             "mnt": "mnt.tif"}
          and work not in result.content and os.path.isfile(os.path.join(root, "envoi", "envoi.zip")), result.content)
    result = executor.execute(ToolCallPart("c", "export_layers", {"layers": ["routes"], "subfolder": "plain"}))
    check("tool: a plain export answers as before", not result.is_error and json.loads(result.content).get("outputs")
          == {"routes": "routes.gpkg"} and "package" not in json.loads(result.content), result.content)


if __name__ == "__main__":
    app = QgsApplication([b"check_agent_export"], False)
    app.initQgis()
    package_root = tempfile.mkdtemp()
    os.symlink(os.environ.get("FM_REPO", "/src"), os.path.join(package_root, "filter_mate"))
    sys.path.insert(0, package_root)
    sys.dont_write_bytecode = True
    print(f"QGIS {__import__('qgis.core').core.Qgis.QGIS_VERSION}, Python {sys.version.split()[0]}")
    main()
    failed = RESULTS.count(False)
    print(f"{len(RESULTS) - failed}/{len(RESULTS)} passed")
    sys.stdout.flush()
    os._exit(1 if failed else 0)
