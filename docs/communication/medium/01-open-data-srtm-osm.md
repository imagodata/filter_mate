# From SRTM Slopes to OpenStreetMap Schools: A Two-Step QGIS Filter

*Chain a terrain threshold and a proximity query to build a focused field-check map — with free global datasets.*

How can you turn a broad terrain question into a short, useful map for field review?

This workflow uses two open datasets around Kathmandu, Nepal:

1. **SRTM elevation** to identify road segments that intersect steep terrain.
2. **OpenStreetMap (OSM)** to find mapped schools near those road segments.

The point is not to create a flood, landslide, or road-safety prediction. It is to show how successive spatial filters can narrow a project from a terrain condition to nearby places worth checking.

The thresholds below — slope of at least **18%** and a **150 m** proximity buffer — are illustrative settings for exploring the workflow. They are not engineering or safety standards.

![The Kathmandu SRTM slope raster with OSM roads and schools in QGIS](./kathmandu-demo/captures/kathmandu-cover.png)

**Walkthrough video:** [Kathmandu FilterMate walkthrough](./kathmandu-demo/video/Kathmandu_FilterMate_Walkthrough.mp4) — 56 seconds, recorded in Windows QGIS 4.2.3 with FilterMate 5.0.1, English captions and a locally generated English voice-over. French subtitles are available in `captions-fr.srt`. Upload the video to a supported host and embed its public URL when publishing.

## Get free data for an area outside France

### Elevation: SRTM

The [USGS SRTM 1 Arc-Second Global dataset](https://www.usgs.gov/centers/eros/science/usgs-eros-archive-digital-elevation-shuttle-radar-topography-mission-srtm-1) provides near-global elevation data at roughly 30 m resolution, including Nepal. Search for Kathmandu in [USGS EarthExplorer](https://earthexplorer.usgs.gov/), choose **SRTM 1 Arc-Second Global**, and download the GeoTIFF tile covering your area. A free EarthExplorer account is required to download data.

### Roads and schools: OpenStreetMap

Install the QGIS **QuickOSM** plugin from the QGIS plugin manager. Zoom to a manageable study area around Kathmandu, then query:

- `highway` for roads;
- `amenity` = `school` for mapped schools.

Use the canvas extent as the query area and retain the road line and school point layers. If you prefer a regional extract, download Nepal from [Geofabrik](https://download.geofabrik.de/asia/nepal.html); the country PBF is a larger download, so QuickOSM is more convenient for a small tutorial area.

OpenStreetMap is licensed under the [ODbL](https://www.openstreetmap.org/copyright). Attribute OpenStreetMap and its contributors in maps and any redistributed data. Coverage and tagging vary by location.

## Prepare a slope raster

In QGIS, reproject the DEM to a suitable local projected CRS before calculating slope, so horizontal and elevation units are both in metres. For Kathmandu, use the appropriate UTM zone for the study area, such as **WGS 84 / UTM zone 45N (EPSG:32645)**.

Run **GDAL → Raster terrain analysis → Slope** on the projected DEM. Enable percent slope output, then inspect the raster’s range and NoData values. The slope raster is a derived surface for this screening example; it is not an authoritative road-gradient survey.

## Filter roads by terrain

1. Set the slope raster as FilterMate’s source.
2. In the raster tools, select values from **18% slope** up to the raster maximum.
3. Set the OSM road layer as the target and choose **Intersect**.
4. Apply the filter. In this captured study extent, the road layer shows **14 of 305 mapped road features** intersecting the selected steep-slope pixels. These counts describe this extract and setting; they will vary with the data snapshot and extent.

This first step uses a raster threshold to filter vector features — a slope condition becomes a road shortlist.

![FilterMate using an 18% SRTM slope threshold to filter OSM roads with Intersect](./kathmandu-demo/captures/slope-to-roads.png)

## Use the filtered roads to find nearby schools

Now use the result of the first filter as the source for a second operation:

1. Make the filtered OSM road layer current and select its visible features as the source geometry.
2. Set the OSM schools layer as the target.
3. Choose **Intersect** and set a **150 m** buffer around the selected road geometry.
4. Apply the second filter.

The schools layer now shows mapped schools within the chosen distance of the road segments that intersected steep terrain. This captured run returned **2 mapped schools**. Both steps remain inspectable in the QGIS project; adjust the slope threshold or buffer and rerun the filter if the question changes.

![FilterMate using the filtered roads as source and schools as the target with Intersect and a 150 m buffer](./kathmandu-demo/captures/roads-to-schools.png)

## Export the answer, not a pile of intermediate files

Review the two filtered layers on the map. When the result is ready to share, configure FilterMate’s **Exporting** tab to export the currently visible road segments and schools to a GeoPackage. The captured GeoPackage includes the layer styles; the QGIS project is supplied separately for reproducing the workflow.

The intermediate filter states help you develop and inspect the analysis in one project. Export is the step that writes the selected final results as deliverable data. The verified GeoPackage contains the final **14 roads and 2 schools**; it does not contain a stack of manually exported intermediate layers.

The [starting QGIS project](./kathmandu-demo/Kathmandu_FilterMate.qgz), [post-filter project](./kathmandu-demo/Kathmandu_FilterMate_Final.qgz), and [exported GeoPackage](./kathmandu-demo/video-output/Kathmandu_final.gpkg) are included with this tutorial package.
The included OSM extract covers a small Kathmandu extent (85.300–85.310° E, 27.710–27.720° N), and the elevation source is SRTM tile N27E085. A fresh OSM query may return different feature counts.

## Read the result carefully

This workflow identifies OSM-mapped schools near road segments intersecting a chosen SRTM slope threshold. It does **not** show whether a school is reachable, whether a road is safe, or whether a slope will fail.

Several factors limit interpretation:

- SRTM is a roughly 30 m elevation product; it does not measure the exact gradient of a road surface.
- An intersecting steep-slope pixel may fall beside, above, or below the mapped road; inspect the map and source resolution.
- The 18% threshold and 150 m buffer are exploratory choices, not official criteria.
- OSM completeness and feature tagging differ from place to place.
- The workflow is a screening map for review, not a substitute for field verification or local engineering data.

The same two-step logic can be adapted to other regions and questions: choose a raster condition, filter a vector layer, then use the filtered features to query a second target.

Try FilterMate with the [user guide](https://imagodata.github.io/filter_mate/guide.html), and tell us what open dataset you would connect next.

*Data sources: NASA / USGS SRTM 1 Arc-Second Global; © OpenStreetMap contributors, ODbL. Demonstration settings are illustrative. Cite and follow the terms of each dataset when sharing outputs.*
