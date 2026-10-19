# Lot E — Tuiles vectorielles et nuages de points distants (étape 7)

**But.** Une couche de tuiles vectorielles peut être la cible d'un filtre. Un nuage EPT ou COPC distant n'est lu que sur l'emprise utile.

**Fichiers à toi.**
- `adapters/qgis/coverage_layers/pdal_cli.py` et `hag_task.py` ;
- les parties nuage de `target_appliers.py` et de `source_jobs.py` ;
- nouveaux modules `adapters/qgis/coverage_layers/vector_tile_*.py` ;
- dans `snapshots.py`, l'état du renderer des tuiles ;
- `core/domain/layer_kind.py`, si un nouveau type est nécessaire ;
- l'ajout des tuiles dans « Couches à filtrer » : `ui/controllers/filtering_controller.py` et `_populate_filtering_targets` de `coverage_mode_controller.py`.

Dans `adapters/qgis/point_cloud_capability.py`, qui appartient au lot D, une seule ligne dans `get_layer_kind` pour reconnaître les tuiles.

**État au 19/10.**
- La découpe COPC est poussée au lecteur (`reader["polygon"]`, PR #172).
- Un EPT est lu avec `filters.crop` après `readers.ept`, sans `bounds` : tout le jeu de données est téléchargé.
- Les tuiles vectorielles sont invisibles dans le dock.

**À faire.**
1. Nuages distants :
   - mesurer octets et durée d'une découpe et d'une HAG sur l'EPT USGS 3DEP et le COPC Autzen en https ;
   - passer `bounds` à `readers.ept` et à `readers.copc` distant, et `polygon` quand la version de PDAL l'accepte ;
   - la HAG et la découpe ne lisent que l'emprise utile ;
   - refus clair si PDAL est trop ancien.
2. Tuiles vectorielles (`QgsVectorTileLayer` : XYZ, ArcGIS Vector Tile Service, MBTiles, VTPK) :
   - cible seulement, jamais couche courante ;
   - le filtre est posé dans les `filterExpression` des styles du renderer : attributaire, et spatial par une géométrie de sélection au budget de sommets borné, comme pour les rasters ;
   - restauré par les snapshots : défiltrer, annuler, favoris, rechargement du projet ;
   - visible dans « Couches à filtrer » avec un badge.
3. Dire honnêtement les limites :
   - une tuile ne porte que les attributs de son niveau de zoom ;
   - un objet découpé sur plusieurs tuiles peut être gardé dans l'une et retiré dans l'autre par un filtre spatial ;
   - un renderer autre que « basic » (style externe) : refus clair.

**Fini quand.**
- La PR donne les octets lus avant et après.
- `check_stream_tiles_pointclouds.py` est vert, avec un MBTiles et un COPC locaux servis en HTTP ; les services publics en SKIP sans réseau.
- Sur le plan IGN vectoriel, un filtre attributaire puis un filtre spatial fonctionnent ; après défiltrage puis rechargement du projet, les styles d'origine sont intacts.

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
