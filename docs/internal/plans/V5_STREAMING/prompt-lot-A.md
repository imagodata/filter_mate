# Lot A — Filtres attributaires envoyés aux services (étape 3, partie attributs)

**But.** Aucune expression ne part vers un service sans avoir été traduite et validée dans le dialecte du serveur. Ce qui ne se traduit pas est refusé clairement, puis, une fois le lot B fusionné, évalué sur une copie bornée.

**Fichiers à toi.**
- nouveau `core/filter/server_dialect.py` : règles par dialecte, pur Python ;
- nouveau `adapters/qgis/server_filter_translation.py` : parcours de l'arbre `QgsExpression`, `QgsOgcUtils` ;
- `adapters/backends/ogr/expression_builder.py` ;
- dans `adapters/backends/ogr/filter_executor.py`, seulement le chemin attributaire (`apply_ogr_subset`) ;
- `core/tasks/executors/attribute_filter_executor.py`.

Pas à toi : `execute_ogr_spatial_selection` (lot B), l'interface (lot C).

**État au 19/10.** Aucun `QgsOgcUtils` dans le code. L'expression QGIS part telle quelle aux providers WFS, OAPIF et ArcGIS. MSSQL, Oracle et HANA, routés vers le backend OGR, reçoivent une expression QGIS comme WHERE natif : `ILIKE` et les fonctions QGIS cassent. Un subset refusé par le provider n'est pas détecté.

**À faire.**
1. Mesurer, en QGIS 3.44 et 4.2, ce que fait chaque provider (WFS Géoplateforme, pygeoapi, ArcGIS sample server) des expressions `"nom" = 'L''Isle-Jourdain'`, `"nom" ILIKE 'saint%'`, `"population" > 1000 AND "insee_dep" = '31'`, `left("nom", 3) = 'Sai'` et `$area > 1e6`. Pour chacune : traduite au serveur, évaluée côté client après un téléchargement complet, ou erreur silencieuse ? Mettre le tableau dans la PR.
2. `translate(expression, dialect, fields)` renvoie un statut `FULL` / `PARTIAL` / `NONE`, la partie serveur, la partie locale et une raison lisible. Les conjonctions `AND` sont séparées : ce qui se traduit part au serveur, le reste est évalué localement. Selon le dialecte :
   - WFS : `QgsOgcUtils.expressionToOgcFilter` (dans la version WFS de la couche) fait foi ;
   - OGC API Features : seulement ce que le provider de cette version de QGIS sait envoyer ;
   - ArcGIS, MSSQL, Oracle, HANA : SQL simple (comparaisons, `IN`, `LIKE`, `IS NULL`, `AND` / `OR` / `NOT`) ; `ILIKE` réécrit en `UPPER(..) LIKE UPPER(..)` là où c'est exact ; aucune fonction QGIS.
3. Brancher la traduction avant tout `setSubsetString` sur une source ou une cible service :
   - `FULL` : le subset est posé ;
   - `PARTIAL` / `NONE` : refus clair qui nomme ce qui ne passe pas, la couche reste telle quelle ;
   - subset refusé par le provider (retour `False`, couche invalide) : détecté et remonté comme un échec.
4. Vérifier que l'API REST, le MCP et Processing passent par ce même chemin quand ils posent un filtre attributaire sur un service.

**Contrat avec le lot B.** Tu exposes `translate(...)` et son résultat `ServerTranslation`. Le lot B expose `adapters/qgis/remote_materializer.py` : une tâche qui lit une couche service bornée (emprise, plafond, délai, annulation), applique localement une expression et renvoie les clés avec un indicateur « complet / partiel ». Le lot qui fusionne en second branche « `PARTIAL` / `NONE` → matérialisation » ; d'ici là, refus clair.

**Fini quand.**
- Les règles de chaque dialecte sont couvertes par des tests purs.
- `check_stream_vector_filters.py` est vert en ltr et stable.
- Sur le WFS Géoplateforme, `"nom" = 'L''Isle-Jourdain'` garde 1 commune, et une fonction non traduisible est refusée avec un message, sans « filtre appliqué » mensonger.

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
