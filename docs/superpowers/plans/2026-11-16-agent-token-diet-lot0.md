# Régime de l'agent, lot 0 : le banc de mesure — plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Chiffrer, sans réseau et à l'identique d'un lot à l'autre, ce que coûte une conversation type de l'agent
(caractères envoyés, part servie par le cache, palier Ollama, coût estimé), et prendre la référence de qualité en appel
réel sur `qwen3:8b` avant que le lot 1 ne change ce que lit le modèle.

**Architecture:** La construction des instructions du chat sort du contrôleur (QGIS) vers un module pur
`core/agent/chat_setup.py`, pour que le banc les reproduise sans copier de texte. `scripts/agent_eval.py` expose ses
morceaux réutilisables (projet simulé, contexte, chargement des familles) et gagne `--repeat` / `--baseline`.
`scripts/agent_request_weight.py --conversation` rejoue dix demandes avec le modèle scripté dans une seule session,
mesure chaque appel sur les corps réels des trois fournisseurs et compare à une référence notée dans le script.

**Tech Stack:** Python 3.10+, pytest (QGIS simulé par le `conftest` racine), Ollama local (`qwen3:8b`).

**Spec:** `docs/superpowers/specs/2026-11-16-agent-token-diet-design.md` (section « Lot 0 — Le banc de mesure » et
« Ordre et vérification »). Les lots 1 à 4 auront chacun leur plan, écrit après la fusion de celui-ci, chiffres du banc
à l'appui.

## Global Constraints

- Worktree `../filter_mate-wt/agent-token-diet-lot0`, branche `claude/agent-token-diet-lot0`, partie de `main` une fois
  le design et ce plan fusionnés. Ne jamais travailler dans le checkout principal (d'autres sessions l'utilisent).
- Le lot 0 ne change **rien** de ce qu'un fournisseur reçoit : mêmes instructions au caractère près, mêmes outils, même
  ordre. Les empreintes de la tâche 1 le prouvent.
- `core/agent` reste du Python pur, sans import QGIS.
- Aucun texte visible par l'utilisateur n'est ajouté (rien pour les 34 catalogues).
- Le mode `--conversation` n'ouvre aucune connexion réseau.
- Tarif relatif d'Anthropic, en caractères : entrée non servie par le cache 1, écriture en cache 1,25, lecture en
  cache 0,1.
- Critère d'un lot (repris par les lots suivants) : le coût estimé et la plus grosse requête de la conversation
  baissent ; aucun des deux ne monte de plus de 5 % au-dessus de la référence.
- Barrière de qualité des lots 1 et 2 : `agent_eval.py --live --provider ollama --model qwen3:8b`, 3 passages par cas ;
  un cas est perdu s'il passait au moins 2 fois sur 3 sur la référence et passe au plus 1 fois sur 3 après.
