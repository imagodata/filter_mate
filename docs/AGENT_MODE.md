# Agent mode: foundations

Status: the steps below are in the code, first published in 5.1.0 (experimental). The chat is on by default
(`APP.OPTIONS.AGENT.enabled`, read when the panel opens; a configuration written while it was off is turned on once), with
a free quota and then the user's own key. For developers of FilterMate; the user guide has a chapter for users
(https://imagodata.github.io/filter_mate/guide.html#agent).

## Goal

An AGENT section, first in the upper stack of the dock, before EXPLORING: the user writes "buildings above 1200 m in the selected commune" and the agent filters.
Any provider, a few free requests through a relay, then the user's own key, and external MCP clients on the same tools.

| Step | Content | State |
|---|---|---|
| 1. Foundations | Neutral conversation, provider adapters, tool catalog, read tools, evaluation bench | done |
| 2. Chat | Panel, Qt transport, key in `QgsAuthManager`, undo of a whole turn | done |
| 3. Free quota | Relay holding the key, limits per token, per address and per month | done |
| 4. Native MCP | Local MCP server without dependencies, shared activity log | done |
| 5. Map context | The map, the layer tree and what changed, sent with each request; style, joins, relations on demand | done |
| 6. Reading the data | Statistics by group, lengths and areas, a sample of features, what lies at a point | done |
| 7. Processing | Find, describe and run the algorithms of QGIS that make layers, undone with the turn | done |
| 8. Style | One symbol, categories, graduated classes, raster ramps, labels, opacity, undone with the turn | done |
| 9. Long conversations | The oldest requests summed up in a few lines past a budget | done |
| 10. Project notes | Facts the user asks the agent to remember, saved in the project, sent with each request | done |
| 11. Editing data | Change, delete (confirmed) and add features, in the edit buffer, never saved by the agent | done |
| 12. Layouts | A print layout of the map added to the project, exported as PDF or PNG (confirmed) | done |
| 13. Vision | The map as an image for the model, with a key of the user and shared values only | done |

Product decisions: filters apply at once with an "undo this turn"; exports are confirmed; the plugin stays free of
Python dependencies and runs from QGIS 3.22.

## Layout

```
core/agent/                 no QGIS, no Qt, no network (load it alone outside QGIS: core/__init__.py imports QGIS)
  messages.py               Message, parts (text, tool call, tool result, opaque), stream events, errors
  providers/                one adapter per wire format: builds requests, parses response bytes
  session.py                AgentSession: what to send next, what to do with a turn
  tool_catalog.json/.py     the tools, as data
  tool_executor.py          validates arguments, runs a handler, always answers
  json_schema.py            the JSON Schema subset the catalog uses
  sql_guard.py              checks on filters written by a model
  system_prompt.py          constant, it opens the cached prefix
  chat_engine.py            one request at a time, event-driven, cancellable
adapters/agent/             Qt network transport, key and settings, undo of a turn
ui/widgets/agent_panel.py   the section and its settings dialog (plain text only)
ui/controllers/agent_chat_controller.py   connects the section to the conversation
adapters/public_api/introspection.py   fields, values, trial run, map state, on real layers
filtermate_api/agent_tools.py          the chat tools, on the accessor used by the REST routes
scripts/export_agent_tools.py          regenerates the catalog
scripts/agent_eval.py                  evaluation bench
```

## Providers

A provider never touches the network. `build_request` gives URL, headers and body; `new_parser` turns the bytes of the
response into events. The transport is the caller's: `QgsNetworkAccessManager` in the dock (it follows the proxy settings
of QGIS), `urllib` in the bench. `AgentSession` holds no thread, so a Qt transport can drive it from signals.

`anthropic` speaks the Messages API, `openai_compatible` the `/chat/completions` format of OpenAI, Mistral, Ollama and
others. Claude goes through plain HTTP because the official SDK needs Python 3.10 and third-party packages.

Rules worth keeping:

- Reasoning blocks come back to the provider that wrote them, unchanged, as `OpaquePart`. Without its signature a block
  makes the next request invalid.
