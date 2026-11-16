# Lot E étendu : l'agent règle EXPLORING, FILTERING et EXPORTING — plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** L'agent lit et règle, comme le ferait l'utilisateur dans le panneau, les champs d'exploration et les
paramètres de filtrage de chaque couche, et les paramètres d'export du projet ; le panneau suit, c'est gardé avec le
projet, et c'est annulé avec le tour.

**Architecture:** Les listes blanches et la vérification des valeurs sont en Python pur (`core/agent/panel_options.py`).
L'application au panneau est dans `adapters/public_api/panel_options.py` (fil principal) : elle écrit les dicts du
panneau puis passe par ses signaux de sauvegarde (`settingLayerVariable`, `settingProjectVariables`) et rafraîchit ses
widgets. Quatre outils (`layer_options`, `set_layer_options`, `export_options`, `set_export_options`) suivent le chemin
de tous les outils : accesseur, route REST, déclaration MCP, catalogue, gestionnaire du chat, risque, annulation. Ils
viennent avec une nouvelle skill `panels` (familles d'outils) : la requête de départ ne grossit que d'une ligne.

**Tech Stack:** Python 3.10+, PyQGIS (QGIS 3.22 à 4.x), pytest, FastAPI/MCP (`requirements-mcp.txt`), contrôle sans
écran dans Docker `qgis/qgis:ltr` (skill `qgis-headless-bench`), `lrelease` (skill `i18n-pipeline`).

**Spec:** `docs/superpowers/specs/2026-11-13-agent-exploring-settings-design.md` (lot E, étendu le 16/11), et la
contrainte de poids de `docs/superpowers/specs/2026-11-16-agent-token-diet-design.md`.

## Global Constraints

- Worktree `../filter_mate-wt/agent-layer-options`, branche `claude/agent-layer-options`.
- Noms des outils : `layer_options`, `set_layer_options`, `export_options`, `set_export_options`. Skill : `panels`.
- Couches vectorielles seulement pour `set_layer_options` (le signal de sauvegarde prend un `QgsVectorLayer`) : une
  couche raster ou nuage de points est refusée en le disant.
- Sans panneau FilterMate ouvert (`plugin.app.dockwidget` absent ou pas initialisé) : refus « Open the FilterMate
  panel first: these options are those of its panels. »
- Toutes les modifications d'un appel sont vérifiées avant d'en écrire une : tout ou rien.
- Couches protégées : `set_layer_options` refusé pour elles (`CHANGED_LAYERS`). `set_export_options` ne change aucune
  couche et n'a pas d'entrée.
- Risque : `layer_options` et `export_options` en lecture (READ) ; `set_*` en PROJECT (affichés dans le fil, annulés
  avec le tour).
- Poids : `python3 scripts/agent_request_weight.py --conversation` reste sous +5 % de sa référence ; l'écart va dans la
  PR. Aucun texte ajouté à `SYSTEM_PROMPT`.
- Textes visibles par l'utilisateur (libellés du fil, d'annulation) : contexte Qt `AgentChat`, dans les 34 catalogues
  (skill `i18n-pipeline`). Textes lus par le modèle : en anglais, hors catalogues.
- Vérifications de chaque tâche : `python3 -m pytest tests/unit tests/api -q -p no:cacheprovider` (sortie dans un
  fichier, lire la fin), `python3 -m flake8` sur les fichiers touchés, `python3 scripts/agent_eval.py --families`.

### Clés permises (valeurs vérifiées par `core/agent/panel_options.py`)

