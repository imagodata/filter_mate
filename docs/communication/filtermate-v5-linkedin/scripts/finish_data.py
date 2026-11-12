from pathlib import Path
import json,os,shutil
import numpy as np
from osgeo import gdal
D=Path(r'C:\Users\Simon\AppData\Local\Temp\fm-linkedin-sarlat\data')
O=Path(r'\\wsl.localhost\Ubuntu\home\simon\dev\filter_mate\docs\communication\filtermate-v5-linkedin')
gdal.UseExceptions()
a=json.loads((O/'data-audit.json').read_text(encoding='utf-8'))
# Align the derived terrain with the exact 1 km orthophoto/LiDAR extent, then interpolate small ground gaps.
shutil.move(D/'mnt_1m.tif',D/'mnt_sol_brut.tif')
gdal.Translate(str(D/'mnt_1m.tif'),str(D/'mnt_sol_brut.tif'),projWin=[559000,6423000,560000,6422000],creationOptions=['TILED=YES','COMPRESS=DEFLATE'])
ds=gdal.Open(str(D/'mnt_1m.tif'),gdal.GA_Update);b=ds.GetRasterBand(1);raw=b.ReadAsArray();initial=int((raw==-9999).sum())
gdal.FillNodata(targetBand=b,maskBand=None,maxSearchDist=40,smoothingIterations=1)
ds.BuildOverviews('AVERAGE',[2,4,8,16]);b=None;ds=None
for file in ('ortho_irc.tif','ortho_rvb.tif'):
 ds=gdal.Open(str(D/file),gdal.GA_Update)
 for i in range(1,ds.RasterCount+1):ds.GetRasterBand(i).DeleteNoDataValue()
 ds=None
for file in ('mnt_1m.tif','ortho_irc.tif','ortho_rvb.tif'):
 ds=gdal.Open(str(D/file));gt=ds.GetGeoTransform();bands=[]
 for i in range(1,ds.RasterCount+1):
  b=ds.GetRasterBand(i);arr=b.ReadAsArray();mask=b.GetMaskBand().ReadAsArray()!=0;valid=arr[mask]
  bands.append({'band':i,'name':b.GetDescription(),'nodata':b.GetNoDataValue(),'valid_percent':round(100*int(mask.sum())/mask.size,5),'min':float(valid.min()),'max':float(valid.max())})
 a['rasters'][file]={'size':[ds.RasterXSize,ds.RasterYSize],'extent':[gt[0],gt[3]+gt[5]*ds.RasterYSize,gt[0]+gt[1]*ds.RasterXSize,gt[3]],'resolution':[gt[1],gt[5]],'bands':bands};ds=None

a['mnt_preparation']={'source':'LiDAR HD classe 2 (sol), IDW PDAL rayon 3 m','raw_missing_pixels':initial,'interpolation':'GDAL FillNodata, recherche 40 pixels au maximum, 1 lissage','crop':'emprise exacte 559000,6422000,560000,6423000','purpose':'fermer les lacunes du sol sous les bâtiments; dérivé de démonstration, pas un MNT officiel IGN'}
a['ortho_preparation']='La valeur 255 n’est plus traitée comme NoData : les blancs saturés des images doivent rester des pixels valides sur cette emprise couverte.'
(O/'data-audit.json').write_text(json.dumps(a,ensure_ascii=False,indent=2),encoding='utf-8')
# Save a portable dataset with this project, so its source files do not depend on the temporary folder.
for file in ('mnt_1m.tif','ortho_irc.tif','ortho_rvb.tif','lidar_hd_sarlat.copc.laz'):
 shutil.copy2(D/file,O/'data'/file)
os._exit(0)
