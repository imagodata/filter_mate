# Régime de l'agent, lot 2 : des outils plus courts — plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** La partie fixe d'une requête (instructions avec l'index + outils du noyau) passe de 32 491 à moins de 20 000
caractères dans la configuration par défaut, et aucun outil ne dépasse 2 000 caractères tel que le modèle le lit.

**Architecture:** Le catalogue garde ses schémas complets (validation, valeurs par défaut) ; les fournisseurs envoient
au modèle une forme allégée (`core/agent/tool_schema.py`). Les descriptions les plus lourdes sont réécrites à la source
(`filtermate_api/mcp/server.py`, `core/agent/tool_catalog.py`) ; les cas rares vont dans la skill de la tâche. L'index
et les notes de sources des instructions sont resserrés.

**Tech Stack:** Python 3.10+, pytest, bancs `scripts/agent_request_weight.py` et `scripts/agent_eval.py`, QGIS sans écran.

**Spec:** `docs/superpowers/specs/2026-11-16-agent-token-diet-design.md` (« Lot 2 », « Objectifs », « Anti-objectifs »).

## Global Constraints

- Worktree `../filter_mate-wt/token-diet-lot2`, branche `claude/token-diet-lot2`.
- Mesure de référence (main 28b5ae5c, premier appel de `--conversation`) : instructions 10 905, outils 21 586 ;
  conversation : coût 272 678, plus grosse requête 50 424.
- Cible : instructions + outils du premier appel < 20 000 ; chaque outil du chat ≤ 2 000 caractères
  (`json.dumps({"name", "description", "input_schema"})` de sa forme pour le modèle) ; un test les borne.
- Le schéma complet reste celui que `tool_executor` valide et dont il tire les valeurs par défaut : la forme allégée
  n'est que ce qu'on envoie.
- Le serveur MCP du plugin envoie toujours tous les outils ; il reçoit les descriptions réécrites, pas la forme
  allégée.
- Rien de ce qu'un outil fait, refuse ou rend ne change ; aucun texte visible par l'utilisateur ne change (pas d'i18n).
- `agent_eval.py` 116/116, avec et sans `--families`. La barrière qwen3:8b ne peut pas tourner ici (lot 0).

## Review Focus

- **Un argument que la forme allégée ne montre plus** (longueur maximale, borne) : le plugin le refuse toujours avec
  le même message — test `test_the_full_schema_still_validates` (tâche 1).
- **Une propriété facultative à `null`** (`anyOf [X, null]`) : le modèle la voit comme X et peut l'omettre ; s'il
  envoie `null`, la validation complète l'accepte encore — test `test_a_null_option_shows_as_its_type` (tâche 1).
- **Une valeur par défaut qui guide** (`selected_only: true`) reste visible ; seules les vides partent — test
  `test_defaults_that_guide_stay` (tâche 1).
- **Un cas rare retiré d'une description** (objets dessinés d'un raster, dérivée du MNT, segments) : la skill qui le
  porte le dit, et `use_tools` nomme cette skill — test `test_what_left_cross_filter_is_in_a_skill` (tâche 2).
