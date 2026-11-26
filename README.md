# ![FilterMate](https://github.com/imagodata/filter_mate/blob/main/icon.png?raw=true) FilterMate

**🧭 Explore, 🔍 filter and 📦 export vector 🗺️, raster 🏔️ and LiDAR point cloud ☁️ layers in QGIS, from one panel.**

[![QGIS Plugin](https://img.shields.io/badge/QGIS%20plugin-5.1.3-589632?logo=qgis&logoColor=white)](https://plugins.qgis.org/plugins/filter_mate)
[![QGIS 3.22 → 4.x](https://img.shields.io/badge/QGIS-3.22%20%E2%86%92%204.x%20%C2%B7%20Qt5%20%2F%20Qt6-589632)](https://plugins.qgis.org/plugins/filter_mate)
[![Tests](https://github.com/imagodata/filter_mate/actions/workflows/test.yml/badge.svg)](https://github.com/imagodata/filter_mate/actions/workflows/test.yml)
[![QGIS headless](https://github.com/imagodata/filter_mate/actions/workflows/qgis-headless.yml/badge.svg)](https://github.com/imagodata/filter_mate/actions/workflows/qgis-headless.yml)
[![Website](https://img.shields.io/badge/docs-website-16232b)](https://imagodata.github.io/filter_mate)
[![License: GPL v3](https://img.shields.io/badge/license-GPLv3-blue)](LICENSE)

**Your feedback shapes FilterMate:** [how you use it](https://imagodata.github.io/filter_mate/feedback.html?ref=readme#usage) · [a quick review](https://imagodata.github.io/filter_mate/feedback.html?ref=readme#review) · [suggest a feature](https://imagodata.github.io/filter_mate/feedback.html?ref=readme#feature) · [become a tester](https://imagodata.github.io/filter_mate/feedback.html?ref=readme#testers) · [training and services](https://imagodata.github.io/filter_mate/feedback.html?ref=readme#services)

Pick a layer, select what matters on it, and FilterMate filters every other layer of the project by its relation to
that selection: buildings near main roads, parcels on steep slopes, LiDAR points beneath rooftops, a DTM
clipped around a church. The filters stay on the existing project layers, keep their styles, can be undone, saved as favorites, exported,
and replayed from Processing or a script. Or ask for them in a sentence: the AGENT section filters, selects and
exports from a typed or dictated request, with the model you choose.

<p align="center">
  <img src="website/img/guide/fm5_filtering_targets.png?v=1" alt="FilterMate panel with a vector layer: a building chosen, then the layers to filter, a LiDAR point cloud and a DTM among them" width="260">
  &nbsp;
  <img src="website/img/guide/fm5_raster_exploring.png?v=4" alt="FilterMate panel with a raster layer: band, value range and histogram, then the layers to filter" width="260">
  &nbsp;
  <img src="website/img/guide/fm5_pointcloud_exploring.png?v=4" alt="FilterMate panel with a LiDAR point cloud: classes and attribute ranges" width="260">
</p>
<p align="center"><em>The panel follows the current layer: a building of a vector layer filtering a point cloud and a DTM, a raster with its histogram, a LiDAR point cloud.</em></p>

<p align="center">
  <img src="website/img/guide/agent-chat.png?v=7" alt="AGENT: two requests in a sentence, each with a filter card that gives the features kept" width="260">
  &nbsp;
  <img src="website/img/guide/agent-question.png?v=7" alt="AGENT asks which of two road layers is meant, with choices to click" width="260">
  &nbsp;
  <img src="website/img/guide/agent-setup.png?v=7" alt="AGENT offers to set FilterMate up: look, data, what the agent may do alone" width="260">
</p>
<p align="center"><em>AGENT (experimental): a request in a sentence and its filters, a question with choices when the decision is yours, and the offer to set FilterMate up.</em></p>

🌐 [Website](https://imagodata.github.io/filter_mate) ·
📖 [User guide](https://imagodata.github.io/filter_mate/guide.html) ·
🇫🇷 [Guide utilisateur](https://imagodata.github.io/filter_mate/guide.fr.html) ·
💡 [Use cases](https://imagodata.github.io/filter_mate/stories.html) ·
📥 [Install from the QGIS repository](https://plugins.qgis.org/plugins/filter_mate)

---

## ✨ New in 5.1.3

- **Agent data in memory.** Downloaded and generated layers stay in project memory where possible.
  **⋯ → Save project and layers…** asks where to save the project and its in-memory agent datasets.
  Closing the project releases unsaved memory datasets. Providers that need files use the chosen folder for
  their outputs and working files.
- **Links to the result.** Click a layer name to reveal it in QGIS's Layers panel. Open exported files,
  their containing folders and web sources directly from the conversation.
- **Processing models and providers.** Discover and run compatible algorithms from installed providers, including
  GDAL, GRASS, SAGA and PDAL, and registered models. **⋯ → Processing model designer…** opens QGIS's native editor;
  the agent can prepare a reusable chain there without expert mode. You choose where to save the model.
- **Microphone dictation.** Click the microphone beside the input to record, then click again to transcribe.
  **⋯ → Microphone settings…** offers a local OpenAI-compatible service, OpenAI or Mistral, independently of the
  chat provider. Recordings stay in RAM for up to two minutes; the text goes into the draft for review before Send.
- **Lighter agent context.** Loaded skills are reused, recent instructions survive tool-result trimming, and shared
  notes refresh when another QGIS session changes them. Recent agent actions are translated in all 34 languages;
  the new microphone controls and errors include French translations.

- **Consistent selections and local copies.** Background expressions use the project's variables, measurement units,
  CRS and ellipsoid. GeoPackage copies keep their SQLite filters when a project reopens; a cancelled or failed
  copy-again operation restores the previous copy and its filter.
- **Respond, Propose or Act.** Read without changing the project, approve each proposed change, or follow the
  permissions saved in the settings. Memory proposals stay yours to accept or refuse.
- **Conversations that resume.** The project's conversation is taken up again with the same server, account and
  attribute-sharing choice. New conversation clears the saved history. Long conversations save faster, and choosing
  a layer with `@` inserts the layer selected in the completion list.
- **Reasoning effort when supported.** An optional menu offers the levels supported by the selected model, with
  **Automatic** keeping the provider's default. The choice is remembered per model and server and applies to the next
  request without clearing the conversation.
- **Charts and clearer navigation.** Standard charts render in QGIS 3 and 4; combine them into vector infographics
  and export them as images, PDF, SVG or an offline HTML page. Navigation icons follow the theme, long model names
  stay readable in tooltips, and EXPLORING keeps its source-layer chooser when FILTERING is hidden.

See [the 5.1.3 release notes](CHANGELOG.md#513---2026-11-27) and [the agent documentation](docs/AGENT_MODE.md) for details.

## ⚙️ How it works

The panel has five sections in two stacks, one section open at a time in each: 🤖 AGENT and 🧭 EXPLORING above the
splitter handle, 🔍 FILTERING, 📦 EXPORTING and 🔧 CONFIGURATION below.

| Section | What you do there |
|---|---|
| 🤖 **AGENT** (experimental) | Type or dictate a request: "buildings above 1200 m in the selected commune". The agent reads the project, filters, selects, zooms, styles and labels layers, edits features (in the edit buffer: you save them), makes print layouts, sets the CRS of the project, brings in the elevation, the OpenStreetMap features, the population or the natural risks (France) of an area, adds web basemaps and open data, runs compatible Processing algorithms and models, draws objects with SAM and exports; each step can be undone. It also organizes the layer tree, makes sliders and charts under the conversation, helps set FilterMate up, asks with choices to click when the decision is yours, and keeps a request as a recipe you run again without calling the chat model. See [docs/AGENT_MODE.md](docs/AGENT_MODE.md). |
| 🧭 **EXPLORING** | Select on the current layer. Vector: one feature, several, or an expression. Raster: a band, a pixel value (picked on the map), a value range on a live histogram, classes of a paletted raster, a raster calculator expression. Point cloud: ASPRS / LiDAR HD classes, Z, intensity and return ranges, chained attribute conditions, height above a DTM. |
| 🔍 **FILTERING** | Choose the layers to filter and how they relate to the selection: geometric predicates (intersects, within, disjoint…), a buffer, AND / OR with existing filters, a minimum coverage for polygons. |
| 📦 **EXPORTING** | Write the filtered layers as they are: vector formats, GeoTIFF / COG for rasters, LAZ / LAS / COPC / GPKG / CSV for point clouds, or a GeoPackage with an embedded QGIS project. |
| 🔧 **CONFIGURATION** | Backends, theme, layer kinds, cache and other options, from the panel. |

**Nine combinations. One panel.** Every kind of layer can be the source or a target. Each cell links to a detailed use case:

| Source ↓ / Target → | 🗺️ Vector | 🏔️ Raster | ☁️ Point cloud |
|---|---|---|---|
| 🗺️ **Vector** (features) | [Buildings near main roads](https://imagodata.github.io/filter_mate/stories.html#s2) | [DTM around the church](https://imagodata.github.io/filter_mate/stories.html#s12) | [Point cloud around the church](https://imagodata.github.io/filter_mate/stories.html#s12) |
| 🏔️ **Raster** (value range, classes…) | [Parcels on steep slopes](https://imagodata.github.io/filter_mate/stories.html#s9) | [NDVI mask on an RGB orthophoto](https://imagodata.github.io/filter_mate/stories.html#s13) | [LiDAR points beneath rooftops](https://imagodata.github.io/filter_mate/stories.html#s14) |
| ☁️ **Point cloud** (classes, ranges…) | [Building heights measured by LiDAR](https://imagodata.github.io/filter_mate/stories.html#s10) | [DTM beneath ground points](https://imagodata.github.io/filter_mate/stories.html#s15) | [High vegetation near power lines](https://imagodata.github.io/filter_mate/stories.html#s16) |

Filtered layers keep their id, style and place in the layer tree. Unfilter, Undo / Redo and unloading the plugin put
the original source back, and project files are always saved with the original sources.

## ✨ Features

- ⚡ **Fast on large data.** Filters run as SQL on PostgreSQL / PostGIS, SpatiaLite and GeoPackage (spatial index used,
  no reload), with an OGR path for everything else. In the [documented Saint-Gaudens run](https://imagodata.github.io/filter_mate/stories.html#s1),
  12 layers from a 2.9 GB department-wide GeoPackage were filtered in under a second. Timings depend on the data, hardware and cache.
- 🌐 **Web services and remote files** (WFS, OGC API Features, ArcGIS, WMS / WMTS / XYZ, WCS, vector tiles, remote COPC / EPT): filtered and explored with bounded, cancellable reads, never on the main thread, and with an explicit refusal rather than a silently partial result. A WMS, a WMTS or a tile basemap can itself be a layer to filter: captured over the area, then cut like a local raster.
- 🤖 **AGENT** (experimental): a chat in the panel that drives FilterMate and QGIS from a sentence, Processing algorithms included, with Claude, Mistral,
  OpenAI or any compatible server, a local Ollama model (the settings help to install it and to download a model). Filters apply at once
  and each step can be undone; exports and added or removed layers are confirmed in the thread, without stopping QGIS, and its history keeps the requests of every project. Choose Respond, Propose or Act;
  Act follows the saved autonomy level, the rules per tool and the layers it must never change. Recipes keep a request in the project and run
  it again without any model, or by themselves each time the edits of their source are saved. When a choice is yours
  it asks with choices to click; *Set up FilterMate* asks the main settings with a few choices, with no model at all
  (offered once per version, and from the menu Vector > FilterMate), and *How FilterMate works* tells the panel
  section by section; a team can give it its own skills, a `SKILL.md` you read and allow first. When the
  project has no such layer, it brings in what a request needs: the elevation of an area (a relief map with its
  contours in one sentence), OpenStreetMap features by tags, the population of an area, the natural risks of France. An expert mode, off by default, lets it run Python code in QGIS, shown and confirmed at each run and not undone. Optional sources: web basemaps (OpenStreetMap, Carto, IGN,
  Google Satellite, OpenTopoMap, Esri light/dark grey / imagery / topographic / street maps), a geocoder, the tables of a PostgreSQL connection of QGIS, open data portals, WFS, WMS and WMTS
  services (IGN, Géorisques), Sentinel-2 scenes, Copernicus elevation, OpenStreetMap (Overpass),
  a population grid, remote MCP connectors. A built-in MCP server lets Claude Code or another client on
  your computer use the same tools ([docs/AGENT_MODE.md](docs/AGENT_MODE.md)).
  CARTO now requires a [personal API key](https://www.carto.com/basemaps/apikey/); use a custom XYZ source with your
  key, or enable an Esri alternative in **Agent settings > Sources > Basemaps**. Hide an existing CARTO notice layer
  in QGIS's Layers panel before adding another background below it.
  The **basemaps** skill also finds official regional backgrounds (Brittany, Basque Country, Spain, Switzerland,
  Austria, Netherlands, Japan, United States), searches enabled local catalogs and reuses local raster files.
  See the [regional source list](docs/AGENT_MODE.md#regional-basemaps-and-local-backgrounds).
- 💾 **Agent data and result links.** Keep downloaded and generated data in memory, then choose where to save the
  project and its agent datasets. Layer links reveal the exact layer in the tree; output actions open the file or
  its folder. Sources on the web open only when you click their links.
- 🧩 **Processing models and providers.** The agent searches installed providers and registered models, describes
  their parameters and steps, and runs compatible treatments on project layers. Build a draft chain or open a model
  in QGIS's graphical designer without enabling expert Python; save it to a chosen `.model3` file or inside the project.
- 🎙️ **Microphone dictation.** Transcribe through a local compatible service, OpenAI or Mistral. Choose the device,
  service and language in **⋯ → Microphone settings…**. Click again to transcribe, or press Esc to discard or cancel.
  Audio stays in memory; recognized text is inserted in the editable draft. You press Send yourself.
- 🎯 **Pipettes on the map**: similar pixels, the clicked object or every similar object on a raster, a value condition
  on a point cloud attribute.
- 🧩 **Objects drawn by SAM** (experimental): on an orthophoto, a click or a box and the SAM 2.1 model draws the object,
  locally on your CPU; similar objects are proposed, to keep or reject. The objects filter other layers, become a
  polygon layer, or are drawn from a layer of points or footprints in Processing ([docs/SEGMENTATION.md](docs/SEGMENTATION.md)).
- ✏️ **Zone on the map**: draw a rectangle, polygon, freehand shape or circle; on a vector layer it selects the features it touches, on a raster it keeps the pixels inside it, on a point cloud it cuts the targets.
- 🎨 **Raster bands**: tick the bands that drive the pipette and the value range, and display one in grey or up to three as a colour composite (false colour included).
- ↩️ **Undo / Redo** of every filter, per layer, and the history of the project in one panel, where you go back to
  before any step. **Compare** shows the map before and after the last filter, or a state you pinned, on each side
  of a line across the map.
- ⭐ **Favorites**: save a filter with its layers and settings, replay it in a click; favorites and the settings of
  each layer are saved in the project, so they travel with it. Share them with a team through a git
  repository ([docs/favorites_sharing/USER_GUIDE.md](docs/favorites_sharing/USER_GUIDE.md)).
- ⚙️ **Automation**: ten Processing algorithms and four ready-made models, `qgis_process`, a Python API for scripts and
  other plugins, an optional REST API, and two MCP servers for AI assistants: one built into the plugin, one over stdio
  ([docs/AUTOMATION.md](docs/AUTOMATION.md)).
- 🪟 **Sections as panels of QGIS**: a rail lists the sections of the panel (or headers, one above the other, if you
  prefer). Any section leaves the panel for a panel of QGIS, alone or grouped with others, by a right-click on its chip
  or by dragging it, and comes back the same way; QGIS puts each panel back where you left it. EXPLORING in its own
  panel shows its own list to choose the current layer. The buttons can sit under each section, and FILTERING or
  EXPORTING can be turned off. Nothing moves unless you ask.
- 🔧 **Configuration**: search a setting by name; display profile automatic from the screen or chosen (compact, normal, hidpi).
- 🧩 **QGIS 3.22 to 4.x**, Qt5 and Qt6, 🌗 light and dark themes, 🌍 34 languages.

## 📥 Installation

In QGIS: **Plugins → Manage and Install Plugins**, search for **FilterMate**, then **Install Plugin**. The FilterMate
button appears in the plugin toolbar.

Manual install: download a zip from [GitHub Releases](https://github.com/imagodata/filter_mate/releases) and use
**Plugins → Manage and Install Plugins → Install from ZIP**.

### 🖥️ Without QGIS: the standalone application

The same dock, unchanged, in a window of its own (a map, a layer panel, the QGIS libraries as the engine):

```bash
# macOS, Linux
curl -LsSf https://raw.githubusercontent.com/imagodata/filter_mate/main/standalone/install.sh | sh
# Windows (PowerShell)
powershell -ExecutionPolicy Bypass -c "irm https://raw.githubusercontent.com/imagodata/filter_mate/main/standalone/install.ps1 | iex"
# or, with pip or pipx already there, in any Python 3.9+
pipx install https://github.com/imagodata/filter_mate/archive/refs/heads/main.zip

filtermate parcels.gpkg dem.tif
```

`filtermate` uses the QGIS of the machine (3.22 to 4.x, found by itself), or installs a runtime of its own without
administrator rights (`filtermate setup`). A Docker image serves it in a browser. See
[docs/STANDALONE.md](docs/STANDALONE.md).

### 📋 Requirements

| | |
|---|---|
| 🟢 QGIS | 3.22 or later, QGIS 4.x included. Point cloud layers need QGIS 3.26+. |
| 🐘 PostgreSQL / PostGIS (optional) | `psycopg2`, shipped with most QGIS installs; otherwise `pip install psycopg2-binary` in the QGIS Python. |
| ☁️ PDAL (optional) | PDAL 2.4+ (`pdal` command, shipped with QGIS on Windows) for the height above a DTM and direct COPC writing. Without it, point clouds are clipped by the QGIS exporter. |
| 🌐 REST API (optional) | `pip install -r requirements-api.txt` (FastAPI, Uvicorn, Pydantic). |
| 🧩 SAM (optional) | `onnxruntime`, installed into your QGIS profile after one confirmation, and the model (62 MB), downloaded on request. |
| 🤖 AGENT | An API key of a provider (kept in the QGIS authentication database), or a local Ollama model. No provider SDK is required. |
| 🧩 Agent Processing providers (optional) | The provider and its dependencies must be installed and active in QGIS. Agent runs that require files need QGIS 3.32+ to keep working files in the chosen project-data folder. |
| 🎙️ Microphone dictation (optional) | Qt Multimedia for the Qt version used by QGIS, plus a running local OpenAI-compatible transcription server or an OpenAI/Mistral API key. The speech service is configured separately from the chat model. |

## 🤖 Automation in two lines

```python
from qgis.utils import plugins

api = plugins["filter_mate"].get_public_api()
api.cross_filter("mnt", ["parcelle", "lhd"], coverage_min=50,
                 raster_selection={"band": 1, "mode": "range", "minimum": 1200, "maximum": 1300})
```

The same operation is available as the `filtermate:cross_filter_from_raster` Processing algorithm, from
`qgis_process`, and as `POST /filters/cross` on the REST API. See [docs/AUTOMATION.md](docs/AUTOMATION.md).

## 📚 Documentation

| | |
|---|---|
| 📖 [User guide](https://imagodata.github.io/filter_mate/guide.html) · [Guide utilisateur](https://imagodata.github.io/filter_mate/guide.fr.html) | Step by step: first filter, exploring, predicates and buffers, rasters and point clouds, favorites, export, backends, configuration. |
| 💡 [Use cases](https://imagodata.github.io/filter_mate/stories.html) · [Cas d'usage](https://imagodata.github.io/filter_mate/stories.fr.html) | Sixteen business questions covering all nine combinations: twelve QGIS recordings and four illustrated recipes, in English and French. |
| 🤖 [docs/AGENT_MODE.md](docs/AGENT_MODE.md) | The AGENT section: providers, tools, levels of autonomy, undo, recipes, widgets, sources, the built-in MCP server. |
| 🔒 [docs/AI_AND_DATA.md](docs/AI_AND_DATA.md) | AI and data: what the AGENT sends, to whom and when; no account, no telemetry. |
| 🧩 [docs/SEGMENTATION.md](docs/SEGMENTATION.md) | Objects drawn by SAM: set up, use, Processing, what it is good at, with measured results. |
| 🖥️ [docs/STANDALONE.md](docs/STANDALONE.md) | FilterMate without the QGIS application: the `filtermate` command, its engine, the browser image. |
| ⚙️ [docs/AUTOMATION.md](docs/AUTOMATION.md) | Processing algorithms and models, `qgis_process`, Python API, REST API, MCP servers. |
| ⭐ [docs/favorites_sharing/](docs/favorites_sharing/USER_GUIDE.md) | Sharing favorites through git repositories. |
| 🏗️ [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) · [CONTRIBUTING.md](CONTRIBUTING.md) | Source tree, code rules, tests and releases, for contributors. |
| 📝 [CHANGELOG.md](CHANGELOG.md) | Release notes. |

## 🛠️ Development

```bash
pip install -r requirements-test.txt
python -m pytest tests/ -o "addopts="     # unit tests, no QGIS needed (qgis.* is mocked)
```

The scripts of `tests/qgis_headless/` load the plugin in the official QGIS Docker images (3.22 → nightly) and drive
the dock with its GUI. Start with [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for a map of the source tree and
[CONTRIBUTING.md](CONTRIBUTING.md) for the code rules (Qt5 / Qt6 guards, translations, zip build, pull requests).

🐛 Bugs and 💬 ideas: [GitHub issues](https://github.com/imagodata/filter_mate/issues) · 💬 Questions and news: [Discord](https://discord.gg/9DNbuVYQ).

## 📄 License

GNU General Public License v3.0, see [LICENSE](LICENSE); the name and the logo are covered by
[TRADEMARKS.md](TRADEMARKS.md). Developed by [imagodata](https://github.com/imagodata) · simon.ducournau+filter_mate@gmail.com.
Map data in the screenshots: BD TOPO® and LiDAR HD © IGN, Licence Ouverte 2.0.
