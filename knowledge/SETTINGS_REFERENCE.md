# FilterMate — settings reference

> Generated from `config/config.default.json` by `scripts/export_config_reference.py`: do not edit by hand. Each setting is edited in the configuration tree of the panel (Settings), or by the AGENT, which reads them with `describe_settings` and `get_setting`.

## Settings

`APP`

| Setting | Default | Allowed | Description |
|---|---|---|---|
| `AUTO_ACTIVATE` | false |  | Auto-activate plugin when a project with vector layers is loaded: true (automatically open plugin), false (manual activation only) |
| `USER_IDENTITY` | (empty) |  | Identity used to stamp the 'owner' column on new favorites. Cascade fallback when empty: QgsSettings 'qgis/userName' → OS user. Set explicitly to stabilize identity across machines or when running as a shared OS user (e.g. a kiosk session). |

## Settings > Interface

`APP.DOCKWIDGET`

| Setting | Default | Allowed | Description |
|---|---|---|---|
| `FEEDBACK_LEVEL` | normal | minimal, normal, verbose | User feedback verbosity: 'minimal' (errors/warnings only), 'normal' (balanced - success messages), 'verbose' (all messages including info/debug) |
| `LANGUAGE` | auto | auto, en, fr, de, es, it, nl, pt, pl, zh, ru, id, vi, tr, hi, fi, da, sv, nb, sl, tl, am, uz | Interface language: 'auto' (use QGIS locale), or force specific language |
| `UI_PROFILE` | auto | auto, compact, normal, hidpi | UI display profile: 'auto' (detect from screen/DPI), 'compact' for small screens, 'normal' for standard displays, 'hidpi' for high resolution displays (4K, Retina) |
| `DOCK_POSITION` | right | left, right, top, bottom | Position of the FilterMate dockwidget in QGIS: 'left' (left side), 'right' (right side), 'top' (top area), 'bottom' (bottom area) |
| `ACTION_BAR_POSITION` | bottom | top, bottom, left, right | Position of the action bar: 'top' (horizontal at top), 'bottom' (horizontal at bottom), 'left' (vertical on left side), 'right' (vertical on right side) |
| `ACTION_BAR_VERTICAL_ALIGNMENT` | top | top, bottom | Vertical alignment of action buttons when action bar is in vertical mode (left/right): 'top' (buttons at top), 'bottom' (buttons at bottom). Use the splitter handle to adjust position. |

## Settings > Interface > Appearance

`APP.DOCKWIDGET.COLORS`

| Setting | Default | Allowed | Description |
|---|---|---|---|
| `ACTIVE_THEME` | auto | auto, default, dark, light | Color theme for UI: 'auto' (detect from QGIS theme), 'default', 'dark', or 'light' |
| `THEME_SOURCE` | config | config, qgis, system | Theme source: 'config' (use configured theme), 'qgis' (inherit from QGIS), 'system' (use OS theme) |

## Settings > Performance > Remote materialization

`APP.OPTIONS.REMOTE_MATERIALIZATION`

| Setting | Default | Allowed | Description |
|---|---|---|---|
| `max_features` | 20000 |  | Maximum remote rows copied for an exact local filter (one extra row detects truncation) |
| `timeout_seconds` | 90 | 1–86400 | Maximum remote read and local evaluation duration in seconds |

## Settings > Performance > Server filters

`APP.OPTIONS.SERVER_FILTER`

| Setting | Default | Allowed | Description |
|---|---|---|---|
| `wfs_timeout_seconds` | 60 | 1–600 | Maximum wait for a WFS or OGC API Features server filter, in seconds (1 to 600); the previous filter is kept after it |
| `timeout_seconds` | 30 | 1–600 | Maximum wait for a server filter on other services (ArcGIS Feature Server, databases), in seconds (1 to 600); the previous filter is kept after it |

## Settings > Performance > SMALL_DATASET_OPTIMIZATION

`APP.OPTIONS.SMALL_DATASET_OPTIMIZATION`

For PostgreSQL layers with fewer features than threshold, use OGR memory backend for faster filtering (avoids network overhead)

| Setting | Default | Allowed | Description |
|---|---|---|---|
| `enabled` | true | true, false | Enable/disable optimization |
| `threshold` | 5000 |  | Number of features below which optimization is applied |
| `method` | ogr_memory | ogr_memory, qgis_processing | Backend to use: 'ogr_memory' (fastest) or 'qgis_processing' (compatible) |
| `prefer_native_for_postgresql_project` | true | true, false | When all project layers are PostgreSQL, always use PostgreSQL backend even for small datasets (ensures consistent behavior and leverages server-side processing) |

