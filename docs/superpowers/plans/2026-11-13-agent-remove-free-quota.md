# Lot B : retrait du quota gratuit — plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Le préréglage `free` disparaît du plugin et du dépôt. Le premier usage guide vers un fournisseur, sa clé et
un modèle, avec un bouton qui teste les trois.

**Architecture:** On supprime d'abord la logique du quota (cœur, adaptateurs, contrôleur, panneau), avec la règle de
lecture d'un profil enregistré sur `free`. Puis on guide l'onglet Fournisseur du dialogue : lien vers la page des
clés, bouton Tester, liste des modèles du fournisseur. Enfin, on supprime le relais, ses contrôles et sa
documentation, et on met à jour les catalogues de traduction.

**Tech Stack:** Python 3.10+, PyQGIS (QGIS 3.22 à 4.x, Qt5 et Qt6), pytest, contrôles sans écran dans Docker
`qgis/qgis` (skill `qgis-headless-bench`), `lrelease` dans Docker (skill `i18n-pipeline`).

**Spec:** `docs/superpowers/specs/2026-11-13-agent-remove-free-quota-design.md`

## Global Constraints

- Travailler dans le worktree `.claude/worktrees/remove-free-quota`, branche `claude/agent-remove-free-quota`.
  D'autres sessions utilisent le checkout principal.
- Un profil enregistré sur `free` se lit comme « aucun fournisseur choisi ». Rien d'autre n'est migré : sans
  fournisseur choisi, le consentement reste à donner.
- Chaque message visible ajouté ou retiré passe par les 34 catalogues `i18n/FilterMate_*.ts` et `.qm` (skill
  `i18n-pipeline`).
- Commits en anglais, dans le style du dépôt, terminés par `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- La CI est coupée exprès : la vérification est locale (pytest, flake8 avec les arguments de la release, contrôle sans
  écran).
- La clé n'est jamais écrite dans un fichier ni dans un journal. Le bouton Tester utilise la clé tapée, ou à défaut la
  clé enregistrée, sans la recopier ailleurs.

## Review Focus

1. Un profil enregistré sur `free`, avec consentement et modèle `claude-haiku-5-5` : le premier envoi doit ouvrir le
   dialogue des réglages, ni planter ni envoyer quoi que ce soit (tâche 1, `test_free_profile_reads_as_no_provider`).
2. Tester sans clé, avec une clé fausse, ou avec un modèle inconnu : un message lisible dans le dialogue, jamais la
   clé dans ce message (tâche 2, `test_provider_test_messages`).
3. La liste des modèles d'OpenAI contient des modèles d'embedding, de voix et d'image. Seuls les modèles de chat
   doivent être proposés (tâche 2, `test_chat_models_only`).
4. Le fournisseur ne répond pas (pas de réseau, délai dépassé) : le dialogue reste utilisable et le nom de modèle tapé
   reste en place (tâche 2, `test_models_fetch_failure_keeps_typed_model`).
5. `view_map` était retiré avec le quota gratuit : il doit rester proposé avec une clé de l'utilisateur quand l'envoi
   des valeurs est autorisé (tâche 1, `test_view_map_offered_with_values`).

---

### Task 1: Le quota gratuit retiré du code du plugin

**Files:**
- Delete: `adapters/agent/free_quota.py`
- Modify: `core/agent/providers/__init__.py:13-26` (supprimer `FREE_PRESET`, `FREE_MODEL`, `FREE_QUOTA_URL` et
  l'entrée `FREE_PRESET` de `PRESETS`)
- Modify: `adapters/agent/settings.py` (supprimer `free_quota_url` ; dans `target_of`, `needs_key` et
  `provider_config`, supprimer les cas `free`)
- Modify: `ui/controllers/agent_chat_controller.py`:
  - imports des lignes 18, 20 et 48 ;
  - `destination_text` (ligne 101) ;
  - `free_available=` (ligne 544) ;
  - la clé cachée (ligne 556) ;
  - `view_map` (ligne 623) ;
  - le jeton (lignes 1307-1313) ;
  - le commentaire de la ligne 1460 ;
  - le renouvellement et les messages du quota (lignes 2070-2077) : garder seulement
    `message = self._error_message(outcome.error)`.
- Modify: `ui/widgets/agent_panel.py`:
  - `PRESET_LABELS` et les libellés traduits (lignes 50 et 66) ;
  - le paramètre `free_available` du dialogue et le choix au premier usage (lignes 892 et 906-911) ;
  - `free_notice` et sa visibilité (lignes 919-923 et 1409-1416) ;
  - `chosen_model` (ligne 1523).
- Modify: `tests/unit/ui/controllers/test_agent_chat_lifecycle.py:170`, `tests/unit/agent/test_providers.py`
- Modify: `tests/unit/test_i18n_pro_sources.py:11`, `tests/unit/agent/test_expert_python.py:13` (retirer
  `free-quota-proxy` des dossiers ignorés)
- Test: `tests/unit/agent/test_settings_no_free_quota.py` (nouveau)

**Interfaces:**
- Produces: `PRESETS` sans `"free"` ; `AgentSettingsDialog(values, target_of, parent=None, tester=None, mcp_error="",
  project_layers=(), tools=(), provider_tester=None)`. Le paramètre `free_available` disparaît ; `provider_tester` est
  ajouté par la tâche 2.

- [ ] **Step 1: Write the failing tests** in `tests/unit/agent/test_settings_no_free_quota.py`:
  - load the modules under a synthetic package, as `tests/unit/ui/controllers/test_agent_settings_hardening.py`
    does (`_load`), with QGIS mocked by the root conftest;
  - the fixture `fake_qgs_settings` is written in this file: it monkeypatches `QgsSettings` in
    `adapters.agent.settings` with a class backed by a dict (`value(key, default=None, type=None)`, `setValue`), and
    yields the dict.

```python
def test_presets_have_no_free_quota():
    from filter_mate.core.agent import providers
    assert "free" not in providers.PRESETS
    assert not hasattr(providers, "FREE_PRESET") and not hasattr(providers, "FREE_QUOTA_URL")

