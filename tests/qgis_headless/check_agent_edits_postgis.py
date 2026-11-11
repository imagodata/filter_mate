# -*- coding: utf-8 -*-
"""The edits of the agent (adapters/public_api/feature_edits.py) on a real PostGIS table, headless.

A PostGIS server is needed (``FM_PG``, a libpq connection string), on a Docker network as for run_postgis_check.py:

    docker network create fm_pg_net
    docker run -d --name fm_pg --network fm_pg_net -e POSTGRES_PASSWORD=fm postgis/postgis:16-3.4
    docker run --rm --network fm_pg_net -v "$PWD:/src:ro" -e FM_PG="host=fm_pg port=5432 dbname=postgres user=postgres \\
        password=fm" qgis/qgis:stable python3 /src/tests/qgis_headless/check_agent_edits_postgis.py

Checks that the agent edits the edit buffer only (nothing reaches the table until the layer is saved), refuses the
key and values of the wrong type, converts what it writes so that saving succeeds, and that undoing the turn steps
back over its commands. Prints one PASS / FAIL line per check; exits with 1 when one failed.
"""
import os
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from qgis.core import QgsApplication, QgsDataSourceUri, QgsProject, QgsProviderRegistry, QgsVectorLayer  # noqa: E402

PG = os.environ.get("FM_PG", "host=fm_pg port=5432 dbname=postgres user=postgres password=fm")
RESULTS = []


def check(label, condition, detail=""):
    RESULTS.append(bool(condition))
    print(f"{'PASS' if condition else 'FAIL'} {label}" + (f" -- {detail}" if not condition else ""), flush=True)


def refused(function, *args, **kwargs):
    try:
        function(*args, **kwargs)
    except ValueError as exc:
        return str(exc) or "refused"
    return ""


def main():
    from filter_mate.adapters.public_api import feature_edits as edits
    from filter_mate.adapters.public_api.introspection import describe_layer
    from filter_mate.adapters.agent.turn_effects import EffectsRecorder, apply_effects
    from filter_mate.core.agent.messages import ToolCallPart

    connection = QgsProviderRegistry.instance().providerMetadata("postgres").createConnection(PG, {})
    sql = connection.executeSql
    sql("DROP SCHEMA IF EXISTS fm_edit CASCADE")
    sql("CREATE SCHEMA fm_edit")
    sql("CREATE TABLE fm_edit.communes (id serial PRIMARY KEY, nom text, pop integer, taux double precision, "
        "geom geometry(Point, 2154))")
    sql("INSERT INTO fm_edit.communes (nom, pop, taux, geom) SELECT 'Commune ' || n, n * 100, n / 4.0, "
        "ST_SetSRID(ST_MakePoint(650000 + n, 6860000), 2154) FROM generate_series(1, 20) AS n")

    def table(query):
        return sql(query)

    uri = QgsDataSourceUri(PG)
    uri.setDataSource("fm_edit", "communes", "geom", "", "id")
    layer = QgsVectorLayer(uri.uri(False), "communes", "postgres")
    check("fixture: the table opens", layer.isValid() and layer.featureCount() == 20, layer.featureCount())
    QgsProject.instance().addMapLayer(layer)
    check("the key is known", [layer.fields().at(index).name() for index in layer.primaryKeyAttributes()] == ["id"],
          layer.primaryKeyAttributes())

    recorder = EffectsRecorder()
    recorder.before_call(ToolCallPart("p1", "update_features", {"layer": "communes"}))
    changed = edits.update_features("communes", values={"nom": "Ville", "taux": "2.5"}, expression='"pop" <= 300')
    check("values in the buffer", changed["changed"] == 3 and layer.isEditable() and layer.isModified(), changed)
    formula = edits.update_features("communes", formulas={"pop": '"pop" * 2'}, expression='"pop" > 1800')
    check("a formula", formula["changed"] == 2 and sorted(f["pop"] for f in layer.getFeatures())[-2:] == [3800, 4000],
          formula)
    check("refuses the key", "key" in refused(edits.update_features, "communes", values={"id": 99}, expression="true"))
    check("refuses a text in an integer", refused(edits.update_features, "communes", values={"pop": "abc"},
                                                  expression="true"))
    deleted = edits.delete_features("communes", expression='"pop" = 1000')
    check("delete in the buffer", deleted["deleted"] == 1 and layer.featureCount() == 19, deleted)
    added = edits.add_features("communes", [{"wkt": "POINT(1.44 43.6)", "attributes": {"nom": "Puits", "pop": "7"}}],
                               crs="EPSG:4326")
    check("add from EPSG:4326, a value converted", added["added"] == 1, added)
    details = describe_layer("communes")
    check("describe_layer: edited, not saved", details["editing"] and details["unsaved"], details)
    check("nothing reaches the table before saving", table("SELECT count(*) FROM fm_edit.communes")[0][0] == 20 and
          table("SELECT count(*) FROM fm_edit.communes WHERE nom = 'Ville'")[0][0] == 0)

    effects = recorder.finish()
    done, left = apply_effects(effects, undo=True)
    check("undo steps back over the commands", done == ["communes"] and not left and not layer.isModified() and
          layer.featureCount() == 20, (done, left))
    apply_effects(effects, undo=False)
    check("redo applies them again", layer.isModified() and layer.featureCount() == 20, layer.featureCount())

    saved = layer.commitChanges()  # what the user does: Save Layer Edits
    check("the user saves: the database takes every change", saved, layer.commitErrors())
    rows = table("SELECT count(*), sum(CASE WHEN nom = 'Ville' THEN 1 ELSE 0 END), max(pop) FROM fm_edit.communes")[0]
    check("the table holds them, with their types", [int(value) for value in rows] == [20, 3, 4000], rows)
    point = table("SELECT pop, ST_SRID(geom), round(ST_X(geom)) > 500000 FROM fm_edit.communes WHERE nom = 'Puits'")
    check("the point added is in Lambert-93, its value an integer", point and int(point[0][0]) == 7 and
          int(point[0][1]) == 2154 and point[0][2] in (True, "true", "t", 1), point)
    done, left = apply_effects(effects, undo=True)
    check("after saving, undo leaves the layer as it is", left == ["communes"] and not layer.isModified(), (done, left))
    QgsProject.instance().removeMapLayer(layer.id())
    sql("DROP SCHEMA fm_edit CASCADE")


if __name__ == "__main__":
    app = QgsApplication([], False)
    app.initQgis()
    package_root = tempfile.mkdtemp()
    os.symlink(os.environ.get("FM_REPO", "/src"), os.path.join(package_root, "filter_mate"))
    sys.path.insert(0, package_root)
    sys.dont_write_bytecode = True
    print(f"QGIS {__import__('qgis.core').core.Qgis.QGIS_VERSION}", flush=True)
    main()
    failed = RESULTS.count(False)
    print(f"{len(RESULTS) - failed}/{len(RESULTS)} passed", flush=True)
    sys.stdout.flush()
    os._exit(1 if failed else 0)
