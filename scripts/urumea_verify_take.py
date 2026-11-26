import argparse,json,sqlite3,zipfile,hashlib
from pathlib import Path
from osgeo import gdal
from qgis.core import QgsApplication,QgsVectorLayer,QgsProject,QgsCoordinateReferenceSystem,QgsRectangle,QgsCoordinateTransform

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--take',type=Path,required=True);args=parser.parse_args();root=Path('/w');take=args.take
 meta=json.loads((take/'meta.json').read_text());assert meta['status']=='complete',meta
 before=json.loads((take/'filtre-observed.json').read_text());reset=json.loads((take/'reset-observed.json').read_text());after=json.loads((take/'rejeu-observed.json').read_text())
 calls=[json.loads(line) for line in (take/'tools.jsonl').read_text().splitlines()]
 expected={}
 for call in calls:
  if call['request']=='filtre' and call['tool']=='cross_filter' and not call['is_error']:
   expected.update(json.loads(call['content'])['kept'])
 assert len(expected)>=4 and all(v>0 for v in expected.values()),expected
 assert reset['filters']=={}
 assert set(before['filters'])==set(after['filters'])
 same={name:before['filters'][name]['subset']==after['filters'][name]['subset'] for name in before['filters']}
 assert all(same.values()),same
 mapping={'Routes':'routes','Ponts lignes':'ponts_lignes','Ponts polygones':'ponts_polygones'}
 independent={}
 with sqlite3.connect((root/'data/urumea-ready.gpkg').resolve().as_uri()+'?mode=ro',uri=True) as db:
  for name,table in mapping.items():
   counts=[]
   for stage in (before,after):
    counts.append(db.execute('SELECT count(*) FROM '+table+' WHERE '+stage['filters'][name]['subset']).fetchone()[0])
   independent[name]={'before':counts[0],'after':counts[1]};assert counts==[expected[name],expected[name]]
 gpkg=next((take/'exports').rglob('*.gpkg'));exported={}
 with sqlite3.connect(gpkg.resolve().as_uri()+'?mode=ro',uri=True) as db:
  for (name,) in db.execute("SELECT table_name FROM gpkg_contents WHERE data_type='features'"):
   exported[name]=db.execute('SELECT count(*) FROM "'+name.replace('"','""')+'"').fetchone()[0]
 assert all(exported.get(name)==count for name,count in expected.items()),exported
 rasters=list((take/'exports').rglob('*.tif'));assert rasters
 raster_info=[]
 for path in rasters:
  dataset=gdal.Open(str(path));assert dataset is not None
  raster_info.append({'file':path.name,'width':dataset.RasterXSize,'height':dataset.RasterYSize,'bands':dataset.RasterCount})
 replay_ops=[c['tool'] for c in calls if c['request']=='rejeu' and not c['is_error']]
 assert 'apply_favorite' in replay_ops
 assert not any(op in replay_ops for op in ('apply_filter','cross_filter','geometry_filter','run_algorithm'))
 package=json.loads((root/'package.json').read_text());version=next(x for x in (root/'release/filter_mate/metadata.txt').read_text().splitlines() if x.startswith('version='));assert version=='version=5.1.3'
 receipt={'expected_counts_from_real_filter_tools':expected,'identical_filter_expressions_after_replay':same,'independent_sql_counts':independent,'exported_counts':exported,'exported_rasters':raster_info,'replay_operations':replay_ops,'verified':True,'package':package,
          'scope_note':'Counters, stored predicates, exported data and tool calls are verified. Model prose is not used as evidence of scope.'}
 (take/'verified-observations.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n');print(json.dumps(receipt,ensure_ascii=False))

if __name__=='__main__':main()
