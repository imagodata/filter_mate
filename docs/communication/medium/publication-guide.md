# Publishing the SRTM + OpenStreetMap article on Medium

## Article package

- **Draft:** [01-open-data-srtm-osm.md](./01-open-data-srtm-osm.md)
- **SRTM source:** [USGS SRTM 1 Arc-Second Global](https://www.usgs.gov/centers/eros/science/usgs-eros-archive-digital-elevation-shuttle-radar-topography-mission-srtm-1)
- **SRTM download:** [USGS EarthExplorer](https://earthexplorer.usgs.gov/)
- **OSM regional extract option:** [Geofabrik Nepal](https://download.geofabrik.de/asia/nepal.html)
- **OSM licence and attribution:** [OpenStreetMap copyright page](https://www.openstreetmap.org/copyright)
- **Video storyboard and capture record:** [video storyboard](./video-storyboard.md)

## Verified publication assets

- **Video master:** [Kathmandu_FilterMate_Walkthrough.mp4](./kathmandu-demo/video/Kathmandu_FilterMate_Walkthrough.mp4) — 55.7 seconds, 1920×1080, H.264 video with AAC narration and English captions burned in; the walkthrough includes the Exploring buttons.
- **English caption source:** [captions-en.srt](./kathmandu-demo/video/captions-en.srt)
- **English narration source:** [voiceover-en.wav](./kathmandu-demo/video/voiceover-en.wav). Narration was generated locally; there is no music.
- **French subtitles:** [captions-fr.srt](./kathmandu-demo/video/captions-fr.srt).
- **Cover image:** [kathmandu-cover.png](./kathmandu-demo/captures/kathmandu-cover.png)
- **Raster-to-vector image:** [slope-to-roads.png](./kathmandu-demo/captures/slope-to-roads.png)
- **Vector-to-vector image:** [roads-to-schools.png](./kathmandu-demo/captures/roads-to-schools.png)
- **Starting project:** [Kathmandu_FilterMate.qgz](./kathmandu-demo/Kathmandu_FilterMate.qgz)
- **Post-filter project:** [Kathmandu_FilterMate_Final.qgz](./kathmandu-demo/Kathmandu_FilterMate_Final.qgz)
- **Verified final output:** [Kathmandu_final.gpkg](./kathmandu-demo/video-output/Kathmandu_final.gpkg)

The workflow was recorded in the actual FilterMate dock in native Windows QGIS 4.2.3, using FilterMate 5.0.1 from the workspace. The video shows single, multiple and expression-based source selection, Exploring actions, cross-type filters and export. The OSM study extent is 85.300, 27.710 to 85.310, 27.720; the elevation source is SRTM tile N27E085. It filtered 14 of 305 OSM road features using the SRTM-derived 18% slope threshold, then found 2 mapped schools with a 150 m buffer. The output GeoPackage contains those 14 roads and 2 schools. Counts describe the bundled study extent and data snapshot only; they are not access, hazard, or safety findings. The threshold and buffer are illustrative, not standards.

## Recommended Medium settings

- **Title:** From SRTM Slopes to OpenStreetMap Schools: A Two-Step QGIS Filter
- **Subtitle:** Chain a terrain threshold and a proximity query to build a focused field-check map — with free global datasets.
- **Tags:** QGIS, GIS, OpenStreetMap, SRTM, Open Data
- **Cover:** upload `kathmandu-cover.png`. It is a new Kathmandu QGIS capture, not a reused website or Sarlat image.

## Verify the new example before publication

1. Download the SRTM 1 Arc-Second Global GeoTIFF for Kathmandu from EarthExplorer. Download access requires a free account.
2. Use QuickOSM to query `highway` and `amenity=school` in a manageable Kathmandu canvas extent, or download the Geofabrik Nepal extract and subset it to the study area.
3. Reproject the DEM into a suitable local metric CRS, derive percent slope with GDAL, and inspect its range and NoData.
4. In FilterMate, use the slope raster to filter OSM roads with an 18% threshold and **Intersect**.
5. Set the resulting filtered roads as source and OSM schools as target; apply **Intersect** with a 150 m buffer.
6. Confirm the road and school results visually. The recorded versions are QGIS 4.2.3 and FilterMate 5.0.1; the captured settings are an 18% slope threshold, Intersect, and a 150 m buffer.
7. Keep the 14-road and 2-school counts tied to this bundled extract. A fresh OSM query may return different counts.
8. Describe the result as exploratory screening, not an access, hazard, or safety finding. Retain the OSM and NASA / USGS SRTM credits and the limitations paragraph.

## Publication steps

1. Start a new Medium story and copy the title and subtitle above.
2. Paste the article body and upload the three referenced PNGs. Add the provided alt text and image captions.
3. Upload the MP4 to a video host supported by Medium, then embed its public URL near the article opening. Keep the burned-in English captions and narration; attach or link the French SRT where the host permits.
4. Add the tags. Preview the cover crop and body on desktop and mobile.
5. Check the SRTM source, OSM attribution/ODbL notice, and limitations paragraph.
6. Publish only after the actual QGIS run and screenshots are verified.

## Launch post

**One terrain threshold. One proximity query. A focused QGIS field-check map.**

I tested a two-step FilterMate workflow with free global datasets: SRTM slope first filtered OpenStreetMap roads, then those roads filtered nearby mapped schools. In this example, the final result was 14 road features and two mapped schools.

The thresholds are exploratory, not safety standards. The article explains how to get the data, chain the filters, and interpret the result carefully:

[Insert the published Medium URL]

#QGIS #GIS #OpenStreetMap #SRTM #OpenData
