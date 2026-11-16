# AI and data

What the AGENT section of FilterMate sends, to whom, and when. Everything else in FilterMate (filtering, exploring,
export, favorites, segmentation) runs on your computer and sends nothing.

## In short

- **No account, no telemetry.** FilterMate collects no usage data and has no server of its own.
- **You choose the model.** Claude, Mistral, OpenAI or any OpenAI-compatible server with your own API key, or a
  local Ollama model. FilterMate never ships or holds a key.
- **Nothing leaves before you agree.** The chat asks for consent the first time you use a provider, and asks again
  when you change the provider or its address.
- **With a local model, nothing leaves your computer.**

## What a request sends to the provider you chose

| Sent | When |
| --- | --- |
| Your message and the conversation so far (older turns summed up past a budget) | Every request |
| The instructions and the list of tools of the chat | Every request |
| A summary of the project: the map extent, the layer tree (names, types, fields, CRS), what changed since the last request | Every request |
| Project notes you asked the agent to remember | Every request |
| Field values: statistics by group, a sample of features, what lies at a point, the values of a field | Only if you allow attribute values in the consent dialog |
| An image of the map | Only with a provider that reads images, and only if you allow attribute values (a map shows its labels) |
| Values already written in your filters and favorites | Every request: the consent dialog says so |

The provider's own terms apply to what it receives: check whether it keeps or trains on your requests.

## What is never sent

- Your API key, except to the server you typed it for. It is kept in the QGIS authentication database, never in a
  settings file.
- Database addresses and credentials: the model names a connection by an id, and the address stays in QGIS.
- Whole layers or files: the agent reads them through QGIS and sends what a tool returns.

## Other network calls, only when you ask for them

- **Public data the agent fetches:** open data portals (behind the "open data" setting), OpenStreetMap through an
  Overpass server you ticked, elevation and population tiles, basemaps. The request names a place or an area, never
  your own data.
- **Downloads after a confirmation:** the segmentation model and its runtime, and portable Git for sharing favorites.
- **The built-in MCP server** is off by default; once on, it listens on your computer only (`127.0.0.1`) and asks for
  an access token.
- **Your own remote layers** (PostgreSQL, WFS, WMS...) are reached by QGIS as usual when you filter them.

## Model in use

The model is the one you pick in the AGENT settings; FilterMate adds none of its own. For details on the providers,
the levels of autonomy and the undo of a turn, see [docs/AGENT_MODE.md](AGENT_MODE.md).