## Settings > Performance > AUTO_OPTIMIZATION

`APP.OPTIONS.AUTO_OPTIMIZATION`

Intelligent automatic optimization based on layer characteristics (v2.7.0). Recommends and applies optimizations for distant layers, large datasets, and complex geometries.

| Setting | Default | Allowed | Description |
|---|---|---|---|
| `centroid_threshold_distant` | 5000 |  | Feature count threshold for auto-enabling centroid on distant layers |
| `centroid_threshold_local` | 50000 |  | Feature count threshold for auto-enabling centroid on large local layers with complex geometries |
| `auto_simplify_geometry` | false | true, false | Automatically simplify complex geometries (LOSSY - may reduce precision). Disabled by default. |
| `auto_simplify_before_buffer` | true | true, false | Automatically simplify geometries before buffer operations (positive or negative). Improves buffer performance without affecting spatial results. |
| `auto_simplify_after_buffer` | true | true, false | Automatically simplify the resulting polygon after buffer operations. |
| `buffer_simplify_after_tolerance` | 0.5 | 0.1–50.0 | Simplification tolerance in meters for post-buffer simplification. |
| `buffer_simplify_vertex_threshold` | 50 | 10–500 | Average vertices per feature threshold for auto-simplifying before buffer |
| `buffer_simplify_feature_threshold` | 1000 | 100–100000 | Feature count threshold for auto-simplifying before buffer |
| `buffer_simplify_default_tolerance` | 1.0 | 0.1–100.0 | Default simplification tolerance in meters for buffer operations |
| `auto_strategy_selection` | true | true, false | Automatically select optimal filtering strategy (attribute-first, bbox-prefilter, progressive chunks) |
| `show_optimization_hints` | true | true, false | Show optimization hints in message bar when recommendations are available |

## Settings > Performance > PROGRESSIVE_FILTERING

`APP.OPTIONS.PROGRESSIVE_FILTERING`

Progressive/two-phase filtering for complex queries on large PostgreSQL datasets (v2.5.9 optimization)

| Setting | Default | Allowed | Description |
|---|---|---|---|
| `enabled` | true | true, false | Enable/disable progressive filtering for complex expressions |
| `two_phase_enabled` | true | true, false | Enable two-phase filtering (bbox pre-filter + full predicate) |
| `complexity_threshold` | 100 |  | Minimum query complexity score to trigger two-phase filtering |
| `lazy_cursor_threshold` | 50000 |  | Minimum features to use lazy cursor streaming (memory-efficient) |
| `chunk_size` | 5000 |  | Number of IDs per chunk for streaming results |

## Settings > Performance > QUERY_CACHE

`APP.OPTIONS.QUERY_CACHE`

Expression caching to avoid rebuilding identical queries (v2.5.9 enhancement)

| Setting | Default | Allowed | Description |
|---|---|---|---|
| `enabled` | true | true, false | Enable/disable query expression caching |
| `max_size` | 100 |  | Maximum number of cached expressions |
| `ttl_seconds` | 0 |  | Time-to-live for cache entries in seconds (0 = no expiration) |
| `cache_result_counts` | true | true, false | Cache result counts to avoid expensive COUNT queries |
| `cache_complexity_scores` | true | true, false | Cache complexity scores to avoid re-analysis |

## Settings > Performance > PARALLEL_FILTERING

`APP.OPTIONS.PARALLEL_FILTERING`

Use parallel execution for filtering multiple layers simultaneously

| Setting | Default | Allowed | Description |
|---|---|---|---|
| `enabled` | true | true, false | Enable/disable parallel layer filtering |
| `min_layers` | 2 |  | Minimum number of layers to trigger parallel execution |
| `max_workers` | 0 |  | Maximum worker threads (0 = auto-detect based on CPU cores) |

## Settings > Performance > STREAMING_EXPORT

`APP.OPTIONS.STREAMING_EXPORT`

Use batch streaming for exporting large datasets to avoid memory issues

| Setting | Default | Allowed | Description |
|---|---|---|---|
| `enabled` | true | true, false | Enable/disable streaming export |
| `feature_threshold` | 10000 |  | Number of features above which streaming is automatically used |
| `chunk_size` | 5000 |  | Number of features per batch during streaming export |

## Settings > Performance

`APP.OPTIONS`

| Setting | Default | Allowed | Description |
|---|---|---|---|
| `GPKG_PRESERVE_GROUPS` | false | true, false | Default behavior for preserving QGIS layer group structure in GPKG exports |
| `KML_PRESERVE_GROUPS` | false | true, false | Default behavior for merging KML exports into a single file with folder structure |