- A refused turn, or tool calls cut by `max_tokens`, stay out of the history: a call with no result breaks every later
  request.
- Tools and system prompt are constant and serialized in a fixed order: a prompt cache needs identical bytes.
- `max_tokens` is only sent to Claude, where it is required; OpenAI-compatible servers disagree on its name.
- An API key is sent over https, or to this machine. It never appears in a `repr`.

## The chat

- **Consent** is for one server: nothing leaves before the user has chosen a model and agreed, and changing the provider
  or its address asks again. Without attribute values, `field_values`, `layer_statistics`, `sample_features` and
  `identify_at` are not offered; values already written in filters
  and favorites are still sent, and the dialog says so.
- **The key** lives in the QGIS authentication database, which asks for the master password, never in a settings file.
  It is only sent to the server it was typed for, and can be removed from the settings. It shows in the network log of
  QGIS if the user turns that log on.
- **Timeouts.** The network timeout of QGIS applies (60 s by default) and cannot be set per request: a local model slow
  to start may need more, and the message says so.
- **Redirections are not followed**, since the key is in the headers.
- **Undo this turn** captures every layer before the first change of a request and pushes one `CrossOperation` in the
  automation history: rasters and point clouds get their source back, a layer changed since is left alone, and the
  derived files of the turn stay alive. Stopping a request keeps what was done and it can still be undone.
- **What a model writes is shown as plain text** (`QPlainTextEdit`): rich text would load its images and links.
- A conversation does not survive a change of project or of provider.
- **A long conversation is summed up** (`core/agent/compaction.py`): every request sends the whole conversation
  again, so past 120 000 characters (about 30 000 tokens) the oldest requests are dropped, whole, before a new
  one, and the first request kept starts with a few lines saying what each asked, which tools changed what, and
  how its answer ended. Written here, without asking a model. A cut falls only before a request of the user: no
  tool call loses its result. The prompt cache misses once, then holds again. The thread says so in a note.
- **Project notes** (`core/agent/project_notes.py`, `adapters/agent/project_notes_store.py`): `add_project_note`
  and `remove_project_note`, tools of the chat alone (not served by the MCP servers), keep up to 20 facts of 300
  characters in an entry of the project (`FilterMateAgent/notes`), saved in the `.qgz`. They go with each request
  under a header saying they are data. A note comes back in every later conversation, so a text met in a tool
  result that asked to be kept would come back too: the prompt keeps notes to what the user asks, each note shows
  in the thread with its text, and undoing the turn takes it back (a `notes` effect of the turn).
- **Editing data** (`adapters/public_api/feature_edits.py`): `update_features` (values, or formulas computed on
  each feature), `delete_features` (the user confirms) and `add_features` (WKT, 100 at most) put the layer in
  editing mode and add one named command to its undo stack: nothing is written to the data source, the user saves
  the layer edits or discards them. Features are chosen by a QGIS expression and/or the selection (all of them
  only with the expression `true`), 100 000 at most. A value is converted to the type of its field first (QGIS
  would take "abc" in an integer field and fail at saving); keys, joined and virtual fields are not written.
  The turn keeps the index of the undo stack before its first edit of a layer; undoing the turn steps back over its
  commands, and is refused on a layer saved, discarded or edited by the user since. `describe_layer` says whether
  a layer is being edited and holds unsaved changes.
- **Layouts** (`adapters/public_api/layouts.py`): `create_layout` adds a print layout to the project (A4, A3, A5
  or Letter, landscape or portrait): a map of the layers checked in the tree or of those given, framed on an
  extent, a layer, the map view or the layers shown, with a title, a legend, a scale bar and a north arrow. The
  user finishes it in the layout designer; undoing the turn removes it (a `layout` effect keeps its XML, redoing
  reads it again). `export_layout` writes one as PDF or PNG into a sub-folder of the export root, never a path
  of the model, and is confirmed by the user like `export_layers`. `map_context` lists the layouts.
