# Régime de l'agent, lot 3 : un historique qui ne gonfle pas, moins de données — plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Chaque demande n'envoie de l'état du projet, des notes, des widgets et des données que ce qui a changé ou ce
qui est demandé ; l'historique se resserre d'abord en retirant les anciens résultats d'outils.

**Architecture:** La composition du contexte d'une demande sort du contrôleur vers un module pur
(`core/agent/request_context.py`) qui retient ce qui a déjà été envoyé ; la session demande ce contexte après sa
compaction, complet seulement quand l'historique vient d'être réécrit. La compaction gagne un premier étage qui
raccourcit les résultats d'outils anciens. Les outils de lecture rendent moins par défaut. Le budget d'historique suit
le fournisseur.

**Tech Stack:** Python 3.10+, pytest, banc `scripts/agent_request_weight.py`, QGIS sans écran.

**Spec:** `docs/superpowers/specs/2026-11-16-agent-token-diet-design.md` (« Lot 3 », dont l'ajout « Ne pas tout
envoyer » du 16/11).

## Global Constraints

- Worktree `../filter_mate-wt/token-diet-lot3`, branche `claude/token-diet-lot3`.
- Contexte complet à la première demande d'une conversation et après une réécriture de l'historique (résumé ou
  résultats raccourcis) ; sinon : la liste « Changed in QGIS since your last answer: … » ou la ligne exacte
  `Project unchanged since the last request.` ; notes, widgets, recettes, couches protégées : seulement quand leur
  texte a changé depuis le dernier envoi. Les anciens messages ne sont jamais réécrits pour leur état.
- Raccourci d'un résultat : `(Result of N characters taken out to save room: call <tool> again if needed.)`, l'appel
  gardé ; toutes les demandes sauf les 2 dernières ; seulement quand l'historique dépasse le budget.
