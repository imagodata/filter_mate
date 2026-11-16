# Fournisseurs, sources et MCP depuis l'agent — plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cocher une source, un connecteur, le serveur MCP ou changer de fournisseur configuré d'un clic dans le menu
« ⋯ » du panneau AGENT, ou en le demandant à l'agent (désactiver sans question, activer avec l'accord de
l'utilisateur).

**Architecture:** Le cœur pur (`core/agent/agent_options.py`) décrit les options et vérifie un changement ; les
réglages (`adapters/agent/settings.py`) gardent la liste des fournisseurs configurés ; le contrôleur applique un
changement par un seul chemin (`apply_agent_options`), tout de suite pour un clic, à la fin de la demande pour l'agent ;
le panneau ajoute trois entrées au menu « ⋯ » ; trois outils du chat passent par le même chemin.

**Tech Stack:** Python 3.10+, PyQGIS (Qt5/Qt6), pytest, QGIS sans écran (skill `qgis-headless-bench`), `lrelease`
(skill `i18n-pipeline`).

**Spec:** `docs/superpowers/specs/2026-11-16-agent-quick-options-design.md`

## Global Constraints

- Worktree `../filter_mate-wt/agent-quick-options`, branche `claude/agent-quick-options`.
- Outils : `agent_options` (lecture), `turn_off_agent_options`, `turn_on_agent_options` ; chat seulement
  (`CHAT_ONLY`) ; apportés par la skill `configuration` ; résumés dans `core/agent/tool_index.py`.
- `turn_on_agent_options` est dans `permissions.SETTINGS_TOOLS` (demandé à chaque niveau, seul).
  `turn_off_agent_options` : classe PROJECT, sans question aux niveaux standard et autonome.
