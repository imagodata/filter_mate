# Agent mode: foundations

Status: the steps below are in the code, first published in 5.1.0 (experimental). The chat is on by default
(`APP.OPTIONS.AGENT.enabled`, read when the panel opens; a configuration written while it was off is turned on once), with
the user's own key or a local Ollama model. For developers of FilterMate; the user guide has a chapter for users
(https://imagodata.github.io/filter_mate/guide.html#agent).

## Goal

An AGENT section, first in the upper stack of the dock, before EXPLORING: the user writes "buildings above 1200 m in the selected commune" and the agent filters.
Any provider with the user's own key, or a local Ollama model, and external MCP clients on the same tools.

| Step | Content | State |
|---|---|---|
| 1. Foundations | Neutral conversation, provider adapters, tool catalog, read tools, evaluation bench | done |
| 2. Chat | Panel, Qt transport, key in `QgsAuthManager`, undo of a whole turn | done |
| 3. Free quota | A relay holding a key, for a few free requests (removed on 2026-11-13: the agent works with the user's own key or a local model) | removed |
| 4. Native MCP | Local MCP server without dependencies, shared activity log | done |
| 5. Map context | The map, the layer tree and what changed, sent with each request; style, joins, relations on demand | done |
| 6. Reading the data | Statistics by group, lengths and areas, a sample of features, what lies at a point | done |
| 7. Processing | Find, describe and run the algorithms of QGIS that make layers, undone with the turn | done |
| 8. Style | One symbol, categories, graduated classes, raster ramps, labels, opacity, undone with the turn | done |
| 9. Long conversations | The oldest requests summed up in a few lines past a budget | done |
| 10. Project notes | Facts the user asks the agent to remember, saved in the project, sent with each request | done |
| 11. Editing data | Change, delete (confirmed) and add features, in the edit buffer, never saved by the agent | done |
| 12. Layouts | A print layout of the map added to the project, exported as PDF or PNG (confirmed) | done |
| 13. Project CRS | The CRS of the project and of the map, undone with the turn | done |
| 14. Expert mode | Python code in QGIS, off by default, read and confirmed at each run, not undone | done |
| 15. Vision | The map as an image for the model of the chat, with a key of the user and shared values only | done |
| 16. Levels of autonomy | Each tool in a risk class; the user chooses how far the chat goes alone; "yes for this conversation" | done |
| 17. Widgets | Controls the agent makes for the user (range, ticked values, a number), kept in the project, undone with the turn | done |
| 18. Layer tree | Groups, names of layers and map themes, undone with the turn | done |
| 19. Fields and joins | A field filled by an expression in the edit buffer, a join by a field, undone with the turn | done |

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

`anthropic` speaks the Messages API, `openai_compatible` the `/chat/completions` format of OpenAI, Mistral and
others, `ollama` Ollama's own `/api/chat`. Claude goes through plain HTTP because the official SDK needs Python 3.10 and
third-party packages.

Why Ollama has its own adapter: Ollama loads a model with 4096 tokens of context unless the request asks for more, and
its OpenAI-compatible endpoint ignores any such request (measured with Ollama 0.30.10, 2026-11-11: `options.num_ctx`
sent to `/v1/chat/completions` left `context_length` at 4096 in `/api/ps`). The system prompt and the tools of the chat
weigh about 71,000 characters, near 18,000 tokens, before the conversation: through `/v1` a local model never saw the
tools nor the request. `core/agent/providers/ollama_chat.py` asks for `num_ctx` 32,768, or 65,536 for a longer
request (two sizes only: each new size makes Ollama load the model again), and reads the lines of JSON Ollama streams.
An address saved with `/v1` still works, and a consent given for it still counts.
The settings list the models Ollama has installed (`GET /api/tags`, `installed_models`; 2 s at most, read while the
dialog stays usable), embedding models left out; a name already typed is kept.
The Provider tab guides Ollama: when nothing answers at the address typed, a note says to install it (with the link of
its download page) and Refresh asks again; when the model typed is not installed, Download posts it to `<address>/api/pull`
(`pull_url`, `pull_body`, `pull_progress` of `ollama_chat.py`) after a question, as the download weighs several GB. The
progress is read line by line, Cancel stops it, and the request has no total timeout: only a silence of 60 s ends it
(the transfer timeout of the request is that silence). A Test and a download never run together.

What a local model can run, measured on 2026-11-11 (Ollama 0.30.10, RTX 5070 Laptop GPU of 8 GB, WSL 2):

| | Every tool (53) | Filtering tools (22) |
|---|---|---|
| Prompt and tools, tokens | 15,300 (qwen3) to 17,600 (qwen3.5) | 8,300 to 9,400 |
| qwen3.5:4b, memory | 3.7 GB at 32k tokens, all on the GPU | 3.2 GB at 16k |
| qwen3:8b, memory | 14.3 GB at 32k, 5.6 GB on the GPU | 9.6 GB at 16k, 5.7 GB on the GPU |
| qwen3.5:4b, `agent_eval.py --live` | 42/69 cases; 33 of the 48 the filtering tools cover | 29/48 |

The memory of the model and of its context decides what runs, more than the tools: `qwen3.5:4b` (hybrid attention)
holds every tool with room to spare, `qwen3:8b` does not fit a GPU of 8 GB even with the filtering tools and crawls on
the processor. With fewer tools a small model did not answer better (sampling at temperature 1: a few cases either
way are noise). So every tool is the default. **Only the tools that filter, for a slow computer** (Provider tab, for
Ollama) gives the model `FILTERING_TOOLS` of `core/agent/tool_catalog.py` (read and filter the project, select, show or
hide, zoom, export, undo, keep a recipe): half as much to read at each request, which matters on a processor without a
GPU; the system prompt says the rest exists. `scripts/agent_eval.py --tools filtering` plays the same set.

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
- **A busy provider is asked again** (`core/agent/chat_engine.py`): after a 429, a 5xx or 529, an `overloaded_error`
  or `rate_limit_error` in the stream, or a connection reset or timed out, the model turn is sent again, twice at most,
  after the `Retry-After` of the server (30 s at most) or 2 s then 6 s. The wait is a `QTimer`, the status line says
  it, and Stop during it ends the request. Never once text of the turn was shown (it would show twice), nor for a
  refused key, a bad request (400, 404), a used-up quota or a refusal, nor when the server asks to come back in more
  than 120 s (a quota of the day): the failure is shown at once.
- **A request that breaks off keeps what it changed** (`AgentSession.interrupt_request`): after a failure, Stop or a
  refusal, when a tool that changes something ran, the conversation is cut after the last tool results, so every
  call kept has its result (a call that Stop left unrun in its turn is answered "not run"), and a note in that
  message tells the model why the request stopped there, that what those steps changed is in place in QGIS, and not
  to do them again without checking. The thread says how many steps stay (Undo takes them back) and the request does
  not come back in the line: sent again whole, it would do them twice; the user asks the agent to go on. Steps are
  the calls that changed something: readings do not count. A request that changed nothing (nothing ran, readings
  only, calls refused or failed) is forgotten and comes back in the line, to be sent again. So is a request the
  server refused for what it holds (400: too long for the model), which would fail again with every later one, and a
  request stopped by a refused key or a used-up quota, since fixing the settings starts another conversation: the
  thread then says which steps stay. The next request follows a message of tool results: each adapter sends two
  messages of the user in a row as one.
- **Redirections are not followed**, since the key is in the headers.
- **Undo this turn** captures every layer before the first change of a request and pushes one `CrossOperation` in the
  automation history: rasters and point clouds get their source back, a layer changed since is left alone, and the
  derived files of the turn stay alive. Stopping a request keeps what was done and it can still be undone.
  A layer counts as added by the turn when it came during one of its tool calls (`TurnCheckpoint.end`, called by the
  engine once the tool ran): a layer the user loads while the model thinks stays at undo. Who runs changes without
  saying when they end (the MCP server of the plugin, a recipe) is compared over the whole turn, as before.
- **Saving the settings** starts another conversation only when the provider changed (preset, model, address, key,
  consent): the thread is then cleared. Other sources, tools or the sending of values under the same provider drop
  the engine alone (`_restart_engine`): the thread and what was allowed for the conversation stay, and the next
  request tells the model what the thread holds (the recap).
- **What a model writes is shown as plain text** (`QPlainTextEdit`): rich text would load its images and links.
- A conversation does not survive a change of project or of provider, but the model is told what came before: with
  the first request of a conversation that starts under a thread already shown (the project opened again, another
  provider), a few lines say what the last six requests asked and which actions the panel showed for each
  (`transcript.recap`). The answers are left out: they may hold values of the data, read under other settings.
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
- **Memory from one project to the next** (`core/agent/memory.py`, `adapters/agent/memory_store.py`; spec
  `docs/superpowers/specs/2026-11-22-agent-local-memory-design.md`, lot 1): notes kept outside the project, in
  `agent_memory.json` of the `FilterMate` folder of the QGIS profile. Two scopes: `user` (every project: a word of
  the trade, a preference) and `source` (a data source, by the signature of the favorites,
  `core/domain/layer_signature.py`: the note comes back in any project that holds a layer of that source). Only a
  table of PostgreSQL or SpatiaLite and a layer of a file (OGR) have one: for the other providers the signature is
  the name the user gave the layer, which a new name would lose and two layers could share. None either for a layer
  held in memory, cut by FilterMate or written by Processing in its temporary folder, nor for a source that is a
  connection string or an address: it may hold a password or a token, and nothing of it is kept. Two files of the
  same name in two folders share their notes, as two tables of the same schema and name do: the tab shows the
  signature. In lot 1 the user writes them in
  the Memory tab of the settings of the agent; the model only reads them, and no tool changes them. They go as a
  part of the context of the request (`request_context.ContextParts.memory`), under a header saying they are
  data: with the first request of a conversation, after a compaction, and when they changed; never in the
  instructions, so the start of a request is the same for everyone. 3,000 characters at most
  (`MAX_MEMORY_BLOCK`): past it the notes of the active layer go first, then those for every project, then the
  other sources, the latest first, and a last line says how many were left. Measured with
  `scripts/agent_request_weight.py --conversation --memory`: an empty memory weighs nothing; a full one costs the
  conversation of the bench +9.6 % (+2.2 % for 643 characters). A note a model proposed while it read attribute
  values (`with_values`, lot 2) is held back once the user no longer shares them. The file is JSON a person can
  correct; one that cannot be read whole, a key this version does not know included, is never written (the tab
  says why): nothing is dropped or corrected in silence. A write holds a lock file, is made on the file as it is at
  that time, then replaces it in one move (through a link, with its permissions). The option `filter_mate/agent/memory` (on by default) stops
  the sending. `scripts/agent_eval.py` plays four words of the trade without and with their note (`vocab_*` and
  `vocab_*_memory`) and prints, for each, how often it passed and the median of the requests sent to the model.
  Measured on 2026-11-22 with `--live --provider ollama --model qwen3.5:4b --families --repeat 3` (a small local
  model, three runs: an order of magnitude, not a rate): 12 passes of 12 with the note against 5 of 12 without.
  Over the runs that passed, the median of the requests to the model went from 5 to 4 (cours d'eau permanents) and
  stayed at 4 (logements, cadastre); RD never passed without its note (3 requests with it). Over every run,
  logements went from 14 to 4: without the note the model searched until it gave up. So the note makes the answer
  right far more than it saves requests: the model still reads the layer before it filters, as its instructions
  ask. The criterion of the spec (one request less in the median) is not met.
- **Editing data** (`adapters/public_api/feature_edits.py`): `update_features` (values, or formulas computed on
  each feature), `delete_features` (the user confirms) and `add_features` (WKT, 100 at most) put the layer in
  editing mode and add one named command to its undo stack: nothing is written to the data source, the user saves
  the layer edits or discards them. Features are chosen by a QGIS expression and/or the selection (all of them
  only with the expression `true`), 100 000 at most. A value is converted to the type of its field first (QGIS
  would take "abc" in an integer field and fail at saving); keys, joined and virtual fields are not written.
  The turn keeps the index of the undo stack before its first edit of a layer; undoing the turn steps back over its
  commands, and is refused on a layer saved, discarded or edited by the user since. `describe_layer` says whether
  a layer is being edited and holds unsaved changes.
  Checked on GeoPackage (`check_agent_tools.py`) and on a PostGIS table (`check_agent_edits_postgis.py`: the key
  refused, nothing in the table before the user saves, then the values and the point added there with their
  types and CRS) and on a WFS-T layer served by QGIS Server (`check_agent_edits_wfst.py`: the GeoPackage behind the
  server read directly, unchanged until the layer is saved, then holding every change).
  QGIS filters no layer in editing mode, so a turn that filters and edits a layer is undone edits first
  (`TurnCheckpoint._move`): a layer the turn itself put in editing mode, back at the start of its undo stack with
  nothing else pending, leaves it (`turn_effects._closable`) and takes its filter back. Its undo stack goes with the
  editing mode: applying that turn again brings the filters back and says the edits were left. A layer the user was
  editing stays in editing mode with their edits. `remove_layers` refuses a layer with unsaved edits (undoing the
  turn would bring it back without them); the joins of other layers to a layer removed, and the relations of the
  project that cite it, come back with it at undo.
- **Layouts** (`adapters/public_api/layouts.py`): `create_layout` adds a print layout to the project (A4, A3, A5
  or Letter, landscape or portrait): a map of the layers checked in the tree or of those given, framed on an
  extent, a layer, the map view or the layers shown, with a title, a legend, a scale bar and a north arrow. The
  user finishes it in the layout designer; undoing the turn removes it (a `layout` effect keeps its XML, redoing
  reads it again). `export_layout` writes one as PDF or PNG into a sub-folder of the export root, never a path
  of the model, and is confirmed by the user like `export_layers`. `map_context` lists the layouts.
  `open_layout` opens one in the layout designer, in front, for the user to finish; `preview_atlas` turns the
  pages of its atlas preview (first, previous, next, last), turning the preview on in its open designer. Both
  are tools of the chat alone (a window is needed) and change nothing of the project.
- **Project CRS**: `set_project_crs` takes an authid, an EPSG code alone or a layer of the project, and sets the
  CRS of the project, which the map follows (layers in other CRS are reprojected on the fly, no data changes).
  The turn keeps the CRS before (its authid, or its WKT for a CRS of its own) and undoing the turn sets it back.
- **Fields and joins** (`adapters/public_api/fields_joins.py`): `add_field` adds a field (integer, integer64, decimal,
  text, date, datetime, boolean) to a vector layer in its edit buffer, as one command of its undo stack, and fills it
  on every feature with a QGIS expression when given (the guard of `update_features` applies; a refused formula
  leaves the field empty and says why). `join_layers` shows the fields of another layer or table beside each
  feature, matched by a field, as the Joins tab does (memory cache, prefix the name of the joined layer and `_` by
  default, a subset of its fields); nothing is written. In the chat, the REST API (`POST /layers/fields`,
  `/layers/join`) and both MCP servers. The turn keeps the undo stack index (the field) and each join it added:
  undoing it removes them. `add_field` is of the class *edit buffer*, `join_layers` of the class *project*.
- **Forms and relations** (`adapters/public_api/forms.py`): `set_form` sets, field by field and all or none (50
  entries), how a vector layer shows in its attribute form: an alias, a widget (`value_map`, `value_relation`,
  `range`, `date`, `checkbox`, `text`, `hidden`, `relation_reference`, or `default` for the choice of QGIS), the
  constraints not null, unique and an expression with its text (soft unless `enforce`), a default value
  expression (and on update), read only. Every entry is checked first: an unknown field, a widget unsuited to the
  type of its field, an option of another widget, a lookup layer or field missing, an expression that does not parse
  or names a field the layer lacks, a constraint the source itself sets. `relations` lists, adds (a child layer
  linked to a parent by a field, association or composition) or removes (by id or name) a relation of the project.
  Nothing is written to the data; REST `POST /layers/form` and `/project/relations`. The turn keeps the form of the
  layer as the XML of its style categories Fields and Forms, and each relation added or removed. Both of the class
  *project*; a relation is refused when one of its two layers is protected. Skill `forms`.
- **Layer tree and map themes** (`adapters/public_api/layer_tree.py`): `group_layers` puts layers in a group, made
  where missing (`Base/Roads` for a group in a group, five levels at most; empty for the top), first or last of it,
  each one kept checked or not; `rename_layer` renames a layer; `map_theme` lists, saves (the layers shown now and
  their styles, replacing a theme of that name), applies or removes a map theme. `group_layers` with `above` puts layers just above another
  layer, in its group; `rename_layer` with `group` renames a group (its path changes: the turn keeps the tree).
  `bookmark` lists, adds (the visible map or an extent, replacing one of that name), zooms to or removes a spatial
  bookmark; its zoom needs the map window. In the chat, the REST API
  (`POST /layers/group`, `/layers/rename`, `/map/themes`, `/map/bookmarks`) and both MCP servers. The turn keeps the place of each layer
  and the groups with their check state, the names, the themes and the bookmarks as XML and, for a theme applied, the visibility and
  the current style of every layer: undoing it brings them back and removes the groups it made.
- **Expert mode** (`adapters/agent/expert_python.py`): `run_pyqgis`, a tool of the chat alone, is offered only when
  the user ticks *Expert: let the agent run Python code in QGIS* in the settings (off by default). Each run opens
  a dialog with its purpose and the whole code, No by default; the code is written to the log, then run on the
  main thread with `iface` and `project` defined, and the answer gives what it printed, `result`, or its
  traceback. It runs with the rights of the user and is not undone with the turn; the MCP servers never offer it.
  The one `exec` of the plugin is marked `nosec B102` for Bandit, with that reason. The evaluation bench leaves the
  tool out, as the default settings do.
- **Vision**: `view_map`, a tool of the chat alone, answers with the map rendered by `map_images.map_image` (the
  view, an extent as WKT, or the whole of a layer), a JPEG in `ToolResultPart.images` (`WithImages`, as the
  MCP-only `map_image` and `contact_sheet`). Offered only with a provider that takes an image and when attribute values are shared (a map shows its labels): a decision of the user, 2026-11-11.
  Claude gets the image in the `tool_result`; an OpenAI-compatible server, whose tool messages hold text only, in
  a user message right after. An image goes with the request it was taken in only: before the next request it
  is replaced by a line saying it was there. A model that reads no image may refuse the request.
- **Showing the user** (`adapters/public_api/gui_control.py`): `flash_features`, `set_active_layer` and
  `show_message`, tools of the chat alone, point at what the agent means while the user watches: features
  matching an expression blink on the map (selecting nothing, 500 at most), a layer becomes active and is shown
  unfolded in the tree, a short message lands in the bar of QGIS (never a question: `ask_user` asks it instead).
  View class, no undo point, refused without a window.
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
- **What a request weighed** shows under the thread when it ends: the tokens read (the cache among them) and
  written, as the provider counted them (`messages.request_usage`); nothing when it counted none. No price: prices
  change, and a local model has none.
- **A source that is not ticked**: the notes of the prompt tell the model to say so and to call `show_settings_link`
  with `sources`, a button to the tab, instead of answering that it cannot.
- **At most 16 model turns per request** (`max_model_turns`, `core/agent/session.py`). Two turns before the limit the
  model is told so, and a request that reaches it stops with a sentence that says why; what was done stays and can be
  undone.
- **Two stacks of sections** (`ui/layout/dock_chrome.py`): AGENT / EXPLORING above the splitter, FILTERING / EXPORTING /
  CONFIGURATION below, one section open at most in each. AGENT folds EXPLORING and FILTERING; FILTERING brings EXPLORING
  back. `tabTools_current_index` stays 0 / 1 / 2 for the lower sections and is -1 when none is open.

## Levels of autonomy

`core/agent/permissions.py`, plain Python. Each tool falls in one risk class, from what it can break and how it is
undone; the user chooses a level in the Autonomy tab of the settings, which says up to which class a tool runs alone.

| Class | Tools | Undone |
|---|---|---|
| read | every `read_only` tool, open data searches included | nothing to undo |
| view | `zoom_to`, `select_features`, `set_layers_visibility`, `group_layers`, `map_theme`, `bookmark`, `open_layout`, `flash_features`, `set_active_layer`, `show_message`, `preview_atlas` | with the turn (a zoom, an opened designer, a flash, the active layer, a message or a turned atlas page is view state: it stays) |
| project | filters, style, Processing, layouts, CRS, SAM layers, any other change | with the turn |
| edit buffer | `update_features`, `add_features`, `add_field` | with the turn, until the user saves |
| irreversible | `destructive` tools: `delete_features`, `export_layers`, `export_layout`, `remove_layers` | not always |
| outside | `open_world` changes (`add_layer`, `add_service_layer`), every tool of a connector (its `readOnlyHint` is not trusted) and `run_pyqgis` | no |

| Level | Runs alone | Asked | Refused |
|---|---|---|---|
| advisor | read | | everything else: the model is told to describe the steps |
| careful | read, view | project and above | |
| **standard** (default) | up to edit buffer | irreversible, outside | |
| autonomous | up to irreversible | outside | |

- `standard` asks exactly what the chat asked before the levels (`ToolSpec.requires_confirmation`); a unit test holds it.
- The notes of the project and `undo_agent_step` run at every level: the user asks for them, and they change only
  what the agent keeps.
- A question offers "Yes for this conversation": that tool then runs alone until a new conversation, another project or
  another level. Never for `run_pyqgis`, asked at every run whatever the level. Two tools are allowed for what the
  call reaches, not as a whole (`permissions.grant_key`): `add_layer` for the host of its address (local files are
  another yes), `delete_features` for its layer. A text read on the web cannot ride a yes given to another address.
  The question shows the address whole, up to 600 characters after the host, and says how many are not shown.
- The level is read at each call (`ChatEngine(policy=...)`), and sent with each request, after the project summary,
  when it is not `standard` (the system prompt stays constant for the cache).
- An invalid call is never asked nor refused: it runs to answer its mistake.
- The MCP servers keep the `standard` level: the level is the chat's. The native one follows the *Always ask* and
  *Never* rules of the Tools tab too (`AgentMcpBridge._policy`); *Always allow* does not take its confirmations away.
- **One question for a turn** (`ChatEngine._confirm_together`, `confirm_many` of the listener): when the model calls
  several tools in one turn and two or more of them would be asked, the user gets one question listing them, all or
  none; a recipe does the same for its steps. Code (`run_pyqgis`) keeps its own dialog, one run at a time; a listener
  without `confirm_many` (the bench) is asked call by call. The verdicts are the same as call by call: refused calls
  stay refused, the others run alone.
- **Exceptions by tool** (Tools tab, `AgentSettings.tool_rules`): *As the level says* (default), *Always ask* (at
  every call; never allowed for a conversation), *Always allow* (not past `advisor`, never for `run_pyqgis`) or
  *Never*: the tool is left out of the tools offered to the model and answered `TURNED_OFF` if it is called anyway,
  in a recipe, or by another application through the native MCP server. The notes and `undo_agent_step` have no
  exception. A protected layer is refused before any exception.
- **Protected layers** (`adapters/agent/protected_layers.py`, kept in the project by their ids, ticked in the Autonomy
  tab): a call that would change one (`permissions.CHANGED_LAYERS`: its filter, style, labels, features, fields, join,
  name, or the layer itself) gets the verdict `PROTECTED`, refused at every level, never turned into a question nor
  allowed for a conversation; in a recipe it stops the replay; the native MCP server answers it the same way, and
  `QGISFilterMateAccessor` checks every change again on the main thread, so the REST API and the MCP server built on
  it (`python -m filtermate_api.mcp`) answer 403 (`X-FilterMate-Refusal: protected-layer`), an undo or redo of the
  dock history that would set the filter of a protected layer included. Protected layers that cannot be read refuse
  a change (`PROTECTION_UNREADABLE`), never let it through. Reading
  one, using it as the source of a cross filter or the table of a join, zooming, selecting or showing it stays
  allowed. Their names go with each request. A favorite is checked on the layers applying it would change (its
  layer, its remote layers, its clips: `operations.favorite_layers`, found as `apply_favorite` finds them); a map
  theme applied on the layers whose current style or legend items it would change (`layer_tree.theme_changed_layers`,
  compared with what QGIS records from the map now; a layer of the theme hidden now counts); removing a layer counts
  as a change of the layers that join it (`permissions.JOINED_CHANGES`: QGIS removes the join). Editing a joined layer
  does not (an editable join and a cascaded delete write from the layer that holds the join into the joined one);
  relations (kept by the project, not by a layer) and virtual layers (their query stays, they can no longer read a
  layer removed) are not counted. Not
  covered: `run_pyqgis` (code, asked at every run).
- The question of a change the level shows first (a filter at `careful`) says what the tool does and its arguments; a
  tool added later without a text of its own gets the same, instead of the text of an export.

## Widgets

`create_widget` and `remove_widget`, tools of the chat alone. A widget is a description, never code
(`core/agent/widgets.py`, plain Python), drawn by `ui/widgets/agent_widgets_strip.py` under the conversation:

| Kind | Made from | What the user does |
|---|---|---|
| `range` | minimum and maximum of a numeric field among the features shown | two bounds; moving them filters the layer |
| `values` | the values of a field among the features shown (50 at most, NULL included) | tick or untick; All / None |
| `stat` | count, or sum, mean, min, max of a numeric field | reads a number that follows the filters and edits |
| `chart` | the features of each value of a field (the 8 most frequent and the others), or a histogram (10 bins) of a numeric field | reads bars that follow the filters and edits; it filters nothing |

- The model chooses the kind, the layer, the field, the aggregate and the title, nothing else: FilterMate builds the
  filter of a widget from the field and values it holds, quoted by `QgsExpression`, and applies it through the public
  API of the plugin (`apply_filter`, source `FilterMate widget`), or `setSubsetString` when two layers share a name.
- The widgets of a layer narrow it together: its filter is the filter it had when its first widget was made (`base`),
  AND the condition of each widget. A bound left at its end, or every value ticked, adds nothing. One filtering
  widget per field of a layer; 12 widgets at most.
- What the user does with a widget is the user's own action: it is applied at once, whatever the level of autonomy,
  and is not a step of the agent's history. Making or removing a widget is (class *project*), undone with the turn
  (`("widgets", "", before, after)` in `adapters/agent/turn_effects.py`).
- Kept in the project file (`FilterMateAgent/widgets`), with the state of each one, so they come back with it. A
  widget whose layer went away says so. Removing a widget leaves the filter it set on its layer.
- The widgets go with each request, after the project summary, as data: kind, layer, title, field, bounds or the
  number of ticked values, never the values themselves.
- The MCP servers do not offer these tools: the widgets live in the panel of the dock.

## Recipes

A recipe keeps the changes of one request of the agent under a name, and runs them again later **without any model**:
nothing is sent, nothing is paid, and it works with no provider set up. `core/agent/recipes.py` (plain Python),
`adapters/agent/recipes_store.py`, and the **Recipes** submenu of the **⋯** menu of the panel.

- What is kept: the calls of the request that changed something and succeeded, in order, each with the arguments the
  model sent and the words of its card. Reads, refused or failed calls, the notes, the widgets, the expert code, the
  agent's own history and the tools of external connectors are never kept. 30 steps, 20 recipes per project at most.
- How one is kept: **⋯ > Recipes > Save the last request as a recipe…** (the last request that changed something, under
  a name the user types), or by asking the agent (`save_recipe`, a tool of the chat alone: the changes of the request
  under way, else of the last one that changed something). The same name replaces a recipe. Kept in the project file
  (`FilterMateAgent/recipes`), so a recipe travels with the project.
- How one runs: **⋯ > Recipes > *name***: the steps are listed, named from their tool and arguments (never from
  the words the file holds), then **Run without the model**. Each step runs through the same executor as the chat.
  A recipe may come with a project made by someone else, so a run asks at least what the usual level asks: what
  cannot be undone here (exports, removals, deletions) and what reaches outside are asked even at *autonomous*; at
  *careful* every change is asked; at *advisor* every step is (the user asked for the run). A yes is for that step
  only, never "for this conversation". The first step declined or failed stops the recipe, and **Stop** stops it
  before its next step; the steps before stay. A run is one turn of the history, undone as one. It is the user's own
  action: the next request tells the model what changed, as for a filter set by hand.
- What a step reads is read again at each run: a cross filter from the selection filters from the selection of the
  moment, and a layer is found by its name. A step that needs a tool the settings now leave out (attribute values not
  shared, a source unticked) stops the recipe and says so.
- A layer made by a step (the output of `run_algorithm`, `segment_objects`, `add_layer`…) is a new layer at each run,
  with a new id. Each step keeps the layers it made (`made`: their ids and names, the layers new in the project after
  the call). At a run, the layers the step makes again are paired with those by name; when exactly one is left on each
  side (the one output of an algorithm, named in another language), those two. With more left nothing tells which is
  which, and they stay unpaired rather than send a later step (a deletion maybe) to the wrong layer. The later steps
  then name the new layers: an id of the first run wherever it is; a name where the arguments name layers (`layer`,
  `layers`, `source_layer`, `target_layers`, `join_layer`, `raster`… and the parameters of `run_algorithm` that take
  layers), the last layer made under that name and still there, or renamed by `rename_layer` in the recipe. A later
  step that names, by id or name, a layer this run did not make again stops the recipe and says which: the layer of
  the first run may still be there under that name. A step on a made layer is asked alone, once that layer is there,
  not in the one question of the recipe. A name protected in the file stays protected, even paired with a layer made
  here. `made` counts in the size of a recipe and in what the approval of a live recipe holds for (`remap`,
  `pair_made`, `stale_reference` in `core/agent/recipes.py`). A recipe kept before this has no `made` and runs as it
  did. Limits: a layer added by something else during a step (the user, another plugin, while Processing runs) counts
  as made by it; a layer made by code or a connector, which are not kept, is not followed; an id inside a longer text
  (an expression, `aggregate('id', …)`) is not replaced.
- The recipes go with each request as data: the name and the tools of each one, never their arguments nor the words
  of the file, so the model can name them or forget one (`remove_recipe`). Keeping or forgetting a recipe through the
  agent is undone with the turn (`("recipes", "", before, after)` in `adapters/agent/turn_effects.py`), unless the
  recipes were changed from the menu since: those are left as they are. From the menu, removing asks first and is not
  a step of the history.
- The MCP servers do not offer these tools: recipes live in the panel of the dock. The model cannot run a recipe.
- A favorite, unlike a recipe, the agent can also keep: `save_favorite` stores the current filter of the project
  under the name the user gives (as the star of the dock does, with its remote layers and clips), through the chat,
  `POST /favorites` and both MCP servers. Refused when nothing is filtered or when the name is taken; never replayed
  by a recipe (it would keep a duplicate); kept when the turn is undone, and said so.

### Live recipes

A filter of FilterMate is a subset string written from the source as it was: when the source changes, the targets
keep the old answer. A favorite does not help, it replays the same strings. A recipe does: its cross filter reads the
source again at each run. So a recipe can be **live** (**⋯ > Recipes > *name* > Run again when its source is saved**):
each time the edits of one of its source layers are saved in QGIS (`afterCommitChanges`), it runs again by itself.

- What may be live (`live_problem` in `core/agent/recipes.py`): a recipe with at least one `cross_filter` (its
  `source_layer` values are the layers followed), whose steps are all in `LIVE_TOOLS`: filters, selection, visibility,
  style and labels. What writes (an export, an edit), adds or removes layers, runs Processing or moves the map is
  refused: it would happen at every save. A stored `live` flag on any other recipe is dropped when the project is
  read, so a project made by someone else cannot make an export run at every save.
- Ticked by the user, on this computer: the project file keeps `live`, but a recipe runs by itself only once the
  user ticked it here for these very steps (`approve_live` in `adapters/agent/recipes_store.py`: a hash of the project,
  the recipe and its steps, in the QGIS settings). A project made by someone else, or a recipe saved again under the
  same name by the agent, shows unticked and follows nothing. Nothing runs alone at the *advisor* and *careful* levels.
- A live run asks nothing: at the usual level these steps run alone, and one that would ask (a layer protected from
  the agent) stops it. It is one turn of the history, undone as one (it empties Redo, as any change does), and shows
  in the thread as a note without leaving the history or the settings.
- Several saves within 0.8 s run it once. While FilterMate or the chat works, or while a layer the recipe filters is
  being edited (its filter cannot change then), it waits and tries again for about five minutes, then says so. A
  source layer is found by its id, then by its name when one layer only has it; the layers followed are updated when
  layers come or go, and on closing a project a pending run is dropped.
- What a cross filter reads is read at each run: with `selected_only`, the selection of the moment, or what the source
  shows when nothing is selected. A save through **Save changes and filter** of the dock runs the live recipes after
  that filter, and they write their targets again.
- Not followed: changes made outside QGIS (another user of a PostGIS table, a script writing the file), and a live
  recipe whose source is the target of another one (a filter is not a save). Only the saves of this QGIS.

## History

- Every turn that changed a layer is one `CrossOperation` under the key `filtermate_agent_turn` of the automation
  history, described by the request. The History page lists them (applied or undone), undoes and redoes them in
  order, and sends a request again. A layer that refuses a restore (being edited) keeps the turn undoable.
- The transcript (requests, actions, answers) is kept per project in the QGIS settings, keyed by the project path, and
  shown again when the project opens. The model does not get it back: a conversation starts afresh.
- A turn also records what it does beside the filters (`adapters/agent/turn_effects.py`): layers added or removed,
  selections, visibility in the layer tree. Undo and redo apply them with the filters. A removed layer comes back from
  its definition, same id, at its place in its group; a layer kept in memory cannot, and the panel says so. Zooms and
  exports are not undone. What the user changed in QGIS since the turn (the visibility of a layer, the project CRS, a
  layer name, the style of a vector layer or the style it has on) is theirs: undo and redo put back only what is still
  as the turn left it, and the message names the rest. Not checked, put back as before: what is read as a whole
  collection (the layer tree, the bookmarks, the map themes: a group ticked or a theme of the user's elsewhere would
  keep the agent's from being undone, and QGIS writes the themes back in another order), a selection (a filter
  empties it by itself), the style of a raster (its XML follows the filter), the widgets and notes (the agent's own).
  The edits, recipes and settings check in their own way. Undo and redo go in three times: the layers added or
  removed, then the filters (a filter needs its layer), then the rest (a filter empties a selection).
- **Steps.** The undo point takes the state of the layers before each change of a turn, and what each change did beside
  the filters (a style, a layer added, a name, a group...). The History page lists the steps of the last request that
  changed something; "Undo back to here" puts the request as it was before the chosen step (its filters and what the
  later steps did beside them, what the user changed since left as it is), as a step of its own that Undo takes back
  (`step_effects` and `effects_reversed` of the `CrossOperation`): a layer a later step made is removed and comes back
  with its filter, a layer a later step removed comes back as it was before the chosen step. Limits: a layer a task
  of a step adds after the next step began counts in the next step; what a step changes without saying so (code,
  Processing on a layer) is not in its effects.
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
  `PG:`, `/vsi...`, UNC path, inline XML or `|subset=`. A service (WFS, WMS) cannot be added by a model. A local
  `.las`, `.laz` or `.copc.laz` file is a point cloud whatever kind is asked (`project_control._add_point_cloud`:
  the `copc` provider, else `pdal`, said missing when QGIS was built without it); never from an address.
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

### Terrain (2026-11-15)

A relief map asked in one sentence ("a terrain map of Lyon over Google Satellite, a semi-transparent elevation
ramp with a subtle hillshade, contours every 25 m, index contours at 100 m") is a chain of tools, given to the
model by the skill `terrain`: `find_place`, `add_basemap`, `add_elevation`, `set_layer_style` (pseudocolor),
`duplicate_layer`, `set_layer_style` (hillshade, blend multiply), `contour_lines`, then a look with `view_map`.
Eight calls and about 6 s of tools on Lyon (373 x 380 pixels, 0.4 MB read).

- `add_elevation` (`adapters/public_api/terrain.py`) reads, from each tile of the model the area touches, only
  the part it needs (GDAL reads the files by parts through `/vsicurl/`), warps it on a grid in metres and writes
  one GeoTIFF in the QGIS profile. The grid is the CRS of the project when it is in metres and keeps distances
  (not Web Mercator, whose metres are those of the equator), else the UTM zone of the area: a slope, a hillshade
  and a contour need metres. Bounded: 16 squares of one degree, 16 million pixels (a larger area is written
  coarser, and said so), 240 s. The layer goes under the data, above the web basemaps.
- `contour_lines` draws the contours of any raster file of the project with the GDAL API, in this process: each
  line has `elevation` and `is_index` (a multiple of `index_interval`). Closed contours shorter than ten pixels
  are left out and counted (`left_out`): in a surface model they are the bumps of buildings (on Lyon, 634 of 852
  lines for an eighth of their length). The layer comes drawn in thin lines with the index contours thicker.
- Both read in a worker thread while the event loop turns: the interface stays alive and Stop ends them. GDAL
  reads with its own HTTP client, which Stop cannot cut in the middle of a request: it is heard between two tiles
  and at each block, and a server gone mute is given up after 8 s (measured: a Stop pressed 1 s into a tile that
  stalls is answered after 8.0 s). When QGIS closes meanwhile, the work is told to end and waited for, without
  turning on an event loop that no longer waits. The other operations of FilterMate are refused meanwhile.
- The Processing algorithms of GDAL stay refused (`core/agent/processing_policy.py`): they build a command line,
  and these tools give GDAL values this code builds, never a text of the model. A CRS is an authid, never a
  definition (which can name a grid by its address). What GDAL says of a failure goes to the model without an
  address nor a folder of this machine (`elevation.quiet_message`), and a refusal names no height of a raster of
  the user when the values are not shared.
- A layer the user protected is read (its contours are drawn) and never copied: a copy is a second layer on the
  same source and no protected one, so what is edited in it is written in the file of the layer copied
  (`duplicate_layer` is among the tools that change their layer, `permissions.CHANGED_LAYERS`).
- A raster stored with a scale or an offset (tenths of metres in whole numbers) is read through them, and its
  heights are read by GDAL in the worker, never on the main thread: the raster may be on a server.
- `set_layer_style` draws a raster as a hillshade (blended between its pixels when the map is closer than they
  are), mixes a layer with what is under it (`blend`), leaves the extreme values out of a ramp (`cut`), draws
  flat steps (`discrete`), and gives a width to one symbol or to each rule; `Terrain` is a ramp of FilterMate (the
  style of QGIS holds none that reads as heights). `set_labels` writes labels along lines (`placement`).
  `duplicate_layer` adds a second layer on the same data: one layer is drawn one way.
- Checked by `tests/qgis_headless/check_agent_terrain.py` in QGIS 3.22, LTR and latest: 125 checks, the tiles
  served by parts by a server of this machine (which can also stall, or serve what is no image), and with
  `FM_NET=1` the real ones.

### OpenStreetMap (2026-11-15)

"The hospitals of Pune", "the buildings along the river", "a heatmap of the restaurants": what a place holds,
when no layer of the project has it. `add_osm_features` (`adapters/public_api/osm_features.py`) brings in the
features of OpenStreetMap that carry given tags in an area, from an Overpass server the user ticked.

- A model gives tags (`amenity=hospital`, `building`) and an area, never a query: the Overpass query is written by
  `core/agent/osm.py` from tags checked one by one (a key in letters, digits and `: _ . -`; a value without a
  quote nor a backslash), so nothing of a model is a piece of a query language. Ten tags, 10 000 km2 and 64 MB at
  most.
- The answer (OpenStreetMap XML) is copied to a temporary file through `bounded_http` (bounded, ended by Stop),
  then read by the OSM driver of GDAL in a worker thread, with a configuration written per request: the keys asked
  become columns, and a feature is kept when it carries one of the tags (the nodes of a way come with tags of
  their own, a door, a traffic light). The query asks for the nodes before the ways (`(._;>;); out body;`): in
  the order Overpass gives by default, GDAL builds no area (0 polygon for the hospitals of Lyon).
- One layer per kind of geometry (`as_mapped`), or one layer of points (a point inside each area, the middle of
  each line) to count, to measure distances and for a heatmap: a hospital is a node here and an area there. The
  layers are kept in a GeoPackage of the QGIS profile, in EPSG:4326, with `osm_id`, `osm_type`, `name`, a column
  per key asked (`addr:street` is `addr_street`) and `other_tags`; a column no feature fills is dropped.
- The public servers are run by volunteers and often busy. Measured on 2026-11-15 on the hospitals of Lyon (34
  features): overpass.openstreetmap.fr answered in 2 s each time, overpass-api.de answered 502 or 429 twice out of
  three and in 28 s the third. So the first is the default, and a refusal says to ask another server of the list
  rather than the same again. An answer the server cut for its time or its memory (a 200 that ends with a
  remark) is refused, never read as whole.
- A part of an answer is never given as the whole. An answer without its `</osm>` is refused before it is read.
  One GDAL cannot read to its end is refused too, and that is asked after every feature: GDAL tells that it
  could not read further on a call that still gives a feature, then gives those it had read and ends without a
  word (2026-11-15: a file broken at its node 29,990 gave 29,990 features and no error at its end). A redirect
  is not followed: it is said as an address to correct in the Sources tab.
- A key asked cannot take the column of another, whatever its case: a GeoPackage tells no column from another by
  its case. `OSM_ID` replaced the identifier of every feature, and with GDAL 3.4 the layer could not be opened;
  `Building` with `building`, `Name`, `fid`, `geom` are refused the same way, before anything is sent.
- The address of a server the user added never comes back to the model: neither whole, nor by its host name
  (`Host ... not found` named it).
- Checked by `tests/qgis_headless/check_agent_osm.py` in QGIS 3.22, LTR and latest (65 checks; an Overpass server
  of this machine that can be busy, stop short, be cut, redirect or go slow; with `FM_NET=1` the real ones).

### Population (2026-11-15)

"How many people live in Pune", "the density of each district", "the people more than 2 km from a hospital".
`add_population` (`adapters/public_api/population.py`) brings in the people of an area as a raster of people per
pixel, from a population grid the user ticked: `meta_population`, the High Resolution Settlement Layer of Data for
Good at Meta and CIESIN (CC BY 4.0), at 30 m, one VRT over 237 cloud optimized GeoTIFFs on AWS, read by parts.
It covers most countries, not all: China, Russia, Iran and North Korea are left out (measured 2026-11-15).

- People are summed, never averaged. The grid is read on the grid of its source (EPSG:4326, one arc second) and
  made coarser by whole blocks of pixels (3 x 3 by default, about 90 m; 32 x 32 for 1 km), with `resampleAlg=sum`
  and the overviews of the source left out (they are averages). Every total is then exact, in GDAL 3.4 as in
  3.12. Warping to a grid in metres was measured first and left: it cuts pixels at the edges (Lyon at 1 km: 3 % of
  the people lost in GDAL 3.12, 8 % in GDAL 3.4).
- Its answer gives `total`, the people of the rectangle around the area (a boundary is no rectangle: that is
  zonal statistics), grown to whole pixels. The people of polygons (districts, an area around hospitals) are `native:zonalstatisticsfb` with the sum
  (`STATISTICS [1]`), which reprojects the polygons itself; the workflows skill gives the chain, the reprojection
  to the UTM zone before a buffer in metres included.
- 50,000 km2 at most (every pixel of the source is read: about 1 s for 1,000 km2, 10 s for the Gironde), 16 million
  pixels written (coarser beyond, and said). An area where nobody lives is refused rather than added empty.
- Out of the grid is not "nobody". The rectangles of the files of the VRT say where it has data: an area out of
  all of them is refused as not covered (Beijing, Moscow, Tehran, Svalbard), and the share of an area out of them is
  said in the note. A country left out inside the rectangle of a file (the Russian side of the border with
  Finland) still reads as nobody: the grid holds no mark for it.
- What the server sends is checked before it is read: the pixels of the VRT must be those the module counts on (a
  grid moved would make every total wrong without a word), and it may name only GeoTIFF files beside it (a path of
  this machine, a parent folder or an address is refused); a VRT runs no Python (`GDAL_VRT_ENABLE_PYTHON=NO`).
  GDAL 3.1 at least (`resampleAlg=sum`).
- `add_field` and `update_features` now measure `$area` in square metres and `$length` in metres on the ellipsoid,
  whatever the CRS of the layer: a density of a layer in degrees was computed on square degrees, 10 billion times
  too large.
- The numbers are a model of a census and of the buildings seen on satellite images (2015 to 2020 by country): the
  note of the answer says to say so.
- Checked by `tests/qgis_headless/check_agent_population.py` in QGIS 3.22, 3.28 (GDAL 3.4), LTR and latest (38
  checks; a VRT over a GeoTIFF on the grid of the real one, served by parts, with people where the check put them;
  with `FM_NET=1` the people of Lyon and of Pune, and Beijing said not covered).

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
  `use_dock_object` the accessor reads the objects of the dock on the main thread and every one of them is an
  example: peaks and appearance take the best cosine over the examples, the area and shape bounds run over all of
  them (2026-11-13: the last one alone, a small pool, found nothing anywhere; see `docs/SEGMENTATION.md`).
- `render_window` waits for the rendering without user input when it runs on the main thread: a click during the run
  must not start another tool.
- SAM missing: the tool says how the user installs it. The agent cannot install it, on purpose (pip and a download
  of 160 MB after a confirmation in the dock).

## Sources

`core/agent/sources.py` is one list, in the Sources tab of the settings, nothing ticked by default:

- **Open data platforms**: data.gouv.fr, Opendatasoft, national CKAN portals, WFS services (IGN Géoplateforme,
  Géorisques, IBGE, PRG).
- **Géorisques** (2026-11-15), the French natural and industrial risks of the BRGM, one MapServer for two platforms:
  `georisques_wms` draws the flood areas of the territories at risk by return period (`ALEA_SYNT_01_01FOR`,
  `ALEA_SYNT_01_02MOY` for 100 years, `ALEA_SYNT_01_04FAI`), the regulatory zones of the flood plans
  (`PPRN_ZONE_INOND`), the potential flood envelopes, groundwater flooding, clay; `georisques_wfs` has the
  perimeters of the plans and the communes concerned, as data (463 perimeters around Bordeaux; GML, no GeoJSON).
  Their titles say "Surface inondable", so a search for "zone inondable" found nothing: when either is ticked, the
  instructions name the key layers (`system_prompt.platforms_note`). The server draws some layers empty in some
  CRS (the regulatory zones in Lambert-93, the perimeters in EPSG:3857), measured with its own GetMap: QGIS 3.22,
  which asks in the CRS of the layer, then shows nothing of the regulatory zones over a project in Lambert-93.
  Checked by `check_agent_image_services_live.py` (the flood areas of Bordeaux drawn, its plans read).
- **Image services** (`adapters/public_api/image_catalog.py`): WMS and WMTS (IGN Géoplateforme built in, any other the
  user adds). `search_open_data` searches their capabilities as it does for a WFS, `add_service_layer` builds the
  source of the `wms` provider for a layer the service lists (the CRS of the project when the layer has it, else Web
  Mercator; PNG first; its first style) and puts it under the layers. A service that says its requests go to another
  host or port is refused, and so is a layer whose tiles, legend or feature information are elsewhere. QGIS
  reads the capabilities again by itself, so that check alone would hold for the document the plugin was given, not
  for the one QGIS gets: the source also tells QGIS to send its requests to the address of the service
  (`IgnoreGetMapUrl`, `IgnoreGetFeatureInfoUrl`). What is left to the service: where the REST tiles of a WMTS and
  the legends are, as QGIS reads them. `wfs_catalog` reads its links the same way (a document that shows one address
  to XML and another to QGIS is refused; host and port are compared, the same host by http for a service in https
  being the same place, as servers behind a proxy say), but the WFS provider of QGIS has no
  such switch: a service that answers QGIS another document than the one the plugin read is not caught. A service
  the user added by its address (WFS, WMS, WMTS, STAC, geocoder, basemap) goes to the model by its id
  (`sources.model_name`, `platform_aliases`): the address may hold a key. The address is no longer a name, and
  it is never answered: `agent_tools._asked` puts the id back in the `platform` of an answer and in the words of
  a refusal. Not covered: the first 30
  characters of host and path are in the id itself, and a platform of `open_data_domains` in the configuration file
  goes by its address. An image service ticked alone does not open the web to `add_layer`.
- A file added from the web is opened without the style it carries (`LayerOptions.loadDefaultStyle` False in
  `project_control._add_layer`): its expressions would run at the first rendering. A local file keeps its style.
  A path that starts with two slashes of either lean is a share of another machine, refused like `\\\\host`.
- **Place search** (`open_data.geocode_url`, `parse_places`): geocoders that answer GeoJSON points to `q` and `limit`
  (IGN Géoplateforme for France, Photon for the world, any other of that shape the user adds). `find_place` is a
  read: the name the user wrote goes to the geocoder, nothing of the project does; each place comes with the extent
  `zoom_to` takes. A geocoder or a basemap ticked alone opens neither `search_open_data` nor the web to `add_layer`.
- **Databases of QGIS** (`adapters/public_api/database_tables.py`): the PostgreSQL connections stored in QGIS show
  in the Sources tab, read from QGIS each time, nothing ticked. For a ticked one, `list_database_tables` gives the
  names of its tables (schema, table, geometry or not, comment: no row; the schemas of the database itself left out)
  and `add_database_table` adds one as a layer, asked alone in its own words; the source is built by QGIS for a table
  the connection lists, and the address and the credentials never leave QGIS (a model names a connection by an id).
  Tools of the chat alone: the REST API and the MCP servers do not offer them, a caller there holds a key of
  FilterMate, not the databases of the user. A view opens with the first key QGIS proposes, a column of several
  kinds of geometries with the first kind, a table of several geometry columns by the one named. The id of a
  connection follows its name and what it connects to: one made again elsewhere under the same name is not ticked.
  The password QGIS keeps for the connection is in the source of the layer, as when the user adds the table from
  the browser, so it is saved with the project; it never goes to the model. Limits: PostgreSQL only; a connection saved without its credentials
  asks for them in a QGIS dialog, or fails; the list is read on the main thread.
- **Satellite imagery**: STAC catalogs with public GeoTIFFs (Earth Search). `search_imagery` finds scenes, `add_layer`
  opens one through `/vsicurl/` without downloading it. Planetary Computer and Copernicus need signed or authenticated
  asset links, so they are left out for now.
- **OpenStreetMap** (`core/agent/osm.py`): two Overpass servers (openstreetmap.fr, overpass-api.de), and any
  the user adds by its address (named to the model by its id, as its address may hold a key). `add_osm_features`
  is offered only when one is ticked; ticked alone it opens neither `search_open_data` nor the web to `add_layer`.
- **Elevation** (`core/agent/elevation.py`): Copernicus DEM GLO-30, worldwide at 30 m, one GeoTIFF per square
  degree in a public bucket of AWS, read by parts and without an account. `add_elevation` is offered only when
  it is ticked (listed with the satellite imagery); a model names the source and an area, never an address, and
  the address of a tile is built from whole degrees. Ticked alone it opens neither `search_open_data` nor the web
  to `add_layer`. A surface model: buildings and trees are in it, which the tool says with its answer.
- **Basemaps** (`core/agent/basemaps.py`): XYZ tiles (OpenStreetMap, Carto, IGN Plan and aerial photographs through
  the WMTS of the Géoplateforme, Google Satellite, OpenTopoMap) and any XYZ address the user adds. `add_basemap` puts one under every
  layer after asking its server for a tile (where the map is, then a quarter of the world: a server of one country
  has none for the world). A model names a basemap of the list, never an address: one the user added goes by its id
  (`sources.model_name`), since its address may hold the key of an account. A basemap ticked alone does not open the
  web to `add_layer`. Limits: an address the user adds is https on port 443, without a comma, and gets zoom 19 at most.
- **MCP connectors** (`core/agent/mcp_client.py`, `adapters/agent/mcp_connection.py`): any Streamable HTTP server, public
  https or on this machine. Their tools join the conversation as `mcp_<server>__<tool>`, bounded in number and size.
  A plugin starts no process: a stdio-only server has to be run in HTTP mode by the user, as IGN's geocontext can be.

Rules: in the chat, only what is ticked can be used (REST and MCP callers hold the API key and are not limited by the
ticks); a connector alone does not let `add_layer` read the web; a WFS layer must be listed by the service, which must keep
its operations on its own host, and its URI is built by the plugin; every connector call stays in the thread; a connector
tool is a call outside even when the server declares it read-only (asked at every level, refused at advisor); a call is sent once, again only when the server lost the session; a server
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
    python scripts/agent_request_weight.py     # what every tool weighs in a request of a local model
    python scripts/agent_request_weight.py --conversation   # what a conversation of ten requests costs, call by
                                                            # call, against the reference before the token diet

A description is read at every request. With every tool offered to a local model (the families off), the
instructions and the tools must hold in the 32k context Ollama is asked for: beyond, it asks for 64k, which
doubles the memory of the model. No model is sent what only checks an argument (`maxLength`, `minLength`,
`maxItems`, `minItems`, `additionalProperties`, `title`), an empty default or a bound beyond a million, and an
optional value (`anyOf` a type or null) is written as its type (`core/agent/tool_schema.for_model`; Ollama only
until lot 2 of the token diet, 2026-11-16): the plugin checks every call against the whole schema of the catalog
and takes its defaults from it, so nothing is lost. On 2026-11-15, 71 tools and the instructions
weigh 94,343 characters for 100,352 at most: about 6,000 characters are left. A test fails when the step is
passed (`test_ollama_provider.py`).

That measure is the tools and the instructions alone. The notes about the sources ticked come on top, and are
written by the chat controller, which needs QGIS: measured on 2026-11-15, 864 characters for a basemap, a
geocoder, an elevation source, an OpenStreetMap server and a population grid, 2,086 with one source of every kind
ticked: still under the step with the families off. With the families on (the default), a request is far under
it. The conversation itself is not weighed either.

### Only the tools a request needs (token diet, lot 1, 2026-11-16)

With the option on (the default, key `offer_tools_by_task`), a request carries the core of the tools
(`core/agent/families.py`, `CORE`: describe_layer, field_values, layer_statistics, preview_filter, apply_filter,
cross_filter, clear_filters, zoom_to, set_layers_visibility, export_layers, undo_agent_step, ask_user, load_skill,
use_tools). The instructions end with an index, one line per other tool of the conversation (`ToolSpec.summary`,
`core/agent/tool_index.py`); `use_tools` adds the tools named, at the end of the list, and a skill loaded still brings
its own. A tool added and not called for 3 requests leaves the request at a compaction only (the cache is lost then
anyway), and use_tools may add it again. The option off offers every tool, without index nor use_tools; the filtering
tools of a local model stay as they are. The core was chosen on the conversation of
`scripts/agent_request_weight.py --conversation`: 9 tools only cost more (each added tool rewrites the cache of
Anthropic), these 14 cost 36 % less than the 25 offered before, with a largest request 39 % smaller.

The catalog is JSON because that server needs pydantic and the MCP SDK, which QGIS does not have. A test fails when the
two disagree. The chat leaves out `undo_filter`, `redo_filter` and `filter_status`: the first two only walk the dock's
history, which is not what the agent did.

Counts (2026-11-12): 47 tools in the catalog; the chat offers 61 at most (the catalog without those three, plus the 7
tools of the plugin's own settings, profiles and skills, plus 10 of its own: `undo_agent_step`, the notes,
`run_pyqgis`, `view_map`, the widgets, the recipes and `show_settings_link`, some only under their setting); the MCP
server of the plugin serves 53 (the chat's tools without its own, plus `map_image` and `contact_sheet`).

- **Layers of the same name** (`agent_tools._one_layer_per_name`): a call of the chat or of the MCP server of the
  plugin that names a layer by a name several layers have is refused with their ids. Each tool used to pick one its
  own way (the first vector one, the first of the kind wanted, the first of any kind), in no order the user sees.
- **`set_layer_style` mode `keep`**: the opacity alone; every other mode replaces the style. An image drawn by its
  service (WMS, WMTS, tiles) takes no other mode: it has no band value to stretch.

### Shorter tools and instructions (token diet, lot 2, 2026-11-16)

The fixed part of a request with the default settings (the instructions with the index, and the tools of the core)
went from 32,491 (30,941 once the light form of the schemas was sent to every provider) to 19,966 characters
(`test_tool_weight.py` bounds it under 20,000). The light form keeps a bound that guides a call (a length of 100 at
most, a number of items of 20 at most that is not the size of an enum, the schema of the values of a map) and drops the
guards; `test_tool_constraints.py` keeps a snapshot of what every tool accepts, so that a rewritten description never
takes a constraint with it. A description says what the tool does,
what it returns and the rule that avoids a frequent mistake; examples and rare cases live in the skill of the task
(the derivatives of a DTM in `terrain`, the objects drawn in the dock and `segments` in `raster-objects`). A tool weighs
2,000 characters at most as the model reads it, except cross_filter (3,500) and set_layer_style (3,200), whose schemas
alone weigh 1,687 and 1,464. The summaries of the index are 60 characters at most, and the sources not ticked are one
paragraph (`chat_setup.MISSING_SOURCES`). The conversation of the bench: cost 257,561 -> 184,870, largest request
47,659 -> 35,602.

### The fields of the active layer (2026-11-17)

The state of the project sent with a request names the fields of the active layer (40 at most, names only, never a
value), and a later request says them again when the active layer changes (`core/agent/project_summary.py`). The
quality gate of the token diet found that qwen3:8b, given the state without them, wrote a field it had guessed in 11
runs of 12 of `narrow_with_and` (`dep`, `department`, `code_dep` for `dept`); with them, the right field in 3 of 3.

### The start of a request stays the same (token diet, lot 4, 2026-11-16)

Each provider's cache serves the start a request shares with an earlier one. The instructions are the way of working,
then the index, then what a setting says (values not shared, sources ticked or not, connectors): nothing that depends
on a setting comes before what does not. The tools a setting brings or changes (`chat_setup.SETTING_TOOLS`: the sources,
the expert mode, the values shared, load_skill and the skills it lists) come after the others, and a tool added by use_tools or load_skill goes at the end. Anthropic gets a
second breakpoint at the end of the instructions (the tools come before them), next to the automatic one at the end of
the request: the tools and the instructions are read again after a compaction rewrites the history (unless that
compaction takes out tools added and left unused, which then costs one write of the cache), and by the next
conversation of the same settings within the five minutes of the cache (19,539 characters of its first request on the
bench). Ollama keeps the largest `num_ctx` of a conversation: a smaller one after a compaction would load the model
again. `agent_request_weight.py --conversation` fails when, between two calls of one request with the same tools and
the same `num_ctx`, a provider's cache does not serve the whole call before. A tool added still costs Anthropic its
cache: the tools come first in its request.

### The options of the panels (2026-11-16)

`layer_options` / `set_layer_options` read and set, per vector layer, what EXPLORING shows (the three selection
expressions, the active mode, tracking, linking) and the FILTERING options of the layer; `export_options` /
`set_export_options` read and set the EXPORTING options of the project. The keys and values allowed are in
`core/agent/panel_options.py`; `adapters/public_api/panel_options.py` writes them the way the panel does (the dict of
the dock, then `settingLayerVariable` or `settingProjectVariables`, then the widgets when they show that layer), all or
none. They need the panel open, refuse a protected layer, are of the class *project* and are undone with the turn
(`layer_options` and `export_options` effects of `adapters/agent/turn_effects.py`, left as they are when the user
changed them since). The skill `panels` brings them (families of tools): they do not weigh on the first request.

### Settings of FilterMate and skills (2026-11-12)

`describe_settings`, `get_setting`, `change_settings` and `diagnose_performance` work on FilterMate itself, not on the
project; `load_skill` loads the instructions of a task. They are declared in `core/agent/tool_catalog.py`
(`SETTINGS_TOOLS`, `SKILL_TOOLS`), served by the chat and the MCP server of the plugin, not by the REST API.

- The settings are the leaves of `config/config.default.json` under `APP`, hidden ones left out
  (`core/agent/settings_reference.py`); the values come from the configuration in use. A name and local paths
  (`PRIVATE`) are only said set or empty. `knowledge/SETTINGS_REFERENCE.md` is generated from the same rows
  (`scripts/export_config_reference.py`, checked by a test).
- `change_settings` is all or none: each value is checked against the choices, bounds and type of its setting. It
  refuses the section `APP.OPTIONS.AGENT` (an agent never widens what it may reach) and the private values; the settings
  dialog of the agent is not reachable at all. The panel applies a change as an edit of the configuration tree would
  (`ConfigModelManager.apply_settings`): the theme, the profile, the action bar, the language, the layer kinds and the
  timers follow at once; undoing the turn puts the values back, except a setting the user changed since.
- Permissions: asked at every level, *Advisor* included (the user reads each setting before and after); at the
  *Autonomous* level, a change of `APP.DOCKWIDGET` alone (how the panel looks, `FEEDBACK_LEVEL` aside) runs without a
  question. Always allow (tab Tools) works above Advisor; Yes for this conversation is not offered: each change is shown.
  A call that would change nothing, or that the tool refuses, is not asked. A recipe never keeps a change of the
  settings.
- In the chat, a change of the settings that the level asks is proposed in the thread: a card lists every setting
  before and after (and what a profile leaves out), with Apply and Cancel, and the tool answers `proposed` without
  changing anything. Apply applies exactly what the card shows, as a step of the history of its own (Undo takes it
  back), and is refused when one of those settings changed since; the next request tells the model what the user
  chose. Another application (MCP) and the question for several actions of a turn keep their dialog; the plan shown
  there is frozen, and a profile changed on disk since is refused.
- Undo: the value "after" is what the agent applied (a value the user set meanwhile stays theirs); back to before a
  step of the turn restores the settings changed from it.
- `show_settings_link` (chat only, read-only) puts a button in the thread that opens a tab of the settings of the
  agent or selects a setting in the configuration tree: the agent shows what it may not change.
- Profiles (`core/agent/settings_profile.py`): `export_settings_profile` writes the settings changed from their
  default, never those the agent may not change, to `profiles/` of the export folder (asked like a file; an existing
  profile is replaced only with `replace`); `apply_settings_profile` applies one by its name from that folder only
  (never a path the model gives: a share or a probe of the disk), 40 changes at most, each shown, and lists what it
  left out.
- `diagnose_performance` sums up the `⏱` lines of the end of `logs/filtermate.log` (`core/agent/performance.py`).
- Skills: one folder each in `skills/` of the plugin, `SKILL.md` (header of an Agent Skill plus the fields of
  FilterMate under `metadata`, then the instructions) and `evals.json` (its cases for the bench); the standard is
  `skills/README.md`, checked by `tests/unit/agent/test_skills_standard.py`, read by `core/agent/skills.py` without
  YAML. `configuration` says how to find, explain and change a setting, what never to change, and how to read the
  timings of a slow filter. The MCP server of the plugin serves the skills of audience `mcp` as prompts
  (`filtermate_configuration`) and the settings reference as the resource `filtermate://settings/reference`;
  `skills/export/filtermate-<name>/SKILL.md` is the same text as an Agent Skill for an application connected to it
  (`scripts/export_agent_skills.py`, checked by a test; not in the plugin zip).
- Skills of the work itself (2026-11-14): `workflows` gives the short chain for a request of several steps (near or
  inside something, around a place, several criteria, a count by category, a thematic map, data fetched then
  filtered) and what makes a turn cost less (read once, one call for several layers, a filter rather than a layer);
  `cartography` says how to choose a style from the data (the mode from what the field holds, the method from
  `layer_statistics`, the ramp from what the values mean); `analysis` lists the Processing algorithms whose id is
  the same from QGIS 3.22 to 4.3 and that the rules let run (read in each of them with `describe_algorithm`), so the
  model skips `find_algorithms` for them. `find_place` is in the index (lot 1 of the token diet; it was always
  offered before). Not measured with a real model: the cases of the three skills pass offline only.
- Processing in QGIS 4: the size of a pixel of a heatmap (`heatmappixelsize`, 4.2) and of an interpolation
  (`interpolationpixelsize`, 4.3), and the rows of an interpolation (`interpolationdata`, 4.3), have types of their
  own there; unknown to `processing_policy`, a heatmap was refused in 4.2 and the interpolations in 4.3. The rows
  are written again by FilterMate under either name (`INTERPOLATION_TYPES`).

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

A web service is not read by any of them, but for `sample_features`: a few features of what the map shows (the
extent of the map as the filter rectangle, 20 at most, no expression nor selection), which its server was already
asked to draw it: a layer unchecked or out of its scale range is refused; never the layer as a whole. Measured
with a WFS server that counts what it sends (`check_agent_wfs_sample.py`, QGIS 3.22, 3.44 and 4.3): one request,
in the extent of the map, with COUNT of the limit plus one; the server sends four features for a sample of three. The answer says so in `scope`.

Processing (`adapters/public_api/processing_tools.py`, rule in `core/agent/processing_policy.py`):

- `find_algorithms` and `describe_algorithm` list only what may run; `run_algorithm` runs it on layers of the project;
- what may run is a list of what is accepted: the providers `native` and `qgis` (GDAL, GRASS, SAGA, PDAL, scripts
  and models start other programs or run code nobody here has read), and an algorithm that makes at least one layer
  or only answers values (statistics). Selection, style, projection, index, truncation, import into a database,
  upload and download make no layer: that alone leaves them out. Executors of SQL or Python, the network
  requests that make a layer and the geocoder that sends addresses to Nominatim are refused by name. The types of
  parameters are a list of what is accepted too (`GIVEN_TYPES`): layers, extent, point, CRS, expression, option, the
  rows of an interpolation, and plain values (numbers, texts, fields, flags, tables, colours, dates, ranges, WKT,
  bands, dataset groups). Any other type (a file, a folder, a database connection, a layout, a map theme, a PROJ
  operation, which names a grid by path or URL, or a type of a later QGIS) refuses the algorithm when it is required
  and stays unset when it is optional; `describe_algorithm` lists it in `left_out`;
- inputs are layers of the project, never a path, a URI or a URL (QGIS would open them); an extent, a point or a CRS
  is numbers, an authid or a project layer. The rows of an IDW or TIN interpolation (`idw_interpolation_data`,
  `source::~::value source::~::field index::~::source type` joined by `::|::`, whose source QGIS opens from its text)
  are written again, each source the id of a vector layer of the project and the rest integers. Expressions go through a list a little wider than the one of
  `select_features` (math, text, geometry functions that only compute; nothing that reads another layer, a file or
  the environment, and no `eval`). Raster calculator expressions have their own parser and are not checked;
- each layer an algorithm makes is written to a temporary file (GeoPackage, GeoTIFF) and added to the project: the
  turn checkpoint sees it as added, so undoing the turn removes it and redoing it opens the file again. A temporary
  file goes when QGIS closes; `export_layers` keeps a layer;
- it runs in a `QgsProcessingAlgRunnerTask` while the event loop turns, busy for the other operations, and Stop
  cancels it. An algorithm flagged `NoThreading` (geometry checks) holds QGIS while it runs;
- without attribute values shared, what an algorithm answers besides its layers (statistics) is left out.

Style (`adapters/public_api/layer_style.py`): `set_layer_style` (vector: single, categorized on a field of 100 values
at most, graduated in 2 to 12 classes by quantile, equal interval, Jenks, pretty breaks or standard deviation, or
`rules`: 20 rules at most, each a condition held to the list of `select_features`, a color and a legend name, one
of them with no condition for every other feature; a feature is drawn by the first rule it matches (QGIS draws it
with every rule it matches: each rule is written to leave out what the rules before it took);
raster: pseudocolor or gray stretch of a band, its range read from the statistics of the band or given, never read
from a web service) and `set_labels` (a field, or an expression held to the list of `update_features`; size, color, halo, the scale
from which they show; or off; what is kept in a style is computed for every feature at every drawing, so `rpad`,
`lpad`, `format_number`, `buffer` and numbers of ten digits are refused there), with a ramp of the style of QGIS and an
opacity. The answer says how many classes were made, never their values. Before the first call of a turn on a layer,
the turn checkpoint keeps its symbology, labels and rendering as XML (`exportNamedStyle`), and undoing the turn puts
them back (`importNamedStyle`); redoing it applies the new style again.

Official styles (`adapters/public_api/style_presets.py`, `core/agent/style_presets.py`): `list_style_presets` and
`apply_style_preset` draw a layer of the BD TOPO of IGN (styles `classique`, `routier`, `bati`, `hydrographie` of the
Géoplateforme, Licence Ouverte 2.0) or of OpenStreetMap (the layers of `add_osm_features`, style VersaTiles colorful,
CC0) as its producer draws it. `scripts/build_style_presets.py` (Docker, QGIS) converts the MapLibre styles with
`QgsMapBoxGlStyleConverter` into a QML per table (`resources/styles/<family>/<dataset>/<style>/<table>.qml`): a
rule-based renderer drawn in the order of the style (symbol levels), a line on an area made its outline, the zoom
range of each class as a scale range (zoom z shown from 1:559,082,264/2^(z-0.5) to 1:559,082,264/2^(z+0.5), as QGIS
draws vector tiles), `@vector_tile_zoom` computed from `@map_scale`, rule-based labels; the OSM filters of the
Shortbread schema rewritten on the columns of `add_osm_features` (`highway`, `railway`, `waterway`, `landuse`,
`natural`, `leisure`, `building`, `admin_level`). `resources/styles/manifest.json` lists each table with its geometry,
the fields its style reads and those that tell it apart. A layer fits a table by its name (or the table of its source)
or its fields, never without the fields the style reads; the variants `gris` and `sombre` are computed in OKLab from
the colours of the QML when it is applied. The categories Symbology, Labeling and Rendering are loaded, undone with
the turn as `set_layer_style`; refused on a protected layer. Bench: `tests/qgis_headless/check_agent_style_presets.py`.

`apply_filter` and `preview_filter` take the same plain clauses through REST and both MCP servers: a subquery or a function
outside the list answers 400. A filter still reaches the database with the rights of the user, so an external agent exposed to
untrusted data is best run with a database role that cannot write.

## Where the time of a request goes

    docker run --rm -v "$PWD":/src -e QT_QPA_PLATFORM=offscreen qgis/qgis:ltr \
        python3 /src/tests/qgis_headless/measure_agent_operations.py

`tests/qgis_headless/measure_agent_operations.py` plays requests through the chat as a user sends them (the
controller, the engine, the undo point, the tools) on a project of 300 000 points, 60 000 polygons and a score of
small layers, against a local server that answers scripted turns at once: what is timed is FilterMate. Each request is
played three times and the fastest is told (one run says little); `FM_MEASURE_PROFILE=1` names the functions that
cost most, and triples the cost of every Python loop, so it is never left on to compare times. The plugin must be
able to write its log, or each line logged costs a traceback: copy the checkout in the container first.

Measured on 2026-11-14 (QGIS 3.44, times in the tools):

- What surrounds the tools costs nothing to speak of: the undo point under 0.01 s a call with 23 layers, the panel
  under 0.1 s a request. The time of a request is the model's, then the tools'.
- An attribute filter on a GeoPackage read the features it keeps three times: the trial `preview_filter` makes, the
  trial `apply_filter` makes itself, the count after it. `feature_count` keeps a count for the file as it is, but from
  QGIS 3.28 a layer opened to be written switches a GeoPackage to its write-ahead log and back, which rewrites the
  header of the file: the trial copy did so, then setting the filter, and no count kept ever answered. The trial
  copy is now opened read-only (`forceReadOnly`: it changes nothing in the file), and its count is kept for the layer
  once the filter is set (`note_trial`, `adopt_trial`, within 3 s, for the same table and filter).
- A plain condition is read by batches (`GetArrowStream`, GDAL 3.10 and later) rather than feature after feature
  from Python: 270 000 features in 0.03 s against 0.31 s. A filter with LIMIT, ORDER BY, GROUP BY or a query of its
  own stays feature after feature: by batches GDAL leaves those words out and counts more than QGIS reads.
  `check_gpkg_feature_count.py` compares both ways and what QGIS reads on twenty filters.
- With both: a filter that keeps 60 000 addresses of 300 000, tried then applied, 0.50 s to 0.08 s; one that keeps
  270 000, 1.42 s to 0.24 s. The count after a filter in the dock, the list of layers and the widgets read the same
  way.
- Not gained: `layer_statistics` (0.6 s for 300 000 features, of which 0.35 s is the provider handing them over;
  summing them up in one go was tried and brought nothing) and the spatial filters (0.05 to 0.5 s, mostly QGIS
  setting the filter of the target).

## Evaluation bench

    python scripts/agent_eval.py                                        # scripted model, free, tests the bench itself
    FILTERMATE_AGENT_API_KEY=... python scripts/agent_eval.py --live \
        --provider anthropic --model claude-haiku-5-5                    # real model, costs money

107 cases in French and English (69 shared, the others with the skills), on a simulated project with attribute, spatial, raster, LiDAR, open data, export and
read-only requests, and one attribute value holding a prompt injection. A case is scored on the filters finally applied.
It is what decides whether a model, in particular a local one, is good enough to offer. `--json` writes, for each case, the tools called and their
arguments (on the simulated project, no data of a user), to read a failure without running it again.

The simulated project keeps what each change did, as QGIS does: `filter_state` and `list_layers` show the filters
applied, `map_context` the selections. A case states what its request takes for granted in `setup`, such as a layer
already filtered or a road selected. Without that, a model that checks its work sees nothing and rightly tries again.

| Run (2026-11-10) | Result |
|---|---|
| Claude Haiku 5.5, direct | 39/39, about 0.09 $ estimated from the token counts |
| Claude Haiku 5.5, direct, 63 cases, 41 tools (2026-11-11) | 58/63; the 5 failures read one by one: 4 came from the bench (a simulated cross filter that dropped the filter it was combined with, a layout and a zoom counted as changes of layers, an edit by selection not accepted), 1 from the model (a favorite applied a second time by hand, a line of the prompt since); those 5 cases again: 5/5 |
| Claude Haiku 5.5, direct, 68 cases, 47 tools (2026-11-11, main 9c065293) | 66/68, about 0.33 $ (1.9 M tokens written to the cache, 6.3 M read, 55 k out); the 2 failures came from the bench: `field_computed` (the simulated layer did not get the field `add_field` added, so the model saw it empty and filled it again with `update_features`; its first call was right, with a formula guarded against 0 floors) and `theme_save` ("keep the view as Relief": a bookmark is as right as a map theme since bookmarks exist; both accepted now, and `theme_named` asks for a map theme by name); those cases again: 3/3 |
| Claude Haiku 5.5, direct, 82 cases, A/B of the skills (2026-11-13) | the prompt of 5.1.0, every domain in it: 80/82; the prompt with analysis, cartography, editing, raster-objects and open-data taken out into skills (`--prompt skills`, about 1,000 tokens lighter): 77/82, with load_skill called 16 times against 7. One run each, within the noise (cross_nothing_kept fails now and then), so the prompt of 5.1.0 stays. Two new cases were too strict for both: a scale reached with zoom_to on an extent (as right as code: a tool first), and a deletion read as hiding (the prompt now says it is the data). About 0.8 $ for both |

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

- The tools of the chat but its own (history, notes, expert code, `view_map`, widgets, recipes), plus `map_image` and
  `contact_sheet`, under the same Sources ticks and the same "attribute values" option. External connectors are not relayed.
- Same SQL allowlist and same confirmations (export, adding or removing a layer), under the name of the application that asks.
- One change is one step of the history of the panel, and shows in the thread with the name of the application.
- A change is refused while the chat is working or while a QGIS dialog is open; reads go on.
- After a refusal, the same tool from the same client is declined for 20 s without a new dialog. A confirmation that comes after
  the client left does nothing.
- Two tools are this server's alone (`MCP_ONLY` in `core/agent/tool_catalog.py`, `adapters/public_api/map_images.py`):
  `map_image`, a JPEG of the map as the user sees it (or of an extent), and `contact_sheet`, the objects of a layer cut out of a
  raster tile by tile, numbered, outlined in red, with tile E an example. Their image goes beside the JSON as an MCP `image`
  block (`ToolResultPart.images`, `WithImages`); the chat never offers them, so no image of the map reaches the provider of the
  chat (decided with the user, 2026-11-11). They are read-only and marked open world: each one shows in the thread, unconfirmed.
  A model judging the proposals of the similar objects on such sheets did not sort them better (`docs/SEGMENTATION.md`).

Access rules, in `core/agent/mcp_server.py`: loopback only, a `Host` of this machine, no `Origin` from elsewhere, a Bearer token
compared in constant time, `application/json` only, one request per connection, heads of 16 KiB and bodies of 4 MiB at most.
Requests are served one at a time, on the Qt main thread, where the tools have to run.

The token is kept in the QGIS settings, not in the authentication database: reading it at startup must not ask for the master
password, and the client's own configuration holds a copy anyway. **New access token** replaces it.