def test_free_profile_reads_as_no_provider(fake_qgs_settings):
    fake_qgs_settings.update({"FilterMate/agent/preset": "free", "FilterMate/agent/model": "claude-haiku-5-5",
                              "FilterMate/agent/consent": True,
                              "FilterMate/agent/consent_target": "https://filtermate-free-quota.filtermate-free-quota-proxy.workers.dev"})
    values = load_settings()
    assert values.preset == "anthropic"
    assert not values.has_consent and not values.is_ready

def test_view_map_offered_with_values():
    # tools_and_handlers with AgentSettings(preset="anthropic", send_values=True): "view_map" is among the tools
    ...
```

  Keep the controller test light: it calls `tools_and_handlers` the way `test_agent_chat_lifecycle.py` builds the
  controller.

- [ ] **Step 2: Run them, check they fail**

Run: `python -m pytest tests/unit/agent/test_settings_no_free_quota.py -v`
Expected: FAIL (`"free"` in `PRESETS`)

- [ ] **Step 3: Remove the code** listed under Files.
  - `load_settings` already maps an unknown preset to `DEFAULT_PRESET` (`"anthropic"`). The consent stays tied to the
    relay's address, so `has_consent` is false and the dialog opens at the first send: no migration code.
  - The 402 / `ERROR_QUOTA` handling of `core/agent/providers` stays: a provider of the user can answer it too.

- [ ] **Step 4: Run the agent and controller tests**

Run: `python -m pytest tests/unit/agent tests/unit/ui -q`
Expected: every test passes. The only allowed failure is the one that fails on main too
(`test_coverage_raster_target.py::test_canceled_selection_is_not_read` is not in these folders).

- [ ] **Step 5: Lint and commit**

Run: `python -m flake8 adapters/agent/settings.py core/agent/providers/__init__.py ui/controllers/agent_chat_controller.py ui/widgets/agent_panel.py`
Expected: no new message compared with `origin/main`.

```bash
git commit -am "AGENT: the free quota removed from the plugin; a profile on it opens the settings at the first request"
```

### Task 2: Premier usage guidé dans l'onglet Fournisseur

**Files:**
- Create: `core/agent/providers/model_list.py` (lecture pure, sans Qt, des réponses de liste de modèles)
- Modify: `ui/widgets/agent_panel.py` (onglet Fournisseur : lien vers la page des clés, bouton Tester et son
  résultat, liste des modèles du fournisseur, texte d'accueil du panneau ligne 547)
- Modify: `ui/controllers/agent_chat_controller.py` (passe `provider_tester` au dialogue ; `_test_provider`)
- Test: `tests/unit/agent/test_model_list.py`, `tests/unit/ui/test_agent_provider_tab.py`

**Interfaces:**
- Consumes: le dialogue de la tâche 1.
- Produces:
  - `models_from_listing(kind: str, data: bytes) -> Tuple[str, ...]` dans `core/agent/providers/model_list.py` ;
  - `KEY_PAGES: Dict[str, str]` dans le même fichier ;
  - `AgentChatController._test_provider(preset: str, model: str, base_url: str, key: str) -> Tuple[bool, str, Tuple[str, ...]]`,
    qui renvoie (ça répond, message lisible, modèles de chat du fournisseur).

- [ ] **Step 1: Write the failing tests** in `tests/unit/agent/test_model_list.py`:

```python
def test_chat_models_only():
    openai = b'{"data":[{"id":"gpt-x"},{"id":"gpt-x-mini"},{"id":"text-embedding-3-large"},{"id":"tts-1"},' \
             b'{"id":"whisper-1"},{"id":"dall-e-3"},{"id":"omni-moderation-latest"},{"id":"gpt-image-1"}]}'
    assert models_from_listing("openai_compatible", openai) == ("gpt-x", "gpt-x-mini")

