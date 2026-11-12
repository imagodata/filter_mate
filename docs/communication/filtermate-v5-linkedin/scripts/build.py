from pathlib import Path
import json,os,subprocess,traceback,shutil
import numpy as np
from osgeo import gdal,ogr,osr
from qgis.core import Qgis,QgsApplication,QgsProject,QgsRasterLayer,QgsVectorLayer,QgsPointCloudLayer,QgsCoordinateReferenceSystem,QgsReferencedRectangle,QgsFillSymbol,QgsLineSymbol,QgsMultiBandColorRenderer
ROOT=Path(r'C:\Users\Simon\AppData\Local\Temp\fm-linkedin-sarlat');DATA=ROOT/'data'
OUT=Path(r'\\wsl.localhost\Ubuntu\home\simon\dev\filter_mate\docs\communication\filtermate-v5-linkedin')
app=QgsApplication([],False);app.initQgis();gdal.UseExceptions();ogr.UseExceptions()
report={'lieu':'Sarlat-la-Canéda','code_insee':'24520','date':'2026-10-21','extent_epsg2154':[559000,6422000,560000,6423000]}
try:
 gpkg=DATA/'sarlat.gpkg'
 if gpkg.exists():gpkg.unlink()
 for i,name in enumerate(('batiment','troncon_de_route')):
  gdal.VectorTranslate(str(gpkg),str(DATA/(name+'.geojson')),format='GPKG',accessMode=None if i==0 else 'append',layerName=name)
 ds=ogr.Open(str(gpkg),1);srs=osr.SpatialReference();srs.ImportFromEPSG(2154);srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
 ly=ds.CreateLayer('parcelle',srs,ogr.wkbMultiPolygon,options=['SPATIAL_INDEX=YES'])
 for field in ('id','commune','nom_com','section','numero'):ly.CreateField(ogr.FieldDefn(field,ogr.OFTString))
 ly.CreateField(ogr.FieldDefn('contenance',ogr.OFTInteger64))
 zone=ogr.CreateGeometryFromWkt('POLYGON((559000 6422000,560000 6422000,560000 6423000,559000 6423000,559000 6422000))')
 src=ogr.Open(str(DATA/'parcelles.geojson'));sl=src.GetLayer(0);sr=sl.GetSpatialRef();sr.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER);trans=osr.CoordinateTransformation(sr,srs)
 n=0;invalid=[];ids=set()
 for f in sl:
  g=f.GetGeometryRef().Clone();g.Transform(trans)
  if not g.Intersects(zone):continue
  ident=f.GetField('id')
  assert ident not in ids;ids.add(ident)
  if not g.IsValid():invalid.append(ident)
  nf=ogr.Feature(ly.GetLayerDefn())
  for field in ('id','commune','section','numero','contenance'):nf.SetField(field,f.GetField(field))
  nf.SetField('nom_com','Sarlat-la-Canéda');nf.SetGeometry(ogr.ForceToMultiPolygon(g));ly.CreateFeature(nf);n+=1
 report['parcelles']={'source_commune_count':sl.GetFeatureCount(),'count_on_tile':n,'invalid_ids':invalid,'duplicates':0,'geometry_policy':'parcelles entieres intersectant la dalle; aucune decoupe de leurs contours'}
 src=None;sl=None;ly=None;ds=None
 for key,descriptions in [('irc',['PIR','Rouge','Vert']),('rvb',['Rouge','Vert','Bleu'])]:
  out=DATA/f'ortho_{key}.tif'
  gdal.Translate(str(out),str(DATA/f'ortho_{key}_raw.tif'),bandList=[1,2,3],creationOptions=['TILED=YES','COMPRESS=JPEG','JPEG_QUALITY=92','PHOTOMETRIC=YCBCR'])
  ds=gdal.Open(str(out),gdal.GA_Update)
  for i,name in enumerate(descriptions,1):ds.GetRasterBand(i).SetDescription(name)
  ds.BuildOverviews('AVERAGE',[2,4,8,16]);ds=None
 pipeline={'pipeline':[{'type':'readers.copc','filename':str(DATA/'lidar_hd_sarlat.copc.laz')},{'type':'filters.expression','expression':'Classification == 2'},{'type':'writers.gdal','filename':str(DATA/'mnt_1m.tif'),'resolution':1.0,'output_type':'idw','radius':3.0,'window_size':3,'bounds':'([559000,560000],[6422000,6423000])','gdaldriver':'GTiff','nodata':-9999}]}
 (ROOT/'mnt-pipeline.json').write_text(json.dumps(pipeline))
 done=subprocess.run([r'C:\Program Files\QGIS 4.2.3\bin\pdal.exe','pipeline',str(ROOT/'mnt-pipeline.json')],capture_output=True,text=True,timeout=180)
 report['pdal']={'returncode':done.returncode,'stderr':done.stderr[-2000:]}
 if done.returncode:raise RuntimeError(done.stderr)
 report['rasters']={}
 for file in ('mnt_1m.tif','ortho_irc.tif','ortho_rvb.tif'):
  ds=gdal.Open(str(DATA/file));gt=ds.GetGeoTransform();bands=[]
  for i in range(1,ds.RasterCount+1):
   b=ds.GetRasterBand(i);a=b.ReadAsArray();mask=b.GetMaskBand().ReadAsArray()!=0;vals=a[mask]
   bands.append({'band':i,'name':b.GetDescription(),'nodata':b.GetNoDataValue(),'valid_percent':round(100*int(mask.sum())/mask.size,4),'min':float(vals.min()),'max':float(vals.max())})
  report['rasters'][file]={'size':[ds.RasterXSize,ds.RasterYSize],'extent':[gt[0],gt[3]+gt[5]*ds.RasterYSize,gt[0]+gt[1]*ds.RasterXSize,gt[3]],'resolution':[gt[1],gt[5]],'bands':bands};ds=None
 p=QgsProject.instance();p.setCrs(QgsCoordinateReferenceSystem('EPSG:2154'));p.setTitle('FilterMate 5 — Sarlat — données vérifiées')
 vectors=[];report['vectors']={}
 for name in ('parcelle','troncon_de_route','batiment'):
  v=QgsVectorLayer(str(gpkg)+'|layername='+name,name,'ogr');fs=list(v.getFeatures());vectors.append(v)
  report['vectors'][name]={'valid':v.isValid(),'count':len(fs),'crs':v.crs().authid(),'subset':v.subsetString(),'invalid_geometry_fids':[f.id() for f in fs if f.hasGeometry() and not f.geometry().isGeosValid()],'empty_geometry_count':sum(not f.hasGeometry() or f.geometry().isEmpty() for f in fs)}
 vectors[0].renderer().setSymbol(QgsFillSymbol.createSimple({'color':'0,0,0,0','outline_color':'#245c80','outline_width':'0.25'}))
 vectors[1].renderer().setSymbol(QgsLineSymbol.createSimple({'color':'#e0a200','width':'0.8'}))
 vectors[2].renderer().setSymbol(QgsFillSymbol.createSimple({'color':'210,69,69,130','outline_color':'#8c2626','outline_width':'0.2'}))
 rasters=[QgsRasterLayer(str(DATA/name),name,'gdal') for name in ('ortho_rvb.tif','ortho_irc.tif','mnt_1m.tif')]
 for r in rasters[:2]:r.setRenderer(QgsMultiBandColorRenderer(r.dataProvider(),1,2,3))
 cloud=QgsPointCloudLayer(str(DATA/'lidar_hd_sarlat.copc.laz'),'lhd','copc')
 report['lidar']={'valid':cloud.isValid(),'point_count':cloud.pointCount(),'crs':cloud.crs().authid(),'extent':[cloud.extent().xMinimum(),cloud.extent().yMinimum(),cloud.extent().xMaximum(),cloud.extent().yMaximum()]}
 p.addMapLayers(rasters+[cloud]+vectors)
 for r in rasters[1:]+[cloud]:p.layerTreeRoot().findLayer(r.id()).setItemVisibilityChecked(False)
 p.viewSettings().setDefaultViewExtent(QgsReferencedRectangle(rasters[2].extent(),p.crs()))
 p.setFilePathStorage(Qgis.FilePathType.Absolute)
 report['project_written']=p.write(str(OUT/'sarlat-verified-layers.qgz'))
 dest=OUT/'data';dest.mkdir(exist_ok=True)
 shutil.copy2(gpkg,dest/'sarlat.gpkg')
except Exception:report['error']=traceback.format_exc()
(OUT/'data-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
os._exit(1 if 'error' in report else 0)
