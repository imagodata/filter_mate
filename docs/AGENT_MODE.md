# Agent mode: foundations

Status: step 1 of 4 is in the code. The chat panel does not exist yet and nothing here is loaded by the plugin at start.
For developers of FilterMate.

## Goal

A chat band above FILTERING: the user writes "buildings above 1200 m in the selected commune" and the agent filters.
Any provider, a few free requests through a relay, then the user's own key, and external MCP clients on the same tools.

| Step | Content | State |
|---|---|---|
| 1. Foundations | Neutral conversation, provider adapters, tool catalog, read tools, evaluation bench | done |
| 2. Chat | Panel, Qt transport, key in `QgsAuthManager`, undo of a whole turn | to do |
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

`apply_filter` through REST or MCP is not restricted this way: those callers hold the API key and existing clients may
send subqueries. An external agent exposed to untrusted data should be run with a database role that cannot write.

## Evaluation bench

    python scripts/agent_eval.py                                        # scripted model, free, tests the bench itself
    FILTERMATE_AGENT_API_KEY=... python scripts/agent_eval.py --live \
        --provider anthropic --model claude-haiku-5-5                    # real model, costs money

31 cases in French and English, on a simulated project with attribute, spatial, raster, LiDAR, export and read-only
requests and one attribute value holding a prompt injection. A case is scored on the filters finally applied. It is
what decides the model of the free quota, and whether a local model is good enough to offer.
