# Interactive segmentation (experimental)

The **Segment** target of the PIPETTE group, on a raster, draws an object from a click or a box with a
segmentation model, locally on the CPU. Validated objects are plain polygons: the filter applied to the
other layers needs no model, and a saved filter replays without one.

FilterMate ships neither the model nor its runtime, so its package stays small and publishable on
plugins.qgis.org. Both are set up once, from the panel.

## Set up

1. Select a raster and choose **Segment** in the PIPETTE group. FilterMate needs onnxruntime, declared by the
   `python_dependencies` key of its `metadata.txt`. If it is missing, a message asks your confirmation.
   Nothing is installed before you agree, and nothing is installed at the start of QGIS.
2. Once you confirm, pip installs it in the background, as a QGIS task, into your QGIS profile
   (`filtermate/python/py<version>`, about 100 MB). The Python of QGIS is not modified and QGIS stays usable.
   If you refuse, an **Install onnxruntime…** button stays in the group. If the install fails (no network,
   no pip), the reason is in the FilterMate log and the group shows the command to run by hand, in a terminal
   (the OSGeo4W Shell on Windows), before restarting QGIS.
3. Click **Install the model (62 MB)…** and confirm. The files of SAM 2.1 hiera tiny are downloaded from a
   pinned revision of [onnx-community/sam2.1-hiera-tiny-ONNX](https://huggingface.co/onnx-community/sam2.1-hiera-tiny-ONNX)
   into your QGIS profile (`filtermate/models/sam2.1-hiera-tiny-q`), each one checked against its SHA-256 before it replaces
   anything. The download runs as a QGIS task, can be canceled, and uses the HTTP proxy set in the QGIS options.
   If the files turn out to be damaged, a **Repair the model…** button replaces the bad ones.

Nothing else leaves your computer: the model runs on your CPU.

## Use

Left click on the object, right click off it, or drag a box. **Enter** (or *Validate object*) adds the object
to the selection, **Escape** forgets the one being drawn, *Clear* forgets the validated ones. Validated objects
are polygons in the CRS of the raster, stored with the filter like any other raster selection. Processing and
the REST API do not accept them yet.

## What it is good at

**Buildings and other well delimited objects.** Measured with this model on a 25 cm orthophoto, 2026-11-09,
median overlap with the reference outlines (IoU, 1 is a perfect match):

| Gesture | 100 buildings | 18 parcels | FilterMate object detector, 3 clicks |
|---|---|---|---|
| 1 click | 0.65 | 0.21 | |
| 3 corrective clicks | 0.76 | 0.27 | buildings 0.52, parcels 0.26 |
| Box | 0.82 | 0.44 | |

Parcels did not reach the improvement we required: a cadastral limit is often invisible on the image.
Trees were not validated either: hedges tend to merge. Use the object detector or a vector layer for them.

On the CPU (4 threads, WSL2): about 1 s to prepare an area, about 35 ms per prompt. These timings were not
measured under QGIS for Windows.

## Model

SAM 2.1 hiera tiny (Meta, Apache 2.0), quantized ONNX export of
[onnx-community/sam2.1-hiera-tiny-ONNX](https://huggingface.co/onnx-community/sam2.1-hiera-tiny-ONNX),
run by onnxruntime with the CPU execution provider, 4 threads at most (more was slower).

Code: `adapters/qgis/coverage_layers/sam_model.py` (files, checksums, download, provider),
`adapters/qgis/coverage_layers/segmentation.py` (window, session, encoding task, download task),
`ui/controllers/segmentation_controller.py` and `ui/tools/segmentation_tool.py` (the tool on the map),
`core/ports/segmentation_port.py` (what FilterMate asks of a model).
