# FilterMate 5.1 — Sources en flux : plan de développement en parallèle

> Rédigé le 19/10/2026. Source : section « Sources en flux » de l'audit du 17/10/2026
> (https://claude.ai/artifact/DJFuADfmk7UXVrpRSYQXux). Les étapes 0 à 2 de l'audit ont été livrées par #155 :
> capacité de source, clé stable, au plus 500 clés envoyées à un service, aucun comptage réseau sur le thread principal.
> Les étapes 3 à 7 sont découpées ici en cinq lots parallèles (A à E) et un lot de clôture (F).

Chaque `prompt-lot-X.md` est complet : il contient la mission du lot, puis les mêmes règles communes. Un prompt se colle
tel quel dans une session Claude Code. Chaque session travaille dans son propre worktree (`.claude/worktrees/stream-<lot>`)
et sur ses propres branches `claude/v5-stream-<lot>-…`.

## État d'avancement (20/10/2026 : terminé)

| Lot | Étape de l'audit | Contenu | PR |
|---|---|---|---|
| A | 3, filtres attributaires | Traduction contrôlée vers le serveur (filtre OGC pour WFS, SQL simple pour ArcGIS / MSSQL / Oracle / HANA) ; refus clair sinon ; provider préparé en tâche | #192 |
| B | 3, filtres spatiaux, et 4 | Emprise envoyée au serveur, prédicat exact en local, matérialisation bornée en tâche | #195 |
| C | 5 | Valeurs, liste d'entités, zoom et emprise filtrée en tâche, annulables, jeton de génération | #193 |
| D | 6 | COG / postgresraster en tâche, WCS raster de valeurs, pipette couleur seule sur WMS / WMTS / XYZ | #190 |
| E | 7 | Tuiles vectorielles cibles (filtre dans les styles du renderer), EPT / COPC distants bornés | #191 |
| F | clôture | i18n 34 langues (#196) ; plantage QGIS 3.34.15 / Python 3.12 (#197) ; revue du lot C (#198) ; filtres serveur de 3.22 à nightly (#199) ; API publique sur les flux (#200, #201) ; gel du premier clic Filtre (#203) ; course du fournisseur détruit (#205) ; derniers défauts (#206) ; CI (#204) ; documentation | voir colonne |

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
  bornée. Branché par #195 (`materialize_translation`).
- **D ↔ E** : une ligne dans `get_layer_kind` pour les tuiles vectorielles. Fait (`LayerKind.VECTOR_TILE`).

## Restes connus après le lot F

- **Limite de 500 clés vers un service** : le cas « département → communes du WFS IGN » (748 clés) est refusé avec le
  conseil d'une copie locale. Étude prévue : longueur de liste acceptée par la Géoplateforme, envoi en POST, prédicat
  spatial OGC côté serveur.
- **OGC API Features** : un filtre attributaire reste refusé côté serveur (le provider n'expose pas de verdict CQL2
  complet) ; la matérialisation bornée couvre les filtres spatiaux et les entités sélectionnées.
- **QGIS 3.22** : filtre WFS refusé (son setter corrompt la mémoire pendant un rendu) ; **3.24–3.31** : WFS synchrone
  (gel borné par la requête en cours) ; **3.26–3.35 sous Python 3.12** : lectures de service refusées (#197).
- **Gardes `activeTasks()`** encore utilisées ailleurs (`cross_filter_service`, `filter_task._drop_deferred_views`,
  `filter_mate_app._cancel_conflicting_tasks`) : une tâche dans son `finished()` y est invisible.
- **Jointure ou champ virtuel** sur une source service filtrée : refusés par le contrôle des champs de
  `remote_materializer.py`.
- **Dette i18n antérieure** : libellés des prédicats (anglais par conception), menus des favoris, `tr(f"…")` de
  `filter_mate.py` et `postgres_info_dialog.py`, modules hors de `FilterMate.pro`.
- Le WCS de la Géoplateforme n'existe plus : l'essai de bout en bout utilise le WCS de démonstration MapServer.
