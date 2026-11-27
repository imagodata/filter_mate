---
name: brainstorm
title: Explore and refine a solution together
description: compare options and refine a solution with the user
metadata:
  version: 1
  plugin_min: 5.1.3
  audience: chat
  tools: ask_user, describe_layer, map_context, agent_options, qgis_capabilities, show_settings_link
  requires: ask_user
  risk: read
  trust: builtin
---

# Brainstorm with the user

Turn a vague need into a concrete, reviewable solution. This skill covers workflows, analysis, data sources and
cartographic design. It works without external data sources. A proposal and a selected option are not permission
to change the project or to enable a source.

1. Restate the goal in one sentence, using the conversation and supplied project state. Keep choices the user
   already made. Do not repeat questions answered earlier. Distinguish a requested brainstorm from an explicit
   request to implement: do not make the user repeat an implementation instruction already given.
2. Identify only gaps that change the decision: intended audience, geographic scope, output, constraints or
   success criteria. Ask one short ask_user question at a time, with two or three concrete choices when helpful.
   At most three initial questions; if the context suffices, start with options. Use only offered read tools to
   check relevant local context; never inspect unrelated layers or send private data to an external source.
3. Propose two or three distinct feasible options. Explain their result, main tradeoff and effort in plain
   language, then recommend one with a reason. Separate existing capabilities from ideas needing new development.
   Do not invent datasets, service endpoints, fields, layout items or capabilities. For disabled sources,
   explain the needed setting and offer show_settings_link, without enabling anything.
4. Invite a choice or correction. Refine that option against the user's feedback, preserving the decisions
   already settled. If a choice changes a dependency, state it explicitly. Do not restart the whole interview.
5. End the refinement with a concrete proposal: expected output, necessary inputs, a short sequence of actions
   and a way to check success. Mention a material limitation or unresolved assumption when relevant.

Choosing a design, saying "that looks good", or clicking a brainstorm answer does not authorize writes. Until
the user asks to apply the solution, do not change styles, layers, themes, layouts, project settings or files.
When implementation was explicitly requested, proceed through the current response mode and normal tool
permissions; do not use brainstorming to bypass confirmations or to add another redundant approval loop.
Use the designer skill for an agreed cartographic workflow when offered. A design shortcut only inserts an
editable request: never treat its text as an action already taken.
