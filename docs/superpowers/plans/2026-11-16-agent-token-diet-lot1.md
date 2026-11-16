# Régime de l'agent, lot 1 : les outils strictement nécessaires — plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Une requête ne porte que le noyau d'outils et ceux que le modèle a demandés ; les autres sont listés en une
ligne chacun dans les instructions, et `use_tools` les ajoute.

**Architecture:** Le découpage (noyau, outils disponibles, index) est en Python pur dans `core/agent/families.py` et un
nouveau `core/agent/tool_index.py`, partagé par le chat, le banc de poids et le banc d'évaluation. `use_tools` est un
outil du chat qui passe par `ChatEngine.offer_tools` comme `load_skill`. La session retient quels outils ajoutés ont
servi et retire, à une compaction seulement, ceux restés inutilisés trois demandes. Les instructions perdent les
paragraphes qui décrivent un outil un par un ; leur sens va dans la description de l'outil ou dans sa skill.

**Tech Stack:** Python 3.10+, pytest (QGIS simulé), Docker `qgis/qgis:ltr`/`latest` pour le chat sans écran, Ollama
local pour la barrière de qualité.

**Spec:** `docs/superpowers/specs/2026-11-16-agent-token-diet-design.md` (section « Lot 1 », « Ordre et vérification »).

## Global Constraints

- Worktree `../filter_mate-wt/token-diet-lot1`, branche `claude/token-diet-lot1`.
- Noyau offert d'office (décidé ici, chiffré à la tâche 7) : `use_tools`, `load_skill`, `ask_user`, `describe_layer`,
  `field_values`, `preview_filter`, `apply_filter`, `clear_filters`, `undo_agent_step`. `preview_filter` en plus de la
  liste du design : les instructions exigent de tester une expression avant `apply_filter`.
- `summary` : une ligne par outil, 90 caractères au plus, en anglais, sans point final.
- Index : titre « Tools you can add with use_tools » ; une ligne `- <name>: <summary>` par outil offert à la
  conversation mais pas encore dans la requête, dans l'ordre du catalogue ; construit avec les instructions, constant
  pendant la conversation ; 6 000 caractères au plus (test).
- `use_tools(names)` : ajoute en fin de liste, dans l'ordre demandé ; répond `{"added": [...], "already": [...]}` ; un
  nom inconnu de l'index ou refusé par une règle (`RULE_NEVER`) : erreur qui le nomme, rien d'ajouté ; lecture seule,
  sans confirmation ; 20 noms au plus par appel.
- Un outil ajouté reste jusqu'à la prochaine compaction ; à une compaction, sort celui qui n'a pas servi pendant les 3
  dernières demandes (il repasse dans l'index). Le noyau ne sort jamais.
- Un outil retenu appelé quand même : « <name> is not offered yet: call use_tools with "<name>" first. »
- L'option existante (`AgentSettings.tool_families`, clé `offer_tools_by_task`, activée par défaut) devient ce mode ;
  désactivée, tous les outils sont offerts comme aujourd'hui. Libellé : « Offer only the tools a request needs (the
  agent adds the others) » dans les 34 catalogues.
- Le serveur MCP du plugin et les autres applications : inchangés (tous les outils).
- Textes lus par le modèle : anglais, hors catalogues.
- Mesure (`scripts/agent_request_weight.py --conversation`) : le coût estimé et la plus grosse requête baissent ; la
  référence n'est pas reprise dans ce lot.
- Barrière de qualité avant fusion : `agent_eval.py --live --provider ollama --model qwen3:8b --families --repeat 3`,
  référence sur `main` puis sur la branche, aucun cas perdu (`--baseline`). Elle ne tourne pas sur ce portable
  (mémoire « Régime de tokens ») : la fusion attend la décision de l'utilisateur.

## Review Focus

- **Un modèle qui répond « je ne peux pas » alors que l'outil est dans l'index** : les instructions disent de chercher
  dans l'index avant de refuser — test `test_the_instructions_send_to_the_index_before_refusing` (tâche 5) et un cas du
  banc `index_tool_not_refused` (tâche 6).
