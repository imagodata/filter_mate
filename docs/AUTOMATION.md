# Automating FilterMate 5 — Processing, Python API, REST API, MCP server

FilterMate 5 filters vector, raster and point cloud layers in any direction. The same operations run without the dock
through three surfaces, which share one implementation (`adapters/public_api/operations.py`); an
[MCP server](#mcp-server) then lets an AI assistant drive the REST API:

| Surface | For | Entry point |
|---|---|---|
| Processing | models, batch processing, `qgis_process`, the Python console | `filtermate:*` algorithms and models |
| Python API | other plugins, console scripts | `plugins['filter_mate'].get_public_api()` |
| REST API | web clients, notebooks, other programs | `filtermate_api` (FastAPI), `X-API-Key` |

Shared rules:

- **In place.** Filters change the project layers, like the dock: a subset string for vector and point cloud layers,
  a derived source (clipped VRT, COPC) for rasters and clipped point clouds. The project file always keeps the
  original sources.
- **Undo.** An operation whose source is a raster or point cloud layer of the project, and `filter_point_cloud`, go to
  the dock's history: the dock's Undo on that layer reverts them. The others (vector source, geometry, unfilter) are
  kept in a separate history so they never interleave with the dock's vector history: revert them with
  `clear_filters` or the dock's Unfilter.
- **One at a time.** An operation is refused while another one runs, and while a task of the dock that changes or
  reads the filters still runs in the background (vector filter, cross filter, export, height above ground; not an
  expression evaluation): the error says so, try again when it ends.
- **Project layers only.** A layer loaded from a path by Processing is a temporary copy: filtering it would be lost,
  so it is skipped with a warning. A *source* can be a temporary layer (a model output such as a slope raster): it is
  only read.
- **Main thread.** The operations run synchronously on the Qt main thread (`FlagNoThreading` in Processing; the REST
  API marshals every call that reads or changes QGIS, reads included).
- **Cache.** After each filter, the derived files nothing refers to any more are removed and the cache is kept under
  `CROSS_FILTER.cache_max_gb` (oldest undo steps holding a file forgotten first), as after a dock run.

## Processing algorithms

| Algorithm | Does | Main parameters | Outputs |
|---|---|---|---|
| `filtermate:cross_filter` | filters any layers by the features of a vector layer | `SOURCE`, `SELECTED_ONLY`, `TARGETS`, `PREDICATES`, `BUFFER`, `COVERAGE`, `OPERATOR` | `OUTPUT` |
| `filtermate:cross_filter_from_raster` | … by the pixels of a raster: value range, classes or raster calculator expression | `SOURCE`, `BAND`, `MODE`, `DERIVATIVE`, `MINIMUM`, `MAXIMUM`, `CLASSES`, `EXPRESSION`, `FILTER_SOURCE` + targets | `OUTPUT` |
| `filtermate:cross_filter_from_point_cloud` | … by the footprint of the points kept on a point cloud | `SOURCE`, `CLASSES`, `Z_MIN`/`Z_MAX`, `INTENSITY_MIN`/`MAX`, `RETURN_NUMBER`, `EXPRESSION`, `SOURCE_OPERATOR` + targets | `OUTPUT` |
| `filtermate:cross_filter_from_geometry` | … by an extent or a WKT geometry | `EXTENT`, `GEOMETRY` + targets | `OUTPUT` |
| `filtermate:filter_point_cloud` | applies the same criteria to several point clouds (LiDAR HD tiles) | `LAYERS`, criteria, `OPERATOR` | `OUTPUT` |
| `filtermate:clear_filters` | back to the original source, no filter | `LAYERS` | `OUTPUT` |
| `filtermate:apply_favorite` | replays a favorite (subsets, raster / point cloud clips) | `FAVORITE` (name or id) | `OUTPUT` |
| `filtermate:export_filtered_layers` | writes each layer as filtered now: GPKG / GeoJSON / SHP / FlatGeobuf / CSV, COG / GeoTIFF, LAZ / COPC / LAS / GPKG / CSV | `LAYERS`, `VECTOR_FORMAT`, `RASTER_FORMAT`, `POINT_CLOUD_FORMAT`, `CRS`, `OUTPUT_FOLDER` | `OUTPUT_FILES`, `OUTPUT_FOLDER` |
| `filtermate:batch_filter` | one expression on several vector layers (4.8) | `INPUT_LAYERS`, `EXPRESSION` | counts |

Target parameters, shared by the four cross filters: `TARGETS` (any kind), `PREDICATES` (indexes of `Intersect`,
`Contain`, `Disjoint`, `Equal`, `Touch`, `Overlap`, `Are within`, `Cross`; rasters and point clouds keep the inside, or
the outside with `Disjoint`), `BUFFER` (source units), `COVERAGE` (minimum share of a polygon target inside the source,
%), `OPERATOR` (0 replace, 1 AND, 2 OR, 3 AND NOT with the previous filter of each target).

`OUTPUT` lists the target layers handled (not the source, even when its criteria filter it), so a filter chains into
the next step of a model: plug the `OUTPUT` of a filter into the `LAYERS` of *Export filtered layers*. Without any
target, a raster source with `FILTER_SOURCE` (or a point cloud source with criteria) filters itself and `OUTPUT` is
that source.

`LAYERS_FILTERED` and `LAYERS_FAILED` give the names of the layers handled and failed (declared outputs from QGIS
3.28; returned by `processing.run` on every version).

Notes: the buffer of `cross_filter_from_geometry` is in the units of the first target's CRS; on a target with no
filter yet, `AND`, `OR` and `AND NOT` keep the new selection, like the vector engine; `filter_point_cloud` and point
cloud source criteria refuse `AND NOT` without an existing filter (they would keep only the excluded points);
`FILTER_SOURCE` is off by default (the dock masks a raster source, automation leaves it untouched unless asked);
`MAX_PIXELS` and `RESOLUTION` left empty use the FilterMate settings (`CROSS_FILTER.raster_source_max_pixels`,
`point_cloud_footprint_resolution`). The progress bar follows the targets and *Cancel* stops a cross filter between
two steps, a point cloud filter or an export before the next layer (`error`: `canceled`); the raster / point cloud
clips of `apply_favorite` and a point cloud being written cannot be interrupted.

### Shipped models (`processing/models/`)

| Model | Chain |
|---|---|
| `filtermate:extraction_par_emprise` | area layer → `cross_filter` (any layers) → `export_filtered_layers` (GPKG, COG, LAZ). Iterate over the area features in batch mode for one package per commune. |
| `filtermate:vegetation_pres_des_lignes` | `filter_point_cloud` (classes 4, 5) → `cross_filter` (lines + corridor buffer) → export COPC |
| `filtermate:parcelles_en_pente_faible` | `native:slope` → `cross_filter_from_raster` (0 – max slope, minimum coverage) → export GPKG |
| `filtermate:batiments_absents_du_lidar` | `cross_filter_from_point_cloud` (class 6, `Disjoint`) → export of the buildings with no building point |

Their output folder parameter is `dossier_de_sortie`. They are generated by `scripts/build_processing_models.py` (QGIS Python). Open one in the modeler (*Model → Open
Model*) to adapt it and save your own copy.

### From the Python console

```python
import processing

result = processing.run("filtermate:cross_filter_from_raster", {
    "SOURCE": "mnt", "BAND": 1, "MODE": 0, "MINIMUM": 1200, "MAXIMUM": 1300,
    "TARGETS": ["parcelle", "lhd"], "PREDICATES": [0], "COVERAGE": 50})
processing.run("filtermate:export_filtered_layers", {
    "LAYERS": result["OUTPUT"], "RASTER_FORMAT": 0, "POINT_CLOUD_FORMAT": 1, "OUTPUT_FOLDER": "C:/exports/zone"})
```

### From the command line (`qgis_process`)

The plugin declares `hasProcessingProvider=yes` and implements `initProcessing()`, so `qgis_process` loads its
algorithms and models without the GUI (the plugin must be enabled in the profile). Layers are the project's ones:

```bat
qgis_process run filtermate:extraction_par_emprise --PROJECT_PATH=C:/data/chantier.qgz -- ^
    emprise=communes selection_seule=false couches=bdtopo_batiment couches=mnt tampon=0 ^
    dossier_de_sortie=C:/exports/communes
```

`qgis_process` does not save the project: a filter only matters for the steps that follow it in the same run, and the
derived files of the run are removed when it exits. To replay a favorite and export the result, chain
`apply_favorite` → `export_filtered_layers` in a model and run the model. Without the dock, `apply_favorite` reads the
favorites saved in the project file.

## Python API (other plugins, scripts)

```python
from qgis.utils import plugins

api = plugins["filter_mate"].get_public_api()
report = api.cross_filter("mnt", ["parcelle", "lhd"], coverage_min=50,
                          raster_selection={"band": 1, "mode": "range", "minimum": 1200, "maximum": 1300})
report = api.cross_filter("lhd", ["batiment"], predicates=["Disjoint"], point_cloud_criteria={"classes": [6]})
report = api.cross_filter_by_geometry("POLYGON((...))", "EPSG:2154", ["mnt", "lhd"], buffer=10)
report = api.filter_point_clouds(["dalle_1", "dalle_2"], {"classes": [3, 4, 5], "z_min": 1200})
report = api.export_layers(["parcelle", "mnt", "lhd"], "C:/exports/zone", point_cloud_format="COPC")
report = api.apply_favorite("Zone humide")
report = api.clear_filters(["parcelle", "mnt", "lhd"])
state = api.get_filter_state()      # [{"id", "name", "kind", "subset", "derived", "source"}]
```

Every operation returns a report: `{"ok", "done", "failed", "skipped", "error", "outputs", "details"}`;
`details["source_filtered"]` tells whether a cross filter also changed its source. Invalid
arguments (NaN or infinite numbers, a buffer beyond 10 000 000 units, a coverage outside 0-100) give `ok = False` with a
message, never an exception; so does an operation refused while FilterMate is busy (`details["busy"]`). Two exported
layers with the same name are reported as `name` and `name (layer id)`. Signals: `operation_completed(name, report)`,
`error_occurred(operation, message)`, plus the 4.7 ones (`filter_applied`, `filter_cleared`).

Exports refuse to overwrite files still needed by a project layer, its original source before filtering or
enrichment, or an undo step. Raster and point cloud writers use private temporary files until the export completes;
cancellation leaves the previous destination intact. COPC output requires a compatible PDAL executable: when it
is unavailable the export fails with a message asking for LAZ, without writing a different filename automatically.

The operations also honor an explicitly supplied `project`. A filter computed in the background is refused for
layers whose source or filter changed while it was running, so newer changes stay intact.

`raster_selection`: `band`, `mode` (`range`, `classes`, `expression`), `minimum`, `maximum`, `classes`,
`expression`, `derivative`. `derivative` (range mode only) says what the bounds apply to when the band is a DTM:
`value` (default), `slope_degrees`, `slope_percent`, `aspect`, `hillshade` (0-255), `roughness` (Wilson TRI, mean
absolute difference with the 8 neighbours). In the `DERIVATIVE` parameter of the Processing algorithm they are
indexes 0 to 5, in this order. Slope, aspect and hillshade use the Horn 3 x 3 kernel; degrees and Web Mercator
cells are converted to ground metres; a pixel next to a NoData has no derivative, nor does a flat pixel have an
aspect. No `north` exposure: a range cannot wrap around 0 / 360 (use two filters, `OR`ed). `point_cloud_criteria`: an expression string, or `classes`, `z_min`, `z_max`, `intensity_min`,
`intensity_max`, `return_number`, `expression`.

### Script: one extraction per commune

```python
import processing
from qgis.core import QgsProject

project = QgsProject.instance()
communes = project.mapLayersByName("commune")[0]
for feature in communes.getFeatures():
    communes.selectByIds([feature.id()])
    filtered = processing.run("filtermate:cross_filter", {
        "SOURCE": communes, "SELECTED_ONLY": True, "TARGETS": ["batiment", "mnt", "lhd"], "PREDICATES": [0]})
    processing.run("filtermate:export_filtered_layers", {
        "LAYERS": filtered["OUTPUT"], "OUTPUT_FOLDER": f"C:/exports/{feature['code_insee']}"})
processing.run("filtermate:clear_filters", {"LAYERS": ["batiment", "mnt", "lhd"]})
communes.removeSelection()
```

## REST API

Start the API from QGIS with a `QGISFilterMateAccessor(plugin.get_public_api(), plugin)` (see
`filtermate_api/qgis_accessor.py`; `plugin` is `qgis.utils.plugins["filter_mate"]`). FilterMate 5 routes:

| Route | Body | Returns |
|---|---|---|
| `POST /filters/cross` | `source_layer` (any kind, id or name), `target_layers`, `predicates`, `buffer`, `coverage_min`, `operator`, `selected_only`, `raster_selection`, `point_cloud_criteria`, `filter_source` | `filtered` (targets), `failed`, `skipped` |
| `POST /filters/geometry` | `wkt`, `crs`, `target_layers`, predicates… | same |
| `POST /filters/point-cloud` | `layers`, `criteria`, `operator` | `done`, `failed`, `skipped` |
| `POST /filters/clear` | `layers` | same |
| `GET /filters/state` | — | filtered layers: name, kind, subset, derived |
| `POST /export` | `layers`, `subfolder`, `vector_format`, `raster_format`, `point_cloud_format`, `crs` | `done`, `outputs` (server paths) |
| `GET /layers` | — | layers with `layer_kind` |
| `POST /favorites/{id}/apply` | — | replays the favorite like the dock's menu: subsets (remote layers too), raster / point cloud clips |

Answers: `400` names what stopped the operation (`"Cross filter failed: <reason>"`; an unexpected error in QGIS is
reported as such, its details stay in the FilterMate log); `503` with `Retry-After` when QGIS
is busy (its main thread on a long task for 30 s, or a FilterMate operation or task running): nothing was changed,
retry later. A change that is done is never reported as failed: its `active_filters` snapshot is `{}` when QGIS was too
busy to read it back (`GET /filters/state` reads the state).

`POST /filters/undo` and `/filters/redo` are the dock's Undo / Redo for vector filters: the same history, whatever
added its last step. Nothing the API changes is recorded there: neither `POST /filters/apply` nor the FilterMate 5
operations (cross, geometry, point cloud, clear, favorites); revert those with `POST /filters/clear`.

`POST /export` only writes below the export root of the server (`FILTERMATE_API_EXPORT_ROOT`, or `API.export_root`
in `config.json`; default: `FilterMate/exports` in the QGIS profile folder, `~/.filtermate/exports` when the API runs
outside QGIS). Clients give a sub-folder name, never a path. The root is private (created or set to mode 0700); a root
that is a symbolic link, a Windows junction, a file or (POSIX) a folder of another user is refused
(`500 Export root unavailable`, the reason in the log), and no output file that is a symbolic link is written over.
The API reads the `API` section of the `config.json` the plugin uses (QGIS profile); while that file has none, the
section of `config/config.json` in the plugin folder (4.x place, or outside QGIS) is used, with a warning in the log.

Web pages the user visits must not drive QGIS through the browser:

- **CORS is off by default**: no origin may call the API from a browser until it is listed in `API.cors_origins`
  (`config.json`, a list or a comma-separated string) or `FILTERMATE_API_CORS_ORIGINS` (comma-separated). `*` is
  refused without an API key.
- **No cross-site changes**: a request that is not a read (`POST`…) and comes from a web page — an `Origin` header,
  or `Sec-Fetch-Site: cross-site` — is refused (`403`) unless that origin is the API's own (`/docs`) or listed in
  `cors_origins`: a form post or a no-cors fetch needs no pre-flight, CORS alone does not stop it. A request body must
  be JSON (`Content-Type: application/json`, else `415`). Scripts and programs send no `Origin`: nothing changes
  for them.
- **Loopback host names only**: bound to `127.0.0.1`, `localhost` or `::1`, the API answers only requests whose `Host`
  is one of these names (a numeric port at most), which defeats DNS rebinding. A request with no `Host` (HTTP/1.0) is
  served. A reverse proxy in front must forward `Host: 127.0.0.1`. Bound to another address, an API key is required.
- **Limits**: request bodies over 1 MiB (`FILTERMATE_API_MAX_BODY_BYTES`) get 413, chunked or not; an expression is at
  most 500 000 characters, a request at most 1 000 layers of at most 1 000 characters each; NaN and Infinity are refused, a buffer is at most 10 000 000
  units (10 000 km in metres) in absolute value. Validation errors (422) say where and why, without echoing the value.

```bash
curl -s -X POST localhost:8000/filters/cross -H "X-API-Key: $KEY" -H "Content-Type: application/json" -d '{
  "source_layer": "lhd", "target_layers": ["batiment"], "predicates": ["Disjoint"],
  "point_cloud_criteria": {"classes": [6]}}'
curl -s -X POST localhost:8000/export -H "X-API-Key: $KEY" -H "Content-Type: application/json" -d '{
  "layers": ["batiment"], "subfolder": "controle/2026-10"}'
```

## MCP server

`filtermate_api/mcp/` is a [Model Context Protocol](https://modelcontextprotocol.io) server that lets an AI assistant
(Claude Code, Claude Desktop, any MCP client) list, filter, undo and export layers of the open QGIS project. It does
not talk to QGIS itself: it speaks MCP over **stdio**, started by the client *outside* QGIS, and relays each tool call
to the [REST API](#rest-api) running inside QGIS (one tool per endpoint, the same validation, the same
main-thread safety, the same API key). It imports neither `qgis` nor `fastapi`, and the plugin never imports it:
without `mcp` installed, FilterMate is unchanged.

### Prerequisites

1. **The REST API is running in QGIS with an API key.** The plugin does not start it by itself. Install `fastapi` and
   `uvicorn` in the Python of QGIS (`requirements-api.txt`), set the key and serve the app from the Python console
   (in a thread, so QGIS stays usable):

   ```python
   import os, threading, uvicorn
   from qgis.utils import plugins
   from filter_mate.filtermate_api.config import APIConfig
   from filter_mate.filtermate_api.qgis_accessor import QGISFilterMateAccessor
   from filter_mate.filtermate_api.server import create_app

   os.environ["FILTERMATE_API_KEY"] = "<a long random key>"   # or API.api_key_sha256 in config.json
   plugin = plugins["filter_mate"]
   config = APIConfig.load()
   app = create_app(config=config, accessor=QGISFilterMateAccessor(plugin.get_public_api(), plugin))
   server = uvicorn.Server(uvicorn.Config(app, host=config.host, port=config.port, log_level="warning"))
   threading.Thread(target=server.run, daemon=True).start()      # server.should_exit = True stops it
   ```

   The API listens on `http://127.0.0.1:8000` by default. On a loopback bind it accepts any request when no key is
   configured on the QGIS side: the MCP server refuses to start without a key, but only a key set in QGIS makes the API
   check it.
2. **Python 3.10 or later** on the machine of the MCP client, with the SDK: `pip install "mcp>=1.7,<3"` (`mcp` 1.x
   and 2.x both work; 1.7 is the oldest release tested, and with pydantic 2.12 or later `mcp` 1.22 or later is needed).
   This is the client's Python, not the one of QGIS. The plugin zip does not ship `requirements-mcp.txt`, hence the
   command above.

### Configuration

| Setting | Default | Meaning |
|---|---|---|
| `FILTERMATE_API_KEY` (environment) | none, required | the API key, sent as `X-API-Key`. `--api-key-env NAME` reads another variable. There is no option to give the key itself: it would show in the process list. |
| `--url` | `http://127.0.0.1:8000` | base URL of the REST API. A URL that is not on this machine is refused unless `--allow-remote` is given (the key then travels over the network: use `https`). |
| `--timeout` | 45 s | HTTP timeout per call, above the 30 s the API waits for the QGIS main thread. |

The server lives in the plugin folder, `filtermate_api/mcp/`. **Run its `__main__.py` file by path**: it works from any
directory with no `PYTHONPATH`, and a folder named `mcp/` in the client's working directory cannot hide the SDK. The
plugin folder is
`%APPDATA%/QGIS/QGIS3/profiles/default/python/plugins/filter_mate` on Windows (`%APPDATA%/QGIS/QGIS4/profiles/default/...`
for QGIS 4), `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/filter_mate` on Linux
(`.../QGIS/QGIS4/...` for QGIS 4); from a clone of the repository, the clone itself. `python -m filtermate_api.mcp`
also works once `PYTHONPATH` is that folder, but run from a directory that has its own `mcp/` folder it imports that one
instead of the SDK.

**Claude Code**

```bash
claude mcp add filtermate --env FILTERMATE_API_KEY=<key> -- python /path/to/filter_mate/filtermate_api/mcp/__main__.py
# or, as a module (PYTHONPATH = the plugin folder)
claude mcp add filtermate --env FILTERMATE_API_KEY=<key> --env PYTHONPATH=/path/to/filter_mate -- python -m filtermate_api.mcp
```

Put the name first, as above: `--env` takes several values. Use the Python that has `mcp` installed (a virtual
environment's `python`), and `--scope user` to have it in every project.

**Claude Desktop** (`claude_desktop_config.json`)

```json
{
  "mcpServers": {
    "filtermate": {
      "command": "python",
      "args": ["/path/to/filter_mate/filtermate_api/mcp/__main__.py", "--url", "http://127.0.0.1:8000"],
      "env": { "FILTERMATE_API_KEY": "<key>" }
    }
  }
}
```

### Tools

One tool per REST endpoint. Layers are designated by id or name (list them with `list_layers`), except
`apply_filter`, which takes the name of a vector layer.

| Tool | Endpoint | Does |
|---|---|---|
| `list_layers` | `GET /layers` | layers with id, name, kind (vector / raster / point cloud), CRS, active filter |
| `filter_status` | `GET /filters/status` | vector filters active, last change, last error |
| `filter_state` | `GET /filters/state` | every layer filtered now, of any kind (subset, clipped source) |
| `apply_filter` | `POST /filters/apply` | sets the subset string (provider SQL `WHERE` clause) of one vector layer |
| `undo_filter`, `redo_filter` | `POST /filters/undo`, `/redo` | the dock's vector history (not what the other tools record, see above) |
| `cross_filter` | `POST /filters/cross` | filters layers of any kind by the selection of a source layer of any kind (selected features, raster pixels, point cloud points) with spatial predicates, buffer, minimum coverage, combine operator |
| `geometry_filter` | `POST /filters/geometry` | same, by a WKT geometry in a given CRS |
| `point_cloud_filter` | `POST /filters/point-cloud` | keeps points by class, Z, intensity, return number or expression on several point clouds (one step of the dock's history of those layers) |
| `clear_filters` | `POST /filters/clear` | back to the original source, no filter (reverts all of the above except undo / redo) |
| `list_favorites`, `apply_favorite` | `GET /favorites`, `POST /favorites/{id}/apply` | saved filters |
| `export_layers` | `POST /export` | writes the layers as filtered now below the export root of the QGIS machine |

The tools carry MCP annotations: the four readers are `readOnlyHint`; no filter tool is destructive (a filter changes
what a layer shows, never its data, and `clear_filters` reverts it); `export_layers` is the only one flagged
destructive, because it writes files and overwrites a file of the same name in its sub-folder. The server also exposes
two read-only resources, `filtermate://layers` and `filtermate://state`. Every tool answers one JSON object as text
(and as `structuredContent` with the SDK versions that produce it); the list tools wrap their rows
(`{"layers": [...]}`, `{"favorites": [...]}`) because an SDK sends a bare list as one text block per row.

Errors reach the assistant as readable tool errors: `503` becomes "QGIS is busy, nothing was changed, retry"; `401` /
`403` "the API key was rejected"; `422` says which field is invalid and why; an unreachable API says to start the REST
API in QGIS; a timeout, or a connection that breaks after a change was sent, tells the assistant to read `filter_state` before
retrying (the change may have been applied). `undo_filter` and `redo_filter` are not idempotent: the server's
instructions ask the assistant to read `filter_state` after one, rather than repeat it blindly.

### Tested

`tests/unit/api/` (a fake REST API on a socket, the MCP server over stdio) and `tests/api/test_mcp_against_real_api.py`
(the real FastAPI app) run without QGIS. `tests/qgis_headless/check_mcp_e2e.py` drives the whole chain in a real QGIS:
a real MCP client starts `filtermate_api/mcp/__main__.py` against the REST API served on the loaded plugin, and every
step is checked on the real layers (subset strings, clipped sources, exported files). Run it in the QGIS image:

```bash
docker run --rm -v "$PWD:/src:ro" qgis/qgis:ltr bash -ec '
  pip install -q --break-system-packages --ignore-installed typing_extensions fastapi uvicorn mcp
  python3 /src/tests/qgis_headless/make_fixtures.py /tmp/fm > /dev/null
  FM_FIXTURES=/tmp/fm xvfb-run -a qgis --nologo --noversioncheck --profiles-path /tmp/profiles \
    --code /src/tests/qgis_headless/check_mcp_e2e.py'
```

It passed on QGIS 3.44 and 4.2 with `mcp` 1.30 and 2.3. Known limit it records: with OGR (GeoPackage, Shapefile),
`apply_filter` with invalid SQL is accepted by the provider and the layer shows nothing; `list_layers` then reports
`feature_count` -1 and `clear_filters` recovers.

### Security

- **An assistant that can call these tools changes what your layers show**, and can write files below the export root.
  Give the key only to a client you trust, and prefer the client's per-tool approval for the tools that change things.
- The key travels in an environment variable of the server process, never on its command line, and is not written in
  any answer. `claude mcp add --env` and `claude_desktop_config.json` store it in the client's configuration file in
  clear text: protect that file.
- The server only talks to a loopback URL (`--allow-remote` to override), uses no proxy for it and follows no redirect,
  so the key goes nowhere else. The REST API's own protections apply to every call (loopback `Host`, size limits,
  export root, validation).
- `undo_filter` only undoes steps of the dock's vector history. What the tools do is not in it, except
  `point_cloud_filter`, which is one step of the dock's history of those point clouds (the dock's Undo on the layer
  reverts it, `undo_filter` does not): `clear_filters` is the way back.