| Groupe | Clé (telle que stockée) | Valeur permise |
|---|---|---|
| exploring | `single_selection_expression`, `multiple_selection_expression`, `custom_selection_expression` | expression QGIS valide pour la couche, 1 000 caractères au plus |
| exploring | `current_exploring_groupbox` | `single_selection`, `multiple_selection`, `custom_selection` |
| exploring | `is_tracking`, `is_linking` | booléen |
| filtering | `has_layers_to_filter`, `has_geometric_predicates`, `has_combine_operator`, `has_buffer_value`, `has_buffer_type` | booléen |
| filtering | `layers_to_filter` | couches vectorielles du projet, par nom ou id ; stockées par id ; jamais la couche réglée elle-même |
| filtering | `geometric_predicates` | sous-liste de `PREDICATES` (`core/domain/api_requests.py:28`) |
| filtering | `source_layer_combine_operator`, `other_layers_combine_operator` | `AND`, `AND NOT`, `OR` |
| filtering | `buffer_value` | nombre fini, ±1 000 000 (bornes du panneau) |
| filtering | `buffer_type` | `Round`, `Flat`, `Square` |
| filtering | `buffer_segments` | entier 1 à 100 |
| export | `layers_to_export` → `LAYERS_TO_EXPORT` | couches du projet, par nom ou id ; stockées par id |
| export | `projection_to_export` → `PROJECTION_TO_EXPORT` | authid valide (`QgsCoordinateReferenceSystem(v).isValid()`) |
| export | `styles_to_export` → `STYLES_TO_EXPORT` | `QML`, `SLD` |
| export | `datatype_to_export` → `DATATYPE_TO_EXPORT` | une clé ou valeur de `LayerExporter.DRIVER_MAP` (`core/export/layer_exporter.py:450`) |
| export | `output_folder_to_export` → `OUTPUT_FOLDER_TO_EXPORT` | dossier existant, accessible en écriture |
| export | `zip_to_export` → `ZIP_TO_EXPORT` | chemin d'un `.zip` dans un dossier existant |
| export | `has_…` de chacune, `batch_output_folder`, `batch_zip` → en majuscules | booléen |

Une clé d'export fixée sans sa case `has_…` dans le même appel coche la case (`has_… = true`), comme le fait le
panneau quand on choisit une valeur ; même règle pour `layers_to_filter`, `geometric_predicates`,
`source_layer_combine_operator`/`other_layers_combine_operator`, `buffer_value`, `buffer_type` avec leur `has_…`.

## Review Focus

- **La couche réglée n'est pas celle du panneau** : rien ne doit bouger dans les widgets ; quand l'utilisateur la
  choisit ensuite, le panneau montre les nouvelles valeurs — test `test_other_layer_is_saved_not_shown` (tâche 2) et
  contrôle sans écran (tâche 6).
- **Une expression qui cite un champ absent ou mal écrite** : refusée avec le nom du champ, rien d'écrit — test
  `test_bad_expression_refuses_the_whole_call` (tâche 1).
- **L'utilisateur change lui-même le réglage après le tour** : annuler le tour ne l'écrase pas, et le dit — test
  `test_undo_leaves_what_the_user_changed_since` (tâche 4).
- **Une couche protégée parmi plusieurs** : tout l'appel est refusé, aucune couche n'est réglée — test
  `test_one_protected_layer_refuses_the_call` (tâche 3).
- **Un projet que FilterMate n'a pas encore enregistré** (pas de ligne dans `fm_projects`) : la sauvegarde d'EXPORTING
  ne fait rien en silence (`database_manager.py:704-709`) ; l'outil le dit (« set for this session; FilterMate saves
  it with the project once the project is saved ») — test `test_export_options_say_when_not_saved` (tâche 2).

---

### Task 1: Listes blanches et vérification, en Python pur

**Files:**
- Create: `core/agent/panel_options.py`
- Test: `tests/unit/agent/test_panel_options.py`

