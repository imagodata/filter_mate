# Automating FilterMate 5 — Processing, Python API, REST API

FilterMate 5 filters vector, raster and point cloud layers in any direction. The same operations run without the dock
through three surfaces, which share one implementation (`adapters/public_api/operations.py`):

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
- **One at a time.** An operation is refused while a filter started from the dock still runs in the background.
- **Project layers only.** A layer loaded from a path by Processing is a temporary copy: filtering it would be lost,
  so it is skipped with a warning. A *source* can be a temporary layer (a model output such as a slope raster): it is
  only read.
- **Main thread.** The operations run synchronously on the Qt main thread (`FlagNoThreading` in Processing; the REST
  API marshals its calls).

## Processing algorithms

| Algorithm | Does | Main parameters | Outputs |
|---|---|---|---|
| `filtermate:cross_filter` | filters any layers by the features of a vector layer | `SOURCE`, `SELECTED_ONLY`, `TARGETS`, `PREDICATES`, `BUFFER`, `COVERAGE`, `OPERATOR` | `OUTPUT` |
| `filtermate:cross_filter_from_raster` | … by the pixels of a raster: value range, classes or raster calculator expression | `SOURCE`, `BAND`, `MODE`, `MINIMUM`, `MAXIMUM`, `CLASSES`, `EXPRESSION`, `FILTER_SOURCE` + targets | `OUTPUT` |
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

Notes: the buffer of `cross_filter_from_geometry` is in the units of the first target's CRS; `AND NOT` needs an
existing filter on the layer (on an unfiltered point cloud it would keep only the excluded points, so it is refused);
`FILTER_SOURCE` is off by default (the dock masks a raster source, automation leaves it untouched unless asked).

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

`qgis_process` does not save the project: a filter only matters for the steps that follow it in the same run. To
replay a favorite and export the result, chain `apply_favorite` → `export_filtered_layers` in a model and run the
model. Without the dock, `apply_favorite` reads the favorites saved in the project file.

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
arguments give `ok = False` with a message, never an exception. Signals: `operation_completed(name, report)`,
`error_occurred(operation, message)`, plus the 4.7 ones (`filter_applied`, `filter_cleared`).

`raster_selection`: `band`, `mode` (`range`, `classes`, `expression`), `minimum`, `maximum`, `classes`,
`expression`. `point_cloud_criteria`: an expression string, or `classes`, `z_min`, `z_max`, `intensity_min`,
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

Start the API from QGIS with a `QGISFilterMateAccessor` (see `filtermate_api/qgis_accessor.py`). FilterMate 5 routes:

| Route | Body | Returns |
|---|---|---|
| `POST /filters/cross` | `source_layer` (any kind), `target_layers`, `predicates`, `buffer`, `coverage_min`, `operator`, `selected_only`, `raster_selection`, `point_cloud_criteria`, `filter_source` | `filtered` (targets), `failed` |
| `POST /filters/geometry` | `wkt`, `crs`, `target_layers`, predicates… | same |
| `POST /filters/point-cloud` | `layers`, `criteria`, `operator` | `done`, `failed`, `skipped` |
| `POST /filters/clear` | `layers` | same |
| `GET /filters/state` | — | filtered layers: name, kind, subset, derived |
| `POST /export` | `layers`, `subfolder`, `vector_format`, `raster_format`, `point_cloud_format`, `crs` | `done`, `outputs` (server paths) |
| `GET /layers` | — | layers with `layer_kind` |
| `POST /favorites/{id}/apply` | — | applies subsets and raster / point cloud clips |

`POST /export` only writes below the export root of the server (`FILTERMATE_API_EXPORT_ROOT`, or `API.export_root`
in `config.json`; default: `<temp>/filtermate_exports_<user>`). Clients give a sub-folder name, never a path.

```bash
curl -s -X POST localhost:8000/filters/cross -H "X-API-Key: $KEY" -H "Content-Type: application/json" -d '{
  "source_layer": "lhd", "target_layers": ["batiment"], "predicates": ["Disjoint"],
  "point_cloud_criteria": {"classes": [6]}}'
curl -s -X POST localhost:8000/export -H "X-API-Key: $KEY" -H "Content-Type: application/json" -d '{
  "layers": ["batiment"], "subfolder": "controle/2026-10"}'
```