- **`use_tools` appelé avec un outil qu'une règle de l'onglet Outils interdit** : refusé, rien d'ajouté, la règle nommée
  — test `test_use_tools_refuses_a_tool_turned_off` (tâche 2).
- **La compaction retire un outil au milieu d'une demande qui s'en sert** : jamais ; seule une compaction (au début d'une
  demande) retire, et seulement après 3 demandes sans usage — test `test_a_tool_used_in_the_last_three_requests_stays`
  (tâche 4).
- **Option désactivée** : tous les outils, pas d'index, pas de `use_tools` — test
  `test_families_off_offers_every_tool_without_index` (tâche 3).
- **Un connecteur MCP chargé par `load_skill`** : ses outils `mcp_…` arrivent comme aujourd'hui et ne passent pas par
  l'index — test `test_connector_tools_stay_out_of_the_index` (tâche 3).

---

### Task 1: Les résumés d'outils et l'index

**Files:**
- Create: `core/agent/tool_index.py`
- Modify: `core/agent/tool_catalog.py` (`ToolSpec.summary`, `chat_tools()` les remplit)
- Test: `tests/unit/agent/test_tool_index.py`

**Interfaces:**
- Produces :
  - `SUMMARIES: Dict[str, str]` — une entrée par outil de `chat_tools()` (et `use_tools`), 90 caractères au plus ;
  - `ToolSpec.summary: str = ""`, rempli par `chat_tools()` depuis `SUMMARIES` (`dataclasses.replace`) ;
  - `INDEX_TITLE = "\n\nTools you can add with use_tools (one call with every tool the request needs):"` ;
  - `index_block(available: Sequence[ToolSpec]) -> str` — le titre puis une ligne `- name: summary` par outil, dans
    l'ordre reçu ; "" sans outil ; `MAX_INDEX = 6000`.

- [ ] **Step 1: Tests** — `test_every_tool_of_the_chat_has_a_summary` (chaque nom de `chat_tools()` a un `summary` non
  vide, ≤ 90, sans point final, sans retour à la ligne) ; `test_index_lists_the_tools_in_order` (deux `ToolSpec` →
  `INDEX_TITLE + "\n- a: A\n- b: B"`) ; `test_index_of_every_tool_stays_small` (`len(index_block(chat_tools())) <=
  MAX_INDEX`) ; `test_no_index_without_tool` (`index_block([]) == ""`).
- [ ] **Step 2:** `python3 -m pytest tests/unit/agent/test_tool_index.py -q` → FAIL.
- [ ] **Step 3:** écrire `SUMMARIES` (verbe d'action, ce que l'outil fait, ce qui le distingue de ses voisins : « Filter a
  layer by its relation to another layer (intersects, within, distance) ») et `index_block`.
- [ ] **Step 4:** PASS ; `python3 -m pytest tests/unit/agent -q` sans régression.
- [ ] **Step 5:** commit `AGENT: a one-line summary of each tool, and the index of the tools not offered yet`.

---

### Task 2: L'outil `use_tools`

**Files:**
- Modify: `core/agent/tool_catalog.py` (`USE_TOOLS = "use_tools"`, sa `ToolSpec` dans `CHAT_ONLY`, `read_only=True`),
  `core/agent/families.py`, `core/agent/tool_executor.py` (texte d'un outil retenu)
- Test: `tests/unit/agent/test_families.py`

**Interfaces:**
- Consumes : tâche 1.
- Produces :
  - `CORE = frozenset({...})` (Global Constraints) dans `families.py`, à la place de `ALWAYS` ; `ALWAYS` reste un alias
    déprécié de `CORE` tant qu'un module l'importe ;
  - `split_tools(tools: Sequence[ToolSpec]) -> Tuple[List[ToolSpec], List[ToolSpec]]` — `(offerts d'office,
    disponibles)`, l'ordre du catalogue gardé ; un outil de connecteur (`mcp_…`) reste hors des deux ;
  - `use_tools_handler(available: Dict[str, ToolSpec], offer: Callable[[List[ToolSpec]], None], refused:
    Callable[[str], str] = lambda name: "") -> Callable[[Dict[str, Any]], Dict[str, Any]]` — `refused(name)` rend la
    raison d'un refus (règle `RULE_NEVER`), "" sinon ; retire de `available` ce qu'il offre ;
  - schéma de `use_tools` : `{"names": array de string, 1 à 20, required}` ; description : « Add tools from the index of
    the instructions to the next requests of this conversation. Add in one call every tool the request needs. »
  - `HELD = "{} is not offered yet: call use_tools with \"{}\" first."` dans `tool_executor.py` ; `ToolExecutor.hold`
    garde sa signature, le texte d'un outil retenu devient `HELD` (et nomme la skill quand elle existe :
    « … first, or load_skill with "<skill>" »).