- Vérifications de chaque tâche : `python3 -m pytest tests/unit/agent tests/unit/ui/controllers -q`,
  `python3 -m flake8` sur les fichiers touchés, `python3 scripts/agent_eval.py` et `python3 scripts/agent_eval.py
  --families` (111/111 aujourd'hui).
- Messages de commit en anglais, préfixe `AGENT:` comme l'historique récent.

## Review Focus

- **Un caractère accentué** (« département », « bâtiments ») : les longueurs et le préfixe commun se comptent en
  caractères sur le texte décodé, pas en octets — test `test_common_prefix_counts_characters` (tâche 3).
- **Un changement de palier `num_ctx`** entre deux appels : Ollama recharge le modèle, rien n'est servi par son cache ;
  le préfixe Ollama vaut 0 — test `test_ollama_prefix_is_lost_when_the_context_step_changes` (tâche 3).
- **Un appel scripté qui échoue** (argument faux, outil retenu) : la conversation serait plus légère que la réalité
  sans que personne le voie ; le rejeu relève toute réponse en erreur — test `test_conversation_runs_offline_and_cleanly`
  (tâche 4).
- **Une skill rechargée à chaque demande** : `load_skill("cartography")` n'est appelé qu'une fois dans la conversation,
  comme le ferait un vrai modèle — même test (tâche 4).
- **Une référence périmée** : la conversation modifiée, la comparaison n'a plus de sens ; une empreinte de la
  conversation est notée avec la référence et un écart fait échouer le mode — test
  `test_a_reference_of_another_conversation_is_refused` (tâche 4).

---

### Task 1: Les instructions du chat dans `core/agent/chat_setup.py`

**Files:**
- Create: `core/agent/chat_setup.py`
- Modify: `ui/controllers/agent_chat_controller.py:99-150` (constantes), `:1763-1830` (`_prompt`), imports
- Test: `tests/unit/ui/controllers/test_agent_chat_setup.py`

**Interfaces:**
- Produces:
  - constantes déplacées telles quelles du contrôleur : `OPEN_DATA_TOOL`, `SERVICE_TOOL`, `IMAGERY_TOOL`,
    `BASEMAP_TOOL`, `ELEVATION_TOOL`, `OSM_TOOL`, `POPULATION_TOOL`, `PLACE_TOOL`, `NO_OPEN_DATA_NOTE`,
    `NO_BASEMAP_NOTE`, `NO_ELEVATION_NOTE`, `NO_OSM_NOTE`, `NO_POPULATION_NOTE`, `NO_GEOCODER_NOTE`, `NO_VALUES_NOTE`
    (le contrôleur les importe de là : `chat_controller.NO_BASEMAP_NOTE` etc. restent valables) ;
  - `SOURCE_TOOLS: frozenset` — les outils qu'aucune source cochée ne laisse offerts : les huit `*_TOOL` ci-dessus plus
    `LIST_TABLES`, `ADD_TABLE` ;
  - `chat_instructions(active: Sequence[Source], *, send_values: bool = True, filtering: bool = False,
    configured_basemaps: Sequence[str] = (), offered: Optional[Sequence[str]] = None) -> str` — le corps actuel de
    `AgentChatController._prompt`, où `values.send_values` devient `send_values` et
    `AgentChatController.local_filtering(values)` devient `filtering`.
  - `AgentChatController._prompt(values, active, configured_basemaps=(), offered=None)` garde sa signature et délègue.

- [ ] **Step 1: Écrire le test qui fige le texte d'aujourd'hui**

Empreintes mesurées le 16/11 sur `ad0b143e` avec `_prompt` (QGIS simulé) ; le module de test charge le contrôleur
comme `tests/unit/ui/controllers/test_agent_connectors_listing.py` (`_load`, paquet synthétique à nom propre).

```python
GOLDEN = {  # (longueur, sha256 du texte UTF-8)
    "default": (12076, "f283741fa187bdb7f978b871441be95d6d7984d1b62f43cb223f480b2852f016"),
    "no_values_local": (12560, "fd94b8db1b5497782b6921ed30b204e181618899945248020affd0ce3b785833"),
    "every_source": (12652, "33ec4921967f247beff014c82a3899afd67c4fcda45f076e6bcaaceb7acff2d0"),
}
# default : AgentSettings(preset="anthropic", model="m"), active=[]
# no_values_local : AgentSettings(preset="ollama", model="m", send_values=False, local_filtering_only=True), active=[]
# every_source : AgentSettings(preset="anthropic", model="m", enabled_sources=<ids de sources.BUILT_IN>),
#                active=sources.BUILT_IN

@pytest.mark.parametrize("name", sorted(GOLDEN))
def test_the_prompt_is_unchanged(name):
    values, active = CONFIGS[name]
    text = AgentChatController._prompt(values, active)
    assert (len(text), sha256(text)) == GOLDEN[name]

@pytest.mark.parametrize("name", sorted(GOLDEN))
def test_chat_instructions_give_the_same_text(name):
    values, active = CONFIGS[name]
    text = chat_setup.chat_instructions(active, send_values=values.send_values,
                                        filtering=AgentChatController.local_filtering(values))
    assert (len(text), sha256(text)) == GOLDEN[name]

def test_source_tools():
    assert chat_setup.SOURCE_TOOLS == {"search_open_data", "add_service_layer", "search_imagery", "add_basemap",
                                       "add_elevation", "add_osm_features", "add_population", "find_place",
                                       "list_database_tables", "add_database_table"}
```

- [ ] **Step 2: Lancer le test**

Run: `python3 -m pytest tests/unit/ui/controllers/test_agent_chat_setup.py -q`
Expected: `test_the_prompt_is_unchanged` PASS (trois cas), les deux autres FAIL (module `chat_setup` absent).

- [ ] **Step 3: Créer `core/agent/chat_setup.py`, faire déléguer `_prompt`**

Déplacer les constantes et le corps de `_prompt` sans changer un caractère des textes ; `tools_and_handlers` garde sa
logique et importe les noms d'outils du nouveau module. Docstring du module : ce que le chat dit au modèle selon les
réglages, en Python pur, pour que les scripts de mesure le reproduisent.

- [ ] **Step 4: Lancer les tests**

Run: `python3 -m pytest tests/unit/agent tests/unit/ui/controllers -q && python3 -m flake8 core/agent/chat_setup.py ui/controllers/agent_chat_controller.py tests/unit/ui/controllers/test_agent_chat_setup.py`
Expected: tout PASS, flake8 muet.

- [ ] **Step 5: Commit**

```bash
git add core/agent/chat_setup.py ui/controllers/agent_chat_controller.py tests/unit/ui/controllers/test_agent_chat_setup.py
git commit -m "AGENT: the instructions of the chat built in core, for the measuring scripts"
```

---

### Task 2: Les morceaux réutilisables du banc d'évaluation

**Files:**
- Modify: `core/agent/session.py:86-130` (deux propriétés)
- Modify: `scripts/agent_eval.py:794-921` (`run_case`, `main`, nouvelles fonctions)
- Test: `tests/unit/agent/test_session_and_tools.py` (classe `TestBench` et un test de session)

**Interfaces:**
- Produces (session) : `AgentSession.system -> str` et `AgentSession.tools -> Tuple[ToolSpec, ...]`, en lecture seule
  (ce que `next_request` passe au fournisseur).
- Produces (`scripts/agent_eval.py`) :
  - `project_context(project: SimulatedProject, before: Optional[Dict[str, Any]] = None) -> str` — ce que `run_case`
    construit aujourd'hui (`project_summary` des couches, sélections, vue), avec `before` passé à `project_summary` ;
  - `project_state_of(project: SimulatedProject) -> Dict[str, Any]` — `project_state` des mêmes données ;
  - `skill_loader(load: Callable, hidden: Dict[str, ToolSpec], offer: Callable[[List[ToolSpec]], None]) -> Callable` —
    la fermeture `load_and_offer` de `run_case` : charge la skill, retire de `hidden` ce qu'elle débloque, appelle
    `offer`, ajoute `tools_now_offered` à la réponse ;
  - `passes_by_case(results: Sequence[Dict[str, Any]]) -> Dict[str, List[bool]]` ;
  - `lost_cases(reference: Dict[str, List[bool]], now: Dict[str, List[bool]]) -> List[str]` — triés ; perdu :
    `sum(reference[id]) >= 2 and sum(now[id]) <= 1` ; un cas absent d'un côté n'est pas perdu ;
  - options `--repeat N` (défaut 1 : chaque cas joué N fois, chaque résultat porte `"attempt": k`, k de 1 à N),
    `--baseline PATH` (un `--json` d'une référence : imprime les cas perdus et rend 1 s'il y en a, 0 sinon, au lieu de
    « tous passés ») ; `--json` réécrit le fichier après chaque cas (un passage réel arrêté garde ce qu'il a fait).

- [ ] **Step 1: Écrire les tests**

```python
def test_session_shows_what_it_sends():
    session = AgentSession(provider, tools, "instructions")
    assert session.system == "instructions" and session.tools == tuple(tools)

class TestBench:
    def test_lost_cases(self, bench):
        reference = {"a": [True, True, False], "b": [True, False, False], "c": [True, True, True], "d": [True] * 3}
        now = {"a": [True, False, False], "b": [False] * 3, "c": [True, True, False]}
        assert bench.lost_cases(reference, now) == ["a"]

    def test_passes_by_case_keeps_the_attempts(self, bench):
        results = [{"id": "x", "passed": True, "attempt": 1}, {"id": "x", "passed": False, "attempt": 2}]
        assert bench.passes_by_case(results) == {"x": [True, False]}

    def test_repeat_and_json(self, bench, tmp_path):
        out = tmp_path / "r.json"
        assert bench.main(["--case", "attr_dept", "--repeat", "2", "--json", str(out)]) == 0
        results = json.loads(out.read_text(encoding="utf-8"))["results"]
        assert [(r["id"], r["attempt"]) for r in results] == [("attr_dept", 1), ("attr_dept", 2)]

    def test_baseline_reports_a_lost_case(self, bench, tmp_path):
        reference = tmp_path / "ref.json"
        reference.write_text(json.dumps({"results": [{"id": "attr_dept", "passed": True, "attempt": k}
                                                     for k in (1, 2, 3)]}), encoding="utf-8")
        assert bench.main(["--case", "attr_dept", "--repeat", "3", "--baseline", str(reference)]) == 0
```

Le dernier test passe en scripté (le cas passe 3 fois, rien n'est perdu) ; le cas perdu est couvert par
`test_lost_cases`.

- [ ] **Step 2: Lancer les tests**

Run: `python3 -m pytest tests/unit/agent/test_session_and_tools.py -q`
Expected: FAIL (`system`, `lost_cases`, `--repeat` absents).

- [ ] **Step 3: Implémenter**

`run_case` utilise `project_context` et `skill_loader` (son comportement ne change pas). Ajouter `project_state_of`,
`passes_by_case`, `lost_cases`, les options, l'écriture du JSON après chaque cas.

- [ ] **Step 4: Vérifier**

Run: `python3 -m pytest tests/unit/agent -q && python3 scripts/agent_eval.py | tail -1 && python3 scripts/agent_eval.py --families | tail -1 && python3 -m flake8 scripts/agent_eval.py core/agent/session.py`
Expected: tests PASS ; `111/111 passed` deux fois ; flake8 muet.

- [ ] **Step 5: Commit**

```bash
git add core/agent/session.py scripts/agent_eval.py tests/unit/agent/test_session_and_tools.py
git commit -m "AGENT: the eval bench plays a case several times and names the cases lost against a reference"
```

---

### Task 3: Les mesures d'un appel

**Files:**
- Modify: `scripts/agent_request_weight.py`
- Test: `tests/unit/agent/test_agent_request_weight.py` (charge le script par `importlib.util.spec_from_file_location`,
  comme la fixture `bench` de `test_session_and_tools.py`)

**Interfaces:**
- Produces :
  - `KINDS = ("anthropic", "openai", "ollama")` et `providers() -> Dict[str, Provider]` — un fournisseur de chaque sorte,
    modèle `qwen3:8b` pour Ollama, adresses de `PRESETS`, sans clé ;
  - `cache_order(kind: str, body: Dict[str, Any]) -> str` — les parties du corps réel dans l'ordre où le serveur les lit
    pour son cache, chacune sérialisée comme `encode_json` (compact, `ensure_ascii=False`) : Anthropic `tools`, `system`,
    `messages` ; OpenAI et Ollama `tools`, `messages` (les instructions y sont le premier message). Interprétation de
    « dans son ordre de sérialisation » de la spec : dans le JSON d'OpenAI et d'Ollama, `tools` suit `messages`, alors
    que les trois serveurs placent les outils en tête du prompt ; mesurer l'ordre littéral du JSON compterait des
    outils identiques comme hors cache ;
  - `common_prefix(a: str, b: str) -> int` — en caractères ;
  - `cached_prefix(kind: str, before: Optional[Dict[str, Any]], body: Dict[str, Any]) -> int` — 0 sans appel
    précédent, 0 pour Ollama quand `options.num_ctx` diffère, sinon `common_prefix` des `cache_order` ;
  - `@dataclass(frozen=True) CallWeight` : `request: int` (rang de la demande, à partir de 1), `instructions: int`,
    `tools: int`, `history: int` (longueurs des parties `system`, `tools`, `messages` du corps Anthropic sérialisées),
    `tool_count: int`, `prefix: Dict[str, int]` (par sorte), `num_ctx: int` ; propriété `sent -> int` = somme des trois
    parties ;
  - `CACHE_READ = 0.1`, `CACHE_WRITE = 1.25` et `estimated_cost(calls: Sequence[CallWeight]) -> float` = somme de
    `CACHE_READ * prefix["anthropic"] + CACHE_WRITE * (sent - prefix["anthropic"])`. Le tarif 1 (entrée hors cache) ne
    s'applique à rien : le fournisseur Anthropic pose `cache_control` sur toute la requête, donc tout ce qui n'est pas lu
    est écrit ; un commentaire le dit.

- [ ] **Step 1: Écrire les tests**

Aides du module de test : `user(text)` = `Message(ROLE_USER, (TextPart(text),))`, `tools = chat_tools()[:2]`.

```python
def test_common_prefix_counts_characters(weight):
    assert weight.common_prefix("département 31", "département 32") == 13

@pytest.mark.parametrize("kind", ["anthropic", "openai", "ollama"])
def test_cache_order_puts_the_tools_first(weight, kind):
    body = json.loads(weight.providers()[kind].build_request("sys", [user("é")], tools).body)
    assert weight.cache_order(kind, body).startswith(json.dumps(body["tools"], ensure_ascii=False, separators=(",", ":")))

def test_ollama_prefix_is_lost_when_the_context_step_changes(weight):
    before = {"tools": [], "messages": [{"role": "user", "content": "a"}], "options": {"num_ctx": 16384}}
    after = dict(before, options={"num_ctx": 32768})
    assert weight.cached_prefix("ollama", before, after) == 0
    assert weight.cached_prefix("openai", before, after) > 0
    assert weight.cached_prefix("ollama", None, before) == 0

def test_estimated_cost(weight):
    first = weight.CallWeight(1, 400, 500, 100, 3, {"anthropic": 0, "openai": 0, "ollama": 0}, 16384)
    second = weight.CallWeight(1, 400, 500, 100, 3, {"anthropic": 900, "openai": 900, "ollama": 900}, 16384)
    assert weight.estimated_cost([first, second]) == pytest.approx(1250 + 90 + 125)
```

- [ ] **Step 2: Lancer les tests** — Run: `python3 -m pytest tests/unit/agent/test_agent_request_weight.py -q` ;
  Expected: FAIL (fonctions absentes).

- [ ] **Step 3: Implémenter** les fonctions ci-dessus dans le script ; `weigh()` et la sortie sans option restent
  telles quelles.

- [ ] **Step 4: Vérifier** — Run: `python3 -m pytest tests/unit/agent/test_agent_request_weight.py -q && python3 scripts/agent_request_weight.py --top 3 && python3 -m flake8 scripts/agent_request_weight.py`
  Expected: PASS ; la sortie sans option inchangée (71 outils, 94 343 caractères) ; flake8 muet.

- [ ] **Step 5: Commit**

```bash
git add scripts/agent_request_weight.py tests/unit/agent/test_agent_request_weight.py
git commit -m "AGENT: measures of one request: its parts, the start the cache can serve, an estimated cost"
```

---

### Task 4: Le mode `--conversation`

**Files:**
- Modify: `scripts/agent_request_weight.py`, `docs/AGENT_MODE.md:736`
- Test: `tests/unit/agent/test_agent_request_weight.py`,
  `tests/unit/ui/controllers/test_agent_request_weight_default.py`

**Interfaces:**
- Consumes : `chat_setup.chat_instructions`, `chat_setup.SOURCE_TOOLS` (tâche 1) ; `AgentSession.system`,
  `AgentSession.tools`, `SimulatedProject`, `ScriptedTransport`, `project_context`, `project_state_of`,
  `skill_loader` (tâche 2) ; `providers`, `cached_prefix`, `CallWeight`, `estimated_cost` (tâche 3).
- Produces :
  - `default_setup() -> Tuple[str, Tuple[ToolSpec, ...], Dict[str, List[str]]]` — instructions, outils offerts au
    départ, outils retenus avec leurs skills, comme le chat avec les réglages par défaut (familles activées, aucune
    source cochée, valeurs partagées, ni Python expert ni filtrage seul) : `chat_tools()` sans `SOURCE_TOOLS` ni
    `RUN_PYTHON`, puis `with_skill_tool(tools, offered)`, puis `families.bringing` ; instructions =
    `chat_instructions([], offered=<noms avant les familles>)` ;
  - `CONVERSATION_SETUP = {"selected": ["communes"]}` et `CONVERSATION` (ci-dessous) ;
  - `@dataclass Replay` : `calls: List[CallWeight]`, `errors: List[str]` (début du contenu de chaque `ToolResultPart`
    à `is_error` relevé dans `session.messages` à la fin de chaque demande — une réponse « call load_skill first »
    d'un outil retenu en est une), `skills_loaded: List[str]` (argument `name` des appels `load_skill` de
    `ExchangeResult.calls`, dans l'ordre), `summarized: int` (`session.summarized`) ;
  - le script ajoute `ROOT / "scripts"` à `sys.path` pour importer `agent_eval` ;
  - `replay() -> Replay` — une session (fournisseur Anthropic scripté, `AgentLimits()` par défaut), un projet simulé,
    un `ToolExecutor` avec `hold(held)` et `skill_loader` ; pour chaque demande : un `ScriptedTransport` de ses étapes,
    `load_first` avec les seuls outils encore retenus, un transport qui mesure enveloppant le scripté (pour chaque
    sorte, `build_request(session.system, session.messages, session.tools)`, `cached_prefix` contre le corps du même
    fournisseur à l'appel précédent de la conversation), contexte `project_context(project, before=seen)` puis
    `seen = project_state_of(project)` à la fin de la demande (comme `_seen` du contrôleur), `confirm` toujours oui ;
  - `fingerprint() -> str` — 12 premiers caractères hexadécimaux du sha256 de `json.dumps([CONVERSATION_SETUP,
    CONVERSATION], sort_keys=True)` ;
  - `REFERENCE: Optional[Dict[str, Any]] = None` (remplie à la tâche 5 : `date`, `commit`, `fingerprint`, `calls`,
    `sent`, `largest`, `cost`) ;
  - option `--conversation` : une ligne par appel (demande, outils offerts, instructions / outils / historique, préfixe
    Anthropic / OpenAI / Ollama, `num_ctx`), puis le total (appels, caractères envoyés, plus grosse requête, coût
    estimé, demandes résumées) et l'écart en % à `REFERENCE`. Rend 1 si l'empreinte diffère de celle de la référence
    (« reference taken on another conversation ») ou si le coût ou la plus grosse requête dépasse la référence de plus
    de 5 %, sinon 0 ; sans référence, 0.

`CONVERSATION` — dix demandes `(texte, étapes)`, arguments repris des cas validés du banc d'évaluation :

| # | Texte | Étapes (`tool`, `args`) |
|---|---|---|
| 1 | Ne garde que les communes de Haute-Garonne (département 31). | `apply_filter` `{"layer_name": "communes", "expression": "\"dept\" = '31'"}` |
| 2 | Quels champs a la couche des routes ? | `describe_layer` `{"layer": "routes"}` |
| 3 | Filtre les bâtiments qui sont dans la commune sélectionnée. | `cross_filter` `{"source_layer": "communes", "target_layers": ["batiments"], "predicates": ["Are within"]}` |
| 4 | Combien y a-t-il de communes par département ? | `layer_statistics` `{"layer": "communes", "group_by": "dept"}` |
| 5 | Colore les communes selon leur population, en 5 classes. | `set_layer_style` `{"layer": "communes", "mode": "graduated", "field": "population", "classes": 5}` |
| 6 | Parmi ces communes, garde seulement celles de plus de 10000 habitants. | `apply_filter` `{"layer_name": "communes", "expression": "\"population\" > 10000", "operator": "AND"}` |
| 7 | Zoome sur la commune sélectionnée. | `zoom_to` `{"layer": "communes", "selected_only": true}` |
| 8 | Hide the parcels layer. | `set_layers_visibility` `{"layers": ["parcelles"], "visible": false}` |
| 9 | Exporte les bâtiments en GeoJSON. | `export_layers` `{"layers": ["batiments"], "vector_format": "GeoJSON"}` |
| 10 | Retire le filtre sur les communes. | `clear_filters` `{"layers": ["communes"]}` |

`load_first` ajoute `load_skill("cartography")` avant la demande 5 (`set_layer_style` est retenu) ; aucune autre étape
n'est retenue aujourd'hui.

- [ ] **Step 1: Écrire les tests**

Dans `tests/unit/agent/test_agent_request_weight.py` :

```python
def test_conversation_runs_offline_and_cleanly(weight, monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError("network")
    monkeypatch.setattr(socket.socket, "connect", refuse)
    run = weight.replay()
    assert run.errors == []
    assert sorted({call.request for call in run.calls}) == list(range(1, 11))
    assert run.skills_loaded == ["cartography"]
    assert all(value == 0 for value in run.calls[0].prefix.values())

def test_within_a_request_the_whole_start_is_shared(weight):
    calls = weight.replay().calls
    for before, after in zip(calls, calls[1:]):
        if after.request == before.request and after.tool_count == before.tool_count:
            assert after.prefix["anthropic"] == before.sent - 1  # tout l'appel précédent sauf le "]" final des messages

def test_main_conversation_without_reference(weight, monkeypatch, capsys):
    monkeypatch.setattr(weight, "REFERENCE", None)
    assert weight.main(["--conversation"]) == 0
    assert "estimated cost" in capsys.readouterr().out

def test_a_reference_of_another_conversation_is_refused(weight, monkeypatch, capsys):
    monkeypatch.setattr(weight, "REFERENCE", {"fingerprint": "000000000000", "cost": 1e12, "largest": 10 ** 9})
    assert weight.main(["--conversation"]) == 1
    assert "another conversation" in capsys.readouterr().out

def test_a_rise_past_five_percent_fails(weight, monkeypatch):
    run = weight.replay()
    cost = weight.estimated_cost(run.calls)
    largest = max(call.sent for call in run.calls)
    reference = {"fingerprint": weight.fingerprint(), "cost": cost / 1.06, "largest": largest}
    monkeypatch.setattr(weight, "REFERENCE", reference)
    assert weight.main(["--conversation"]) == 1
    monkeypatch.setattr(weight, "REFERENCE", dict(reference, cost=cost / 1.04))
    assert weight.main(["--conversation"]) == 0
```

Dans `tests/unit/ui/controllers/test_agent_request_weight_default.py` (contrôleur chargé comme dans
`test_agent_connectors_listing.py`, sous son propre nom de paquet synthétique, avec la même fixture `plugin_tools`
et le même `_Host` sans portail ; le script chargé par `importlib` sous le nom `weight`) :

```python
def test_the_bench_starts_as_the_chat_does(plugin_tools):
    values = agent_settings.AgentSettings(preset="anthropic", model="m")
    tools, handlers, active = run(_Host(), values)
    offered = [tool.name for tool in tools]
    kept, _handlers, held = families(_Host(), values, tools, handlers, active)
    prompt, start, bench_held = weight.default_setup()
    assert [tool.name for tool in start] == [tool.name for tool in kept]
    assert set(bench_held) == held
    assert prompt == AgentChatController._prompt(values, active, [], offered)
```

- [ ] **Step 2: Lancer les tests** — Run: `python3 -m pytest tests/unit/agent/test_agent_request_weight.py tests/unit/ui/controllers/test_agent_request_weight_default.py -q` ;
  Expected: FAIL (`replay`, `default_setup` absents).

- [ ] **Step 3: Implémenter** `default_setup`, `CONVERSATION`, `replay`, `fingerprint`, `REFERENCE = None`, le mode
  `--conversation` ; docstring du script et `docs/AGENT_MODE.md:736` : une ligne pour
  `python scripts/agent_request_weight.py --conversation` (ce qu'une conversation type coûte, comparé à la référence).
  La note « Not weighed » du docstring dit que le mode conversation pèse l'historique, pas les notes des sources.

- [ ] **Step 4: Vérifier**

Run: `python3 -m pytest tests/unit/agent tests/unit/ui/controllers -q && python3 scripts/agent_request_weight.py --conversation && python3 -m flake8 scripts/agent_request_weight.py tests/unit/agent/test_agent_request_weight.py tests/unit/ui/controllers/test_agent_request_weight_default.py`
Expected: PASS ; dix demandes imprimées, aucune erreur ; le premier appel autour de 48 500 caractères (12 076 + les 27
outils de départ, ~36 400) ; code de sortie 0.

- [ ] **Step 5: Commit**

```bash
git add scripts/agent_request_weight.py docs/AGENT_MODE.md tests/unit/agent/test_agent_request_weight.py tests/unit/ui/controllers/test_agent_request_weight_default.py
git commit -m "AGENT: the weight of a whole conversation, call by call, with what the cache can serve"
```

---

### Task 5: Les références, puis la fusion

**Files:**
- Modify: `scripts/agent_request_weight.py` (`REFERENCE`)
- Create: `scripts/agent_eval_baselines/qwen3-8b-2026-11-16.json`

- [ ] **Step 1: Noter la référence de poids**

Run: `python3 scripts/agent_request_weight.py --conversation`, puis remplir `REFERENCE` avec `date="2026-11-16"`,
`commit` = le `main` de départ du lot, l'empreinte, et les quatre totaux imprimés. Commentaire au-dessus : mesurée
avant le lot 1, comme `NOTES_OF_SOURCES`.
Expected ensuite : `--conversation` imprime des écarts de +0,0 % et rend 0.

- [ ] **Step 2: Lancer la référence de qualité en arrière-plan**

Pré-requis : `ollama list` montre `qwen3:8b`. Run (en arrière-plan, plusieurs heures possibles : 111 cas × 3) :
`python3 scripts/agent_eval.py --live --provider ollama --model qwen3:8b --families --repeat 3 --json scripts/agent_eval_baselines/qwen3-8b-2026-11-16.json`
`--families` : la configuration par défaut du chat. Le code du lot 0 ne change rien de la requête : cette référence
vaut pour `main`.
Expected : le fichier complet (333 résultats) ; le taux de réussite est noté dans la PR, pas jugé (c'est la référence).

- [ ] **Step 3: Vérifier et commiter**

Run: `python3 -m pytest tests/unit/agent tests/unit/ui/controllers -q && python3 scripts/agent_eval.py --families | tail -1 && python3 scripts/agent_request_weight.py --conversation`

```bash
git add scripts/agent_request_weight.py scripts/agent_eval_baselines/qwen3-8b-2026-11-16.json
git commit -m "AGENT: the references of the token diet, weight and quality, taken before lot 1"
```

- [ ] **Step 4: PR et fusion**

La fusion attend le fichier complet de l'étape 2. Description : la sortie de `--conversation`, le taux de `qwen3:8b` par cas (passages sur 3), et le rappel que rien de
ce que reçoit un fournisseur n'a changé (empreintes de la tâche 1). Revue `opus-reviewer` du diff, puis fusion sans
redemander (mémoire « Merger au fur et à mesure »). Pas de contrôle `qgis-headless-bench` : le dock ne change pas,
seul l'import des constantes du contrôleur bouge, couvert par les tests du contrôleur.