**Interfaces:**
- Produces:
  - `EXPLORING_KEYS`, `FILTERING_KEYS`, `EXPORT_KEYS: Dict[str, str]` — nom de l'outil → clé stockée (`EXPORT_KEYS` vers
    les majuscules) ; `GROUPBOXES`, `COMBINE_OPERATORS`, `BUFFER_TYPES`, `STYLE_FORMATS`, `MAX_BUFFER = 1_000_000`,
    `MAX_EXPRESSION = 1000`, `MAX_LAYERS_PER_CALL = 50` ;
  - `@dataclass(frozen=True) LayerFacts`: `layer_id: str`, `name: str`, `vector: bool`;
  - `check_layer_changes(exploring: Mapping, filtering: Mapping, *, layer: LayerFacts, layers: Sequence[LayerFacts],
    predicates: Sequence[str], expression_problem: Callable[[str], str]) -> Tuple[Dict[str, Dict[str, Any]], List[str]]`
    — `({"exploring": {clé stockée: valeur}, "filtering": {...}}, problèmes)` ; les `has_…` cochés selon la règle
    ci-dessus ; `layers_to_filter` résolu en ids ;
  - `check_export_changes(changes: Mapping, *, layers: Sequence[LayerFacts], formats: Collection[str],
    crs_problem: Callable[[str], str], folder_problem: Callable[[str], str]) -> Tuple[Dict[str, Any], List[str]]`
    — clés stockées en majuscules ;
  - `resolve_layer(reference: str, layers: Sequence[LayerFacts]) -> Optional[LayerFacts]` — par id d'abord, puis par
    nom exact (un nom porté par deux couches : `None`, et le problème le dit).

- [ ] **Step 1: Écrire les tests**

```python
COMMUNES = LayerFacts("communes_a1", "communes", True)
ROUTES = LayerFacts("routes_c3", "routes", True)
MNT = LayerFacts("mnt_f6", "mnt", False)
LAYERS = [COMMUNES, ROUTES, MNT]

def no_problem(_):
    return ""

def test_exploring_values_are_kept_as_stored():
    clean, problems = check_layer_changes(
        {"single_selection_expression": '"nom"', "current_exploring_groupbox": "multiple_selection", "is_tracking": True},
        {}, layer=COMMUNES, layers=LAYERS, predicates=PREDICATES, expression_problem=no_problem)
    assert problems == [] and clean["exploring"] == {"single_selection_expression": '"nom"',
                                                     "current_exploring_groupbox": "multiple_selection", "is_tracking": True}

def test_bad_expression_refuses_the_whole_call():
    clean, problems = check_layer_changes(
        {"single_selection_expression": '"nmo"', "is_tracking": True}, {}, layer=COMMUNES, layers=LAYERS,
        predicates=PREDICATES, expression_problem=lambda text: "unknown field nmo" if "nmo" in text else "")
    assert clean == {} and problems == ["single_selection_expression: unknown field nmo"]

def test_filtering_values_tick_their_box_and_store_ids():
    clean, problems = check_layer_changes(
        {}, {"layers_to_filter": ["routes"], "geometric_predicates": ["Intersect"], "buffer_value": 50},
        layer=COMMUNES, layers=LAYERS, predicates=PREDICATES, expression_problem=no_problem)
    assert problems == []
    assert clean["filtering"] == {"layers_to_filter": ["routes_c3"], "has_layers_to_filter": True,
                                  "geometric_predicates": ["Intersect"], "has_geometric_predicates": True,
                                  "buffer_value": 50.0, "has_buffer_value": True}

@pytest.mark.parametrize("filtering, problem", [
    ({"layers_to_filter": ["communes"]}, "layers_to_filter: not the layer itself"),
    ({"layers_to_filter": ["mnt"]}, "layers_to_filter: mnt is not a vector layer"),
    ({"geometric_predicates": ["Near"]}, "geometric_predicates: Near is not one of"),
    ({"buffer_value": 2e6}, "buffer_value: between -1000000 and 1000000"),
    ({"buffer_type": "Mitre"}, "buffer_type: one of Round, Flat, Square"),
    ({"other_layers_combine_operator": "XOR"}, "other_layers_combine_operator: one of AND, AND NOT, OR"),
    ({"bogus": 1}, "bogus: not an option of a layer"),
])
def test_filtering_refusals(filtering, problem):
    clean, problems = check_layer_changes({}, filtering, layer=COMMUNES, layers=LAYERS, predicates=PREDICATES,
                                          expression_problem=no_problem)
    assert clean == {} and problems and problems[0].startswith(problem)

def test_a_raster_layer_is_refused():
    clean, problems = check_layer_changes({"is_tracking": True}, {}, layer=MNT, layers=LAYERS, predicates=PREDICATES,
                                          expression_problem=no_problem)
    assert clean == {} and problems == ["mnt: only a vector layer has these options"]

def test_export_values_map_to_the_stored_keys():
    clean, problems = check_export_changes(
        {"layers_to_export": ["communes"], "datatype_to_export": "GPKG", "zip_to_export": "/tmp/out/a.zip"},
        layers=LAYERS, formats={"GPKG", "GeoJSON"}, crs_problem=no_problem, folder_problem=no_problem)
    assert problems == [] and clean == {"LAYERS_TO_EXPORT": ["communes_a1"], "HAS_LAYERS_TO_EXPORT": True,
                                        "DATATYPE_TO_EXPORT": "GPKG", "HAS_DATATYPE_TO_EXPORT": True,
                                        "ZIP_TO_EXPORT": "/tmp/out/a.zip", "HAS_ZIP_TO_EXPORT": True}

@pytest.mark.parametrize("changes, problem", [
    ({"datatype_to_export": "DXF"}, "datatype_to_export: DXF is not a format FilterMate exports"),
    ({"styles_to_export": "LYRX"}, "styles_to_export: one of QML, SLD"),
    ({"zip_to_export": "/tmp/out/a.tar"}, "zip_to_export: a path ending in .zip"),
    ({"layers_to_export": ["nowhere"]}, "layers_to_export: no layer nowhere"),
])
def test_export_refusals(changes, problem):
    clean, problems = check_export_changes(changes, layers=LAYERS, formats={"GPKG"}, crs_problem=no_problem,
                                           folder_problem=no_problem)
    assert clean == {} and problems[0].startswith(problem)

def test_two_layers_of_one_name_are_named_as_such():
    twins = [COMMUNES, LayerFacts("communes_b2", "communes", True)]
    assert resolve_layer("communes", twins) is None and resolve_layer("communes_b2", twins).layer_id == "communes_b2"
```

