# Agent mode: foundations

Status: steps 1 and 2 of 4 are in the code. The chat is off by default (`APP.OPTIONS.AGENT.enabled`, read when the panel
opens) and works with the user's own key. For developers of FilterMate.

## Goal

An AGENT section, first in the accordion before FILTERING: the user writes "buildings above 1200 m in the selected commune" and the agent filters.
Any provider, a few free requests through a relay, then the user's own key, and external MCP clients on the same tools.

| Step | Content | State |
|---|---|---|
| 1. Foundations | Neutral conversation, provider adapters, tool catalog, read tools, evaluation bench | done |
| 2. Chat | Panel, Qt transport, key in `QgsAuthManager`, undo of a whole turn | done |
| 3. Free quota | Relay holding the key, per-install and global limits | to do |
| 4. Native MCP | Local MCP server without dependencies, shared activity log | to do |

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
  or its address asks again. Without attribute values, `field_values` is not offered; values already written in filters
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
- **The accordion.** `tabTools_current_index` stays 0 / 1 / 2 for FILTERING / EXPORTING / CONFIGURATION with the section in
  front of them, and is -1 on AGENT: the action bar and the undo buttons read that number.

## History

- Every turn that changed a layer is one `CrossOperation` under the key `filtermate_agent_turn` of the automation
  history, described by the request. The History page lists them (applied or undone), undoes and redoes them in
  order, and sends a request again. A layer that refuses a restore (being edited) keeps the turn undoable.
- The transcript (requests, actions, answers) is kept per project in the QGIS settings, keyed by the project path, and
  shown again when the project opens. The model does not get it back: a conversation starts afresh.
- Zooms, selections, layers added or removed are not undone by a turn and a turn made only of those is not listed; the
  last two are confirmed first. A filter set on a layer added in the same turn is undone with the turn.
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

`search_open_data` blocks the interface until the platform answers or the network timeout of QGIS runs out.

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

See `free-quota-proxy/README.md` for deployment, limits and what happens when the budget is reached.
