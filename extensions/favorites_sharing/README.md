# Favorites Sharing — FilterMate optional extension

Distribute and consume FilterMate favorite collections through the QGIS
[Resource Sharing](https://github.com/akbargumbira/qgis_resources_sharing)
plugin.

This extension is **fully optional**. FilterMate works without it. When
the extension is absent, the JSON import/export still works as before —
you just can't browse curated collections from within the dialog.

> **Documentation**
> - End-user guide (consume + publish, FR): [docs/favorites_sharing/USER_GUIDE.md](../../docs/favorites_sharing/USER_GUIDE.md)
> - Repo admin guide (set up a sharing Git repo, FR): [docs/favorites_sharing/REPO_SETUP.md](../../docs/favorites_sharing/REPO_SETUP.md)
> - This README: technical reference (config schema, JSON formats, internals).

## What it does

**Consume** (import favorites published by others):
- **Scans** `{profile}/resource_sharing/collections/**/filter_mate/favorites/*.fmfav{,-pack}.json`
  on every plugin load and on project change.
- **Exposes** discovered favorites in a read-only "📡 Shared..." picker,
  accessible from:
  - the favorites ★ menu (entry "Import from Resource Sharing...")
  - the Favorites Manager dialog (button in the header row)
- **Filters by author** — the picker has an *Author* dropdown built from
  the distinct collection authors. The author badge is also shown next
  to each entry in the list so identical favorite names from different
  publishers stay disambiguated.
- **Forks** a shared favorite into the current project's SQLite DB —
  re-binds portable signatures (`postgres::schema.table`, …) to the
  user's local layer UUIDs.
- **Preserves provenance**: forked favorites carry
  `_extra.forked_from = {collection, file}` for traceability.

**Publish** (share your favorites with others):
- Accessible from:
  - the favorites ★ menu → "📤 Publish to Resource Sharing..."
  - the Favorites Manager dialog → "📤 Publish..." button
  - **Quick publish** ("🚀 Quick publish to default repo") — one-click
    push of every favorite to the configured default remote repo,
    skipping the dialog. Hidden when no default repo is configured.
- Target selection: pick a **configured remote repo** (git-backed,
  curated by IT — see the *Remote repos* section), an **existing**
  collection under your Resource Sharing root, create a **new
  collection** in the root (one click), or **browse to a custom
  directory** for collections hosted outside the default path.
- Multi-select favorites with checkboxes, pre-fill collection metadata
  (name, author, license, tags, homepage, description) from config.
- Writes the bundle at `<target>/filter_mate/favorites/<name>.fmfav-pack.json`
  using the canonical v3 format, and **merges** the collection-level
  `collection.json` manifest (preserves pre-existing keys like
  `qgis_min`, `tags` set by the Resource Sharing plugin).
- **Manage repos** ("🌐 Manage Resource Sharing repos…") opens a CRUD
  dialog to add/edit/delete remote repos, set the default, link a QGIS
  Auth Manager entry, and run "Test connection" — without editing the
  raw JSON in the configuration tree.

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

All entries live under `EXTENSIONS.favorites_sharing` in your
FilterMate `config.json`. Defaults ship in `config.default.json`.

```json
{
  "EXTENSIONS": {
    "favorites_sharing": {
      "enabled": {"value": true},
      "resource_sharing_root": {"value": ""},
      "default_publish_collection": {"value": ""},
      "default_publish_metadata": {
        "value": {
          "author": "Your Name",
          "license": "CC-BY-4.0",
          "homepage": "https://example.org"
        }
      },
      "allowed_collections": {"value": []},
      "auto_refresh_on_project_load": {"value": true}
    }
  }
}
```

| Key | Purpose |
|---|---|
| `enabled` | Toggle the whole extension. When `false`, menu / dialog entries are hidden. |
| `resource_sharing_root` | Override the auto-detected Resource Sharing `collections/` directory. Leave empty to let the scanner find it from the QGIS profile. Useful for shared network mounts or custom setups. |
| `default_publish_collection` | Absolute path (or directory basename under the root) of the collection pre-selected in the Publish dialog. When empty the first available collection is used. |
| `default_publish_metadata` | `author` / `license` / `homepage` pre-filled in the Publish dialog — saves re-typing for organisations publishing many bundles. |
| `allowed_collections` | Opt-in allow-list of collection directory names (basenames only). When non-empty the scanner **only** ingests favorites from these collections — useful to restrict an org to curated repos. Empty list = scan everything. |
| `auto_refresh_on_project_load` | Re-scan on every project load so signature resolution picks up the current project's layers. |
| `remote_repos` | List of git-backed publish targets. See **Remote repos** below. |

## Remote repos

A remote repo lets a team publish favorite bundles by pushing to a
shared git repository (GitHub, GitLab, Gitea, …). Anonymous read access
is supported out of the box — only the publisher needs credentials.

Each entry in `remote_repos` is a dict:

```json
{
  "name": "Acme team",
  "git_url": "https://github.com/acme/qgis-collections.git",
  "branch": "main",
  "local_clone": "",
  "target_collection": "acme-favorites",
  "is_default": true,
  "authcfg_id": "qg1xy7w"
}
```

| Field | Required | Notes |
|---|---|---|
| `name` | yes | Display label in the publish combo. |
| `git_url` | no | When empty → fallback A (write locally, user pushes). |
| `branch` | no | Defaults to the remote's HEAD. |
| `local_clone` | no | Empty → `[profile]/FilterMate/repos/<slug>`. Relative paths anchor on the same dir. |
| `target_collection` | no | Sub-directory under `collections/`. Empty → repo root *is* the collection. **Validated** with `safe_join_under()` — values that would escape `local_clone` (`../foo`, absolute paths, symlink-out) are rejected with a warning. |
| `is_default` | no | Picks this repo on dialog open. |
| `authcfg_id` | no | **Preferred** — id of a QGIS Auth Manager entry. Resolved at exec time. |
| `auth_header` | no | **Deprecated** — plaintext header (`Basic xxx` / `Bearer xxx`). Logs a warning on read. |

### Authentication: use QGIS Auth Manager

`authcfg_id` is the id of an entry in QGIS' encrypted credential store
(*Settings → Options → Authentication*). FilterMate supports two config
methods that map onto an HTTP `Authorization:` header:

- **Basic** — username + password → `Basic <base64(user:pass)>`. Use
  this for GitHub PATs (username = anything, password = PAT).
- **API Header / token-style** — store the token under a `token` /
  `Authorization` / `header` config key. A bare token is auto-prefixed
  with `Bearer `; a value already starting with a scheme word is sent
  verbatim.

The plaintext credential never lands in `config.json`. The
master-password prompt fires the first time a publish runs.

## Security & path safety

The extension exposes an internet-facing surface (git subprocess +
untrusted JSON bundles + untrusted SQL expressions from third-party
publishers). The defenses below are wired by default:

| Threat | Mitigation | Implementation |
|---|---|---|
| Plain-text PAT in `config.json` | Prefer `authcfg_id` (encrypted at rest) | [git_client.py](git_client.py): `_resolve_authcfg_header()` |
| Token leak in logs / GitError msgs | Scrub `Authorization:` headers + URL-embedded creds | [git_client.py](git_client.py): `_scrub_command/_scrub_text` |
| Token visible in `argv` / process list | Inject via `git -c http.extraHeader=…` | [git_client.py](git_client.py): `_run()` |
| Path traversal via `target_collection: "../foo"` | `safe_join_under()` realpath check | [path_utils.py](path_utils.py), [remote_repo_manager.py](remote_repo_manager.py): `RemoteRepo.collection_dir` |
| Symlink bypass of `allowed_collections` | TODO — H1 in audit 2026-04-27 | (not yet wired in scanner) |
| Malformed bundle ingested into DB | Validator runs at scan time | TODO C3 — wire `validate()` in `_load_file()` |
| Argv flag-injection on `git_url` | TODO — emit `--` separator | C2 in audit 2026-04-27 |
| Master password prompt at startup | Resolve `authcfg_id` lazily at exec time, not at config load | [git_client.py](git_client.py): `_resolve_auth_header()` |

See [docs/favorites_sharing/REPO_SETUP.md §3](../../docs/favorites_sharing/REPO_SETUP.md#3--permissions)
for the operator-side controls (branch protection, PAT scope, etc.).

## Unit tests

```bash
pytest tests/unit/extensions/favorites_sharing/
```

Coverage (108 tests as of 2026-04-27):
- `test_git_client.py` — subprocess wrapper, secret scrubbing, authcfg resolution
- `test_remote_repo_manager.py` — config parsing, CRUD, default selection, publish E2E, test_connection
- `test_scanner.py` — collection discovery, allow-list, cache
- `test_validator.py` — schema v3 lightweight + jsonschema modes
- `test_publish.py` — bundle write, manifest merge, overwrite safety
- `test_roundtrip.py` — `FilterFavorite` ↔ JSON normalization
- `test_author_filter.py` — `SharedFavorite.author`, `list_authors()`, search composition

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