- [ ] **Step 2: Lancer** — `python3 -m pytest tests/unit/agent/test_panel_options.py -q` ; Expected: FAIL (module absent).
- [ ] **Step 3: Implémenter `core/agent/panel_options.py`** (sans import QGIS ; `PREDICATES` importé de
  `core/domain/api_requests.py` s'il est pur, sinon passé en argument comme dans les tests). Un problème par clé fautive,
  de la forme `"<clé>: <raison>"` ; `layers_to_filter` d'une couche à deux homonymes : `"layers_to_filter: two layers
  are named X, give its id"`.
- [ ] **Step 4: Vérifier** — même commande, PASS ; flake8 muet.
- [ ] **Step 5: Commit** — `git commit -m "AGENT: the options of the panels an agent may set, checked in core"`

---

### Task 2: Lire et écrire dans le panneau

**Files:**
- Create: `adapters/public_api/panel_options.py`
- Test: `tests/unit/adapters/public_api/test_panel_options.py`

**Interfaces:**
- Consumes: tâche 1.
- Produces (fil principal, dicts simples, `ValueError` pour un refus) :
  - `layer_options(dock, layer: str) -> Dict[str, Any]` — `{"layer_name", "layer_id", "exploring": {...},
    "filtering": {...}, "choices": {"current_exploring_groupbox": [...], "geometric_predicates": [...],
    "combine_operators": [...], "buffer_types": [...]}}` ; seules les clés des listes blanches ;
    `layers_to_filter` rendu en noms ;
  - `set_layer_options(dock, layers: List[Dict[str, Any]]) -> Dict[str, Any]` — `layers` : `[{"layer": str,
    "exploring": {...}, "filtering": {...}}]`, 50 au plus ; tout vérifié d'abord (tâche 1, expression par
    `QgsExpression` + `QgsExpressionContextUtils` de la couche : `hasParserError` ou champ inconnu) ; puis, par couche,
    `dock.PROJECT_LAYERS[id][groupe].update(...)`, `dock.settingLayerVariable.emit(layer, [(groupe, clé), ...])`, et si
    `dock.current_layer` est cette couche : `dock._synchronize_layer_widgets(layer, dock.PROJECT_LAYERS[id])` puis
    `dock._reset_exploring_button_states(props)` et `dock._reset_filtering_button_states(props)` (comme
    `resetLayerVariableEvent`, `filter_mate_dockwidget.py:6997-7000`). Rend `{"changed": [{"layer_name", "exploring",
    "filtering"}], "shown_in_panel": bool}` ;
  - `export_options(dock) -> Dict[str, Any]` — clés de l'outil (minuscules) avec leurs valeurs, `layers_to_export` en
    noms, `"formats"` permis, `"saved": bool` (le projet a sa ligne dans FilterMate) ;
  - `set_export_options(dock, changes: Dict[str, Any]) -> Dict[str, Any]` — vérifié (tâche 1), puis
    `dock.project_props["EXPORTING"].update(...)`, `dock.CONFIG_DATA["CURRENT_PROJECT"]["EXPORTING"] =
    dock.project_props["EXPORTING"]`, `dock.setProjectVariablesEvent()`, `dock.set_exporting_properties()` (widgets).
    Rend `{"changed": {...minuscules...}, "saved": bool, "note"?: str}`.
  - `dock_problem(dock) -> str` — "" quand le panneau est prêt (`widgets_initialized`), sinon le texte de refus des
    Global Constraints.