- **Vision** (`adapters/public_api/map_view.py`): `view_map`, a tool of the chat alone, renders the map
  (`QgsMapRendererSequentialJob` from the settings of the canvas, or the layers checked in the tree without one;
  never `canvas.grab()`) as a JPEG of 1568 pixels at most and answers with it. It is offered only with a key of
  the user (the free quota relay takes no image) and when attribute values are shared (a map shows its labels).
  An image goes with the request it was taken in only: before the next request it is replaced by a line saying
  it was there, or every later request would carry it again. Claude gets it in the `tool_result`; an
  OpenAI-compatible server, whose tool messages hold text only, in a user message right after. A model that
  reads no image may refuse the request: the provider says so in its error.
- **The map context** (`core/agent/project_summary.py`) goes with each request of the user, after it in the same
  message, so the cached prefix does not change. Three levels:
  - always: the project CRS, the scale, the visible extent, the active layer; up to 30 layers in the order of the layer
    tree with kind, feature count, CRS when it is not the project's, group, hidden, filter; the selections;
  - what changed since the last answer, when something did: layers added or removed, filters, visibility, selections,
    active layer, view. The project is read when an answer ends and compared at the next request, so these are changes
    made outside the conversation (the user, or another application through the MCP server);
  - on demand, `describe_layer`: place in the tree, extent, style (renderer, its field, how many classes, labels,
    opacity, scale range), joins and relations. No attribute value is in the style: class values and labels stay out,
    as `field_values` does when values are not shared. The extent of a web service is not read.
- **At most 16 model turns per request** (`max_model_turns`, `core/agent/session.py`). Two turns before the limit the
  model is told so, and a request that reaches it stops with a sentence that says why; what was done stays and can be
  undone.
- **Two stacks of sections** (`ui/layout/dock_chrome.py`): AGENT / EXPLORING above the splitter, FILTERING / EXPORTING /
  CONFIGURATION below, one section open at most in each. AGENT folds EXPLORING and FILTERING; FILTERING brings EXPLORING
  back. `tabTools_current_index` stays 0 / 1 / 2 for the lower sections and is -1 when none is open.

## History

- Every turn that changed a layer is one `CrossOperation` under the key `filtermate_agent_turn` of the automation
  history, described by the request. The History page lists them (applied or undone), undoes and redoes them in
  order, and sends a request again. A layer that refuses a restore (being edited) keeps the turn undoable.
- The transcript (requests, actions, answers) is kept per project in the QGIS settings, keyed by the project path, and
  shown again when the project opens. The model does not get it back: a conversation starts afresh.
- A turn also records what it does beside the filters (`adapters/agent/turn_effects.py`): layers added or removed,
  selections, visibility in the layer tree. Undo and redo apply them with the filters. A removed layer comes back from
  its definition, same id, at its place in its group; a layer kept in memory cannot, and the panel says so. Zooms and
  exports are not undone.
- **Steps.** The undo point takes the state of the layers before each change of a turn. The History page lists the steps
  of the last request; "Undo back to here" puts its layers as they were before the chosen step, as a step of its own
  that Undo takes back.
- **The action bar.** While AGENT is open, Undo and Redo of the action bar, and Ctrl+Z / Ctrl+Y, walk this history; their
  tooltip names the request. Folded, they are the dock ones again.
- **In the conversation.** `undo_agent_step`, a tool of the chat alone (not in REST nor in the MCP servers), takes back the
  last request when the user asks for it, before any other change of the request; it can be redone.
- New conversation forgets what was kept for the project; only the 20 latest projects are kept.

## Driving QGIS and open data

`zoom_to`, `select_features` (QGIS expression, parsed by `QgsExpression`, never SQL), `set_layers_visibility`,
`add_layer`, `remove_layers`, `search_open_data`, in `adapters/public_api/project_control.py`, with the REST routes of
`routers/project.py`. Open data (`core/agent/open_data.py`, pure): data.gouv.fr and the Opendatasoft hub are built in,
other portals come from `APP.OPTIONS.AGENT.open_data_domains`; a platform not in the list is refused. In the chat the
whole thing is behind the "open data" setting: without it `search_open_data` is not offered and `add_layer` takes local
files only. `add_layer` and `remove_layers` ask the user; a search stays in the thread.