- **Les connecteurs MCP externes** passent par la même forme allégée sans casser leur schéma (bornés à l'entrée) —
  test `test_an_external_schema_goes_through` (tâche 1).

---

### Task 1: La forme d'un schéma pour le modèle

**Files:**
- Create: `core/agent/tool_schema.py`
- Modify: `core/agent/providers/anthropic_messages.py`, `openai_chat.py`, `ollama_chat.py` (sérialisation des outils)
- Test: `tests/unit/agent/test_tool_schema.py`

**Interfaces:**
- Produces : `for_model(schema: dict) -> dict` — retire `title`, `minLength`, `maxLength`, `minItems`, `maxItems`,
  `additionalProperties: false`, les bornes numériques de valeur absolue ≥ 1 000 000, les `default` vides (`None`,
  `""`, `[]`, `{}`) ; `anyOf [X, {"type": "null"}]` devient X (avec la description et le défaut de la propriété) ;
  garde `enum`, `required`, les autres `default`, `minimum`/`maximum` utiles ; récursif ; ne modifie pas l'entrée.
  Les trois fournisseurs envoient `for_model(tool.input_schema)`.

- [ ] Tests : `test_bounds_and_titles_go`, `test_a_null_option_shows_as_its_type`, `test_defaults_that_guide_stay`,
  `test_the_input_is_not_changed`, `test_the_full_schema_still_validates` (une chaîne trop longue refusée par
  `ToolExecutor` comme avant), `test_an_external_schema_goes_through`, `test_each_provider_sends_the_light_form`.
  FAIL → implémenter → PASS ; banc ; commit `AGENT: the model reads a lighter form of each tool's schema`.

---

### Task 2: `cross_filter` et `set_layer_style` réécrits

**Files:**
- Modify: `filtermate_api/mcp/server.py` (docstrings, `Field(description=…)` de ces outils et de leurs modèles
  imbriqués), `core/agent/tool_catalog.json` (régénéré), `skills/raster-objects/SKILL.md`, `skills/terrain/SKILL.md`,
  `skills/cartography/SKILL.md` (ce qui part des descriptions)
- Test: `tests/unit/agent/test_tool_weight.py`

- [ ] Garder : ce que l'outil fait, ce qu'il rend, la règle qui évite une erreur fréquente (source vectorielle :
  sélection, sinon filtre ; `operator` ; `raster_selection` requis pour un raster). Partir vers la skill : les
  exemples, les dérivées du MNT, `segments` et `dock_objects`, les détails par mode de style. Si la forme allégée
  reste au-dessus de 2 000 avec des descriptions d'une ligne, les propriétés imbriquées perdent leur description
  quand leur nom suffit.
- [ ] Tests : `test_cross_filter_and_set_layer_style_weigh_2000_at_most`, `test_what_left_cross_filter_is_in_a_skill`.
  FAIL → réécrire → régénérer le catalogue → PASS ; `agent_eval.py` 116/116 ; commit
  `AGENT: cross_filter and set_layer_style say it shorter`.

---

### Task 3: Les autres outils au-dessus de 1 500 caractères

**Files:**
- Modify: `filtermate_api/mcp/server.py`, `core/agent/tool_catalog.py` (`load_skill`, `ask_user`, …),
  `core/agent/tool_catalog.json`, skills concernées
- Test: `tests/unit/agent/test_tool_weight.py`

- [ ] Liste prise au banc après la tâche 2 (aujourd'hui, forme allégée : similar_objects, geometry_filter,
  segment_objects, load_skill, add_osm_features, point_cloud_filter, apply_filter, create_widget, layer_statistics,
  ask_user, set_labels, create_layout) ; plus les outils du noyau `describe_layer` et `export_layers`. Même règle que la
  tâche 2. `load_skill` : une ligne courte par skill.
- [ ] Test : `test_every_chat_tool_weighs_2000_at_most`. FAIL → réécrire → PASS ; éval ; commit
  `AGENT: the heavy tools say it shorter`.

---

### Task 4: L'index et les notes de sources

**Files:**
- Modify: `core/agent/tool_index.py` (résumés), `core/agent/chat_setup.py` (notes « not available »),
  `core/agent/system_prompt.py` si une règle y redit une description
- Test: `tests/unit/agent/test_tool_index.py`, tests de `chat_setup`

- [ ] Résumés de l'index ≤ 60 caractères ; les notes des sources non cochées en un seul paragraphe qui les nomme toutes
  avec leur outil et la conduite commune (le dire, `show_settings_link` cible `sources`, ne jamais deviner de
  coordonnées) ; chaque source garde ce qui lui est propre (sous quel onglet la cocher).
- [ ] Tests : `test_index_summaries_are_short`, `test_the_unticked_sources_are_one_paragraph` (chaque outil nommé une
  fois). Commit `AGENT: a shorter index, the sources not ticked in one paragraph`.

---

### Task 5: La borne, les chiffres, QGIS, revue, fusion

- [ ] `test_the_fixed_part_is_under_20000` (instructions + outils du noyau de `default_setup`, forme allégée).
- [ ] `--conversation` : nouvelle référence si le coût baisse ; chiffres par tâche dans la PR.
- [ ] `check_agent_tools.py` et `check_agent_chat.py` (ltr, latest).
- [ ] Revue `opus-reviewer` ; PR ; fusion au fur et à mesure ; suivi de revue en PR séparée.
