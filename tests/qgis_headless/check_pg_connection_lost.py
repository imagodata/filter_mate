# -*- coding: utf-8 -*-
"""A PostgreSQL server lost while a layer is filtered: the refusal names the lost connection (2026-11-16).

Seen in a project of 9 PostGIS layers: the server became unreachable, the unfilter was refused on every
layer, and the log read "finished() ✗ FAILED: Cables · Wyre - " (no reason) while "Successfully removed
filters" came after the warning. This check stops the server between the load of the layer and the
unfilter, then applies the unfilter of two layers of the same database as FilterMate does at the end of a
task (``apply_pending_subset_requests`` with ``safe_set_subset_string``): the second one finds the
connection already bad, as the 8 layers after the first one in the ticket.

The host stops the server when the script writes ``ready`` in ``FM_OUT`` and answers with ``stopped``:

    docker network create fm_sfr_net
    docker run -d --name fm_sfr_pg --network fm_sfr_net -e POSTGRES_PASSWORD=fm postgis/postgis:16-3.4
    docker run --init --rm --network fm_sfr_net -v "$PWD:/plugins/filter_mate:ro" -v "$OUT:/out" \\
        -e FM_OUT=/out -e DBUS_SESSION_BUS_ADDRESS=disabled: -e QT_QPA_PLATFORM=offscreen \\
        qgis/qgis:ltr python3 /plugins/filter_mate/tests/qgis_headless/check_pg_connection_lost.py &
    until [ -e "$OUT/ready" ]; do sleep 1; done; docker stop fm_sfr_pg; touch "$OUT/stopped"; wait
"""
import os
import sys
import time

import psycopg2
from qgis.core import QgsApplication, QgsVectorLayer

PG = os.environ.get('FM_PG', 'host=fm_sfr_pg port=5432 dbname=postgres user=postgres password=fm')
OUT = os.environ.get('FM_OUT', '/out')
sys.path.insert(0, '/plugins')

app = QgsApplication([], False)
app.initQgis()


def wait_for_server():
    for _ in range(60):
        try:
            return psycopg2.connect(PG)
        except psycopg2.OperationalError:
            time.sleep(1)
    raise SystemExit('FAIL   the PostGIS server never answered')


connection = wait_for_server()
connection.autocommit = True
layers = []
for table, name in (('fm_sfr_cable', 'Cables'), ('fm_sfr_conduit', 'Conduites')):
    with connection.cursor() as cursor:
        cursor.execute(f'DROP TABLE IF EXISTS {table}')
        cursor.execute(f'CREATE TABLE {table} (id serial PRIMARY KEY, geom geometry(Point, 2154))')
        cursor.execute(f'INSERT INTO {table} (geom) SELECT ST_SetSRID(ST_MakePoint(i, i), 2154) '
                       'FROM generate_series(1, 50) AS i')
    uri = f"{PG} key='id' srid=2154 type=Point table=\"public\".\"{table}\" (geom)"
    layer = QgsVectorLayer(uri, name, 'postgres')
    assert layer.isValid(), f'{name} not valid'
    assert layer.setSubsetString('"id" > 10') and layer.featureCount() == 40, f'first filter of {name} refused'
    layers.append(layer)
connection.close()

from filter_mate.core.tasks.task_completion_handler import apply_pending_subset_requests  # noqa: E402
from filter_mate.infrastructure.utils import safe_set_subset_string  # noqa: E402
from filter_mate.adapters.qgis.subset_failure_reason import CONNECTION_LOST  # noqa: E402

open(os.path.join(OUT, 'ready'), 'w').close()
for _ in range(120):
    if os.path.exists(os.path.join(OUT, 'stopped')):
        break
    time.sleep(0.5)
else:
    raise SystemExit('FAIL   the server was not stopped')

failures = []
applied = apply_pending_subset_requests([(layer, '') for layer in layers], safe_set_subset_string, failures=failures)
print(f'applied={applied} failures={failures}', flush=True)
results = {
    'the unfilters are refused': applied == 0,
    'the previous filters are kept': all(layer.subsetString() == '"id" > 10' for layer in layers),
    'each refusal names the lost connection': failures == [f'Cables: {CONNECTION_LOST}',
                                                           f'Conduites: {CONNECTION_LOST}'],
}
for name, ok in results.items():
    print(f"{'PASS' if ok else 'FAIL'}   {name}", flush=True)
app.exitQgis()
os._exit(0 if all(results.values()) else 1)
