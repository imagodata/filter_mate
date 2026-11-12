from pathlib import Path
import urllib.request,urllib.parse,json,gzip,concurrent.futures
root=Path('/tmp/filtermate-linkedin-sarlat/data')
bbox='559000,6422000,560000,6423000,EPSG:2154'
urls={n:'https://data.geopf.fr/wfs/ows?'+urllib.parse.urlencode({'SERVICE':'WFS','VERSION':'2.0.0','REQUEST':'GetFeature','TYPENAMES':'BDTOPO_V3:'+n,'SRSNAME':'EPSG:2154','BBOX':bbox,'OUTPUTFORMAT':'application/json','COUNT':10000}) for n in ('batiment','troncon_de_route','commune')}
urls['parcelles']='https://cadastre.data.gouv.fr/data/etalab-cadastre/2026-09-01/geojson/communes/24/24520/cadastre-24520-parcelles.json.gz'
for key,layer in [('ortho_irc_raw','ORTHOIMAGERY.ORTHOPHOTOS.IRC'),('ortho_rvb_raw','ORTHOIMAGERY.ORTHOPHOTOS')]:
 urls[key]='https://data.geopf.fr/wms-r/wms?'+urllib.parse.urlencode({'SERVICE':'WMS','VERSION':'1.3.0','REQUEST':'GetMap','LAYERS':layer,'STYLES':'','CRS':'EPSG:2154','BBOX':'559000,6422000,560000,6423000','WIDTH':4000,'HEIGHT':4000,'FORMAT':'image/geotiff'})
def fetch(pair):
 name,url=pair
 path=root/(name+('.tif' if name.startswith('ortho') else '.geojson'))
 if path.exists():return name
 with urllib.request.urlopen(url,timeout=90) as r:raw=r.read()
 if name=='parcelles':raw=gzip.decompress(raw)
 if not name.startswith('ortho'):
  d=json.loads(raw)
  if name!='parcelles': assert int(d['numberReturned'])==int(d['totalFeatures'])
  print(name,len(d['features']),flush=True)
 else:print(name,len(raw)//1024,'KiB',flush=True)
 path.write_bytes(raw)
 return name
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:list(pool.map(fetch,urls.items()))
(root.parent/'sources.json').write_text(json.dumps(urls,ensure_ascii=False,indent=2))