- [ ] **Step 1: Tests** — `test_split_keeps_the_core_and_the_order` ; `test_use_tools_adds_in_the_order_asked`
  (`{"names": ["b", "a"]}` → `offer([B, A])`, réponse `{"added": ["b", "a"], "already": []}`) ;
  `test_use_tools_ignores_what_is_already_offered` ; `test_use_tools_refuses_an_unknown_name` (ToolFailure nommant le
  nom, `offer` non appelé) ; `test_use_tools_refuses_a_tool_turned_off` (`refused=lambda n: "turned off by the user"`
  → ToolFailure, rien d'offert) ; `test_a_held_tool_says_use_tools`.
- [ ] **Step 2:** FAIL. **Step 3:** implémenter. **Step 4:** PASS, `tests/unit/agent` sans régression.
- [ ] **Step 5:** commit `AGENT: use_tools adds the tools a request needs`.

---

### Task 3: Le chat, le banc de poids et le banc d'évaluation dans ce mode

**Files:**
- Modify: `ui/controllers/agent_chat_controller.py` (`_families`, `_build_engine`, `_prompt`),
  `core/agent/chat_setup.py` (`chat_instructions(..., available: Sequence[ToolSpec] = ())` ajoute `index_block`),
  `scripts/agent_request_weight.py` (`default_setup`), `scripts/agent_eval.py` (`run_case` avec `families=True`,
  `ScriptedTransport.load_first`)
- Test: `tests/unit/ui/controllers/test_agent_request_weight_default.py`, `tests/unit/ui/controllers/test_agent_chat_setup.py`,
  `tests/unit/ui/controllers/test_agent_connectors_listing.py`

**Interfaces:**
- Consumes : tâches 1 et 2.
- Produces :
  - option activée : offerts d'office = `split_tools(...)[0]` ; disponibles = le reste ; `load_skill` offre, comme
    aujourd'hui, les outils de sa skill parmi les disponibles (et les retire de l'index pour la suite de la requête :
    l'index, lui, ne change pas) ; `use_tools` offre les autres ; `hold` de tous les disponibles ;
  - instructions = `chat_instructions(..., available=disponibles)` : l'index à la fin, après les notes des sources ;
  - option désactivée : tous les outils, ni `use_tools` ni index ;
  - `ScriptedTransport.load_first(held, skill)` devient `use_first(held, skill)` : avant les étapes, **un** appel
    `use_tools` avec les outils retenus que les étapes appellent (dans leur ordre), sauf ceux qu'apporte un `load_skill`
    que le cas fait lui-même ;
  - `default_setup()` du banc de poids rend le nouveau découpage ; le test de garde qui le compare au contrôleur reste
    la preuve.

- [ ] **Step 1: Tests** — garde contrôleur/banc mise à jour (même découpage, mêmes instructions) ;
  `test_families_off_offers_every_tool_without_index` ; `test_connector_tools_stay_out_of_the_index` (sur le modèle de
  `test_agent_connectors_listing.py`) ; empreintes de `test_agent_chat_setup.py` : celles **sans** index inchangées
  (`available=()`), une nouvelle pour la configuration par défaut avec index (la reprendre à la main après avoir lu
  l'index produit) ; `test_the_starting_request_stays_under_50_kb` : le plafond redescend à 50 000.
- [ ] **Step 2:** FAIL. **Step 3:** implémenter. **Step 4:** PASS ; `python3 scripts/agent_eval.py --families` et sans
  (114/114) ; `python3 scripts/agent_request_weight.py --conversation` : noter appels, plus grosse requête, coût.
- [ ] **Step 5:** commit `AGENT: the chat offers the core and the tools asked for, with the index of the others`.

---

### Task 4: Les outils inutilisés sortent à la compaction

**Files:**
- Modify: `core/agent/session.py` (`AgentSession`), `core/agent/chat_engine.py`
- Test: `tests/unit/agent/test_session_and_tools.py`

**Interfaces:**
- Produces :
  - `AgentSession(..., core: Collection[str] = ())` ; `AgentSession.offer(tools)` retient la demande où chaque outil a
    été ajouté ; chaque appel d'outil accepté (`accept_turn`) note la demande de son dernier usage ;
  - dans `add_user_text`, quand `compact` a résumé au moins une demande : les outils ajoutés (hors `core`) sans usage
    dans les 3 dernières demandes sortent de la requête ; `AgentSession.dropped -> Tuple[str, ...]` les nomme ;
  - `ChatEngine(..., released: Callable[[Sequence[str]], None] = lambda names: None)` : après chaque
    `add_user_text`, si `session.dropped` n'est pas vide, `executor.hold` les reprend (avec leur skill quand elle existe)
    et `released(noms)` est appelé ; le contrôleur y remet les `ToolSpec` dans le dict `available` de
    `use_tools_handler`.

- [ ] **Step 1: Tests** — `test_an_unused_tool_leaves_at_a_compaction` ; `test_a_tool_used_in_the_last_three_requests_stays` ;
  `test_nothing_leaves_without_a_compaction` ; `test_the_core_never_leaves` ; `test_a_dropped_tool_can_be_added_again`
  (par `ChatEngine` : retenu, puis `use_tools` l'offre de nouveau).
- [ ] **Step 2:** FAIL. **Step 3:** implémenter (`MAX_IDLE_REQUESTS = 3`). **Step 4:** PASS, `tests/unit/agent` sans
  régression. **Step 5:** commit `AGENT: tools left unused leave the request at a compaction`.

---

### Task 5: Des instructions sans description d'outil

**Files:**
- Modify: `core/agent/system_prompt.py`, `filtermate_api/mcp/server.py` (docstrings, puis
  `scripts/export_agent_tools.py`), `skills/*/SKILL.md` concernés (puis `scripts/export_agent_skills.py`),
  `tests/unit/ui/controllers/test_agent_chat_setup.py` (empreintes)
- Test: `tests/unit/agent/test_system_prompt.py` (nouveau)

**Interfaces:**
- Lignes retirées de `SYSTEM_PROMPT` (numéros de la sortie de `SYSTEM_PROMPT.split("\n")` au 16/11) et où va leur sens,
  sans rien perdre — vérifier que la destination le dit déjà, sinon l'y ajouter :
  - 5 Processing → skill `analysis` ; 6 `add_field` → skills `analysis`, `editing` ; 7 `group_layers`, 9 styles, 12
    mises en page, 13 CRS → skill `cartography` ; 8 widgets → skill `dashboards` ; 10 terrain → la ligne de `terrain`
    dans `load_skill` suffit ; 11 éditions → skill `editing` ; 14 `run_pyqgis` → skill `pyqgis` ; 15 `view_map`, 16
    notes, 17 recettes, 29 vue/sélection/visibilité/`find_place` → description de l'outil ; 18 configuration → la ligne
    de `configuration` dans `load_skill` ; 24 objets dessinés → skill `raster-objects` ; 30 open data → skill
    `open-data`.
  - Restent : 0, 2-4, 19-23, 25-28, 31-34 (manière de travailler, filtres, sécurité, annulation, questions, données).
  - Ajouts : « The index at the end lists the tools you can add with use_tools: before saying a thing cannot be done,
    look there; add in one call every tool the request needs. » ; « Do not call a read tool when the state of the
    project sent with the request already answers. »

- [ ] **Step 1: Tests** — `test_the_instructions_send_to_the_index_before_refusing` (les deux ajouts présents) ;
  `test_no_tool_described_one_by_one` (aucun des noms `add_field`, `group_layers`, `create_widget`, `set_layer_style`,
  `create_layout`, `set_project_crs`, `run_pyqgis`, `add_project_note`, `save_recipe`, `search_open_data` dans
  `SYSTEM_PROMPT`) ; `test_the_instructions_are_shorter` (`len(SYSTEM_PROMPT) < 7000`).
- [ ] **Step 2:** FAIL. **Step 3:** déplacer, régénérer catalogue et skills, reprendre les empreintes de
  `test_agent_chat_setup.py` (le texte change, c'est voulu ; la PR liste chaque ligne et sa destination).
- [ ] **Step 4:** `tests/unit/agent` (dont `test_skills_standard`, `test_agent_skills`), `tests/unit/ui/controllers`,
  `agent_eval.py` avec et sans `--families` : PASS. **Step 5:** commit `AGENT: the instructions keep the way of working; each tool says what it does`.

---

### Task 6: L'option, ses textes, les cas du banc

**Files:**
- Modify: `ui/widgets/agent_panel.py:1155-1160` (libellé et info-bulle), `i18n/FilterMate_*.ts|.qm`,
  `scripts/agent_eval_cases.json` (un cas), `docs/AGENT_MODE.md` (familles d'outils → ce mode)

- [ ] **Step 1:** cas `index_tool_not_refused` : « Regroupe les routes et les cours d'eau dans un groupe Réseau. » →
  `[[use_tools {"names": {"contains": ["group_layers"]}}, group_layers {"layers": ["routes", "cours_eau"], "group":
  "Réseau"}]]`, interdit `remove_layers` ; `python3 scripts/agent_eval.py --families --case index_tool_not_refused` → PASS
  (le modèle scripté passe par `use_first`).
- [ ] **Step 2:** libellé « Offer only the tools a request needs (the agent adds the others) », info-bulle « Fewer tools
  in each request: a lighter, cheaper request. The agent sees a one-line list of the others and adds those it needs. » ;
  34 catalogues (skill `i18n-pipeline`), test des contextes i18n PASS.
- [ ] **Step 3:** `docs/AGENT_MODE.md` : la section des familles décrit le noyau, l'index, `use_tools`, le retrait à la
  compaction. **Step 4:** commit `AGENT: the option says what it does now; a case of the bench for the index`.

---

### Task 7: Chiffres, contrôle dans QGIS, barrière de qualité

- [ ] **Step 1: Le noyau au banc** — `--conversation` avec le noyau des Global Constraints, puis sans `preview_filter`,
  puis avec `cross_filter` en plus ; garder le plus léger qui ne demande pas de `use_tools` aux demandes 1, 6 et 10
  (filtres attributaires) ; noter les trois résultats dans la PR.
- [ ] **Step 2: Poids** — `python3 scripts/agent_request_weight.py --conversation` : coût et plus grosse requête sous la
  référence (291 616, 80 432) ; partie fixe de départ (instructions + outils offerts) notée, objectif < 20 000 à la fin du
  lot 2.
- [ ] **Step 3: QGIS** — `tests/qgis_headless/check_agent_chat.py` sur `ltr` et `latest` (skill `qgis-headless-bench`) :
  `check_families` adapté (la première requête porte le noyau et l'index ; après `use_tools`, l'outil est offert).
- [ ] **Step 4: Revue** `opus-reviewer` de la branche (Review Focus), corrections en TDD.
- [ ] **Step 5: Barrière de qualité** — sur une machine qui charge `qwen3:8b` à 32k : référence sur `main`
  (`--json main.json`), puis branche avec `--baseline main.json`, `--timeout 900`. Aucun cas perdu : fusion. Ici :
  PR prête, fusion suspendue, l'utilisateur décide.
