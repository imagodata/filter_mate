"""Opt-in, bounded observations of public providers before translation.

Run in an isolated Docker profile with --service wfs|oapif|arcgis.
These observations do not infer server support from setSubsetString alone.
"""
import argparse
import json
import os
import time
from pathlib import Path
import sys
import tempfile

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from qgis.core import (  # noqa: E402
    Qgis, QgsApplication, QgsFeatureRequest, QgsNetworkAccessManager,
    QgsNetworkRequestParameters, QgsSettings, QgsVectorLayer,
)
from qgis.PyQt.QtCore import QUrlQuery  # noqa: E402

parser = argparse.ArgumentParser()
parser.add_argument('--service', choices=('wfs', 'oapif', 'arcgis'), required=True)
parser.add_argument('--verify', action='store_true')
args = parser.parse_args()
if args.verify:
    temporary = Path(tempfile.mkdtemp(prefix='fm-verify-stream-a-'))
    (temporary / 'filter_mate').symlink_to(Path(__file__).resolve().parents[2], target_is_directory=True)
    os.environ['FILTERMATE_LOG_DIR'] = str(temporary / 'logs')
    sys.path.insert(0, str(temporary))
    from filter_mate.infrastructure.database.sql_utils import safe_set_subset_string
app = QgsApplication([], False)
app.initQgis()
QgsSettings().setValue('/qgis/networkAndProxy/networkTimeout', 10000)
requests = []


def record(*arguments):
    request = next((arg for arg in arguments if hasattr(arg, 'url')), None)
    if request is None:
        return
    query = QUrlQuery(request.url())
    requests.append({key: query.queryItemValue(key) for key in
                     ('FILTER', 'filter', 'filter-lang', 'where', 'resultType', 'returnIdsOnly',
                      'limit', 'stn_id', 'id', 'value', 'datetime')
                     if query.hasQueryItem(key)})


QgsNetworkAccessManager.instance().requestAboutToBeCreated[QgsNetworkRequestParameters].connect(
    lambda parameters: record(parameters.request()))
sources = {
    'wfs': ('WFS', "url='https://data.geopf.fr/wfs/ows' "
            "typename='ADMINEXPRESS-COG.LATEST:commune' version='2.0.0' "
            "srsname='EPSG:4326' maxNumFeatures='5' restrictToRequestBBOX='1'"),
    'oapif': ('OAPIF', "url='https://demo.pygeoapi.io/master' typename='obs' maxNumFeatures='5'"),
    'arcgis': ('arcgisfeatureserver', "url='https://sampleserver6.arcgisonline.com/arcgis/rest/"
               "services/Census/MapServer/3'"),
}
provider, uri = sources[args.service]
layer = QgsVectorLayer(uri, 'measure', provider)
print('VERSION', Qgis.QGIS_VERSION, 'SERVICE', args.service, 'VALID', layer.isValid(), flush=True)
if not layer.isValid():
    print('SKIP public service unavailable', flush=True)
    raise SystemExit(0)
print('FIELDS', [field.name() for field in layer.fields()], flush=True)
expressions = ["\"nom\" = 'L''Isle-Jourdain'", '"nom" ILIKE \'saint%\'',
               '"population" > 1000 AND "insee_dep" = \'31\'',
               'left("nom", 3) = \'Sai\'', '$area > 1e6']
if os.environ.get('FM_REAL_FIELDS'):
    replacements = {
        'wfs': {'nom': 'nom_officiel', 'insee_dep': 'code_insee_du_departement'},
        'oapif': {'nom': 'stn_id', 'population': 'value', 'insee_dep': 'id'},
        'arcgis': {'nom': 'STATE_NAME', 'population': 'POP2000', 'insee_dep': 'STATE_FIPS'},
    }[args.service]
    expressions = [expression for expression in expressions]
    for name, replacement in replacements.items():
        expressions = [expression.replace('"' + name + '"', '"' + replacement + '"')
                       for expression in expressions]
for expression in expressions:
    requests.clear()
    start = time.monotonic()
    before = layer.subsetString()
    accepted = safe_set_subset_string(layer, expression) if args.verify else layer.setSubsetString(expression)
    rows = 0
    if accepted:
        iterator = layer.getFeatures(QgsFeatureRequest().setLimit(2))
        for feature in iterator:
            rows += 1
            if rows == 2:
                break
        iterator.close()
    elif args.verify:
        assert layer.subsetString() == before
    app.processEvents()
    print(json.dumps(dict(expression=expression, accepted=accepted, valid=layer.isValid(),
                          rows_up_to_two=rows, seconds=round(time.monotonic() - start, 2),
                          requests=requests)), flush=True)
if args.verify and args.service == 'wfs':
    expression = '"nom_officiel" = \'L\'\'Isle-Jourdain\' AND "code_insee" = \'32160\''
    assert safe_set_subset_string(layer, expression)
    rows = list(layer.getFeatures(QgsFeatureRequest().setLimit(2)))
    assert len(rows) == 1 and rows[0]['code_insee'] == '32160'
    print('PASS WFS L\'Isle-Jourdain (32160): exactly one commune', flush=True)
    from filter_mate.adapters.qgis.server_filter_translation import restore_server_subset, ServerFilterError
    before = layer.subsetString()
    try:
        restore_server_subset(layer, '"field_absent_on_server" = 1')
    except ServerFilterError:
        assert layer.subsetString() == before
        print('PASS WFS server rejection preserves previous provider', flush=True)
    else:
        raise AssertionError('WFS rejected predicate silently installed')
if args.verify and args.service == 'arcgis':
    assert safe_set_subset_string(layer, '"OBJECTID" = 1')
    rows = list(layer.getFeatures(QgsFeatureRequest().setLimit(2)))
    assert len(rows) == 1 and rows[0]['OBJECTID'] == 1
    print('PASS ArcGIS OBJECTID=1: exactly one feature', flush=True)
