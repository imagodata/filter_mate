# Spike FilterMate 5.0 (14/10/2026) : vérifie en QGIS réel les API raster / nuage du plan
# docs/internal/plans/V5_RASTER_LIDAR_PLAN.md. Lancer avec python-qgis.bat ; chemins de données Windows à adapter.
import os, sys, tempfile
from qgis.core import *
app = QgsApplication([], False); app.initQgis()
print("QGIS", Qgis.version())
out = tempfile.mkdtemp()
laz = r"C:\Users\Simon\Downloads\BATIMENT0000000300601860.laz"
pc = QgsPointCloudLayer(laz, "pc", "pdal")
print("pc valid", pc.isValid(), "count", pc.pointCount(), "ext", pc.extent().toString(1), "crs", pc.crs().authid())
# wait for index
import time
for _ in range(60):
    if pc.dataProvider().indexingState() == QgsPointCloudDataProvider.PointCloudIndexGenerationState.Indexed: break
    pc.dataProvider().generateIndex(); app.processEvents(); time.sleep(0.5)
print("indexed", pc.dataProvider().indexingState())
attrs = [a.name() for a in pc.attributes().attributes()]
print("attrs", attrs)
st = pc.statistics()
print("classes", st.classesOf("Classification"))
e = pc.extent(); cx, cy = e.center().x(), e.center().y()
bbox = f"X >= {e.xMinimum():.3f} AND X <= {cx:.3f} AND Y >= {e.yMinimum():.3f} AND Y <= {cy:.3f}"
print("setSubset XY", pc.setSubsetString(bbox), "subset now", pc.subsetString()[:60])
# exporter honours subset?
def export(geom=None, tag=""):
    ex = QgsPointCloudLayerExporter(pc)
    ex.setFormat(QgsPointCloudLayerExporter.ExportFormat.Memory)
    if geom is not None: ex.setFilterGeometry(geom.constGet().clone())
    ex.doExport()
    lyr = ex.takeExportedLayer()
    print(tag, "exported", lyr.featureCount() if lyr else None, ex.lastError())
export(tag="with subset")
pc.setSubsetString("")
export(tag="no subset")
tri = QgsGeometry.fromWkt(f"POLYGON(({e.xMinimum()} {e.yMinimum()}, {e.xMaximum()} {e.yMinimum()}, {e.xMinimum()} {e.yMaximum()}, {e.xMinimum()} {e.yMinimum()}))")
export(tri, "triangle geom")
# LAS export
ex = QgsPointCloudLayerExporter(pc); ex.setFormat(QgsPointCloudLayerExporter.ExportFormat.Las)
ex.setFileName(os.path.join(out, "clip.laz")); ex.setFilterGeometry(tri.constGet().clone()); ex.doExport()
print("laz export", os.path.exists(os.path.join(out, "clip.laz")), ex.lastError())
# identify inside polygon
pts = pc.dataProvider().identify(0.0, tri, QgsDoubleRange(), 100000)
print("identify n", len(pts), list(pts[0].keys())[:6] if pts else None)
# setDataSource on PC keeps id?
lid = pc.id(); pc.setDataSource(os.path.join(out, "clip.laz"), "pc", "pdal"); print("pc setDataSource valid", pc.isValid(), pc.id()==lid)

# raster
r = QgsRasterLayer(r"C:\Users\Simon\Documents\ign\valence.tif", "mnt", "gdal")
print("raster valid", r.isValid(), r.bandCount(), r.width(), r.height(), r.crs().authid())
stats = r.dataProvider().bandStatistics(1, QgsRasterBandStats.Stats.Min | QgsRasterBandStats.Stats.Max)
lo, hi = stats.minimumValue, stats.maximumValue; mid = (lo+hi)/2
print("min max", lo, hi)
# transparency outside range
t = r.renderer().rasterTransparency() or QgsRasterTransparency()
P = QgsRasterTransparency.TransparentSingleValuePixel
try:
    t.setTransparentSingleValuePixelList([P(-1e30, lo + (hi-lo)*0.3, 100, True, False), P(mid, 1e30, 100, False, True)])
    print("transparency ranges ok", len(t.transparentSingleValuePixelList()))
except Exception as ex2: print("transparency ctor err", ex2)
# virtualraster with if()
from qgis.core import QgsRasterDataProvider
params = QgsRasterDataProvider.VirtualRasterParameters()
params.crs = r.crs(); params.extent = r.extent(); params.width = r.width(); params.height = r.height()
inp = QgsRasterDataProvider.VirtualRasterInputLayers(); inp.name = "mnt"; inp.uri = r.source(); inp.provider = "gdal"
params.rInputLayers = [inp]
params.formula = f'if ( "mnt@1" >= {lo+(hi-lo)*0.3} AND "mnt@1" <= {mid}, "mnt@1", -9999 )'
uri = QgsRasterDataProvider.encodeVirtualRasterProviderUri(params)
v = QgsRasterLayer(uri, "virt", "virtualraster")
print("virtualraster valid", v.isValid())
if v.isValid():
    s2 = v.dataProvider().bandStatistics(1, QgsRasterBandStats.Stats.Min | QgsRasterBandStats.Stats.Max)
    print("virt min max", s2.minimumValue, s2.maximumValue, "nodata?", v.dataProvider().sourceHasNoDataValue(1))
# setDataSource raster keeps id + renderer?
rid = r.id(); rend = r.renderer().type()
r.setDataSource(uri, "mnt", "virtualraster", QgsDataProvider.ProviderOptions(), True)
print("raster setDataSource valid", r.isValid(), r.id()==rid, rend, "->", r.renderer().type())
# gdal warp cutline VRT
from osgeo import gdal, ogr
cut = os.path.join(out, "cut.gpkg")
drv = ogr.GetDriverByName("GPKG"); ds = drv.CreateDataSource(cut)
srs = __import__("osgeo.osr", fromlist=["osr"]).SpatialReference(); srs.ImportFromWkt(r.crs().toWkt())
lyr = ds.CreateLayer("cut", srs, ogr.wkbPolygon)
ext = r.extent(); f = ogr.Feature(lyr.GetLayerDefn())
f.SetGeometry(ogr.CreateGeometryFromWkt(f"POLYGON(({ext.xMinimum()} {ext.yMinimum()},{ext.center().x()} {ext.yMinimum()},{ext.xMinimum()} {ext.center().y()},{ext.xMinimum()} {ext.yMinimum()}))"))
lyr.CreateFeature(f); ds = None
vrt = os.path.join(out, "cut.vrt")
w = gdal.Warp(vrt, r"C:\Users\Simon\Documents\ign\valence.tif", format="VRT", cutlineDSName=cut, cropToCutline=True, dstNodata=-9999)
w = None
cl = QgsRasterLayer(vrt, "cut", "gdal"); print("cutline vrt valid", cl.isValid(), cl.width(), cl.height(), "size", os.path.getsize(vrt))
cog = os.path.join(out, "cut_cog.tif"); gdal.Translate(cog, vrt, format="COG", creationOptions=["COMPRESS=DEFLATE"]); print("COG", os.path.getsize(cog))