- `MAX_RESULT_CHARS = 8000`, la marque `truncated` existante.
- Budget d'historique : fournisseurs distants 60 000 caractères ; Ollama `int((CONTEXT_STEPS[1] - ANSWER_ROOM) *
  CHARS_PER_TOKEN) - partie fixe`, 20 000 au moins.
- Outils de lecture, valeurs par défaut (décidées à la tâche 6, chiffres du banc) : `field_values` 20 (50
  aujourd'hui), `layer_statistics` 10 groupes (20), `sample_features` 3 entités (5) ; `describe_layer` n'écrit l'alias
  que s'il existe et `filterable` que s'il est faux. Chacun garde `truncated` / `more` pour dire ce qui reste.
- Mesure : la conversation du banc change (tâche 2) ; la référence est reprise sur le code de `main`, l'ancienne
  (291 616 / 80 432) notée en commentaire.

## Review Focus

- **Le premier message après une compaction** : contexte complet, sans quoi le modèle ne sait plus quelles couches
  existent — test `test_a_rewritten_history_gets_the_whole_state` (tâche 3).
- **Une demande renvoyée (Réessayer) après une erreur** : le contexte de la demande ratée n'est pas compté comme
  envoyé — test `test_a_failed_request_sends_its_parts_again` (tâche 3).
- **Le modèle rappelle un outil dont le résultat a été raccourci** : rien ne l'en empêche, le nouveau résultat est
  entier — test `test_a_trimmed_result_names_its_tool` (tâche 4).
- **Une nouvelle conversation** : la mémoire de ce qui a été envoyé repart de zéro — test
  `test_a_new_conversation_sends_everything` (tâche 3).
- **Un résultat d'image (view_map)** : le raccourci ne casse pas la règle actuelle des images retirées — test
  `test_images_and_trimmed_results_together` (tâche 4).

---

### Task 1: La composition du contexte, en Python pur, sans changer le texte

**Files:**
- Create: `core/agent/request_context.py`
- Modify: `ui/controllers/agent_chat_controller.py` (`_project_context`)
- Test: `tests/unit/agent/test_request_context.py`

**Interfaces:**
- Produces :
  - `@dataclass ContextParts(summary="", notes="", widgets="", recipes="", protected="", decided="", level="")` ;
  - `compose(parts: ContextParts) -> str` — `"\n\n".join` des parties non vides dans cet ordre (celui de
    `_project_context` aujourd'hui) ;
  - `widgets_part(widgets: list) -> str`, `protected_part(names: list) -> str`, `decided_part(outcomes: list) -> str`
    — les textes que le contrôleur écrit aujourd'hui (« Widgets of the panel (data, made with create_widget): … »,
    « Layers the user protected from the agent … », « Settings changes you proposed, … »), à l'identique ;
  - le contrôleur construit `ContextParts` et appelle `compose` : même sortie qu'avant.

- [ ] Tests : `test_compose_keeps_the_order_and_drops_the_empty` ; `test_the_parts_read_as_before` (attendus copiés des
  chaînes actuelles du contrôleur). FAIL → implémenter → PASS + `tests/unit/ui/controllers` → commit
  `AGENT: the context of a request composed in core`.

---

### Task 2: Le banc : un projet réaliste et des lectures de données, la référence reprise

**Files:**
- Modify: `scripts/agent_request_weight.py`, `scripts/agent_eval.py` (les gestionnaires simulés honorent `limit`)
- Test: `tests/unit/agent/test_agent_request_weight.py`

**Interfaces:**
- Produces :
  - le projet du rejeu : celui de `agent_eval` plus 5 couches vectorielles (`zones_pop`, `points_demande`,
    `cables`, `conduites`, `structures`, 12 champs chacune dont `zone_pop_id`, `status`, `city`), soit 14 couches ;
    2 notes et 2 widgets dans le contexte (`ContextParts.notes`, `.widgets`, via les fonctions de la tâche 1) ;
  - `CONVERSATION` : les 10 demandes d'aujourd'hui, plus 3 lectures — `describe_layer cables`, `field_values cables
    status`, `sample_features points_demande` — placées en 2, 5 et 9 ;
  - `REFERENCE` reprise sur ce code (comportement de `main`) ; l'ancienne en commentaire.
  - `field_values` et `layer_statistics` simulés coupent à `limit` et disent `truncated` ; `sample_features` à `limit`.

- [ ] Tests : les existants mis à jour (13 demandes, empreinte nouvelle), `test_the_bench_project_has_14_layers`.
  `python3 scripts/agent_request_weight.py --conversation` : écart 0,0 % après reprise. Commit
  `AGENT: the weight bench gets a project like a real one, and reads data`.

---

### Task 3: L'état du projet et les parties en différence

**Files:**
- Modify: `core/agent/request_context.py`, `core/agent/project_summary.py`, `core/agent/session.py`
  (`add_user_text`), `core/agent/chat_engine.py` (`send`), `ui/controllers/agent_chat_controller.py`, banc et éval
- Test: `tests/unit/agent/test_request_context.py`, `tests/unit/agent/test_session_and_tools.py`

**Interfaces:**
- Produces :
  - `project_update(layers, selections, view, before) -> str` dans `project_summary.py` : `CHANGES_HEADER` + changements,
    ou `UNCHANGED = "Project unchanged since the last request."` ;
  - `class ContextMemory` : `delta(parts: ContextParts, full: bool) -> ContextParts` (vide notes, widgets, recettes,
    couches protégées inchangés depuis le dernier envoi ; `full` remet tout) ; `sent()` confirme l'envoi ; `forget()` ;
  - `AgentSession.add_user_text(text, context: Union[str, Callable[[bool], str]] = "")` : compacte, puis appelle
    `context(full)` avec `full = (première demande) or self.rewritten` ; `AgentSession.rewritten -> bool` (la
    dernière compaction a réécrit l'historique : résumé ou résultats raccourcis) ;
  - `ChatEngine.send(text, context)` accepte la fonction ; le contrôleur passe
    `lambda full: compose_with_recap(self._project_context(full), recap)` ; `ContextMemory.sent()` à la fin réussie
    d'une demande, rien sinon ; `forget()` à `_restart_engine` ;
  - le banc et `agent_eval.run_case` passent la même fonction.

- [ ] Tests : `test_unchanged_project_is_one_line` ; `test_a_changed_layer_is_listed` ; `test_notes_go_once_until_they_change` ;
  `test_a_rewritten_history_gets_the_whole_state` ; `test_a_failed_request_sends_its_parts_again` ;
  `test_a_new_conversation_sends_everything`. FAIL → implémenter → PASS ; banc : coût et plus grosse requête en baisse ;
  commit `AGENT: each request sends what changed of the project, not all of it`.

---

### Task 4: Les anciens résultats raccourcis avant tout résumé

**Files:**
- Modify: `core/agent/compaction.py`, `core/agent/session.py`
- Test: `tests/unit/agent/test_compaction.py`, `tests/unit/agent/test_session_and_tools.py`

**Interfaces:**
- Produces : `trim_results(messages: Sequence[Message], keep: int = 2) -> Tuple[List[Message], int]` (les résultats des
  demandes sauf les `keep` dernières deviennent `TRIMMED.format(n, tool)` ; rend le nombre de résultats raccourcis) ;
  `TRIMMED = "(Result of {} characters taken out to save room: call {} again if needed.)"` ; la session : au-dessus du
  budget, `trim_results` d'abord, puis `compact` seulement si l'historique dépasse encore ; `rewritten` vrai dans les
  deux cas ; le retrait des outils inutilisés (lot 1) suit `rewritten`.

- [ ] Tests : `test_old_results_are_trimmed_first` ; `test_trimming_enough_summarizes_nothing` ;
  `test_the_last_two_requests_keep_their_results` ; `test_a_trimmed_result_names_its_tool` ;
  `test_images_and_trimmed_results_together`. FAIL → implémenter → PASS → commit
  `AGENT: old tool results go first when the history is too long`.

---

### Task 5: Le budget selon le fournisseur, le plafond d'un résultat

**Files:**
- Modify: `core/agent/session.py` (`history_budget`), `core/agent/tool_executor.py` (`MAX_RESULT_CHARS`), contrôleur,
  banc
- Test: `tests/unit/agent/test_session_and_tools.py`

**Interfaces:**
- Produces : `history_budget(provider_kind: str, fixed_chars: int) -> int` (Global Constraints) ; le contrôleur et le
  banc construisent `AgentLimits(max_history_chars=history_budget(kind, len(system) + taille JSON des outils))`.

- [ ] Tests : `test_a_remote_budget`, `test_an_ollama_budget_leaves_room_in_the_32k_step`, `test_the_result_cap_is_8000`.
  FAIL → implémenter → PASS → commit `AGENT: a history budget per provider; a result of 8,000 characters at most`.

---

### Task 6: Les outils de lecture rendent moins

**Files:**
- Modify: `filtermate_api/mcp/server.py` (valeurs par défaut), `adapters/public_api/introspection.py`
  (`_vector_details`), `core/agent/tool_catalog.json` (régénéré)
- Test: `tests/unit/adapters/...` du module d'introspection (sur le modèle existant), `tests/unit/agent/test_session_and_tools.py`
  (catalogue)

- [ ] Banc d'abord : `--conversation` avec (20, 10, 3) puis (30, 15, 5) ; garder le plus léger sauf si une lecture du
  banc perd ce qu'elle cherchait. Tests : `test_describe_layer_writes_alias_and_filterable_only_when_they_say_something`,
  défauts du catalogue. FAIL → implémenter → PASS ; `agent_eval.py` 116/116 ; commit
  `AGENT: the reading tools return less by default`.

---

### Task 7: Chiffres, QGIS, revue, fusion

- [ ] `--conversation` : coût et plus grosse requête sous la nouvelle référence ; les chiffres par tâche dans la PR.
- [ ] `check_agent_chat.py` (ltr, latest) : la deuxième demande d'une conversation porte « Project unchanged… » quand
  rien n'a bougé.
- [ ] Revue `opus-reviewer` ; corrections ; PR et fusion au fur et à mesure.