- [ ] **Step 1: Écrire les tests** avec un panneau factice (`types.SimpleNamespace` : `PROJECT_LAYERS`,
  `current_layer`, `settingLayerVariable` = `MagicMock()` avec `.emit`, `_synchronize_layer_widgets`,
  `_reset_exploring_button_states`, `_reset_filtering_button_states`, `project_props`, `CONFIG_DATA`,
  `setProjectVariablesEvent`, `set_exporting_properties`, `widgets_initialized=True`) et des couches mémoire QGIS
  (le `conftest` racine simule QGIS : suivre `tests/unit/adapters/public_api/test_public_api.py` pour les couches) :

```python
def test_current_layer_is_saved_and_shown(dock, communes):
    dock.current_layer = communes
    answer = set_layer_options(dock, [{"layer": "communes", "exploring": {"single_selection_expression": '"nom"'}}])
    assert dock.PROJECT_LAYERS[communes.id()]["exploring"]["single_selection_expression"] == '"nom"'
    dock.settingLayerVariable.emit.assert_called_once_with(communes, [("exploring", "single_selection_expression")])
    dock._synchronize_layer_widgets.assert_called_once()
    assert answer["shown_in_panel"] is True

def test_other_layer_is_saved_not_shown(dock, communes, routes):
    dock.current_layer = routes
    set_layer_options(dock, [{"layer": "communes", "exploring": {"is_tracking": True}}])
    dock.settingLayerVariable.emit.assert_called_once()
    dock._synchronize_layer_widgets.assert_not_called()

def test_nothing_written_when_one_layer_is_wrong(dock, communes, routes):
    with pytest.raises(ValueError, match="nmo"):
        set_layer_options(dock, [{"layer": "routes", "exploring": {"is_tracking": True}},
                                 {"layer": "communes", "exploring": {"single_selection_expression": '"nmo"'}}])
    dock.settingLayerVariable.emit.assert_not_called()

def test_layer_options_name_the_layers_to_filter(dock, communes, routes):
    dock.PROJECT_LAYERS[communes.id()]["filtering"]["layers_to_filter"] = [routes.id()]
    assert layer_options(dock, "communes")["filtering"]["layers_to_filter"] == ["routes"]

def test_export_options_are_saved_and_shown(dock, communes, tmp_path):
    answer = set_export_options(dock, {"layers_to_export": ["communes"], "output_folder_to_export": str(tmp_path)})
    assert dock.CONFIG_DATA["CURRENT_PROJECT"]["EXPORTING"]["LAYERS_TO_EXPORT"] == [communes.id()]
    dock.setProjectVariablesEvent.assert_called_once()
    dock.set_exporting_properties.assert_called_once()
    assert answer["changed"]["output_folder_to_export"] == str(tmp_path)

def test_export_options_say_when_not_saved(dock, communes, monkeypatch):
    monkeypatch.setattr(panel_options, "_project_saved", lambda: False)
    answer = set_export_options(dock, {"batch_zip": True})
    assert answer["saved"] is False and "once the project is saved" in answer["note"]

def test_no_panel():
    assert "Open the FilterMate panel first" in dock_problem(None)
```

