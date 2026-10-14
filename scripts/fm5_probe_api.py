# Sonde FilterMate 5.0 (14/10/2026) : liste les classes, fournisseurs et algos Processing raster / nuage
# disponibles dans une installation QGIS. Lancer avec python-qgis.bat.
import sys
from qgis.core import Qgis, QgsApplication
print("QGIS", Qgis.version())
app = QgsApplication([], False); app.initQgis()
import qgis.core as c
import qgis.analysis as a
print("analysis:", [n for n in ("QgsRasterCalcNode","QgsRasterCalculator","QgsZonalStatistics") if hasattr(a,n)])
for n in ["QgsPointCloudLayerExporter","QgsPointCloudLayerExporterTask","QgsPointCloudDataProvider",
          "QgsRasterTransparency","QgsRasterCalcNode","QgsRasterCalculator","QgsZonalStatistics",
          "QgsPointCloudExpression","QgsMapClippingRegion","QgsRasterDataProvider","QgsVirtualRasterProvider",
          "QgsRasterLayerElevationProperties","QgsPointCloudStatistics","QgsRasterFileWriter"]:
    print(n, hasattr(c, n))
E = c.QgsPointCloudLayerExporter
print("exporter methods:", [m for m in dir(E) if not m.startswith("_")][:80])
print("pc provider methods:", [m for m in dir(c.QgsPointCloudDataProvider) if m in ("identify","subsetString","setSubsetString","supportsSubsetString","polygonBounds","pointCount","index","generateIndex")])
print("ExportFormat:", [k for k in dir(E.ExportFormat) if not k.startswith("_")])
import inspect
print("identify doc:", c.QgsPointCloudDataProvider.identify.__doc__[:400])
print("setFilterGeometry doc:", E.setFilterGeometry.__doc__[:400])
# raster calc if()
err = ""
for s in ['if ( "a@1" >= 200 AND "a@1" <= 260, "a@1", -9999 )', '"a@1" * ("a@1" >= 200)']:
    node = a.QgsRasterCalcNode.parseRasterCalcString(s, err)
    print("parse", s, "->", node is not None)
T = c.QgsRasterTransparency
print("transparency:", [m for m in dir(T) if "Pixel" in m or "pixel" in m])
try:
    import pdal; print("python pdal", pdal.__version__)
except Exception as e: print("no python pdal", e)
from osgeo import gdal
print("GDAL", gdal.__version__, "COG driver", gdal.GetDriverByName("COG") is not None)
from qgis.analysis import QgsNativeAlgorithms
import os; sys.path.append(os.path.join(os.environ.get("QGIS_PREFIX_PATH",""), "python", "plugins"))
import processing
from processing.core.Processing import Processing
Processing.initialize()
ids = [a.id() for a in QgsApplication.processingRegistry().algorithms()]
print("pdal algs:", sorted(a for a in ids if a.startswith("pdal:")))
print("zonal:", [a for a in ids if "zonal" in a])
print("sample:", [a for a in ids if "sampl" in a.lower()])
