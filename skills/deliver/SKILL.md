---
name: deliver
title: Deliver data as files
description: files of the user's layers: format for whom, CRS, styles, a zip
metadata:
  version: 2
  plugin_min: 5.1.2
  audience: chat, mcp
  tools: export_layers, filter_state, list_layers, describe_layer, preview_filter, apply_filter
  risk: change
  trust: builtin
---

# Deliver data as files

export_layers writes layers as they are filtered now into a sub-folder of the export root of the QGIS machine. The
user is asked before anything is written. This skill says how to choose what it writes.
In the QGIS chat, the user chooses the default export folder locally at the first export, or from the agent menu.
Cancelling that choice writes nothing. Exports never go into a QGIS profile.
Never propose that location or bypass a refused destination. The folder choice is separate from the usual
permission to run an export.

## Method

1. Export only when the user asks for files ("export", "send me", "give me a file", "for my colleague who uses
   Excel"). A question about the data, a filter or a map is not a request for files.
2. The data first. export_layers writes what the filter of each layer keeps now, every feature of a layer with no
   filter; a selection alone is not used. filter_state tells what is filtered. When the user wants a part ("only the
   communes of 31"), filter first with apply_filter (preview_filter to check the count), then export.
3. The format, for whom the files are (vector_format):
   - GPKG (the default): for QGIS and most GIS software; several layers, long field names, any CRS.
   - GeoJSON or FlatGeobuf: for the web and developers. GeoJSON is text, for small layers; FlatGeobuf is fast for
     large ones.
   - CSV or XLSX: for a spreadsheet (Excel, LibreOffice): the attributes, without the geometry. XLSX when they name
     Excel.
   - KML: for Google Earth; always written in WGS 84 longitude and latitude.
   - GeoParquet: for data analysis (Python, DuckDB, cloud warehouses).
   - ESRI Shapefile: only when the user names it. It cuts field names to 10 characters and holds one geometry
     type per file; say so when the layer has longer names.
   Rasters go as COG (cloud optimized GeoTIFF, the default) or GTiff; point clouds as LAZ (the default), COPC (to
   stream on the web), LAS, GPKG or CSV. Web basemaps are not exported (they are skipped).
4. The CRS: leave crs out and each layer keeps its own. Set it only when the user names one ("in Lambert 93":
   EPSG:2154, "in WGS 84" or "GPS coordinates": EPSG:4326). For a GeoJSON meant for a web map, propose EPSG:4326.
   describe_layer tells the CRS of a layer.
5. Styles (styles): qml when the files go to a QGIS user, so the layers open with the colors of the map (a .qml
   beside each file, read by QGIS when the file is opened); sld for a map server (GeoServer, MapServer) or other OGC
   software; none otherwise. A spreadsheet (CSV, XLSX) gets no style. Rasters get a .qml with qml.
6. One file or a package:
   - single_file (GPKG only) writes every vector layer into one GeoPackage named package_name, one table each; the
     answer gives tables ({layer: table}) and package. The QML styles are kept inside it. Good for "everything in
     one file" for a QGIS user.
   - zip packs every file written, styles too, into package_name.zip: for an email or an upload, or a Shapefile
     (several files). An existing zip is never overwritten: export_2.zip, export_3.zip... come instead. outputs and
     styles then name the files inside the zip.
   - package_name: a short name the user would recognize (communes_31, delivery_2026-11); "export" otherwise.
7. subfolder: a short folder named after the delivery (letters, digits, _ . - and / between two levels). A file of
   the same name in it is overwritten (a zip never): use a new subfolder to keep an older export.
8. Then tell the user what was written, in their words: the files (outputs) or the package, the folder, and each
   layer failed or skipped with its reason.

## Never

- Never export what the user did not ask for: no file "to be safe", no other layer than those named.
- Never choose ESRI Shapefile on your own.
- Never use run_pyqgis to write files export_layers refuses. When a format is refused because this QGIS lacks its
  driver (KML, XLSX, GeoParquet depend on how GDAL was built), say so and propose another format: GPKG, FlatGeobuf
  or CSV.
- Never promise a file before the answer of export_layers: the user may decline, a layer may fail.
- Never give paths of the computer: the answer names the files from the sub-folder, say it that way.

## Where to look

- list_layers: the layers of the project and their kinds.
- describe_layer: the fields (their names, for a Shapefile) and the CRS of a layer.
- filter_state: what each layer keeps now.