def test_mistral_keeps_chat_capable_models():
    mistral = b'{"data":[{"id":"mistral-small-latest","capabilities":{"completion_chat":true}},' \
              b'{"id":"mistral-embed","capabilities":{"completion_chat":false}}]}'
    assert models_from_listing("openai_compatible", mistral) == ("mistral-small-latest",)

def test_anthropic_listing():
    assert models_from_listing("anthropic", b'{"data":[{"id":"claude-haiku-5-5","type":"model"}]}') == ("claude-haiku-5-5",)

def test_unreadable_listing_is_empty():
    assert models_from_listing("anthropic", b"<html>") == ()

def test_key_pages_are_https():
    assert set(KEY_PAGES) == {"anthropic", "mistral", "openai"}
    assert all(url.startswith("https://") for url in KEY_PAGES.values())
```

  And in `tests/unit/ui/test_agent_provider_tab.py`, with the dialog built the way the existing dialog tests build it,
  and a fake `provider_tester`:
  - `test_provider_test_messages`:
    - a tester returning `(False, "Invalid API key.", ())` shows that text in the result label;
    - a key typed in the field is never part of any label text.
  - `test_models_fetch_failure_keeps_typed_model`: a tester returning `(False, "No answer.", ())` leaves
    `model.currentText()` unchanged.
  - `test_models_from_test_fill_the_list`: `(True, "It answers.", ("a", "b"))` puts `a` and `b` in the model list and
    keeps the typed name.

- [ ] **Step 2: Run them, check they fail**

Run: `python -m pytest tests/unit/agent/test_model_list.py tests/unit/ui/test_agent_provider_tab.py -v`
Expected: FAIL (module `model_list` not found)

- [ ] **Step 3: Implement**
  - `models_from_listing`:
    - reads the `data[].id` list;
    - for Mistral, keeps the entries whose `capabilities.completion_chat` is not false;
    - for every listing, drops ids containing `embed`, `tts`, `whisper`, `dall-e`, `moderation`, `image`, `audio`,
      `transcribe`, `realtime`, `search`;
    - keeps the order and at most 50 entries, as `MAX_LISTED_MODELS` does for Ollama.
  - `KEY_PAGES`: `anthropic` → `https://console.anthropic.com/settings/keys`, `mistral` →
    `https://console.mistral.ai/api-keys`, `openai` → `https://platform.openai.com/api-keys`. Open each page once in a
    browser before committing: a page that moved is replaced by the current one.
  - `MODEL_SUGGESTIONS` gains `"mistral": ("mistral-small-latest", "mistral-medium-latest", "mistral-large-latest")`.
  - Provider tab:
    - under the key field, a link « Create a key » to `KEY_PAGES[preset]`, hidden for Ollama;
    - a « Test » button next to the model, with a result label under it;
    - Test calls `provider_tester(preset, model, base_url, key)` and shows the message;
    - when it answers, the models it returns fill the model list, and the typed name stays.
  - `_test_provider`:
    - with the key typed, or else the stored one (`read_key(values.authcfg)` when its target is the same server), it
      sends one request "Reply with OK." with `max_tokens` 16 through the provider of `create_provider`, waiting at
      most 30 s in a local event loop;
    - then it lists the models: `GET {base}/models` with the provider's headers, for Ollama the existing
      `/api/tags` path;
    - failures are worded by `_error_message`, never with the key.
  - The welcome note of the panel (`agent_panel.py:547`) becomes "It needs an AI provider: your own API key, or a
    local model with Ollama. Nothing is sent before you agree."