Two allowlists hold, on every path (chat, REST, MCP), because QGIS and GDAL interpret these strings:

- `add_layer` (`open_data.source_problem`): a plain local data file, or a public https URL of one. No provider URI, no
  `PG:`, `/vsi...`, UNC path, inline XML or `|subset=`. A service (WFS, WMS) cannot be added by a model.
- `select_features` (`sql_guard.expression_problem`): plain conditions and a short list of functions. QGIS expressions
  can read the environment and the disk (`env`, `file_exists`, `aggregate`) and write to SQLite
  (`sqlite_fetch_and_increment`).

A remote file is asked for its first byte before anything is read (`project_control._probe`): the redirects are
followed, each hop held to the rules above, and the answer tells its format (the name its server gives it, else its
address, else its content type), its size, and whether the server gives parts of it (`open_data.remote_file`).

- A GeoPackage, FlatGeobuf, GeoTIFF or zip on a server that gives parts is read where it is, through `/vsicurl/`.
- Anything else is copied to `<QGIS profile>/filtermate/open_data/` first, through `bounded_http`: 512 MB and
  3 minutes at most, Stop ends it, the interface stays alive, a copy cut before its end is discarded. An export made
  on request (an Opendatasoft portal, and what data.gouv.fr lists for the portals it harvests) has no size and cannot
  be read by parts, which is what GDAL needs; its address ends with the name of a format, not of a file. A zip is
  read in the copy (`/vsizip/`), never extracted, and the name of the file read in it must be plain; an archive
  that would unpack to more than 2 GB is refused, since QGIS reads it on the main thread.
- Each download has a folder of its own and is written under its final name: a copy a layer reads is never
  replaced or removed, by a second download of the same link or by a failure, and nothing is renamed (an antivirus
  holds a new file on Windows). Copies stay in the folder when their layers are removed.
- Every failure says its step: the status of the server, a web page (at the probe or for the file itself), a file
  too large, too slow or cut, an archive with no layer. The error of an invalid layer is never read (it crashed QGIS
  3.22).
- The stdio MCP server waits 330 s for `add_layer` (redirects, download, opening) instead of its usual 45 s: a
  client that gave up earlier would retry a download QGIS is still making.

`search_open_data` blocks the interface until the platform answers or the network timeout of QGIS runs out.

## Objects on a raster

`adapters/public_api/drawn_objects.py`, with `POST /objects/segment` and `GET /map/context`:

- `map_context` adds `drawn_objects`, read from the dock (`CoverageModeController.drawn_objects`: the panel of the raster
  shown, the state kept for the others). Only counts, areas and extents go to the model; `raster_selection.dock_objects`
  makes `cross_filter` read the polygons in QGIS (`QGISFilterMateAccessor._dock_selection`). The project summary of each
  request has a line for them.
- `segment_objects` runs `filtermate:segment_from_features` on the main thread, as every tool, with a feedback that
  stops the run between two windows past 20 s, and marks it as the operation running (`operations.running`): a REST or
  MCP change queued meanwhile is refused instead of running nested. A guide that gives more than `limit` features, or
  whose count is unknown (a web service), is refused, never cut: the model selects fewer. The errors of the algorithm
  stay in the log; the model reads its own messages only, never a traceback or a path. The objects are written to a
  temporary GeoPackage, as the outputs of `run_algorithm`: not confirmed, since it adds a layer and changes none; Undo
  of the turn removes it and Redo opens the file again. A layer held in memory (none the agent makes) is recorded
  without a definition, so Redo says it cannot come back instead of bringing back an empty layer.
- `drawn_objects` only offers the objects that select in the dock: object target and SAM engine. With the colour
  engine the panel keeps SAM's objects for later, and they are left out.
