# Favorites Sharing — FilterMate optional extension

Distribute and consume FilterMate favorite collections through the QGIS
[Resource Sharing](https://github.com/akbargumbira/qgis_resources_sharing)
plugin.

This extension is **fully optional**. FilterMate works without it. When
the extension is absent, the JSON import/export still works as before —
you just can't browse curated collections from within the dialog.

## What it does

- **Scans** `{profile}/resource_sharing/collections/**/filter_mate/favorites/*.fmfav{,-pack}.json`
  on every plugin load and on project change.
- **Exposes** discovered favorites in a read-only "📡 Shared..." picker,
  accessible from:
  - the favorites ★ menu (entry "Import from Resource Sharing...")
  - the Favorites Manager dialog (button in the header row)
- **Forks** a shared favorite into the current project's SQLite DB —
  re-binds portable signatures (`postgres::schema.table`, …) to the
  user's local layer UUIDs.
- **Preserves provenance**: forked favorites carry
  `_extra.forked_from = {collection, file}` for traceability.

## Publishing a collection

A Resource Sharing collection is a Git repository. Any directory named
`filter_mate/favorites/` under the collection root is scanned.

```
my-collection/
  collection.json          # Resource Sharing manifest (optional)
  icon.svg                 # collection icon
  filter_mate/
    favorites/
      zones_bruxelles.fmfav-pack.json   # multi-favorite bundle
      snippets/
        single_zone.fmfav.json          # bare favorite payload
```

### Bundle format (schema v3)

Recommended: export via `FavoritesService.export_favorites(..., collection_metadata={...})`
and check the resulting JSON into your collection repo.

Minimal valid bundle:

```json
{
  "schema": "filter_mate.favorites",
  "schema_version": 3,
  "min_compat_plugin_version": "4.0.0",
  "generator": "filter_mate/5.0.12",
  "exported_at": "2026-04-23T12:00:00",
  "version": "3.0",
  "collection": {
    "name": "Zones Bruxelles",
    "author": "imagodata",
    "license": "CC-BY-4.0",
    "tags": ["bruxelles", "urbanisme"]
  },
  "favorites": [
    {
      "name": "Zone Molenbeek",
      "expression": "\"nom_commune\" = 'Molenbeek'",
      "tags": ["bruxelles"],
      "remote_layers": {
        "postgres::public.batiments": {
          "expression": "\"type\" = 'residentiel'",
          "layer_signature": "postgres::public.batiments",
          "display_name": "Bâtiments",
          "provider": "postgres"
        }
      },
      "spatial_config": {
        "source_layer_signature": "postgres::public.zones",
        "predicates": {"INTERSECT": true}
      }
    }
  ]
}
```

### Bare snippet format

For quick sharing (one-off pastes), a single favorite payload is
accepted directly at the file root:

```json
{
  "name": "Quick snippet",
  "expression": "TRUE",
  "description": "Useful one-liner"
}
```

## Portability rules

A favorite is **portable** when it carries portable signatures — format
`<provider>::<key>` where `<key>` is:

| Provider       | Key                                       | Example                             |
|---------------:|:------------------------------------------|:------------------------------------|
| `postgres`     | `schema.table`                            | `postgres::public.zones`            |
| `spatialite`   | `table`                                   | `spatialite::zones`                 |
| `ogr` (GPKG)   | `layername`                               | `ogr::zones`                        |
| `ogr` (shape)  | file stem without extension               | `ogr::zones`                        |
| other          | `layer.name()` (fallback)                 | `wms::my-wms`                       |

Favorites without signatures (legacy v1/v2) still import, but only
resolve cleanly when the destination project contains a layer with the
same `name()` — which is fragile across users.

## Config

Toggle via `config.json`:

```json
{
  "EXTENSIONS": {
    "favorites_sharing": {
      "enabled": {"value": true}
    }
  }
}
```

## Unit tests

```bash
pytest tests/unit/extensions/favorites_sharing/
```

See `tests/unit/extensions/favorites_sharing/` for round-trip,
signature-keying, scanner, and validator tests.

## JSON Schema

The canonical schema is at
[`schema/favorites-v3.schema.json`](schema/favorites-v3.schema.json).

Validation is built-in (structural checks) and upgraded to full
JSON-Schema when the `jsonschema` package is installed:

```python
from filter_mate.extensions.favorites_sharing.validator import validate, validate_with_jsonschema
ok, errors = validate(my_bundle_dict)          # lightweight, always available
ok, errors = validate_with_jsonschema(my_bundle_dict)  # strict, needs `pip install jsonschema`
```
