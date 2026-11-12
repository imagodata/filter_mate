# FilterMate video storyboard — global data, complete workflow

## Purpose

Create one concise, screen-recorded video to accompany the Medium article and give the website a strong, understandable product demonstration. Show that FilterMate has several ways to define a vector source, useful map/action buttons, and source-to-target filtering across different data types.

The video is a product walkthrough, not a result claim. Record the full workflow in QGIS before editing; replace planned values or steps if the verified data require changes.

## Working title

**From a terrain threshold to a field-check map: FilterMate in QGIS**

## Delivered video

- **Master:** 55.7 seconds, 16:9, 1920×1080, H.264 video with AAC audio.
- **Capture:** actual Windows QGIS 4.2.3 and FilterMate 5.0.1 UI; the video captures the QGIS window, not a synthetic mock-up.
- **Captions:** English captions are burned in; French subtitles are provided as `kathmandu-demo/video/captions-fr.srt`.
- **Audio:** English voice-over, generated locally with the Windows speech voice; the source WAV is included. No music. The 30–45 second vertical/social cut is not produced.
- **Credits:** NASA / USGS SRTM and © OpenStreetMap contributors appear on screen; the article carries the ODbL notice.
- **Reproducibility:** QGIS 4.2.3, FilterMate 5.0.1; the bundled run returned 14 roads and 2 schools.

## Storyboard

| Time | Picture / interaction | On-screen caption |
|---|---|---|
| 0:00–0:05 | Open on the complete SRTM slope context, with roads and mapped schools visible. Show NASA / USGS and OSM credit. | “One terrain question. Two filters. A focused result.” |
| 0:05–0:10 | Show **Single selection** without changing the map extent. | “Choose one feature as the source.” |
| 0:10–0:14 | Show **Multiple selection** with several roads checked; preserve the same framing. | “Or choose several features.” |
| 0:14–0:20 | Show **Custom selection / expression** on the road layer. | “Or define the source with a QGIS expression.” |
| 0:20–0:29 | Keep the Exploring rail legible. Demonstrate Zoom, Identify and Selecting preview; show and name Tracking, Linking, More and Reset without implying each was individually activated. | “Explore: Zoom · Identify · Preview · Track · Link · More · Reset.” |
| 0:29–0:38 | Set the SRTM slope range and filter OSM roads with **Intersect**. Zoom the canvas to the filtered road geometries after completion. | “SRTM slope → roads \| ≥18% (illustrative, not a standard).” |
| 0:38–0:45 | Use the filtered roads as source; target OSM schools with **Intersect** and a 150 m buffer. Zoom to the combined result extent. | “Filtered roads → OSM schools \| 150 m buffer.” |
| 0:45–0:56 | Show the Exporting tab and verified GeoPackage output. End with counts and the interpretation limitation. | “14 roads · 2 schools. GeoPackage ready to share. Not an access or safety assessment.” |

## Interaction accuracy and capture checklist

- The three vector selection modes are alternatives for defining a source. The edit must not suggest they are three sequential operations in one filter chain.
- The actual two-stage example is: **slope raster → OSM roads**, then **filtered roads → OSM schools**.
- Confirm FilterMate permits the selected filtered road features to act as the second source in the captured workflow. If not, revise the workflow, story and narration rather than staging a false sequence.
- Keep the Exploring tool rail visible during the selection and filter scenes. Demonstrate Zoom, Identify and the Selecting preview, and explicitly name Tracking, Linking, More and Reset. Raster/point-cloud layers expose different type-specific exploration tools.
- Keep one canvas extent for the three source-selection modes so the view does not jump between alternatives. After each filter, zoom to the returned geometries rather than the full source-layer extent.
- Capture frames every 250 ms with monotonic timestamps and encode at 30 fps, preserving the real time spent on UI operations; keep captions compact.
- Show FilterMate's Filtering rail controls only when useful: Auto current layer, Layers to filter, Combine operator, Geometric predicates and Buffer value.
- Do not imply that filtering mutates or copies vector source data. The final Export action writes the currently visible features of the selected layers. Raster and point-cloud filters may use temporary files while active.
- The recorded run verified QGIS 4.2.3, FilterMate 5.0.1, the 18% threshold, the 150 m buffer, 14 roads and 2 schools. Counts describe only the bundled extent and data snapshot.
- Do not describe the threshold or buffer as safety, engineering or access standards.
- Ensure school locations and names are not framed as proof of accessibility or service coverage.

## Delivered assets

- Master video: `kathmandu-demo/video/Kathmandu_FilterMate_Walkthrough.mp4`
- English narration source: `kathmandu-demo/video/voiceover-en.wav`
- French subtitles: `kathmandu-demo/video/captions-fr.srt`
- Cover frame: `kathmandu-demo/captures/kathmandu-cover.png`
- Raster-to-vector frame: `kathmandu-demo/captures/slope-to-roads.png`
- Vector-to-vector frame: `kathmandu-demo/captures/roads-to-schools.png`
- Starting and post-filter projects, plus final GeoPackage: `kathmandu-demo/Kathmandu_FilterMate.qgz`, `kathmandu-demo/Kathmandu_FilterMate_Final.qgz`, and `kathmandu-demo/video-output/Kathmandu_final.gpkg`

## Publication integration

- Embed the full video near the article introduction, after the opening question and before the data-download instructions.
- Use `kathmandu-cover.png` as the thumbnail and upload the two step images with descriptive alt text.
- Keep captions enabled; narration is included in the master. A separate social cut can be produced in a later pass.
- Link the detailed guide and downloads below the video so readers can both watch and reproduce the steps.
