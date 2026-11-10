# Objects drawn by SAM (experimental)

The two object targets of the PIPETTE group, on a raster, can use a segmentation model: SAM 2.1 tiny,
locally on the CPU.

- **Clicked object** draws the object under the click.
- **Similar objects** draws the clicked object, then every object like it in the visible map.

The objects are plain polygons. The filter applied to the other layers needs no model, and a saved filter
replays without one. Without SAM, both targets keep finding objects by their colour, as before.

FilterMate ships neither the model nor its runtime, so its package stays small and publishable on
plugins.qgis.org. Both are installed once, from the panel, after your confirmation.

## Set up

1. Select a raster and choose **Clicked object** or **Similar objects** in the PIPETTE group. A message
   offers to install SAM: onnxruntime (about 100 MB) and the model (62 MB). Nothing is installed before you
   agree, and nothing is installed at the start of QGIS. The question comes once a session; an
   **Install SAM…** button stays in the group.
2. Once you confirm, pip installs onnxruntime in the background, as a QGIS task, into your QGIS profile
   (`filtermate/python/py<version>`). The Python of QGIS is not modified. onnxruntime is declared by the
   `python_dependencies` key of `metadata.txt`.
3. The model then downloads from a pinned revision of
   [onnx-community/sam2.1-hiera-tiny-ONNX](https://huggingface.co/onnx-community/sam2.1-hiera-tiny-ONNX)
   into `filtermate/models/sam2.1-hiera-tiny-q`. Each file is checked against its SHA-256 before it replaces
   anything. The download can be canceled and uses the HTTP proxy set in the QGIS options.
4. If pip fails (no network, no pip), the reason is in the FilterMate log and the group shows the command to
   run by hand in a terminal (the OSGeo4W Shell on Windows). If the model files turn out to be damaged, a
   **Repair the model…** button replaces the bad ones.

Nothing else leaves your computer: the model runs on your CPU.

## Use

Turn the object detector or the similar objects tool of the rail on, or choose the target in the PIPETTE
group. The **Engine** list of the group switches between SAM and the colour engine.

| Gesture | Effect |
|---|---|
| Move the mouse | Outline of the object under it, once the area is prepared |
| Click | A new object, added at once |
| Shift+click | The last object, extended |
| Right click | The last object, trimmed |
| Drag a box | A new object inside the box |
| G (or Tab when QGIS lets it through) | The last object at the next granularity: a part, the object, a group |
| Escape | Rejects the proposals; otherwise removes the last object, or the last search with its clicked object |
| *Clear* | Forgets every object drawn by SAM |
| *To layer* | Adds the objects to the project as a polygon layer (memory layer, area in m² on the project ellipsoid) |

The first click of an area prepares it: about 3 s under QGIS for Windows, then about 0.1 s per gesture.

SAM proposes three outlines for each click and FilterMate keeps the one it rates best. On 20 buildings that was
the best of the three 11 times: G shows the others (median overlap 0.71 with the chosen one, 0.76 with the best
of the three).

**Similar objects** first draws the clicked object. The patches of a similar colour in the visible map, at
most 120 of them, are then proposed to SAM, which redraws each one in the background. An object is kept when
its area, and its shape with *same shape*, are within the ratios of the group compared with the clicked one,
and when it looks like it: the encoder features of SAM under the two objects must point the same way (cosine
at least 0.68).

The objects found are **proposals**, outlined in dashes, outside the selection: click one to keep it, right
click to reject it, Enter (or *Keep*) keeps them all, Escape (or *Reject*) rejects them all.

The objects are polygons in the CRS of the raster, stored with the filter like any other raster selection.
Processing (the `SEGMENTS` parameter of *Filter layers of any type by the pixels of a raster*, a polygon layer),
the REST API and the MCP tools (`segments` in `raster_selection`) accept them too: see `docs/AUTOMATION.md`.
*To layer* turns them into a memory layer of the project, numbered, with their area in m²: the layer to give
Processing, to export or to edit. It is not saved with the project: *Make Permanent* in QGIS keeps it.

## From a vector layer (Processing)

*Draw objects on a raster with SAM from points or polygons* (`filtermate:segment_from_features`) draws one object
per feature of a guide layer, with no click: a point is a click on the object, a polygon gives its bounding box and
a point inside it. The output is a polygon layer in the CRS of the raster, with the attributes of the feature,
`sam_score` (the score SAM gives its mask) and, for a polygon, `sam_iou` (overlap of the footprint with the drawn
object, from 0 to 1). It runs in the background and changes no layer of the project; it can be a step of a
model, for example before *Filter layers of any type by the pixels of a raster* with its `SEGMENTS`.

A multipoint gives all its points to one object. A multipolygon is prompted by its largest part. An invalid
footprint is made valid before `sam_iou` is computed. A footprint under a pixel is prompted by its point. Source
fields named `sam_score` or `sam_iou` (any case) are replaced. A window that cannot be drawn, such as a tile of a
service, is reported and loses its objects only; the run fails only when no window could be drawn.

Nearby objects of one size share a window of 1024 pixels, encoded once. The cell is the native one, doubled as
often as needed for a box to fill at most two thirds of the window. A point sees at least 150 m of ground.

Measured 2026-11-10 on 40 buildings of the BD TOPO (50 to 2000 m²) on the 25 cm Cerdagne orthophoto, median
overlap with the footprint (`scripts/sam_feature_bench.py`, rule set before the run):

| Prompt | Median IoU |
|---|---|
| Box of the footprint and a point inside it (kept) | 0.81 |
| Box only | 0.80 |
| Box grown by 10 % and the point | 0.78 |
| Point only (a point layer) | 0.73 |

Neither other prompt met the rule (+0.02, at most 4 of 40 buildings losing more than 0.05). The 40 buildings
took 8 windows of about 1.8 s each under QGIS for Windows. The BD TOPO footprint is not the roof seen from above:
a low `sam_iou` points at a building to look at, it does not prove a change.

```python
processing.run("filtermate:segment_from_features", {
    "RASTER": ortho, "FEATURES": footprints, "OUTPUT": "memory:"})
```

## What it is good at

**Buildings and other well delimited objects.** Measured with this model on a 25 cm orthophoto, 2026-11-09,
median overlap with the reference outlines (IoU, 1 is a perfect match):

| Gesture | 100 buildings | 18 parcels | Colour engine, 3 clicks |
|---|---|---|---|
| 1 click | 0.65 | 0.21 | |
| 3 corrective clicks | 0.76 | 0.27 | buildings 0.52, parcels 0.26 |
| Box | 0.82 | 0.44 | |

Parcels did not reach the improvement we required: a cadastral limit is often invisible on the image.
Trees were not validated either: hedges tend to merge. Use the colour engine or a vector layer for them.

**Similar objects: a start, not a finished tool.** Measured on the 25 cm orthophoto of the test project
(Cerdagne), 2026-11-10, with `scripts/sam_similar_bench.py` under QGIS 4.2.3 for Windows. Ten reference
buildings of 80 to 400 m² were each clicked in a 150 m view, with the default ratios (0.5 to 2, same shape).
A found object counts when it overlaps a BD TOPO building with an IoU of at least 0.5. Medians:

| | SAM | Colour engine |
|---|---|---|
| Precision (found objects that are buildings) | 0.36 | 0.00 |
| Recall (buildings of the same size found) | 0.46 | 0.00 |
| Time per search | 5.2 s | 2.4 s, 24 s on two views |
| Overlap of the clicked object | 0.78 | |

These were the numbers before the appearance filter. On ten other buildings of the same orthophoto
(`scripts/sam_similar_features.py`), SAM did less well: median precision 0.24, recall 0.31.

**Appearance filter, adopted** (2026-11-10, rule set before the run: a threshold chosen on the first ten
buildings, judged on the ten others, adopted if the median precision gains at least 0.10 for a recall loss of
at most 0.05). The cosine of the encoder features of SAM separates the classes (median 0.80 for the buildings
found, 0.69 for the rest). With the threshold of 0.68 chosen on the first ten (`scripts/sam_similar_appearance.py`):

| Median | First ten, before | First ten, after | Ten others, before | Ten others, after |
|---|---|---|---|---|
| Precision | 0.36 | 0.49 | 0.24 | 0.35 |
| Recall | 0.46 | 0.43 | 0.31 | 0.26 |

About half of the objects proposed are buildings: keep or reject them before filtering with them.

**Tried and not adopted.** A score and colour filter (precision 0.24 to 0.31 on the ten others, short of the
0.10 required, `scripts/sam_similar_analysis.py`), and a second, framed pass of SAM after the click (median
overlap 0.711 to 0.713 on 20 buildings, short of the 0.02 required).

**Colour engine.** Its similar objects took up to 34 s on this orthophoto: the patches of the whole raster
were simplified to a vertex budget they did not need. They are now only measured, and the budget applies to
the objects kept: 5.5 s at most, median precision 0.06 and recall 0.11 instead of 0 and 0, as the patches and
the clicked object are now measured alike.

## Model

SAM 2.1 hiera tiny (Meta, Apache 2.0), quantized ONNX export of
[onnx-community/sam2.1-hiera-tiny-ONNX](https://huggingface.co/onnx-community/sam2.1-hiera-tiny-ONNX),
run by onnxruntime with the CPU execution provider, 4 threads at most (more was slower).

Code: `adapters/qgis/coverage_layers/sam_model.py` (files, checksums, download, provider),
`adapters/qgis/coverage_layers/segmentation.py` (windows, session, encoding, similar objects and download
tasks), `ui/controllers/segmentation_controller.py` and `ui/tools/segmentation_tool.py` (the gestures on the
map), `core/ports/segmentation_port.py` (what FilterMate asks of a model).