- [ ] **Step 4: Run the tests**

Run: `python -m pytest tests/unit/agent tests/unit/ui -q`
Expected: every test passes

- [ ] **Step 5: Check in a real QGIS, without a screen** (skill `qgis-headless-bench`): open the dialog, choose each
  provider, check the link and the Test button show or hide as expected. Expected: the GUI smoke passes on `ltr` and
  `latest`.

- [ ] **Step 6: Lint and commit**

```bash
git add -A && git commit -m "AGENT settings: the provider tab guides a first use: where to get a key, Test, the provider's models"
```

### Task 3: Ollama guidé : l'installer, télécharger un modèle

**Files:**
- Modify: `core/agent/providers/ollama_chat.py` (fonctions pures près de `TAGS_PATH`, ligne 213)
- Modify: `ui/widgets/agent_panel.py` (onglet Fournisseur, à côté de `_fetch_ollama_models` et `_on_ollama_models`,
  lignes 1421-1460)
- Test: `tests/unit/agent/test_ollama_provider.py`, `tests/unit/ui/test_agent_provider_tab.py`

**Interfaces:**
- Consumes: l'onglet Fournisseur de la tâche 2.
- Produces, dans `core/agent/providers/ollama_chat.py` :
  - `PULL_PATH = "/api/pull"` ;
  - `RECOMMENDED_LOCAL_MODEL = "qwen3.5:4b"` ;
  - `OLLAMA_DOWNLOAD_PAGE = "https://ollama.com/download"` ;
  - `pull_body(model: str) -> bytes`, qui encode `{"model": model, "stream": true}` ;
  - `pull_progress(line: bytes) -> Optional[Tuple[str, int, int]]`, qui renvoie (statut, octets reçus, octets au
    total) ; `None` pour une ligne illisible ; une ligne avec `error` lève `ProviderError` avec son texte.

- [ ] **Step 1: Write the failing tests**

```python
def test_pull_body():
    assert json.loads(pull_body("qwen3.5:4b")) == {"model": "qwen3.5:4b", "stream": True}

def test_pull_progress_lines():
    assert pull_progress(b'{"status":"pulling a1b2","digest":"sha256:a1b2","total":3400000000,"completed":1700000000}') \
        == ("pulling a1b2", 1700000000, 3400000000)
    assert pull_progress(b'{"status":"success"}') == ("success", 0, 0)
    assert pull_progress(b"not json") is None
    with pytest.raises(ProviderError, match="file does not exist"):
        pull_progress(b'{"error":"pull model manifest: file does not exist"}')
```

  In `tests/unit/ui/test_agent_provider_tab.py`, Ollama chosen:
  - `test_ollama_not_answering_offers_install`: when the model list fails, the install note and its link to
    `OLLAMA_DOWNLOAD_PAGE` are visible, and so is Refresh.
  - `test_ollama_without_the_model_offers_download`: the list answers without `qwen3.5:4b` and the model field is
    empty, so the field shows `qwen3.5:4b` and Download is visible.
  - `test_download_asks_first`: Download with the question answered no sends nothing (no request made).

