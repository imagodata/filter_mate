# Lot D — Rasters en flux : COG, WCS, WMS / WMTS / XYZ (étape 6)

**But.** Chaque raster en flux est traité selon ce qu'il contient :
- un COG distant ou postgresraster est un raster de valeurs, lu sans geler QGIS ;
- un WCS est un raster de valeurs, lu sur une emprise et une résolution bornées ;
- un WMS, WMTS, XYZ ou ArcGIS MapServer n'offre que la pipette couleur, sur un rendu maîtrisé, avec un avertissement.

**Fichiers à toi.**
- `adapters/qgis/point_cloud_capability.py` : `ANALYSIS_RASTER_PROVIDERS`, `NON_ANALYSIS_RASTER_PROVIDERS`, `exclude_non_analysis_rasters`, `is_raster_layer`, `get_layer_kind`, `layer_kind_by_class` ;
- `adapters/qgis/coverage_layers/raster_adapter.py` (`band_range`, `band_histogram`, dérivés) et `gdal_warp.py` ;
- `ui/widgets/coverage_panels/raster_*.py` ;
- les parties raster de `ui/controllers/coverage_mode_controller.py` (`_populate_raster`) et de `ui/controllers/coverage_dock_extras.py`.

Le lot E ajoute une ligne pour les tuiles vectorielles dans `get_layer_kind` : garde-la en fusionnant.

**État au 19/10.**
- WMS, WCS et ArcGIS MapServer sont exclus des listes.
- Un GDAL WMS / XYZ est reconnu comme rendu et exclu aussi.
- Statistiques et histogrammes sont lus sur le thread principal au changement de couche, d'où un gel sur un COG distant.

**À faire.**
1. Mesurer sur un COG public en `/vsicurl/` : durée et octets lus au changement de couche, à l'aperçu et au filtre.
2. COG distant et postgresraster :
   - statistiques, histogrammes et dérivés de terrain calculés en tâche, annulables, avec résultat périmé ignoré ;
   - lectures bornées à l'emprise utile ;
   - aucune lecture sur le thread principal au changement de couche.
3. WCS :
   - admis comme raster de valeurs ;
   - lecture bornée : emprise de la vue ou de la source, résolution plafonnée par les réglages `MAX_PIXELS` / `RESOLUTION` existants ;
   - comme source ou cible : copie GeoTIFF locale dans le cache de session (mécanisme des fichiers dérivés, `snapshots.DerivedSourceRegistry`), jamais dans les dossiers de l'utilisateur.
4. WMS / WMTS / XYZ / ArcGIS MapServer / GDAL WMS :
   - admis dans le dock pour la seule pipette couleur, sur un rendu dont la résolution et l'emprise sont maîtrisées ;
   - avertissement : « couleurs rendues : elles dépendent du style et de l'échelle » ;
   - bandes, indices, seuils, classes et dérivés désactivés, avec leur raison ;
   - jamais cible d'un filtre.
5. Même traitement partout : listes de couches du dock, « Couches à filtrer », Processing, API REST et MCP (`layer_kind_by_class`). Un raster rendu n'est jamais pris pour un raster de valeurs.

**Fini quand.**
- `check_stream_raster.py` est vert, avec un COG servi par un serveur HTTP local ; WCS et WMTS publics en SKIP sans réseau.
- Un filtre croisé depuis une sélection couleur sur l'ortho WMTS de la Géoplateforme fonctionne.
- Aucun gel mesuré sur un COG distant.

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
