# FilterMate 5.1 — Sources en flux : plan de développement en parallèle

> Rédigé le 19/10/2026. Source : section « Sources en flux » de l'audit du 17/10/2026
> (https://claude.ai/artifact/DJFuADfmk7UXVrpRSYQXux). Les étapes 0 à 2 de l'audit ont été livrées par #155 :
> capacité de source, clé stable, au plus 500 clés envoyées à un service, aucun comptage réseau sur le thread principal.
> Les étapes 3 à 7 sont découpées ici en cinq lots parallèles (A à E) et un lot de clôture (F).

Chaque `prompt-lot-X.md` est complet : il contient la mission du lot, puis les mêmes règles communes. Un prompt se colle
tel quel dans une session Claude Code. Chaque session travaille dans son propre worktree (`.claude/worktrees/stream-<lot>`)
et sur ses propres branches `claude/v5-stream-<lot>-…`.

## État d'avancement (19/10/2026)

| Lot | Étape de l'audit | Contenu | État |
|---|---|---|---|
| A | 3, filtres attributaires | Traduction contrôlée vers le serveur (filtre OGC pour WFS, SQL simple pour ArcGIS / MSSQL / Oracle / HANA) ; refus clair sinon ; provider préparé en tâche | fusionné, #192 |
| B | 3, filtres spatiaux, et 4 | Emprise envoyée au serveur, prédicat exact en local, matérialisation bornée en tâche | en cours |
| C | 5 | Valeurs, liste d'entités, zoom et emprise filtrée en tâche, annulables, jeton de génération | fusionné, #193 |
| D | 6 | COG / postgresraster en tâche, WCS raster de valeurs, pipette couleur seule sur WMS / WMTS / XYZ | fusionné, #190 |
| E | 7 | Tuiles vectorielles cibles (filtre dans les styles du renderer), EPT / COPC distants bornés | fusionné, #191 |
| F | clôture | i18n, CI, essai bout en bout, CHANGELOG, documentation, mise à jour de l'audit | après B |

## Répartition des fichiers

| Lot | Fichiers principaux |
|---|---|
| A | `core/filter/server_dialect.py`, `adapters/qgis/server_filter_translation.py`, `adapters/backends/ogr/expression_builder.py`, chemin attributaire de `filter_executor.py` |
| B | `execute_ogr_spatial_selection` dans `filter_executor.py`, `adapters/qgis/remote_materializer.py`, `core/domain/materialization.py` |
| C | `exploring_controller.py`, `custom_widgets.py`, `filter_mate_dockwidget.py` (emprise filtrée), `integration.py`, `layer_selection_mixin.py` |
| D | `point_cloud_capability.py`, `raster_adapter.py`, `gdal_warp.py`, `coverage_panels/raster_*.py`, parties raster des contrôleurs |
| E | `pdal_cli.py`, `hag_task.py`, parties nuage de `target_appliers.py` / `source_jobs.py`, `vector_tile_*.py`, `snapshots.py` |
| F | `i18n/*`, `.github/workflows/*`, `tests/qgis_headless/run_smoke.py`, `CHANGELOG.md`, `docs/ARCHITECTURE.md` |

Fichiers partagés, en ajout seulement : `core/domain/source_capability.py`, `CHANGELOG.md`, `.claude/memory.md`.

## Raccords entre lots

- **A ↔ B** : A expose `translate(...)` → `ServerTranslation` (`FULL` / `PARTIAL` / `NONE`) ; B expose la matérialisation
  bornée. Le lot fusionné en second branche « `PARTIAL` / `NONE` → matérialisation ». A est fusionné : c'est à B de le faire.
- **D ↔ E** : une ligne dans `get_layer_kind` pour les tuiles vectorielles. Fait (`LayerKind.VECTOR_TILE`).

## Points relevés pour le lot F

- **Filtre attributaire WFS / ArcGIS refusé hors QGIS 3.44 et 4.2** (`adapters/qgis/server_subset_job.py`) : il est refusé
  sous 3.32, et au-delà la liste blanche est figée sur `(344, 402)`. Or `qgisMinimumVersion=3.22`. Correction proposée,
  à confirmer : vérifier le transfert asynchrone dans les images 3.34, 4.0 et nightly et l'autoriser là où il passe ;
  sous 3.32, appliquer un filtre WFS entièrement traduisible de façon synchrone comme avant #192, et garder le refus
  pour ArcGIS.
- **Revue du lot C** : #193 a été relu sans `opus-reviewer` (indisponible dans la session). Refaire une revue adversariale.
- **i18n** : environ 135 nouvelles chaînes pour A, C, D et E (listées dans chaque PR), plus celles de B. Les PR i18n
  précédentes (#143, #144) traduisaient les 34 langues.
- **OGC API Features** : toujours refusé côté serveur par A (aucun verdict CQL2 complet exposé par le provider) ;
  à revoir une fois la matérialisation de B branchée.
- **Plantage natif** observé une fois sur un WFS public pendant le lot C, non reproduit.