- `similar_objects` (`POST /objects/similar`) runs on the main thread too, marked as running, with the same 20 s: the
  example is drawn on its window, then `search_windows` cuts the area searched in windows of 1024 pixels at the
  cell of the example (overlapping by 64 pixels, the example's first, then nearest first; more than 64 is refused).
  In each, the 40 best peaks of `similarity_peaks` (cosine at least 0.7) are drawn and kept as in the dock (same object
  at IoU 0.5, area and shape within 0.5 to 2, appearance at least 0.8). These are the settings of the *feature peaks
  only* variant of `scripts/sam_similar_candidates.py`, chosen there for the recall and judged at precision 0.55, recall
  0.20 on ten buildings: the tool and the system prompt say the layer is to be checked, not counted. With
  `use_dock_object` the accessor reads the objects of the dock on the main thread and the last one is the example.
- `render_window` waits for the rendering without user input when it runs on the main thread: a click during the run
  must not start another tool.
- SAM missing: the tool says how the user installs it. The agent cannot install it, on purpose (pip and a download
  of 160 MB after a confirmation in the dock).

## Sources

`core/agent/sources.py` is one list, in the Sources tab of the settings, nothing ticked by default:

- **Open data platforms**: data.gouv.fr, Opendatasoft, national CKAN portals, WFS services (IGN Géoplateforme, IBGE, PRG).
- **Satellite imagery**: STAC catalogs with public GeoTIFFs (Earth Search). `search_imagery` finds scenes, `add_layer`
  opens one through `/vsicurl/` without downloading it. Planetary Computer and Copernicus need signed or authenticated
  asset links, so they are left out for now.
- **MCP connectors** (`core/agent/mcp_client.py`, `adapters/agent/mcp_connection.py`): any Streamable HTTP server, public
  https or on this machine. Their tools join the conversation as `mcp_<server>__<tool>`, bounded in number and size.
  A plugin starts no process: a stdio-only server has to be run in HTTP mode by the user, as IGN's geocontext can be.

Rules: in the chat, only what is ticked can be used (REST and MCP callers hold the API key and are not limited by the
ticks); a connector alone does not let `add_layer` read the web; a WFS layer must be listed by the service, which must keep
its operations on its own host, and its URI is built by the plugin; every connector call stays in the thread; a connector
tool not declared read-only asks the user first; a call is sent once, again only when the server lost the session; a server
that does not answer is left out of the conversation and said so.

Anything fetched from these servers goes through `adapters/agent/bounded_http.py`: redirects are not followed, total time and
size are capped, Stop works, and a 401 or a TLS error is a failure rather than a QGIS dialog worded by the server. Layers
opened by GDAL have their redirects checked first and its own HTTP time limits. Connector descriptions and schemas are
reduced to well-formed, bounded JSON. `readOnlyHint` is what a server declares about itself: the thread shows these calls
after the fact, with their arguments.

The built-in list favours the countries where QGIS plugins are downloaded most (public dashboard
plugins-analytics.qgis.org, 30 days to 2026-11-09: United States 26 %, Brazil 11 %, France 10 %, then Singapore, Germany,
Hong Kong, Poland, United Kingdom, Netherlands, Spain, Italy, Japan). The dashboard has no figure for one given plugin.
Each entry was checked to answer without an account; `tests/qgis_headless/check_agent_sources_live.py` checks them again.

## Tools

`filtermate_api/mcp/server.py` is the one place where a tool is described. After changing one:

    pip install -r requirements-mcp.txt
    python scripts/export_agent_tools.py

The catalog is JSON because that server needs pydantic and the MCP SDK, which QGIS does not have. A test fails when the
two disagree. The chat leaves out `undo_filter`, `redo_filter` and `filter_status`: the first two only walk the dock's
history, which is not what the agent did.

What the chat adds to the REST checks, because a model can be steered by what it reads:

- arguments are validated against the schema before a handler runs;
- a filter must be a plain condition, read token by token against a list of what is accepted (`sql_guard.py`): no
  subquery, no function outside the list, no E-string or dollar quoting. A filter reaches the database with the rights of
  the user. `preview_filter` applies the same rule everywhere, REST and MCP included, because it is announced as read-only;
- on OGR and SpatiaLite, `apply_filter` tries the expression first: those providers accept invalid SQL and the layer then
  shows nothing, and SQLite reads an unknown `"name"` as the text `'name'`;
- the text of an unexpected exception stays in the log.

`preview_filter` and `field_values` run on the main thread: on a very large PostgreSQL table they hold the interface
while they run.

Reading the features (`adapters/public_api/introspection.py`), so that a question about the data is computed and not
estimated:

- `layer_statistics`: count, sum, mean, extremes and standard deviation of a numeric field, count and distinct values of
  another, or the lengths and areas of the geometries (metres and square metres, on the ellipsoid of the project), in
  all or by the values of a field. One pass over the features the layer shows, or over its selection, refused above
  500 000 features: it runs on the main thread;
- `sample_features`: up to 20 rows, the fields asked for, optionally the features matching a QGIS expression (the same
  list of accepted functions as `select_features`) and where each geometry is (type, centroid, bounding box: never its
  vertices);
- `identify_at`: the features and the raster values at a point, on the visible layers or the ones named.

A web service is not read by any of them.

Processing (`adapters/public_api/processing_tools.py`, rule in `core/agent/processing_policy.py`):

- `find_algorithms` and `describe_algorithm` list only what may run; `run_algorithm` runs it on layers of the project;
- what may run is a list of what is accepted: the providers `native` and `qgis` (GDAL, GRASS, SAGA, PDAL, scripts
  and models start other programs or run code nobody here has read), and an algorithm that makes at least one layer
  or only answers values (statistics). Selection, style, projection, index, truncation, import into a database,
  upload and download make no layer: that alone leaves them out. Executors of SQL or Python, and the network
  requests that make a layer, are refused by name. A parameter that needs a file, a folder, a database connection,
  a layout or a map theme refuses the algorithm; an optional one stays unset;
- inputs are layers of the project, never a path, a URI or a URL (QGIS would open them); an extent, a point or a CRS
  is numbers, an authid or a project layer. Expressions go through a list a little wider than the one of
  `select_features` (math, text, geometry functions that only compute; nothing that reads another layer, a file or
  the environment, and no `eval`). Raster calculator expressions have their own parser and are not checked;
- each layer an algorithm makes is written to a temporary file (GeoPackage, GeoTIFF) and added to the project: the
  turn checkpoint sees it as added, so undoing the turn removes it and redoing it opens the file again. A temporary
  file goes when QGIS closes; `export_layers` keeps a layer;
- it runs in a `QgsProcessingAlgRunnerTask` while the event loop turns, busy for the other operations, and Stop
  cancels it. An algorithm flagged `NoThreading` (geometry checks) holds QGIS while it runs;
- without attribute values shared, what an algorithm answers besides its layers (statistics) is left out.

Style (`adapters/public_api/layer_style.py`): `set_layer_style` (vector: single, categorized on a field of 100 values
at most, graduated in 2 to 12 classes by quantile, equal interval, Jenks, pretty breaks or standard deviation;
raster: pseudocolor or gray stretch of a band, its range read from the statistics of the band or given, never read
from a web service) and `set_labels` (a field, size, color, halo; or off), with a ramp of the style of QGIS and an
opacity. The answer says how many classes were made, never their values. Before the first call of a turn on a layer,
the turn checkpoint keeps its symbology, labels and rendering as XML (`exportNamedStyle`), and undoing the turn puts
them back (`importNamedStyle`); redoing it applies the new style again.

`apply_filter` and `preview_filter` take the same plain clauses through REST and both MCP servers: a subquery or a function
outside the list answers 400. A filter still reaches the database with the rights of the user, so an external agent exposed to
untrusted data is best run with a database role that cannot write.

## Evaluation bench

    python scripts/agent_eval.py                                        # scripted model, free, tests the bench itself
    FILTERMATE_AGENT_API_KEY=... python scripts/agent_eval.py --live \
        --provider anthropic --model claude-haiku-5-5                    # real model, costs money

39 cases in French and English, on a simulated project with attribute, spatial, raster, LiDAR, open data, export and
read-only requests, and one attribute value holding a prompt injection. A case is scored on the filters finally applied.
It is what decides the model of the free quota, and whether a local model is good enough to offer.

The simulated project keeps what each change did, as QGIS does: `filter_state` and `list_layers` show the filters
applied, `map_context` the selections. A case states what its request takes for granted in `setup`, such as a layer
already filtered or a road selected. Without that, a model that checks its work sees nothing and rightly tries again.

| Run (2026-11-10) | Result |
|---|---|
| Claude Haiku 5.5, direct | 39/39, about 0.09 $ estimated from the token counts |
| Claude Haiku 5.5, through the free quota relay, 3 cases with tools | 3/3 |

The first live run gave 31/39 on a project that kept no state: every failure came from the bench.

## Other applications (MCP server of the plugin)

Agent settings, tab **Other applications**. Off by default. Once on, FilterMate listens on `http://127.0.0.1:17823/mcp`
(port configurable) and needs no Python package, unlike the stdio server of `filtermate_api/mcp`, which stays.

Buttons copy the JSON most clients read, the entry for `claude_desktop_config.json`, or the `claude mcp add` command. All
contain the access token. Claude Desktop starts local servers as programs, so its entry goes through `mcp-remote` (Node.js),
with the header written without a space, as Claude Desktop on Windows does not quote arguments. That entry has not been tried
with Claude Desktop itself.

`tests/mcp_client_check.py` drives the server with the official MCP Python SDK, against a QGIS started by
`tests/qgis_headless/serve_agent_mcp.py` (`docker run --network host`). The server starts when FilterMate is opened and keeps running while its panel is
closed, until QGIS closes or the plugin unloads.

It listens on `127.0.0.1` of the machine running QGIS. With QGIS on Windows and the client in WSL 2, that address is not the same
machine unless WSL uses mirrored networking.

Rules of a call, in `ui/controllers/agent_mcp_bridge.py`:

- Same tools as the chat, under the same Sources ticks and the same "attribute values" option. External connectors are not relayed.
- Same SQL allowlist and same confirmations (export, adding or removing a layer), under the name of the application that asks.
- One change is one step of the history of the panel, and shows in the thread with the name of the application.
- A change is refused while the chat is working or while a QGIS dialog is open; reads go on.
- After a refusal, the same tool from the same client is declined for 20 s without a new dialog. A confirmation that comes after
  the client left does nothing.

Access rules, in `core/agent/mcp_server.py`: loopback only, a `Host` of this machine, no `Origin` from elsewhere, a Bearer token
compared in constant time, `application/json` only, one request per connection, heads of 16 KiB and bodies of 4 MiB at most.
Requests are served one at a time, on the Qt main thread, where the tools have to run.

The token is kept in the QGIS settings, not in the authentication database: reading it at startup must not ask for the master
password, and the client's own configuration holds a copy anyway. **New access token** replaces it.

## Free quota

`free-quota-proxy/` is a Cloudflare Worker, outside the plugin zip, that relays the requests of the panel to the Messages API with
one server-side key. It is deployed at https://filtermate-free-quota.filtermate-free-quota-proxy.workers.dev and set in `FREE_QUOTA_URL` (`core/agent/providers/__init__.py`); a user can
point to another relay with `APP.OPTIONS.AGENT.free_quota_url`. `tests/qgis_headless/check_free_quota_live.py` sends one real
request through it, the way the plugin does.

Limits by default, all set on the relay: 200 $ a month for the whole service, 0.50 $ a month per access token, 2 $ a month
per IP address (an IPv6 address counts for its /64), 3 new tokens per address and per day, 300 requests per token and per day,
Claude Haiku 5.5 only, no image. Once a limit is reached, the panel asks for the user's own key. The relay counts what is spent
and keeps no conversation.

See `free-quota-proxy/README.md` for deployment, every limit and what happens when the budget is reached.
