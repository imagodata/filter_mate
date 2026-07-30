# Fix: SELECTION mode outranking FIELD_BASED/ALL-FEATURES mode in source-mode resolution

**Date:** 30 juillet 2026
**Fichiers:**
- `adapters/backends/spatialite/filter_executor.py` (`determine_spatialite_source_mode`, ~ligne 105-167)
- `adapters/backends/ogr/filter_executor.py` (`determine_source_mode`, ~ligne 592-647)
**Tests:**
- `tests/unit/adapters/backends/spatialite/test_filter_executor.py` (nouveau fichier, 6 tests)
- `tests/unit/adapters/backends/ogr/test_filter_executor.py` (`TestDetermineSourceMode`, 2 tests ajoutés)

## Contexte / symptôme rapporté

Filtre spatial "intersecte" sur une couche cible GeoPackage (backend Spatialite,
`.gpkg` → `detect_layer_provider_type()` retourne `'spatialite'`), avec la
couche source en mode UI "Custom Selection" et une expression toujours vraie
(idiome `1` = "prends toutes les features actuelles de la couche, qu'elle soit
déjà filtrée ou non"). Résultat observé : 0 entités filtrées côté couche
distante, **aucune erreur visible**.

Note : la syntaxe SQL générée pour GeoPackage-via-OGR
(`ST_Intersects`/`ST_MakeValid`/`ST_GeomFromText`, préfixe `ST_` obligatoire —
voir [[negative_buffer_wkt_handling]]) a été vérifiée empiriquement **valide**
via `ogrinfo`/GDAL 3.11 (requête exécutée avec succès contre un vrai .gpkg en
EPSG:31370) avant de creuser plus loin — ce n'était PAS la cause.

## Root cause

`core/services/source_layer_filter_executor.py::_execute_all_features_mode()`
positionne correctement `is_field_expression=(True, "__all_features__")`
quand l'expression custom est un littéral toujours vrai (détecté par
`adapters/task_builder.py::determine_skip_source_filter()` — absence
d'opérateur de comparaison dans l'expression). Ce flag est censé forcer le
mode FIELD_BASED en aval : "utilise `layer.getFeatures()` sans le préfiltrer
par une sélection quelconque", ce qui respecte automatiquement le
`subsetString()` courant de la couche (API QGIS standard).

Mais `determine_spatialite_source_mode()` a une cascade de priorité :

```python
if has_task_features and not is_field_based_mode:
    return SourceMode.TASK_PARAMS, metadata
elif has_subset and not has_task_features:
    return SourceMode.SUBSET, metadata
elif has_selection:                      # <-- BUG: pas de "and not is_field_based_mode"
    return SourceMode.SELECTION, metadata
elif is_field_based_mode:
    return SourceMode.FIELD_BASED, metadata
else:
    return SourceMode.FALLBACK, metadata
```

La branche `SELECTION` n'était pas gardée par `is_field_based_mode`,
contrairement à la classe sœur `SourceFeatureResolver` (`adapters/qgis/source_feature_resolver.py`,
lignes ~198-203, `if has_selection and not is_field_based_mode:`) — écrite
~13h plus tôt le même jour (`4247b623`, MIG-204) que `determine_spatialite_source_mode`
(`16f9cb15`). Le garde n'a jamais été propagé au duplicata Spatialite lors de
son extraction depuis `filter_task.py` (EPIC-1 Phase E4-S8).

Donc si la couche source avait, au moment du filtrage, une **sélection QGIS
résiduelle** (features surlignées suite à une interaction précédente,
totalement indépendante de l'intention "Custom Selection = toutes les
features") avec `selectedFeatureCount() > 0`, le mode SELECTION gagnait sur
FIELD_BASED. La géométrie source utilisée pour le prédicat spatial était donc
construite à partir de cette poignée de features non pertinentes au lieu de
*toutes* les features de la couche respectant son état de filtre courant —
d'où une intersection ne matchant rien contre la couche distante, sans erreur
(la requête SQL est parfaitement valide, elle porte juste sur la mauvaise
géométrie).

Même bug dupliqué dans le backend OGR (`elif has_subset or has_selection:`
sans garde `is_field_based`) — ce backend est aussi emprunté pour des couches
GeoPackage via le sentinel `USE_OGR_FALLBACK` de `SpatialiteExpressionBuilder`
(buffer dynamique avec référence de champ, ou géométrie source de type
GeometryCollection) — corrigé en parallèle.

## Fix

```python
# spatialite/filter_executor.py
elif has_selection and not is_field_based_mode:
    return SourceMode.SELECTION, metadata

# ogr/filter_executor.py
elif has_subset or (has_selection and not is_field_based):
    ...
```

## Tests ajoutés

`tests/unit/adapters/backends/spatialite/test_filter_executor.py` (nouveau,
charge `determine_spatialite_source_mode` via `importlib` en mockant
uniquement `filter_mate.adapters.repositories.history_repository` — la
fonction est pure Python, aucun mock QGIS nécessaire) :
- `test_field_based_mode_wins_over_stale_selection` — le test de régression
  direct (échoue avant fix : `SELECTION` au lieu de `FIELD_BASED`).
- `test_field_based_mode_wins_over_stale_selection_with_existing_subset`
- `test_selection_mode_used_when_not_field_based` (non-régression)
- `test_field_based_mode_no_selection_no_subset`
- `test_task_params_mode_takes_priority`
- `test_fallback_mode_when_nothing_matches`

`tests/unit/adapters/backends/ogr/test_filter_executor.py::TestDetermineSourceMode` :
- `test_field_based_mode_wins_over_stale_selection`
- `test_subset_mode_wins_over_stale_selection_when_field_based`

Suite complète `tests/unit/` : 1491 passed après fix (aucune régression).

## Méthode de diagnostic (pour référence future)

1. Vérifié empiriquement que la syntaxe SQL GPKG-via-OGR n'était pas en cause
   (création d'un vrai .gpkg EPSG:31370 via `ogr2ogr`, requête exacte du
   plugin exécutée via `ogrinfo -where ...`, y compris test de mismatch
   volontaire du SRID interne — GDAL ne rejette pas, matche sur les
   coordonnées brutes).
2. Écarté le bug de SRID périmé déjà corrigé la veille
   ([[spatialite_source_srid_kwarg_fix_2026_07_29]]) — ne s'applique pas
   pour une CRS déjà métrique (pas de reprojection déclenchée par
   `configure_metric_crs()`).
3. Indice utilisateur déterminant : "sélection custom sur champs ou
   expression vraie comme 1, il faut filtrer avec tous les éléments de la
   couche dans l'état où elle est (déjà filtrée ou non)" → a orienté la
   recherche vers le pipeline "Custom Selection" / `is_field_expression`
   plutôt que vers la construction SQL.
4. Deux tracés indépendants (lecture manuelle du code + sous-agent
   d'exploration) ont convergé sur le même fichier/fonction.
5. Comparaison avec `SourceFeatureResolver` (classe sœur, déjà correcte) a
   révélé le garde manquant — recherche `git blame` a confirmé la chronologie
   (garde correct écrit en premier, duplicata buggé écrit ~13h après, jamais
   réconcilié).

## Lien

Voir aussi [[negative_buffer_wkt_handling]] (choix ST_-préfixé pour
GPKG-via-OGR) et [[spatialite_source_srid_kwarg_fix_2026_07_29]] (bug
apparenté de staleness sur `source_srid`, veille de ce fix).
