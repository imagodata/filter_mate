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
| Escape | Removes the last object, or the last search with its clicked object |
| *Clear* | Forgets every object drawn by SAM |

The first click of an area prepares it: about 3 s under QGIS for Windows, then about 0.1 s per gesture.

**Similar objects** first draws the clicked object. The patches of a similar colour in the visible map, at
most 120 of them, are then proposed to SAM, which redraws each one in the background. An object is kept when
its area, and its shape with *same shape*, are within the ratios of the group compared with the clicked one.

The objects are polygons in the CRS of the raster, stored with the filter like any other raster selection.
Processing and the REST API do not accept them yet.

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

SAM finds roughly half of the buildings of the same size in the view, where the colour engine finds almost
none. About two found objects out of three are not buildings, though: check the result before filtering
with it, and remove the wrong ones with Escape or *Clear*. On ten other buildings of the same orthophoto
(`scripts/sam_similar_features.py`), SAM did less well: median precision 0.24, recall 0.31.

**A filter tried and not adopted** (2026-11-10, rule set before the run). The objects that are not buildings
have a lower SAM score (median 0.75 against 0.88) and a colour further from the clicked object (largest
difference of the mean R, G, B: 25.6 against 11.4). Thresholds chosen on the first ten buildings (score at
least 0.42, colour distance at most 30) raised the median precision on the ten others from 0.24 to 0.31 for a
recall from 0.31 to 0.29 (`scripts/sam_similar_analysis.py`). The gain required was 0.10: the search is
unchanged.

## Model

SAM 2.1 hiera tiny (Meta, Apache 2.0), quantized ONNX export of
[onnx-community/sam2.1-hiera-tiny-ONNX](https://huggingface.co/onnx-community/sam2.1-hiera-tiny-ONNX),
run by onnxruntime with the CPU execution provider, 4 threads at most (more was slower).

Code: `adapters/qgis/coverage_layers/sam_model.py` (files, checksums, download, provider),
`adapters/qgis/coverage_layers/segmentation.py` (windows, session, encoding, similar objects and download
tasks), `ui/controllers/segmentation_controller.py` and `ui/tools/segmentation_tool.py` (the gestures on the
map), `core/ports/segmentation_port.py` (what FilterMate asks of a model).
