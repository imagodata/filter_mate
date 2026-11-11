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
  Checked on GeoPackage (`check_agent_tools.py`) and on a PostGIS table (`check_agent_edits_postgis.py`: the key
  refused, nothing in the table before the user saves, then the values and the point added there with their
  types and CRS) and on a WFS-T layer served by QGIS Server (`check_agent_edits_wfst.py`: the GeoPackage behind the
  server read directly, unchanged until the layer is saved, then holding every change).
- **Layouts** (`adapters/public_api/layouts.py`): `create_layout` adds a print layout to the project (A4, A3, A5
  or Letter, landscape or portrait): a map of the layers checked in the tree or of those given, framed on an
  extent, a layer, the map view or the layers shown, with a title, a legend, a scale bar and a north arrow. The
  user finishes it in the layout designer; undoing the turn removes it (a `layout` effect keeps its XML, redoing
  reads it again). `export_layout` writes one as PDF or PNG into a sub-folder of the export root, never a path
  of the model, and is confirmed by the user like `export_layers`. `map_context` lists the layouts.
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
  MCP-only `map_image` and `contact_sheet`). Offered only with a key of the user (the free quota relay takes no
  image) and when attribute values are shared (a map shows its labels): a decision of the user, 2026-11-11.
  Claude gets the image in the `tool_result`; an OpenAI-compatible server, whose tool messages hold text only, in
  a user message right after. An image goes with the request it was taken in only: before the next request it
  is replaced by a line saying it was there. A model that reads no image may refuse the request.
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

## Levels of autonomy

`core/agent/permissions.py`, plain Python. Each tool falls in one risk class, from what it can break and how it is
undone; the user chooses a level in the Autonomy tab of the settings, which says up to which class a tool runs alone.

| Class | Tools | Undone |
|---|---|---|
| read | every `read_only` tool, open data searches included | nothing to undo |
| view | `zoom_to`, `select_features`, `set_layers_visibility`, `group_layers`, `map_theme`, `bookmark` | with the turn |
| project | filters, style, Processing, layouts, CRS, SAM layers, any other change | with the turn |
| edit buffer | `update_features`, `add_features`, `add_field` | with the turn, until the user saves |
| irreversible | `destructive` tools: `delete_features`, `export_layers`, `export_layout`, `remove_layers` | not always |
| outside | `open_world` changes (`add_layer`, `add_service_layer`, connectors) and `run_pyqgis` | no |

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
  another level. Never for `run_pyqgis`, asked at every run whatever the level.
- The level is read at each call (`ChatEngine(policy=...)`), and sent with each request, after the project summary,
  when it is not `standard` (the system prompt stays constant for the cache).
- An invalid call is never asked nor refused: it runs to answer its mistake.
- The MCP servers keep the `standard` rules (`ToolExecutor.needs_confirmation`): the level is the chat's.
- **Protected layers** (`adapters/agent/protected_layers.py`, kept in the project by their ids, ticked in the Autonomy
  tab): a call that would change one (`permissions.CHANGED_LAYERS`: its filter, style, labels, features, fields, join,
  name, or the layer itself) gets the verdict `PROTECTED`, refused at every level, never turned into a question nor
  allowed for a conversation; in a recipe it stops the replay; the native MCP server answers it the same way. Reading
  one, using it as the source of a cross filter or the table of a join, zooming, selecting or showing it stays
  allowed. Their names go with each request. Not covered: `run_pyqgis` (code, asked at every run) and
  `apply_favorite` (the layer is in the favorite, not in the call).
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
  shared, a source unticked) stops the recipe and says so. Known limit: a step that used a layer an earlier step made
  (the output of `run_algorithm`, `segment_objects`, `add_layer`), by its id, still names the layer of the first run;
  by its name, it finds the first layer of that name.
- The recipes go with each request as data: the name and the tools of each one, never their arguments nor the words
  of the file, so the model can name them or forget one (`remove_recipe`). Keeping or forgetting a recipe through the
  agent is undone with the turn (`("recipes", "", before, after)` in `adapters/agent/turn_effects.py`), unless the
  recipes were changed from the menu since: those are left as they are. From the menu, removing asks first and is not
  a step of the history.
- The MCP servers do not offer these tools: recipes live in the panel of the dock. The model cannot run a recipe.

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

Counts (2026-11-11): 47 tools in the catalog; the chat offers 53 at most (the catalog without those three, plus 9 of its
own: `undo_agent_step`, the notes, `run_pyqgis`, `view_map`, the widgets and the recipes, some only under their
setting); the MCP server of the plugin serves 46 (the chat's tools without its own, plus `map_image` and
`contact_sheet`).

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

69 cases in French and English, on a simulated project with attribute, spatial, raster, LiDAR, open data, export and
read-only requests, and one attribute value holding a prompt injection. A case is scored on the filters finally applied.
It is what decides the model of the free quota, and whether a local model is good enough to offer. `--json` writes, for each case, the tools called and their
arguments (on the simulated project, no data of a user), to read a failure without running it again.

The simulated project keeps what each change did, as QGIS does: `filter_state` and `list_layers` show the filters
applied, `map_context` the selections. A case states what its request takes for granted in `setup`, such as a layer
already filtered or a road selected. Without that, a model that checks its work sees nothing and rightly tries again.

| Run (2026-11-10) | Result |
|---|---|
| Claude Haiku 5.5, direct | 39/39, about 0.09 $ estimated from the token counts |
| Claude Haiku 5.5, through the free quota relay, 3 cases with tools | 3/3 |
| Claude Haiku 5.5, direct, 63 cases, 41 tools (2026-11-11) | 58/63; the 5 failures read one by one: 4 came from the bench (a simulated cross filter that dropped the filter it was combined with, a layout and a zoom counted as changes of layers, an edit by selection not accepted), 1 from the model (a favorite applied a second time by hand, a line of the prompt since); those 5 cases again: 5/5 |
| Claude Haiku 5.5, direct, 68 cases, 47 tools (2026-11-11, main 9c065293) | 66/68, about 0.33 $ (1.9 M tokens written to the cache, 6.3 M read, 55 k out); the 2 failures came from the bench: `field_computed` (the simulated layer did not get the field `add_field` added, so the model saw it empty and filled it again with `update_features`; its first call was right, with a formula guarded against 0 floors) and `theme_save` ("keep the view as Relief": a bookmark is as right as a map theme since bookmarks exist; both accepted now, and `theme_named` asks for a map theme by name); those cases again: 3/3 |

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
