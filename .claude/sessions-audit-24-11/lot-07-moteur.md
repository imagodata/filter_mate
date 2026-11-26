# Lot 7 — Moteur : JSON, NOT/NULL, perfs (audit 24/11/2026)

## Contexte
Plugin FilterMate, base `main` à `a03bb9e0`. Le passage des listes de clés en JSON (#636) tient, y compris sous 3.22. Ne rien corriger hors de ce lot.

## Défauts à corriger
1. Sous-ensemble hybride GeoPackage : liste IN en clair jusqu'à 100 000 clés. 50 000 clés → 11,1 s de gel du thread principal + 3,75 s par lecture ; 0,02 s en JSON.
   - `filtermate_core/filter/native_dialect.py:963` (ouvert depuis le 19/11, hors #636) → forme JSON pour les hybrides GPKG.
2. GDAL 3.4.1 (QGIS 3.22/3.28) garde les NULL sous NOT (`"x" > 5`) et NOT IN : 3 entités au lieu de 2 sur Shapefile ; égal sous GDAL 3.12.
   - `native_dialect.py:591` et `:684` (ouvert depuis le 18/11) → barrière de version GDAL.
3. `json_key_clause` : `int('²')` lève `ValueError` (`isdigit()` vrai pour chiffre Unicode).
   - `adapters/backends/ogr/expression_builder.py:185` → `try int()` / `isdecimal` strict.
4. Second rang : lectures de couche restantes dans les tâches (`filter_executor.py:826`, `filter_task.py:348`, #593) ; `__source` dans une valeur efface le sous-ensemble comme « corrompu » (`core/filter/filter_orchestrator.py:494`, très basse).

## Vérification
- `check_native_translation.py` + sonde 50 000 clés (temps avant/après) + image 3.22 pour le cas NOT/NULL.
- Vérifié sans régression : `json_each` sous 3.22, clés > 2^53, apostrophe/guillemet/antislash/Unicode, JSON réservé GPKG+SQLite. Rendre compte sans committer.
