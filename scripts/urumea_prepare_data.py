import json
from pathlib import Path
from qgis.core import QgsApplication,QgsVectorLayer,QgsVectorFileWriter,QgsCoordinateReferenceSystem,QgsCoordinateTransform,QgsProject,QgsRectangle
app=QgsApplication([],False);app.initQgis(); project=QgsProject.instance()
source='/w/data/legacy-vectors.gpkg';output='/w/data/urumea-ready.gpkg';metric=QgsCoordinateReferenceSystem('EPSG:32630');area=QgsRectangle(-1.985,43.295,-1.948,43.324)
result={'source':'legacy OSM snapshot, raw buildings without derived alt_mean','area_wgs84':[-1.985,43.295,-1.948,43.324],'crs':'EPSG:32630','layers':[]}
for index,(table,name) in enumerate([('Buildings San Sebastián','batiments'),('Roads San Sebastián','routes'),('Bridges San Sebastián (lines)','ponts_lignes'),('Bridges San Sebastián (polygons)','ponts_polygones'),('Urumea river','urumea')]):
 layer=QgsVectorLayer(source+'|layername='+table,name,'ogr');assert layer.isValid()
 options=QgsVectorFileWriter.SaveVectorOptions();options.driverName='GPKG';options.layerName=name
 options.actionOnExistingFile=QgsVectorFileWriter.ActionOnExistingFile.CreateOrOverwriteFile if index==0 else QgsVectorFileWriter.ActionOnExistingFile.CreateOrOverwriteLayer
 options.ct=QgsCoordinateTransform(layer.crs(),metric,project);options.filterExtent=options.ct.transformBoundingBox(area)
 status=QgsVectorFileWriter.writeAsVectorFormatV3(layer,output,project.transformContext(),options)
 if int(status[0])!=0:raise RuntimeError(str(status))
 saved=QgsVectorLayer(output+'|layername='+name,name,'ogr');assert saved.isValid() and saved.featureCount()>0
 result['layers'].append({'table':name,'count':saved.featureCount(),'crs':saved.crs().authid()})
Path('/w/data/preparation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
