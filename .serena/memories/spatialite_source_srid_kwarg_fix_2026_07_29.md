
# Fix: SpatialiteExpressionBuilder.build_expression() ignorait le kwarg source_srid

**Date:** 29 juillet 2026
**Fichier:** `adapters/backends/spatialite/expression_builder.py` (méthode `build_expression`, ~ligne 230-252)
**Tests:** `tests/unit/adapters/backends/spatialite/test_expression_builder.py`
**Branche:** `claude/spatialite-empty-filter-fix`

## Bug

`SpatialiteExpressionBuilder.build_expression()` ignorait le kwarg `source_srid`
passé par l'appelant et appelait systématiquement `self._get_source_srid()`
(défini dans `core/ports/geometric_filter_port.py`), qui lit
`task_params['infos']['layer_crs_authid']`.

Ce champ est rempli **une seule fois** par `initialization_handler.py` à partir
de la CRS *originale* de la couche source, et n'est **jamais mis à jour** après
reprojection. Or `configure_metric_crs()` (appelé inconditionnellement pour
toute CRS source non-métrique, pas seulement quand un buffer est demandé)
reprojette la géométrie source vers une CRS métrique — mais la variable
`self.source_layer_crs_authid` sur le `FilterEngineTask`, elle, EST mise à jour
après cette reprojection.

Le vrai flux d'appel (`FilterEngineTask.execute_geometric_filtering()` →
`self._get_expression_builder()` → `core/filter/expression_builder.py`
`ExpressionBuilder`) calcule bien `source_srid` à partir de
`self.source_layer_crs_authid` (donc la valeur *post-reprojection*) et le passe
en kwarg à `backend.build_expression(source_srid=self.source_srid, ...)`.

**Conséquence:** quand la CRS source originale == CRS cible (cas fréquent),
`self._get_source_srid() == target_srid` → `ST_Transform` est sauté → le WKT
(dans la CRS métrique reprojetée) est étiqueté avec le SRID géographique
d'origine → `ST_Intersects` ne matche jamais → `setSubsetString` réussit mais
la couche affiche 0 entités, silencieusement.

## Fix

```python
source_srid = kwargs.get('source_srid')
if source_srid is None:
    source_srid = self._get_source_srid()
```

Ceci **aligne Spatialite sur PostgreSQL** — `PostgreSQLExpressionBuilder.build_expression()`
faisait déjà `source_srid = kwargs.get('source_srid')` (sans fallback, voir
`adapters/backends/postgresql/expression_builder.py:197`). Spatialite n'avait
jamais reçu la même mise à jour.

## Tests ajoutés

Dans `TestBuildExpression` (test_expression_builder.py) :
- `test_source_srid_kwarg_overrides_task_params`: le kwarg `source_srid=4326`
  doit gagner sur `task_params["source_srid"]=2154` → pas de `ST_Transform`.
- `test_source_srid_falls_back_when_kwarg_missing`: sans kwarg, fallback sur
  `_get_source_srid()` (2154) → `ST_Transform` présent.

## Note environnement

pytest/pip absents de cet environnement sandbox (pas de venv détecté, `python3 -m pip`
indisponible). Validation faite via un script Python autonome qui reproduit le
harnais de mocks du fichier de test (mêmes assertions) — voir historique de
session pour le script. À relancer avec `pytest tests/unit/adapters/backends/spatialite/test_expression_builder.py`
dès qu'un environnement avec pytest est disponible.

## Lien

Voir aussi [[negative_buffer_wkt_handling]] (architecture WKT/buffer Spatialite/PostgreSQL)
et [[geographic_crs_handling]] (configure_metric_crs, reprojection EPSG:3857).