## Settings > Performance > OPTIMIZATION_THRESHOLDS

`APP.OPTIONS.OPTIMIZATION_THRESHOLDS`

Thresholds for automatic optimizations (feature counts and sizes)

| Setting | Default | Allowed | Description |
|---|---|---|---|
| `large_dataset_warning` | 50000 | 0–1000000 | Feature count above which performance warnings are displayed (0 to disable) |
| `async_expression_threshold` | 10000 | 1000–500000 | Feature count above which expression evaluation runs in background thread |
| `update_extents_threshold` | 50000 | 1000–500000 | Feature count below which layer extents are automatically updated after filtering |
| `centroid_optimization_threshold` | 5000 | 1000–100000 | Feature count above which centroid optimization is applied for distant layers |
| `exists_subquery_threshold` | 100000 | 10000–1000000 | WKT length (chars) above which EXISTS subquery mode is used instead of inline WKT |
| `source_mv_fid_threshold` | 500 | 50–5000 | Maximum number of source FIDs to include inline in EXISTS query. |
| `parallel_processing_threshold` | 100000 | 10000–1000000 | Feature count above which parallel processing is enabled |
| `progress_update_batch_size` | 100 | 10–1000 | Number of features between progress bar updates |

## Settings > Performance > HISTORY

`APP.OPTIONS.HISTORY`

Filter history (undo/redo) settings

| Setting | Default | Allowed | Description |
|---|---|---|---|
| `max_history_size` | 100 |  | Maximum number of filter operations to keep in history per layer |
| `persist_history` | true | true, false | Save filter history to project file |

## Settings > Performance > GEOMETRY_SIMPLIFICATION

`APP.OPTIONS.GEOMETRY_SIMPLIFICATION`

Geometry simplification settings for large WKT expressions

| Setting | Default | Allowed | Description |
|---|---|---|---|
| `enabled` | true | true, false | Enable automatic geometry simplification for large WKT expressions |
| `max_wkt_length` | 100000 | 10000–1000000 | Maximum WKT string length (chars) before simplification is applied |
| `preserve_topology` | true | true, false | Preserve geometry topology during simplification (prevents self-intersections) |
| `min_tolerance_meters` | 1.0 | 0.1–100.0 | Minimum simplification tolerance in meters |
| `max_tolerance_meters` | 100.0 | 10.0–1000.0 | Maximum simplification tolerance in meters (prevents excessive distortion) |
| `show_simplification_warnings` | true | true, false | Show warning messages when geometry is simplified |

## Settings > Performance > UI_RESPONSIVENESS

`APP.OPTIONS.UI_RESPONSIVENESS`

User interface responsiveness settings (debounce timers, refresh delays)

| Setting | Default | Allowed | Description |
|---|---|---|---|
| `expression_debounce_ms` | 450 | 100–2000 | Delay in milliseconds before evaluating expression changes while typing |
| `filter_debounce_ms` | 300 | 50–1000 | Delay in milliseconds before applying text search filter in list widgets |
| `canvas_refresh_delay_simple_ms` | 500 | 100–5000 | Canvas refresh delay after simple filter operations in milliseconds |
| `canvas_refresh_delay_complex_ms` | 1500 | 500–10000 | Canvas refresh delay after complex filter operations in milliseconds |

## Settings > Performance > FAVORITES

`APP.OPTIONS.FAVORITES`

Favorites management settings

| Setting | Default | Allowed | Description |
|---|---|---|---|
| `recent_favorites_limit` | 10 | 3–50 | Maximum number of recent favorites shown in the quick access menu |

## Settings > Performance > SPATIALITE

`APP.OPTIONS.SPATIALITE`

SpatiaLite backend processing settings

| Setting | Default | Allowed | Description |
|---|---|---|---|
| `batch_size` | 5000 | 500–50000 | Number of features processed per batch in SpatiaLite queries |
| `progress_interval` | 1000 | 100–10000 | Report progress every N features during SpatiaLite processing |
| `query_timeout_seconds` | 120 | 10–600 | Maximum time in seconds for a single SpatiaLite query before cancellation |

## Settings > Performance > EXPRESSION_BUILDER

`APP.OPTIONS.EXPRESSION_BUILDER`

SQL expression construction limits

| Setting | Default | Allowed | Description |
|---|---|---|---|
| `max_fids_per_in_clause` | 5000 | 500–50000 | Maximum number of feature IDs in a single SQL IN clause |
| `absolute_fid_limit` | 50000 | 5000–500000 | Absolute maximum feature IDs for inline SQL expressions |
| `max_inline_features` | 1000 | 100–10000 | Maximum features for inline IN clause before switching to subquery strategy |
| `max_expression_length` | 10000 | 1000–100000 | Maximum expression string length in characters before switching to optimized strategy |

