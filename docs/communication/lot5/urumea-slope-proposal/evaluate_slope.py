"""Preflight only: use a fresh /review and the previous film under /source."""
import json,math,sys,shutil
from pathlib import Path
from osgeo import gdal
from qgis.core import QgsApplication,QgsVectorLayer,QgsRasterLayer,QgsGeometry
app=QgsApplication([],False);app.initQgis()
sys.path.insert(0,'/usr/share/qgis/python/plugins')
from processing.core.Processing import Processing
Processing.initialize()
import processing
root=Path('/review');source=Path('/source')
(root/'data').mkdir(parents=True,exist_ok=True)
assert not (root/'data/batiments_pente.gpkg').exists(), 'Use a fresh /review directory'
shutil.copy2(source/'data/urumea-ready.gpkg',root/'data/urumea-input.gpkg')
dem=source/'out/take03/urumea/exports/urumea/Copernicus 30 m.tif';slope=root/'data/pente_pourcent.tif'
gdal.UseExceptions();gdal.DEMProcessing(str(slope),str(dem),'slope',slopeFormat='percent',computeEdges=True)
raster=QgsRasterLayer(str(slope),'Pente (%)','gdal')
buildings=QgsVectorLayer(str(root/'data/urumea-input.gpkg')+'|layername=batiments','Bâtiments','ogr')
river=QgsVectorLayer(str(root/'data/urumea-input.gpkg')+'|layername=urumea','Urumea','ogr')
assert buildings.isValid() and raster.isValid() and river.isValid()
output=root/'data/batiments_pente.gpkg'
result=processing.run('native:zonalstatisticsfb',{'INPUT':buildings,'INPUT_RASTER':raster,'RASTER_BAND':1,'COLUMN_PREFIX':'pente_','STATISTICS':[2],'OUTPUT':str(output)})
layer=QgsVectorLayer(result['OUTPUT'],'Bâtiments pente','ogr');assert layer.isValid()
water=QgsGeometry.unaryUnion([f.geometry() for f in river.getFeatures()])
features=[]
for f in layer.getFeatures():
 value=f['pente_mean']
 if isinstance(value,(float,int)) and math.isfinite(value):features.append((float(value),f.geometry().distance(water)))
rows=[]
for threshold in (5,10,15,20):
 for distance in (200,300,500,750):
  rows.append({'mean_slope_below_percent':threshold,'river_distance_m':distance,'buildings':sum(s<threshold and d<=distance for s,d in features)})
result={'dataset':'same 3073 raw OSM buildings and same Copernicus DSM as the previous film','source_crs':layer.crs().authid(),'raster_pixel_m':[raster.rasterUnitsPerPixelX(),raster.rasterUnitsPerPixelY()],'slope_units':'percent','method':'GDAL Horn slope in percent with computeEdges, native QGIS zonal mean, metric geometry distance to river','total_buildings':layer.featureCount(),'valid_means':len(features),'mean_slope_min':min(x[0] for x in features),'mean_slope_max':max(x[0] for x in features),'results':rows,'status':'preflight_not_new_filmed_behavior'}
result['slope_only_below_10_percent']=sum(s<10 for s,d in features)
(root/'slope-buffer-comparison.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False))
