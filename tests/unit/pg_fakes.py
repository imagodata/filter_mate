# -*- coding: utf-8 -*-
"""A small in-memory PostgreSQL catalog behind a psycopg2-like connection / cursor.

It understands exactly the statements the FilterMate cleanups send (listing
matviews / tables with ``LIKE ANY``, schema content, ``to_regclass``, ``DROP``
of one object, ``DROP SCHEMA``), so the tests check the SQL that is sent and
what is left in the catalog.
"""
import re

_QUALIFIED = re.compile(r'^"((?:[^"]|"")*)"\."((?:[^"]|"")*)"$')


def _like_to_regex(pattern, escape="\\"):
    out = []
    i = 0
    while i < len(pattern):
        char = pattern[i]
        if char == escape and i + 1 < len(pattern):
            out.append(re.escape(pattern[i + 1]))
            i += 2
            continue
        out.append(".*" if char == "%" else "." if char == "_" else re.escape(char))
        i += 1
    return re.compile("^" + "".join(out) + "$", re.DOTALL)


class FakePgCatalog:
    """Objects as ``(kind, schema, name)`` with kind in matview / table / view."""

    def __init__(self, objects=(), schemas=(), dependents=None, undroppable=(), ghosts=(), overbroad=False):
        self.objects = list(objects)
        self.schemas = set(schemas) | {schema for _k, schema, _n in self.objects}
        self.dependents = dependents or {}     # name -> names that must be dropped first
        self.undroppable = set(undroppable)    # DROP raises
        self.ghosts = set(ghosts)              # DROP succeeds but the object stays
        self.overbroad = overbroad             # listing ignores the LIKE patterns
        self.executed = []

    def statements(self):
        return [" ".join(sql.split()) for sql, _p in self.executed
                if sql.lstrip().upper().startswith(("DROP", "CREATE"))]

    def has(self, name, schema=None):
        return any(n == name and (schema is None or s == schema) for _k, s, n in self.objects)


class FakeCursor:
    def __init__(self, catalog):
        self.catalog = catalog
        self._rows = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def close(self):
        pass

    def execute(self, sql, params=None):
        catalog = self.catalog
        catalog.executed.append((sql, params))
        flat = " ".join(sql.split())
        self._rows = []
        if flat.startswith("SELECT matviewname FROM pg_matviews"):
            self._rows = [(n,) for k, s, n in catalog.objects if k == "matview" and s == params[0]]
        elif "ESCAPE '!'" in flat and ("FROM pg_tables" in flat or "FROM pg_matviews" in flat):
            kind = "matview" if "pg_matviews" in flat else "table"
            patterns = [_like_to_regex(p, "!") for p in params if isinstance(p, str) and "%" in p]
            schemas = params[0] if params and isinstance(params[0], list) else None
            self._rows = [(s, n) for k, s, n in catalog.objects if k == kind and any(p.match(n) for p in patterns)
                          and (schemas is None or s in schemas)]
        elif "FROM pg_matviews" in flat or "FROM pg_tables" in flat:
            kind = "matview" if "pg_matviews" in flat else "table"
            patterns = [_like_to_regex(p) for p in params[0]]
            self._rows = [(s, n) for k, s, n in catalog.objects if k == kind
                          and (catalog.overbroad or any(p.match(n) for p in patterns))]
        elif "FROM pg_class" in flat:
            code = {"matview": "m", "table": "r", "view": "v"}
            self._rows = [(n, code[k]) for k, s, n in catalog.objects if s == params[0]]
        elif "information_schema.schemata" in flat:
            self._rows = [(1 if params[0] in catalog.schemas else 0,)]
        elif flat.startswith("SELECT to_regclass"):
            match = _QUALIFIED.match(params[0])
            schema, name = (part.replace('""', '"') for part in match.groups())
            self._rows = [(f"{schema}.{name}" if catalog.has(name, schema) else None,)]
        elif flat.startswith(("DROP MATERIALIZED VIEW", "DROP TABLE")):
            match = _QUALIFIED.match(re.sub(r"^DROP (?:MATERIALIZED VIEW|TABLE) ", "", flat))
            if match is None:
                raise RuntimeError(f"unexpected qualified name in: {flat}")
            schema, name = (part.replace('""', '"') for part in match.groups())
            if name in catalog.undroppable:
                raise RuntimeError(f"cannot drop {name}")
            if not catalog.has(name, schema):
                raise RuntimeError(f"{name} does not exist")
            if any(catalog.has(dep) for dep in catalog.dependents.get(name, ())):
                raise RuntimeError(f"other objects depend on {name}")
            if name not in catalog.ghosts:
                catalog.objects = [o for o in catalog.objects if not (o[1] == schema and o[2] == name)]
        elif flat.startswith("DROP SCHEMA"):
            schema = flat.split(" ")[-1].strip('"')
            if "CASCADE" in flat:
                catalog.objects = [o for o in catalog.objects if o[1] != schema]
            elif any(o[1] == schema for o in catalog.objects):
                raise RuntimeError(f"cannot drop schema {schema} because other objects depend on it")
            catalog.schemas.discard(schema)

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._rows[0] if self._rows else None


class FakeConnection:
    def __init__(self, catalog):
        self.catalog = catalog
        self._cursor = FakeCursor(catalog)
        self.commits = self.rollbacks = 0
        self.closed = False

    def cursor(self):
        return self._cursor

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.closed = True
