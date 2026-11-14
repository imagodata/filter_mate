# -*- coding: utf-8 -*-
"""The tables of a PostgreSQL connection of QGIS, listed and added by the agent, on a real PostGIS server.

A PostGIS server is needed (``FM_PG``, a libpq connection string), on a Docker network as for
check_agent_edits_postgis.py:

    docker run --rm --network fm_pg_net -v "$PWD:/src:ro" -e FM_PG="host=fm_pg port=5432 dbname=postgres user=postgres \\
        password=fm" qgis/qgis:ltr python3 /src/tests/qgis_headless/check_agent_database_tables.py

The check makes a schema of its own and drops it at the end. Prints one PASS / FAIL line per check; exits with 1
when one failed.
"""
import os
import sys
import tempfile
import uuid

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from qgis.core import Qgis, QgsApplication, QgsDataSourceUri, QgsProject, QgsProviderRegistry  # noqa: E402

PG = os.environ.get("FM_PG", "host=fm_pg port=5432 dbname=postgres user=postgres password=fm")
SCHEMA = "fm_dbt_" + uuid.uuid4().hex[:8]
NAME = "FM bench (PostGIS)"
RESULTS = []


def check(label, condition, detail=""):
    RESULTS.append(bool(condition))
    print(f"{'PASS' if condition else 'FAIL'} {label}" + (f" -- {str(detail)[:400]}" if not condition else ""), flush=True)


def refused(function, *args, **kwargs):
    try:
        function(*args, **kwargs)
    except ValueError as exc:
        return str(exc) or "refused"
    return ""


def main():
    from filter_mate.adapters.public_api import database_tables
    from filter_mate.core.agent.sources import database_sources

    print(f"QGIS {Qgis.QGIS_VERSION}", flush=True)
    metadata = QgsProviderRegistry.instance().providerMetadata("postgres")
    # As a connection the user saved with its credentials: one stored without them asks for them in a dialog.
    kept = {"saveUsername": True, "savePassword": True}
    connection = metadata.createConnection(QgsDataSourceUri(PG).uri(False), kept)
    metadata.saveConnection(connection, NAME)
    connection.executeSql(f"""
        CREATE SCHEMA {SCHEMA};
        CREATE TABLE {SCHEMA}.communes (id serial PRIMARY KEY, nom text, geom geometry(Point, 2154));
        COMMENT ON TABLE {SCHEMA}.communes IS 'Les communes   du banc';
        INSERT INTO {SCHEMA}.communes (nom, geom) SELECT 'c' || n, ST_SetSRID(ST_MakePoint(570000 + n, 6270000), 2154)
            FROM generate_series(1, 7) AS n;
        CREATE TABLE {SCHEMA}.tarifs (code integer PRIMARY KEY, libelle text);
        INSERT INTO {SCHEMA}.tarifs VALUES (1, 'a'), (2, 'b');
        CREATE TABLE {SCHEMA}."Quoted name" (a integer, b integer, PRIMARY KEY (a, b));
    """)
    try:
        check("the connections of QGIS are listed by name", NAME in database_tables.connection_names(),
              database_tables.connection_names())
        source, = database_sources([NAME])
        check("a connection is a source named by an id", source.id.startswith("db_fm_bench_postgis_") and source.address == NAME, source)

        found = database_tables.list_tables(NAME, search=SCHEMA)
        rows = {row["table"]: row for row in found["tables"]}
        check("the tables of the schema are listed, with geometry and comment, no row",
              sorted(rows) == ["Quoted name", "communes", "tarifs"] and rows["communes"]["geometry"] is True
              and rows["tarifs"]["geometry"] is False and rows["communes"]["comment"] == "Les communes du banc"
              and set(rows["communes"]) == {"schema", "table", "geometry", "comment"} and found["count"] == 3, found)
        check("searched by every word, in the name or the comment",
              [row["table"] for row in database_tables.list_tables(NAME, search=f"{SCHEMA} BANC")["tables"]] == ["communes"]
              and database_tables.list_tables(NAME, search=f"{SCHEMA} nothing")["count"] == 0)
        everything = database_tables.list_tables(NAME, limit=2)
        check("the list is bounded and says so, the schemas of the database itself left out",
              len(everything["tables"]) == 2 and everything["truncated"] and everything["count"] >= 3
              and not any(row["schema"] in database_tables.SYSTEM_SCHEMAS
                          for row in database_tables.list_tables(NAME, limit=50)["tables"]), everything)

        project = QgsProject.instance()
        layer = database_tables.add_table(NAME, SCHEMA, "communes", "Communes du banc")
        check("a table with a geometry opens as a layer of the project",
              layer.isValid() and layer.name() == "Communes du banc" and layer.featureCount() == 7 and layer.isSpatial()
              and layer.crs().authid() == "EPSG:2154" and project.mapLayer(layer.id()) is layer
              and layer.providerType() == "postgres", layer.source())
        plain = database_tables.add_table(NAME, SCHEMA, "tarifs")
        check("a table with no geometry opens too, named after itself",
              plain.isValid() and plain.name() == "tarifs" and plain.featureCount() == 2 and not plain.isSpatial())
        odd = database_tables.add_table(NAME, SCHEMA, "Quoted name")
        check("a table with a quoted name and a key of two columns opens", odd.isValid() and odd.featureCount() == 0)
        count = len(project.mapLayers())
        for label, call in (
                ("a table the connection does not list", lambda: database_tables.add_table(NAME, SCHEMA, "absent")),
                ("a table of a schema of the database itself", lambda: database_tables.add_table(NAME, "pg_catalog", "pg_class")),
                ("a name that is a query", lambda: database_tables.add_table(
                    NAME, SCHEMA, f'communes" WHERE true; DROP SCHEMA {SCHEMA} CASCADE; --')),
                ("a connection QGIS does not have", lambda: database_tables.add_table("absent", SCHEMA, "communes")),
                ("the tables of a connection QGIS does not have", lambda: database_tables.list_tables("absent"))):
            check(f"refused: {label}", refused(call) and len(project.mapLayers()) == count, label)
        check("the schema is still there after the refusals", database_tables.list_tables(NAME, search=SCHEMA)["count"] == 3)

        metadata.saveConnection(metadata.createConnection(
            QgsDataSourceUri("host=fm_pg port=5432 dbname=postgres user=postgres password=wrong").uri(False), kept), "wrong password")
        said = refused(database_tables.list_tables, "wrong password")
        check("a database that refuses the connection is said, without its address", "did not answer" in said
              and "fm_pg" not in said and "wrong" not in said, said)
    finally:
        project = QgsProject.instance()
        project.removeAllMapLayers()
        connection.executeSql(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")


if __name__ == "__main__":
    app = QgsApplication([], True)
    app.initQgis()
    root = tempfile.mkdtemp()
    os.symlink(os.environ.get("FM_REPO", "/src"), os.path.join(root, "filter_mate"))
    sys.path.insert(0, root)
    sys.dont_write_bytecode = True
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        RESULTS.append(False)
    print(f"{RESULTS.count(True)}/{len(RESULTS)} passed", flush=True)
    os._exit(1 if RESULTS.count(False) else 0)