- Jamais par l'agent : clé, accord d'envoi, autonomie, règles des outils, fournisseur non configuré.
- Un changement de l'agent s'applique quand sa demande se termine ; l'outil répond `{"applies": "after this request",
  ...}` ; un autre fournisseur : `"applies": "in a new conversation"`.
- Fournisseurs configurés : clé de réglage `agent/providers` (JSON), 8 au plus, le plus récent d'abord ; une entrée =
  `preset, model, base_url, authcfg, consent_target, key_target` ; ajoutée ou remontée à chaque enregistrement d'un
  fournisseur dont l'accord est coché.
- Textes visibles : contexte `AgentPanel` (menu) et `AgentChat` (fil), 34 catalogues.

## Review Focus

- **L'agent coche une source pendant que l'utilisateur coche une autre dans le menu** : les deux restent (la fin de
  demande relit les réglages avant d'appliquer) — test `test_a_pending_change_applies_over_the_current_settings`
  (tâche 3).
- **Un fournisseur configuré dont la clé a été effacée de QGIS** : le choisir dit que la clé manque et ouvre l'onglet
  Fournisseur, rien n'est changé — test `test_a_provider_without_its_key_is_not_switched_to` (tâche 3).
- **Une source qui n'existe plus** (source ajoutée supprimée, connexion de base retirée) : refusée en la nommant —
  test `test_unknown_source_is_refused` (tâche 1).
- **Le serveur MCP qui ne démarre pas** (port pris) : la case revient décochée et l'erreur s'affiche comme depuis la
  boîte de réglages — contrôle sans écran (tâche 5).
- **L'agent demande d'activer une source déjà active** : rien n'est demandé à l'utilisateur pour elle, la réponse dit
  « already » — test `test_already_on_is_not_asked` (tâche 1).

---

### Task 1: Le cœur : options, changements, groupes

**Files:**
- Create: `core/agent/agent_options.py`
- Modify: `core/agent/sources.py` (`source_group`)
- Test: `tests/unit/agent/test_agent_options.py`

**Interfaces:**
- Produces :
  - `source_group(source: Source) -> str` dans `sources.py` : `"open_data"`, `"imagery"` (STAC, altitude, population),
    `"basemaps"`, `"places"`, `"databases"`, `"connectors"` — les règles de `AgentSettingsDialog._fill_sources`, qui
    l'utilise ensuite ;
  - `@dataclass(frozen=True) ProviderEntry(preset, model, base_url, authcfg="", consent_target="", key_target="")`,
    propriété `label -> str` (« preset · model ») ;
  - `remember(entries: Sequence[ProviderEntry], entry: ProviderEntry, keep: int = 8) -> Tuple[ProviderEntry, ...]`
    (en tête, sans doublon `preset+model+base_url`) ; `forget(entries, entry)` ;
  - `options_view(sources, enabled_ids, providers, current: ProviderEntry, mcp_on: bool) -> Dict` : `{"provider":
    label, "providers": [labels], "sources": [{"id", "title", "group", "on"}], "mcp_server": bool}` ;
  - `@dataclass(frozen=True) Change(sources_on=(), sources_off=(), mcp_server: Optional[bool]=None,
    provider: Optional[ProviderEntry]=None)` ;
  - `plan_off(sources, enabled_ids, ids, mcp_server) -> Tuple[Change, Dict]` et `plan_on(sources, enabled_ids, ids,
    mcp_server, provider_label, providers, current) -> Tuple[Change, Dict]` : le changement à faire et la réponse
    (`{"turned_on"|"turned_off": [...], "already": [...], ...}`) ; `ValueError` nommant une source ou un fournisseur
    inconnu ; `mcp_server` doit être `False` pour off, `True` pour on ;
  - `apply_change(enabled_ids: Tuple[str, ...], change: Change) -> Tuple[str, ...]` (ordre gardé, ajouts à la fin).

- [ ] **Step 1: Tests** — `test_groups_follow_the_sources_tab` (une source de chaque sorte) ;
  `test_remember_puts_the_latest_first_and_keeps_eight` ; `test_off_lists_what_was_on` ; `test_already_on_is_not_asked`
  (`plan_on` d'une source cochée → `Change` vide pour elle, `"already"`) ; `test_unknown_source_is_refused` ;
  `test_only_a_configured_provider` (`plan_on(provider_label="openai · gpt-x")` absent de `providers` → ValueError) ;
  `test_apply_change_keeps_the_order`.
- [ ] **Step 2:** FAIL. **Step 3:** implémenter ; `_fill_sources` de la boîte de réglages utilise `source_group`.
- [ ] **Step 4:** PASS + `tests/unit/ui` sans régression. **Step 5:** commit `AGENT: the options of the agent and their changes, in core`.

---

### Task 2: Les fournisseurs configurés dans les réglages

**Files:**
- Modify: `adapters/agent/settings.py`, `ui/controllers/agent_chat_controller.py` (enregistrement de la boîte)
- Test: `tests/unit/agent/test_settings_providers.py` (sur le modèle de `test_settings_tool_families.py`)

**Interfaces:**
- Produces : `read_providers() -> Tuple[ProviderEntry, ...]`, `write_providers(entries)` (clé `agent/providers`) ;
  `current_provider(values: AgentSettings) -> ProviderEntry` ; la boîte de réglages, à l'enregistrement avec l'accord
  coché, appelle `write_providers(remember(read_providers(), current_provider(nouvelles valeurs)))`.

- [ ] Tests : `test_providers_round_trip`, `test_a_bad_json_reads_as_none`, `test_saving_a_provider_remembers_it`
  (contrôleur chargé comme dans `test_agent_settings_hardening.py`). FAIL → implémenter → PASS → commit
  `AGENT: the providers set up are remembered`.

---

### Task 3: Un seul chemin pour appliquer un changement

**Files:**
- Modify: `ui/controllers/agent_chat_controller.py`
- Test: `tests/unit/ui/controllers/test_agent_quick_options.py`

**Interfaces:**
- Produces (contrôleur) :
  - `apply_agent_options(change: Change) -> str` — relit les réglages, applique `apply_change` / `mcp_enabled` /
    fournisseur (`ProviderEntry` → `preset, model, base_url, authcfg, consent_target, key_target`, `consent=True`),
    `save_settings`, puis : autre fournisseur → `_reset_view` ; autres sources → `_restart_engine` ; `_sync_mcp` ;
    `_refresh_ready`. Rend "" ou la raison d'un refus (clé absente : `read_key(authcfg)` vide pour un preset qui en
    demande une → `_tr("The key of {} is missing: enter it in the Provider tab.")` et l'onglet s'ouvre) ;
  - `_pending_options: List[Change]` ; les gestionnaires des outils y ajoutent ; à la fin d'une demande (là où l'issue
    de la demande est traitée, `on_outcome` ou équivalent), chaque changement en attente passe par
    `apply_agent_options`, puis la liste se vide.

- [ ] Tests (contrôleur chargé, QGIS simulé) : `test_a_click_applies_at_once` (source cochée → réglages enregistrés,
  `_restart_engine` appelé) ; `test_another_provider_resets_the_view` ; `test_a_provider_without_its_key_is_not_switched_to` ;
  `test_a_pending_change_applies_over_the_current_settings` (réglages changés entre l'appel et la fin → les deux
  gardés) ; `test_nothing_applies_during_the_request`. FAIL → implémenter → PASS → commit
  `AGENT: one way to apply the options of the agent, at once or after the request`.

---

### Task 4: Le menu « ⋯ » du panneau

**Files:**
- Modify: `ui/widgets/agent_panel.py` (menu `more_button`), `ui/controllers/agent_chat_controller.py` (signaux),
  `i18n/FilterMate_*.ts|.qm`
- Test: `tests/unit/ui/test_agent_panel_quick_options.py` (QGIS simulé) et contrôle sans écran (tâche 6)

**Interfaces:**
- Produces (panneau) : sous-menus `sources_menu` (« Sources ») et `models_menu` (« Model »), action cochable
  `mcp_action` (« MCP server of the plugin ») ; signaux `source_toggled(str, bool)`, `provider_chosen(int)`,
  `provider_forgotten(int)`, `mcp_toggled(bool)`, `options_requested()` (émis à `aboutToShow` pour que le contrôleur
  remplisse) ; `fill_options(groups: List[Tuple[str, List[Tuple[str, str, bool]]]], providers: List[Tuple[str, bool]],
  mcp_on: bool)` — groupes déjà titrés (traduits par le contrôleur via les titres de l'onglet Sources), un sous-menu par
  groupe non vide ; « Source settings… » et « Other provider or model… » ouvrent l'onglet voulu (`open_settings(tab)`).
- Textes nouveaux (AgentPanel) : « Sources », « Model », « MCP server of the plugin », « Source settings… », « Other
  provider or model… », « Remove from the list ».

- [ ] Tests : `test_the_menu_lists_groups_and_ticks` ; `test_a_tick_emits_the_source` ; `test_the_current_provider_is_checked`.
  FAIL → implémenter → PASS ; catalogues (skill `i18n-pipeline`) ; commit `AGENT: sources, model and MCP server from the menu of the panel`.

---

### Task 5: Les outils du chat

**Files:**
- Modify: `core/agent/tool_catalog.py` (`CHAT_ONLY`), `core/agent/tool_index.py` (résumés), `core/agent/permissions.py`
  (`SETTINGS_TOOLS`), `ui/controllers/agent_chat_controller.py` (gestionnaires, `_describe`), `skills/configuration/SKILL.md`
  (+ export), `i18n/*`
- Test: `tests/unit/agent/test_agent_options.py`, `tests/unit/agent/test_permissions.py`

**Interfaces:**
- Consumes : tâches 1 et 3.
- Produces : schémas — `agent_options` `{}` ; `turn_off_agent_options` `{"sources": [id], "mcp_server": false}` (l'un
  au moins) ; `turn_on_agent_options` `{"sources": [id], "mcp_server": true, "provider": "<label>"}` (l'un au moins) ;
  descriptions : ce qui change, quand (« after this request »), et que l'agent ne saisit jamais de clé ni d'accord ;
  `_describe` : `_tr("Turning off: {}")`, `_tr("Turning on: {}")`, `_tr("Reading the options of the agent")`.
- Skill `configuration` : une section « Sources, model and MCP server » (lire `agent_options`, couper sans question ce
  que l'utilisateur demande de couper, proposer d'activer en disant pourquoi, jamais de clé ni d'accord).

- [ ] Tests : risques (`agent_options` READ, `turn_off_agent_options` PROJECT, `turn_on_agent_options` LOCAL et
  demandé à chaque niveau) ; les trois noms dans `chat_tools()` avec un `summary` ; `bringing` les associe à
  `configuration`. FAIL → implémenter → PASS ; `agent_eval.py` avec et sans `--families` ; un cas
  `configuration` : « Coupe data.gouv pour cette conversation. » → `turn_off_agent_options {"sources": ["datagouv"]}`,
  interdit `turn_on_agent_options` ; commit `AGENT: the agent turns its sources, model and MCP server on or off`.

---

### Task 6: Dans un vrai QGIS, revue, fusion

- [ ] `run_gui_smoke.py` : étapes `FM_ONLY=options` — le menu « ⋯ » montre Sources / Model / MCP ; cocher une source
  enregistre `enabled_sources` et garde le fil ; la case MCP sur un port pris revient décochée avec l'erreur.
- [ ] `check_agent_chat.py` : `turn_off_agent_options` s'exécute sans question et s'applique à la fin de la demande ;
  `turn_on_agent_options` est demandé (dialogue remplacé par le script).
- [ ] `ltr` et `latest` ; revue `opus-reviewer` ; corrections en TDD ; PR et fusion.
