# Lot C — Interface asynchrone pour les services (étape 5)

**But.** Avec une couche service, le dock ne gèle jamais. Aucune requête réseau ne passe sur le thread principal. Chaque lecture longue tourne en tâche, s'annule, et son résultat est ignoré si la couche a changé entre-temps.

**Fichiers à toi.**
- `ui/controllers/exploring_controller.py` : `_get_unique_values` (appelle `uniqueValues()` sur le thread principal) et `zoom_to_*` ;
- `ui/widgets/custom_widgets.py` : sélecteur d'entités, `_populate_features_sync` ;
- `filter_mate_dockwidget.py` : emprise filtrée, vers les lignes 4490 et 5100 ;
- `ui/controllers/integration.py` : délégués de zoom ;
- `ui/controllers/mixins/layer_selection_mixin.py` ;
- une nouvelle tâche générique de lecture distante, dans `core/tasks/` ou `adapters/qgis/`.

Pas à toi : les backends OGR (lots A et B), les panneaux raster et nuage (lots D et E).

**À faire.**
1. Mesurer : instrumenter `QgsNetworkAccessManager.requestAboutToBeCreated` en notant le thread courant. Puis, sur le WFS Géoplateforme (communes) : changer de couche courante, ouvrir la liste de valeurs, chercher une entité, zoomer sur une expression puis sur la sélection, filtrer et défiltrer. Lister dans la PR chaque requête faite sur le thread principal.
2. Pour toute couche dont `counts_cheaply` est faux, passer en tâche : les valeurs uniques (avec une limite, `uniqueValues(index, limit)`), la liste d'entités, le zoom sur une expression ou une sélection, l'emprise filtrée. Chaque tâche :
   - affiche un état « chargement… » ;
   - s'annule par le `QgsFeedback` ;
   - porte un jeton de génération, pour ignorer un résultat périmé (couche ou expression changée).
3. Un nombre d'entités inconnu (`feature_count_or_none` renvoie `None`) est traité comme « grand » partout : seuils sync / async, messages.
4. Passer à une couche service comme couche courante ne fait aucune requête réseau sur le thread principal.

**Fini quand.**
- La liste de la mesure est vide après le lot.
- La logique de génération et d'annulation est couverte par des tests unitaires.
- `check_stream_ui_async.py` (dock sous xvfb, modèle `run_gui_smoke.py`) est vert.
- Aucune régression sur une couche locale : les chemins synchrones rapides restent synchrones.

## Règles communes (identiques dans les six prompts)

**Contexte.** FilterMate est un plugin QGIS (dépôt `/home/simon/projects/filter_mate`, 5.0.0 publiée). Tu réalises une partie du plan « Sources en flux » de l'audit du 17/10/2026 : artifact « Audit FilterMate 5.0 », https://claude.ai/artifact/DJFuADfmk7UXVrpRSYQXux (lis-le avec l'outil Artifact, action `read`, pas WebFetch). Les étapes 0 à 2 sont livrées par la PR #155 (`gh pr view 155`). Cinq sessions (lots A à E) travaillent en même temps ; le lot F clôt après elles.

**À lire avant de coder.** `CLAUDE.md`, `.claude/memory.md`, puis le socle à réutiliser sans le dupliquer :
- `core/domain/source_capability.py` : `classify`, `SourceCapability` (localité, `ServerFilter`, `ValueKind`, `NetworkCost`, `key_list_limit` = 500, `in_list_max`) ;
- `adapters/qgis/source_capability_probe.py` : `capability_for_layer`, `counts_cheaply`, `feature_count_or_none`, `is_remote_layer`, `stable_key_for_layer` ;
- `core/domain/stable_key.py` ; `core/filter/pk_formatter.py` (le seul formateur de littéraux).

**Isolation.** Travaille uniquement dans ton propre worktree (outil `EnterWorktree`, ou `git worktree add .claude/worktrees/stream-<lot> -b claude/v5-stream-<lot>-<sujet> origin/main`), jamais dans `/home/simon/projects/filter_mate` lui-même. Une branche par PR, toujours partie d'`origin/main` à jour.

**Fichiers.** Tu possèdes ceux de ton lot ; ailleurs, modifications minimales. Fichiers partagés :
- `core/domain/source_capability.py` : ajouts seulement, sans renommer ni réordonner ;
- `CHANGELOG.md` : tes puces sous `## [Unreleased]` ;
- `.claude/memory.md` : ta section datée en tête.

En cas de conflit sur ces fichiers, garde les deux côtés. Réservés au lot F : `i18n/*.ts`, `i18n/*.qm`, `.github/workflows/*`, `tests/qgis_headless/run_smoke.py`, `metadata.txt`. Nouvelles chaînes : `tr()` / `translate()` seulement, listées dans la description de la PR.

**Contraintes.**
- QGIS 3.22 → 4.2, Qt5 et Qt6 (enums scopés, `exec()`), syntaxe Python 3.8.
- `core/domain` reste pur Python ; QGIS seulement dans `adapters/`.
- Aucun appel réseau, `featureCount()` ou `uniqueValues()` distant, ni lecture de pixels distants sur le thread principal.
- Jamais de résultat faux silencieux : un refus ou un résultat partiel donne un message clair.
- Aucun identifiant dans les journaux ni dans `config.json`. Ne pas toucher à la configuration QGIS système.
- Code, commentaires, commits et PR en anglais (style du dépôt), PEP 8, docstrings Google.

**Méthode.** Mesure d'abord le comportement actuel sur un vrai service et note-le dans la PR. TDD : chaque comportement a un test qui échoue sans le correctif. Petites PR. Si une décision change ce qui est livré et que ni l'audit ni le code ne la tranchent, pose une seule question à Simon ; sinon prends le défaut le plus prudent et écris-le dans la PR.

**Vérification dans un vrai QGIS.** Ton propre script `tests/qgis_headless/check_stream_<lot>.py` (modèle : `check_combine_literals.py`), lancé dans les images `qgis/qgis:ltr` et `qgis/qgis:stable` (commandes en tête de `.github/workflows/qgis-headless.yml`). Sans réseau, une étape qui a besoin d'un service est SKIP, jamais FAIL. Fixtures locales pour l'automatique (serveur HTTP local, pygeoapi en Docker) ; services publics en vérification manuelle : WFS / WMTS / WMS de la Géoplateforme (`https://data.geopf.fr/wfs/ows`, `ADMINEXPRESS-COG.LATEST:commune`), pygeoapi (OGC API), sampleserver6.arcgisonline.com (ArcGIS), COPC Autzen, EPT USGS 3DEP.

**Avant chaque PR.**
1. `git fetch && git merge origin/main`.
2. `python -m pytest tests/ -q -o "addopts="` vert.
3. `python -m flake8 --extend-exclude=tests,scripts,website,docs --count` = 0.
4. Smoke en ltr et stable.
5. Revue adversariale par le sous-agent `opus-reviewer` ; chaque trouvaille corrigée, ou écartée avec sa raison.

Puis `git push`, `gh pr create`, `gh pr merge --merge` sans redemander (consigne de Simon : fusionner chaque lot vérifié), et une nouvelle branche depuis `origin/main` pour la suite. Ne pas taguer ni changer de version.

**Compte rendu.** À chaque PR fusionnée, en français : fait, vérifié (nombre de tests, smoke, services essayés), non vérifié, limites connues, numéro de PR.
