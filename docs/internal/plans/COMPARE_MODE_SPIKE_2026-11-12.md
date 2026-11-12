# Compare mode — rendering spike (2026-11-12)

**Question.** Can FilterMate show the state of its layers *before* a filter and *after* it, side by side behind a
swipe line, without adding layers to the project? The swipe plugins of QGIS (02Multimap, QMapCompare, Leafmap) compare
sets of layers; none compares filter states (`subsetString` never appears in their code, read on 2026-11-09). The value
of FilterMate is the pair before / after it already keeps for each layer of a filter (`CrossOperation.changes`,
`LayerSnapshot`).

**Script.** `scripts/spikes/compare_render.py`, on the fixtures of `tests/qgis_headless/make_fixtures.py` (five squares,
a DEM of 100 × 100, a LAS of 5,000 points), in a standalone QGIS, offscreen.

## Results

| Check | Docker stable (Linux) | QGIS 4.2.3 Windows | QGIS 3.44.8 Windows |
|---|---|---|---|
| Vector: clone with the former subset renders, differs (samples) | yes, 342 | yes, 342 | yes, 342 |
| The clone stays out of the project, nothing added | yes | yes | yes |
| Canvas item: left of the line = "before" image (drawn samples) | 324/324 | 324/324 | 324/324 |
| Canvas: right of the line = the canvas drawing "after" | 1225/1296 | 1225/1296 | 1226/1296 |
| Raster: clone on the former source (DEM / DEM clipped to a zone) | yes, 17,640 | yes, 17,640 | yes, 17,640 |
| Point cloud: clone without the subset `"Classification" = 2` (COPC) | no PDAL provider in the image | yes, 597 | yes, 597 |
| Render of one state (these fixtures, 800 × 600) | 2–17 ms | 3–33 ms | 4–33 ms |
| Paint of the canvas item | 5 ms | 8 ms | 14 ms |

The right side misses 71 of 1,296 drawn samples: anti-aliased edges, where the canvas and a render job do not draw the
same pixels. Not a defect of the method.

Pitfalls met:

- A canvas grabbed before its first `mapCanvasRefreshed` shows nothing; paint it (`QWidget.render`) once refreshed.
- A point cloud opened on a LAS draws its extent only until it reloads on the COPC its indexing writes; open the COPC.
- `QgsPointCloudLayer.setSubsetString` does not exist in QGIS 3.22 (3.26 and later).

## Real data (QGIS 4.2.3 Windows, 1920 × 1080)

`scripts/spikes/compare_real_data.py`, second render of each state (the one a user waits for once the files are in the
caches of the system), and the share of sampled pixels each render drew:

| Case | Before | After |
|---|---|---|
| BD TOPO 31 buildings (1,173,829 in the layer), extent of Toulouse | 2.22 s, 39 % drawn | 0.39 s (`"hauteur" > 15`), 3 % drawn |
| DEM 1 m (Cerdagne), whole extent | 0.041 s | 0.022 s (clipped to the centre quarter) |
| LiDAR HD tile (25,111,931 points, COPC), whole tile | 0.33 s (first 1.08 s), 56 % drawn | 0.03 s (class 6), 4 % drawn |
| Same tile, 200 m around its centre | 0.09 s, 97 % drawn | nothing drawn (no class 6 there) |

Pitfalls of the measure (each one first measured a blank image in a few milliseconds):

- A render job of a standalone QGIS draws nothing without a GUI application (`QgsApplication([], True)`).
- The style the BD TOPO GeoPackage carries shows the buildings from 1:25,000 only; at the scale of the department
  nothing is drawn, scale-based visibility off or not (a rule of the style).
- The hierarchy of a COPC loads in the background: a render right after opening the layer draws its extent only.

So the "before" image costs what a render of those layers costs: up to two or three seconds for a dense vector layer at
the scale of a city. It must be rendered in the background (`QgsMapRendererParallelJob`, not waited on the main
thread), kept for the extent it was made for, and the swipe shows the canvas alone, with a busy sign on the line, until
it arrives; a pan or a zoom starts a new one and cancels the one under way.

## What it means for the mode

The method holds for the three kinds of layers FilterMate filters:

1. **Before state from the history.** For each layer of the operation to compare, `layer.clone()`, then the
   `LayerSnapshot` of the state before: `setDataSource(snapshot.source, name, snapshot.provider)` when it differs (a
   derived raster or point cloud gets its original source back), `setSubsetString(snapshot.subset)`. Never added to the
   project: adding a layer makes FilterMate refresh everything.
2. **Drawing.** The canvas keeps drawing the layers as they are (after). A `QgsMapCanvasItem` (as `_MaskItem` of
   `preview_overlay.py`) paints the "before" image clipped to the left of the line; dragging the line repaints the item
   only. The "before" image is rendered again, in a `QgsMapRendererParallelJob`, when the extent changes (pan, zoom),
   with the layers of the canvas in their order, the clones in place of the layers compared.
3. **Cost.** One render of the compared layers per extent; on real data it is the render time of those layers, no more.

Open before building it:

- Real data on PostGIS: not measured yet (a GeoPackage of 1.2 million buildings and a LiDAR HD COPC are, above).
- Which operation is compared: the last one, or one chosen in the history of the agent / of the dock.
- Layers not filtered by the operation: drawn once, on both sides (in the canvas only).
- A derived file of the history may have been removed since: the clone then has no source; say so and leave that layer
  out of the "before" image.
- QGIS 3.22: no point cloud subset, so a point cloud compared there by its derived file only.

Measured outputs (PNG and JSON) of the runs above are kept outside the repository.
