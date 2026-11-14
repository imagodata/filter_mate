**Title**

FilterMate 5.1 (free QGIS plugin): spatial filters across vector, raster and LiDAR layers, plus an experimental SAM tool and agent. 55-second video

**Body**

I maintain FilterMate, a free and open source QGIS plugin (GPLv3, QGIS 3.22 to 4.x). It carries a selection from one layer to the others: the buildings near main roads, the parcels on steep slopes, the LiDAR points above a height. Vector, raster and point cloud layers can each be the source or the target, and the filter is written in the SQL of each source (PostGIS, GeoPackage, SpatiaLite, files), so nothing is copied.

The 55-second video shows the real plugin in QGIS 4.2, on French open data (BD TOPO and LiDAR HD of the IGN):

- one click filters 12 layers to Toulouse Métropole (360,577 buildings in that run)
- chained filters with AND / OR / AND NOT
- buildings over 7 m read from the point cloud
- Undo / Redo and a Compare line (the map before and after the last filter)
- export of only the filtered layers to one GeoPackage, Processing algorithms, Python and REST API

Two parts are new and experimental, and I would like feedback on them:

- **SAM**: one click outlines an object on an orthophoto (SAM 2.1, on the CPU, no GPU). Measured on building roofs at 25 cm only; parcels and trees are not validated.
- **AGENT**: a chat panel that filters from a sentence. It works with your own API key (Claude, Mistral, OpenAI, a compatible server) or a local Ollama model; with a local model nothing leaves the computer. Each step shows how many features it keeps and can be undone.

Known limits: raster and point cloud filters go through temporary files; the agent sends field values and samples to the provider you chose unless the model is local.

Links: [site and guide](https://imagodata.github.io/filter_mate/) · [plugin page](https://plugins.qgis.org/plugins/filter_mate/) · [source](https://github.com/imagodata/filter_mate)

What breaks on your data is what I most want to hear about.