`_project_saved() -> bool` : vrai quand le projet QGIS a un chemin et une ligne dans `fm_projects` (lire
`adapters/database_manager.py:704-709` pour la même condition).

- [ ] **Step 2: Lancer** — `python3 -m pytest tests/unit/adapters/public_api/test_panel_options.py -q` ; FAIL.
- [ ] **Step 3: Implémenter** `adapters/public_api/panel_options.py` (docstring de module : ce qu'il règle, par quel
  chemin du panneau, et que l'annulation est dans `adapters/agent/turn_effects.py`).
- [ ] **Step 4: Vérifier** — PASS ; flake8 muet.
- [ ] **Step 5: Commit** — `git commit -m "AGENT: read and set the options of the panels as the panel does"`

---

### Task 3: Les quatre outils, de l'accesseur au chat

**Files:**
- Modify: `filtermate_api/accessor.py` (protocole `FilterMateAccessor` et `InMemoryAccessor`),
  `filtermate_api/qgis_accessor.py`, `filtermate_api/routers/project.py`, `filtermate_api/mcp/server.py`,
  `core/agent/tool_catalog.json` (régénéré), `filtermate_api/agent_tools.py`, `core/agent/permissions.py`,
  `ui/controllers/agent_chat_controller.py` (`_describe`), `i18n/FilterMate_*.ts|.qm`
- Test: `tests/api/test_qgis_accessor.py`, `tests/unit/agent/test_permissions.py`, `tests/api/` (route)

**Interfaces:**
- Consumes: tâche 2.
- Produces :
  - Accesseur : `layer_options(layer: str) -> Dict[str, Any]`, `set_layer_options(layers: List[Dict[str, Any]]) ->
    Dict[str, Any]`, `export_options() -> Dict[str, Any]`, `set_export_options(changes: Dict[str, Any]) -> Dict[str,
    Any]`. `QGISFilterMateAccessor` lit le panneau (`self._app_attribute("dockwidget")`), refuse par `FilterRejected`
    quand `dock_problem` parle, puis `self._control(<nom>, dock, ..., module="adapters.public_api.panel_options",
    changes=...)` (`changes={"layers": layers}` pour `set_layer_options`). `InMemoryAccessor` garde un dict par couche
    et un dict d'export, avec les mêmes formes de réponse.
  - Routes : `GET /panels/layer?layer=`, `POST /panels/layer`, `GET /panels/export`, `POST /panels/export`.
  - MCP (docstrings = descriptions lues par le modèle, sobres : poids) :
    - `layer_options(layer)` — `ToolAnnotations(title="Options of a layer in the panels", readOnlyHint=True,
      openWorldHint=False)` ;
    - `set_layer_options(layers: list[{layer, exploring?, filtering?}], reason: str)` — `_write("Set the options of
      layers in the panels", idempotent=True)` ;
    - `export_options()` — lecture ; `set_export_options(changes: dict, reason: str)` — `_write(..., idempotent=True)`.
    La description de `set_layer_options` cite les clés permises en une ligne chacune ; les règles de choix sont dans la
    skill (tâche 5), pas ici.
  - `core/agent/permissions.py` : `CHANGED_LAYERS["set_layer_options"]` et, dans `changed_layers`, les éléments
    dictionnaires d'une liste donnent leur `"layer"`.
  - `_describe` : `set_layer_options` → `_tr("Panel options of: {}")`, `set_export_options` → `_tr("Export options of
    the panel")` ; les deux lectures → `_tr("Reading the panel options")`.

- [ ] **Step 1: Écrire les tests**

```python
# tests/unit/agent/test_permissions.py
def test_one_protected_layer_refuses_the_call():
    assert changed_layers("set_layer_options", {"layers": [{"layer": "routes"}, {"layer": "communes"}]}) == ["routes", "communes"]
    # et la politique, avec "communes" protégée, refuse l'appel (suivre les cas protégés existants vers :322)

@pytest.mark.parametrize("name, risk", [("layer_options", READ), ("export_options", READ),
                                        ("set_layer_options", PROJECT), ("set_export_options", PROJECT)])
def test_risk_of_panel_tools(name, risk): ...  # par le catalogue chargé, comme la table vers :40

# tests/api/test_qgis_accessor.py
def test_panel_options_need_the_panel():  # plugin sans dockwidget -> FilterRejected "Open the FilterMate panel first"
def test_set_layer_options_goes_to_the_panel_module():  # _control appelé avec module="adapters.public_api.panel_options"
```

Plus : les quatre noms sont dans `chat_tools()` et dans `build_handlers(...)`, et `TestCatalog` existant (description,
schéma valide) passe pour eux.

- [ ] **Step 2: Lancer** — FAIL.
- [ ] **Step 3: Implémenter** dans l'ordre accesseur, route, MCP, `pip install -r requirements-mcp.txt` si besoin puis
  `python3 scripts/export_agent_tools.py`, gestionnaires `agent_tools.py` (`_report` comme les autres),
  permissions, `_describe`. Chaînes nouvelles : skill `i18n-pipeline` (34 catalogues, `lrelease` dans Docker).
- [ ] **Step 4: Vérifier** — suite unit + api PASS ; `python3 scripts/agent_eval.py --families` 111/111 ;
  `python3 scripts/agent_request_weight.py --top 3` : les quatre outils apparaissent et aucun ne dépasse 2 000
  caractères.
- [ ] **Step 5: Commit** — `git commit -m "AGENT: the tools layer_options, set_layer_options, export_options, set_export_options"`

---

### Task 4: Annulés avec le tour

**Files:**
- Modify: `adapters/agent/turn_effects.py`
- Test: `tests/unit/adapters/agent/test_turn_effects*.py` (suivre le test existant des effets `widgets` / `settings`)

**Interfaces:**
- Consumes: tâche 2 (`layer_options`, `export_options` pour lire l'état, et l'écriture par
  `set_layer_options` / `set_export_options` du module du panneau pour le remettre).
- Produces : `PANEL_TOOLS = frozenset({"set_layer_options"})`, `EXPORT_PANEL_TOOLS = frozenset({"set_export_options"})` ;
  effets `("layer_options", layer_id, before_json, after_json, name)` et `("export_options", "", before_json,
  after_json)` (JSON trié des seules clés des listes blanches) ; libellés `_export_options_label()` →
  `QCoreApplication.translate("AgentChat", "export options of the panel")` ; une couche nommée par son nom.
  À l'annulation : remis seulement si l'état actuel est encore celui que le tour a laissé ; sinon nommé dans « left ».

- [ ] **Step 1: Écrire les tests** : `test_layer_options_undone_with_the_turn` (avant/après, l'annulation remet
  l'expression et émet la sauvegarde), `test_undo_leaves_what_the_user_changed_since`, `test_export_options_undone`.
- [ ] **Step 2: Lancer** — FAIL.
- [ ] **Step 3: Implémenter** : capture dans `before_call` (lecture par le module du panneau), comparaison dans
  `finish`, application dans `apply_effects` ; chaîne nouvelle dans les catalogues.
- [ ] **Step 4: Vérifier** — PASS ; suite unit + api PASS.
- [ ] **Step 5: Commit** — `git commit -m "AGENT: the options of the panels are undone with the turn"`

---

### Task 5: La skill `panels`, ses cas de banc, la mise en route

**Files:**
- Create: `skills/panels/SKILL.md`, `skills/panels/evals.json`
- Modify: `scripts/agent_eval.py` (`SimulatedProject.handlers`), `skills/configuration/SKILL.md` (mise en route),
  `docs/AGENT_MODE.md` (liste des outils), sorties de `scripts/export_agent_skills.py` (régénérées)

**Interfaces:**
- Consumes: tâche 3 (noms et schémas des outils).
- Produces : front matter `name: panels`, `title: Set up the panels of FilterMate`, `description: set up FilterMate's
  panels for the user: the fields EXPLORING shows for each layer, the filtering options of a layer, the export
  options of the project`, `metadata.tools: layer_options, set_layer_options, export_options, set_export_options,
  describe_layer, field_values, list_layers, ask_user`, `risk: change`, `trust: builtin`, `audience: chat, mcp`.
  Corps (court, c'est lu à chaque chargement) : la méthode du design (libellé lisible et unique, jamais un identifiant
  technique quand un nom existe, sans valeurs partagées partir des noms de champs, un vrai choix par `ask_user`, tout
  le projet en un seul appel), les champs de rattachement (`zone_*_id`) en tête quand ils lient les couches, la
  sélection multiple pour un champ à peu de valeurs, et pour l'export : préparer le panneau quand l'utilisateur veut
  exporter lui-même, `export_layers` quand il demande l'export.
- `SimulatedProject` : gestionnaires des quatre outils sur des dicts (formes de réponse de la tâche 2).

- [ ] **Step 1: Écrire les cas** (`skills/panels/evals.json`) :
  - `panels_readable_label` : « Règle l'exploration des communes pour qu'on voie leur nom. » → `set_layer_options`
    avec `{"layers": [{"layer": "communes", "exploring": {"single_selection_expression": {"contains": ["nom"]}}}]}` ;
    interdit : `apply_filter`.
  - `panels_prepare_export` : « Prépare l'export des bâtiments en GeoPackage, je le lancerai moi-même. » →
    `set_export_options` avec `{"changes": {"layers_to_export": ["batiments"], "datatype_to_export": "GPKG"}}` ;
    interdit : `export_layers`.
- [ ] **Step 2: Lancer** — `python3 scripts/agent_eval.py --families --case panels_readable_label --case panels_prepare_export` ; FAIL (skill absente).
- [ ] **Step 3: Écrire** la skill, les gestionnaires simulés, la ligne de mise en route dans `configuration`, la
  ligne de `docs/AGENT_MODE.md` ; `python3 scripts/export_agent_skills.py`.
- [ ] **Step 4: Vérifier** — `python3 scripts/agent_eval.py --families` (113/113) et sans `--families` ;
  `python3 -m pytest tests/unit/agent -q` (dont `test_skills_standard`) ; `python3 scripts/agent_request_weight.py
  --conversation` : sous +5 %, écart noté.
- [ ] **Step 5: Commit** — `git commit -m "AGENT: the skill panels: the agent sets up FilterMate's panels"`

---

### Task 6: Dans un vrai QGIS, puis la fusion

**Files:**
- Modify: `tests/qgis_headless/check_agent_tools.py`

- [ ] **Step 1: Ajouter les contrôles** (avec le vrai panneau si le script en ouvre un, sinon le panneau factice de la
  tâche 2 sur de vraies couches) : `set_layer_options` change l'expression de sélection simple d'une couche, la
  variable `exploring_single_selection_expression` de la couche la porte, `layer_options` la relit ; une expression
  fausse est refusée ; `set_export_options` puis `export_options` relisent le format.
- [ ] **Step 2: Lancer** dans Docker (skill `qgis-headless-bench`, image `qgis/qgis:ltr`, puis `latest`) ; Expected :
  tous PASS.
- [ ] **Step 3: Revue** `opus-reviewer` de toute la branche (Review Focus ci-dessus), corrections en TDD.
- [ ] **Step 4: PR et fusion** — description : ce que l'agent peut régler, l'écart de poids du banc, les contrôles
  QGIS passés.
