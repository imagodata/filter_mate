# Lot B — Filtres spatiaux vers les services et matérialisation bornée (étape 3 partie spatiale, étape 4)

**But.** Un filtre spatial dont la cible ou la source est un service ne télécharge que l'emprise utile, applique le prédicat exact localement et pose une liste de clés bornée. Quand le serveur ne peut pas appliquer un filtre, une copie bornée le calcule en tâche de fond, et un résultat incomplet est annoncé comme tel.

**Fichiers à toi.**
- `execute_ogr_spatial_selection` et ses fonctions voisines dans `adapters/backends/ogr/filter_executor.py` ;
- nouveau `adapters/qgis/remote_materializer.py` (`QgsTask`) ;
- nouveau `core/domain/materialization.py` : limites, issue complète ou partielle, pur Python ;
- les clés de configuration des plafonds.

Pas à toi : `expression_builder.py` et le chemin attributaire (lot A), l'interface (lot C).

**À faire.**
1. Mesurer aujourd'hui le cas cible = communes du WFS Géoplateforme, source = un polygone local (un département) : nombre de requêtes, entités téléchargées, durée. Compter les requêtes avec `QgsNetworkAccessManager.requestAboutToBeCreated`. Faire la même mesure avec un service comme source.
2. Cible service :
   - entités demandées avec un `filterRect` égal à l'emprise de la source (BBOX côté serveur) ;
   - prédicat exact évalué localement : géométrie source préparée, mêmes prédicats, tampons et reprojection que le chemin OGR actuel ;
   - liste de clés via `stable_key`, avec le plafond de 500 et les refus existants ;
   - jamais de lecture sans emprise.

   Source service : lire seulement ses entités sélectionnées ou filtrées.
3. Matérialisation :
   - une tâche copie en mémoire une couche service bornée (emprise utile, plafond d'entités, délai, annulation par le `QgsFeedback`), applique le filtre exact sur la copie et renvoie les clés ;
   - plafonds par défaut choisis après mesure (ordre de grandeur : quelques dizaines de milliers d'entités, une à deux minutes), réglables dans la configuration ;
   - plafond ou délai atteint : le résultat est annoncé partiel, jamais complet ;
   - rien n'est écrit dans les dossiers de l'utilisateur, et la copie est libérée en fin de tâche ;
   - plus de 500 clés : refus existant, aucune couche ajoutée au projet.
4. Contrat avec le lot A : `materialize(layer, rect, server_expression, local_expression, limits, feedback)` renvoie `MaterializationOutcome(keys, complete, fetched, reason)`. Le lot A expose `translate(...)` dans `core/filter/server_dialect.py`. Le lot qui fusionne en second branche « `PARTIAL` / `NONE` → matérialisation ».

**Fini quand.**
- La PR chiffre l'avant et l'après.
- `check_stream_vector_spatial.py` est vert.
- Un filtre Haute-Garonne → communes WFS ne télécharge que l'emprise du département et donne le même résultat que sur une copie locale complète.
- Un plafond atteint affiche « résultat partiel ».

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