- [ ] **Step 2: Run them, check they fail**

Run: `python -m pytest tests/unit/agent/test_ollama_provider.py tests/unit/ui/test_agent_provider_tab.py -v`
Expected: FAIL (`pull_body` not defined)

- [ ] **Step 3: Implement**
  - The pure functions above.
  - In the dialog:
    - the install note with its link and Refresh (Refresh calls `_fetch_ollama_models`);
    - Download asks first;
    - then it posts `pull_body` to `<address>/api/pull` with the dialog's network manager, without a total timeout:
      only a silence of 60 s ends it;
    - it reads the lines as they come and updates a `QProgressBar` (busy until a total is known);
    - Cancel calls `reply.abort()`;
    - at `success` it reads the model list again and selects the model;
    - an error is shown in the result label.
  - Closing the dialog during a download aborts it (as `_closing` does for the model list).

- [ ] **Step 4: Run the tests**

Run: `python -m pytest tests/unit/agent tests/unit/ui -q`
Expected: every test passes

- [ ] **Step 5: Lint and commit**

```bash
git add -A && git commit -m "AGENT settings: Ollama guided: where to install it, a model downloaded from the dialog"
```

### Task 4: Le relais, ses contrôles, sa documentation et les catalogues

**Files:**
- Delete: `free-quota-proxy/` (dossier entier), `tests/qgis_headless/check_free_quota_live.py`
- Modify: `tests/qgis_headless/check_agent_chat.py` (supprimer `check_free_quota` lignes 1950-2040 et son appel
  ligne 1158)
- Modify: `scripts/agent_eval.py:84` (le commentaire ne cite plus le relais)
- Modify: `README.md` (lignes 66, 105, 126), `docs/AGENT_MODE.md` (lignes 5, 11, 184, 636, 646, 695-697 et la
  section du relais), `docs/ARCHITECTURE.md:20`, `CHANGELOG.md` (section non publiée : « The free quota is removed:
  the agent works with your own API key or a local Ollama model. »)
- Modify: `i18n/FilterMate_*.ts` et `.qm` (34 catalogues)

**Interfaces:**
- Consumes: les messages retirés par la tâche 1 et ajoutés par les tâches 2 et 3.

- [ ] **Step 1: Check nothing points to the relay any more**

Run: `grep -rn "free.quota\|FREE_QUOTA\|FREE_PRESET\|free-quota-proxy" --include='*.py' --include='*.md' --include='*.json' . | grep -v "^./i18n\|docs/superpowers"`
Expected: only the CHANGELOG lines of past releases and the new line of the unreleased section

- [ ] **Step 2: Update the 34 catalogs** with the skill `i18n-pipeline`:
  - mark the messages of the quota obsolete;
  - add the messages of tasks 2 and 3 (the welcome note, « Create a key », « Test », the result words, the Ollama
    install note, « Refresh », « Download », the download question and progress) in every language;
  - compile the `.qm` with `lrelease` in Docker.

Expected: `python -m pytest tests/unit/test_i18n*.py -q` passes.

- [ ] **Step 3: Run the full unit suite and the agent chat check**

Run: `python -m pytest tests/unit -q`. Expected: only
`test_coverage_raster_target.py::test_canceled_selection_is_not_read` fails, as on main.

Run: `check_agent_chat.py` through the skill `qgis-headless-bench`. Expected: every check passes.

- [ ] **Step 4: Commit**

```bash
git add -A && git commit -m "Free quota: its relay, checks and documentation removed; catalogs updated"
```

- [ ] **Step 5: Tell the user what is theirs to do**
  - Turn off the deployed Worker when they want: `npx wrangler secret put DISABLED` from a copy of `free-quota-proxy/`
    taken from Git, or delete the Worker in Cloudflare.
  - Then revoke the Anthropic key of its workspace.