## Settings > Performance > QUERY_TIMEOUTS

`APP.OPTIONS.QUERY_TIMEOUTS`

Backend query timeout settings

| Setting | Default | Allowed | Description |
|---|---|---|---|
| `postgresql_timeout_seconds` | 60.0 | 5.0–300.0 | Circuit breaker timeout for PostgreSQL operations in seconds |
| `local_timeout_seconds` | 30.0 | 5.0–120.0 | Circuit breaker timeout for local (SpatiaLite/OGR) operations in seconds |

## Settings > Performance > AGENT

`APP.OPTIONS.AGENT`

Chat section that filters your layers from a sentence. Sends your request, the names of your layers and fields and the results of its tools to the provider you choose

| Setting | Default | Allowed | Description |
|---|---|---|---|
| `open_data_domains` | (empty) |  | Open data platforms allowed besides data.gouv.fr and the Opendatasoft hub, comma separated: a host (Opendatasoft portal) or host:kind with kind opendatasoft or ckan, e.g. data.toulouse-metropole.fr, data.example.org:ckan |
| `enabled` | true | true, false | Show the AGENT section before FILTERING (on: when the panel is next opened; off: after restarting QGIS) |

## Settings > Performance > EXPLORATION

`APP.OPTIONS.EXPLORATION`

Layer exploration and feature identification settings

| Setting | Default | Allowed | Description |
|---|---|---|---|
| `point_buffer_distance_m` | 50 | 1–10000 | Buffer distance in meters applied to point features for zoom-to-feature |
| `feature_picker_limit` | 1000 | 100–50000 | Maximum number of features loaded in the feature picker list widget |
| `auto_zoom_on_filter` | true |  | Auto-zoom on the union extent of filtered layers (source + cascade targets) after a filter or favorite is applied. Per-layer is_tracking still forces zoom on its own layer. |

## Settings > Performance > POINT_CLOUD

`APP.OPTIONS.POINT_CLOUD`

Exploring and filtering of point cloud layers (LAS/LAZ/COPC): classification, elevation, intensity, height above a DTM. Requires QGIS 3.26 or newer

| Setting | Default | Allowed | Description |
|---|---|---|---|
| `enabled` | true | true, false | Show point cloud layers in the layer lists, as source (EXPLORING selection) and as target (clipped by the source geometry) |

## Settings > Performance > RASTER

`APP.OPTIONS.RASTER`

Exploring and filtering of raster layers: pixel value, value range, classes, raster expression. Requires QGIS 3.22 or newer

| Setting | Default | Allowed | Description |
|---|---|---|---|
| `enabled` | true | true, false | Show raster layers in the layer lists, as source (EXPLORING selection) and as target (pixels outside the source geometry set to NoData) |

## Settings > Performance > CROSS_FILTER

`APP.OPTIONS.CROSS_FILTER`

Filtering between layers of different kinds (vector, raster, point cloud)

| Setting | Default | Allowed | Description |
|---|---|---|---|
| `vector_source_raster_targets` | true | true, false | List the raster layers among the layers to filter of a vector source (with RASTER enabled). Web basemaps (WMS, WMTS, XYZ) are listed greyed: colours only, they cannot be filtered |
| `vector_source_point_cloud_targets` | true | true, false | List the point cloud layers among the layers to filter of a vector source (with POINT_CLOUD enabled) |
| `point_cloud_clip` | exact | exact, bbox | How a point cloud target is clipped: exact (derived file, background task) or bbox (instant X/Y expression, approximate) |
| `raster_source_max_pixels` | 100000000 |  | Pixels of a raster selection read at the native resolution, tile by tile; beyond, every 2nd, 4th... pixel is read (the outline stays light either way) |
| `point_cloud_footprint_resolution` | 2.0 |  | Cell size (map units) of the footprint of the points kept by a point cloud selection |
| `cache_max_gb` | 5 |  | Maximum size of the FilterMate cache of derived rasters and point clouds |
| `cache_dir` | (empty) |  | Folder of the FilterMate cache of derived rasters and point clouds (empty: in the QGIS profile) |
| `raster_export_format` | COG | COG, GTiff | File format of the exported rasters: Cloud Optimized GeoTIFF or plain GeoTIFF |
| `point_cloud_export_format` | LAZ | LAZ, LAS, COPC, GPKG, CSV | File format of the exported point clouds |
| `pdal_path` | (empty) |  | Path to the pdal executable (empty: detected next to QGIS or on PATH) |
