# FilterMate Segmentation

Optional QGIS plugin that gives FilterMate its interactive segmentation model. FilterMate ships no
model and no runtime, so its own package stays publishable on plugins.qgis.org.

This plugin is **not** in the FilterMate zip and is not published on plugins.qgis.org: it depends on a
compiled runtime and on a model file.

## Install

1. Copy `filter_mate_segmentation` into the `python/plugins` folder of your QGIS profile and enable it.
2. Install the runtime yourself, from the Python of your QGIS (OSGeo4W Shell on Windows):
   `python -m pip install onnxruntime`. The plugin never does it for you.
3. *Plugins > FilterMate Segmentation > Install the segmentation model…* downloads 62 MB, once you
   confirm, from a pinned revision. Each file is checked against its SHA-256.
4. In FilterMate, on a raster, choose **Segment** in the PIPETTE group.

## Use

Left click on the object, right click off it, or drag a box. **Enter** validates the object, **Escape**
forgets the one being drawn. Validated objects are plain polygons: the filter applied to the other layers
needs no model. Processing and the REST API do not accept them yet.

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
[onnx-community/sam2.1-hiera-tiny-ONNX](https://huggingface.co/onnx-community/sam2.1-hiera-tiny-ONNX).
