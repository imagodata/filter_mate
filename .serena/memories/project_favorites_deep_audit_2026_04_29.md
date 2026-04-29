---
name: Favorites deep audit consolidation/harmonisation (2026-04-29)
description: Audit 360° post F4-step-3. 37 findings (6L + 16M + 15S). 3 cross-cutting CRIT vérifiés. Plan en 4 vagues. ~1635 LOC supprimables + restructuration ~1400 LOC.
type: project
---

Deep audit demandé 2026-04-29 sur favoris (gestion + harmonisation + consolidation). 3 agents parallèles : core/domain, UI, extension sharing. Périmètre ~13 000 LOC prod (hors tests).

**Why:** user a demandé un audit deep complet post-F4-step-3 (livré stages 1→5 du 2026-04-28).

**How to apply:** ces findings sont **dette de design / consolidation**, pas sécurité (déjà fermée). Les 3 CRIT-cross sont vérifiés grep dans la session.

## Cross-cutting CRITs vérifiés

### XCUT-1 — Deux `FavoritesService` instances vivent en parallèle (CORE-12)
- `filter_mate_app.py:452` → `self.favorites_manager = FavoritesService()`
- `ui/orchestrator.py:253` → `'favorites': FavoritesService(self._dockwidget)`
Deux instances → 2 SQLite connections, 2 caches, signaux `favorites_changed` divergents. Régression latente du fix CRIT-4 (audit 2026-04-23).
**Action** : orchestrator reçoit l'instance via DI depuis l'app. **L, à faire en priorité.**

### XCUT-2 — F5 invariant cassé : dialog importe l'extension sharing en fallback (UI-4 ≡ EXT-3)
- `ui/dialogs/favorites_manager.py:1281` → `from ...extensions.favorites_sharing.ui import SharedFavoritesPickerDialog`
- `ui/dialogs/favorites_manager.py:1316` → `from ...extensions.favorites_sharing.ui import PublishFavoritesDialog`
R1 (commit eacb5c2a) avait routé via bridge mais a laissé un fallback. C'est exactement le pattern que F5 voulait éliminer.
**Action** : drop fallback (bridge constructor-injected, `None` impossible en prod). ~50-70 LOC. **M, quick win.**

### XCUT-3 — F4 step 3 = code displacement, pas seam-extraction (UI-1)
`favorites_spatial_handler.py:11-17` rejette explicitement le Protocol `DockwidgetSurface` du design memo. Le handler grappille `dockwidget.*` partout (~20 widgets/attrs). 900 LOC déplacées sans seam testable headless.
**Action** : poser le Protocol promis + facade typée. Sinon F4 step 3 reste à finir. **L, dette directe du sprint qui vient de finir.**

## Tableau synthétique findings (37 total)

### Couche CORE (12 findings — 3L + 5M + 4S, ~600 LOC)
- **CORE-1 (L)** : `_favorites_manager` est en réalité un Service injecté ; tous les `hasattr` du controller sont dead-defensive. Renommer + drop guards (~120 LOC).
- **CORE-2 (L)** : 4 sites SQL bypass F7 timestamp/owner policy (`make_favorite_global`, `copy_to_global`, `import_global_to_project`, `migrate_orphan_favorites`). Router via `add_favorite/update_favorite` ou `_persist_row()` privé.
- **CORE-3 (M)** : 5 méthodes Service + 6 signaux Qt orphans (`apply_favorite`, `create_from_current_state`, `set_callbacks`, `get_global_favorites`, `get_all_with_global`, `copy_to_global`, `import_global_to_project`, signaux `favorite_added/removed/updated/applied/imported/exported`). Delete-only ~250 LOC.
- **CORE-4 (S)** : `save()` / `save_to_project()` = no-op qui delegate à un no-op. `load_from_project` ≡ `load_from_database`. ~30 LOC.
- **CORE-5 (M)** : pas de `fm_meta(schema_version)` table. `_backfill_remote_layer_signatures` re-scanne la table à chaque set_database(). Ajouter version-bump guard.
- **CORE-6 (S)** : duplicate aliases `get_favorite/get_by_id`, `count/get_favorites_count`, `load_from_project/load_from_database`. Garder un seul. ~25 LOC.
- **CORE-7 (M)** : contrat erreurs 3-têtes (Optional[str] vs raise vs result-dataclass vs return False). `remove_favorite("missing-id")` indistinguable de succès. F16 phase 3 skip se voit.
- **CORE-8 (S)** : `TABLE_FAVORITES` / `TABLE_PROJECTS` constants jamais utilisées. 22 SQL sites en literal `'fm_favorites'`. Soit threader, soit delete.
- **CORE-9 (S)** : domain leak `_project_uuid` lu par dialog ligne 872. Dialog ré-implémente `list_by_scope` au lieu de l'appeler.
- **CORE-10 (M)** : `restore_from_project_file` (~107 LOC) + `import_favorites` (~80 LOC) duplicate dedup logic. Extraire `_merge_favorites()`.
- **CORE-11 (S)** : `FavoritesMigrationService.ensure_global_project_exists` orphan + DDL inline dupliqué dans manager.
- **CORE-12 (M)** : XCUT-1 ci-dessus.

### Couche UI (13 findings — 3L + 6M + 4S, ~785 LOC)
- **UI-1 (L)** : XCUT-3 — Protocol DockwidgetSurface absent.
- **UI-2 (L)** : `FavoritesManagerDialog` god-class 1347 LOC (31 méthodes + 190 LOC QSS inline). Extraire `FavoritesListView`, `FavoritesScopeFilter`, `FavoriteDetailEditor`, `FavoriteSharingButtonsBar`. ~500 LOC.
- **UI-3 (L)** : `_get_dialog_stylesheet` 190 LOC inline duplique `favorites_styles.py` (qui a 95 LOC et est l'évier prévu). Move/merge.
- **UI-4 (M)** : XCUT-2 ci-dessus.
- **UI-5 (M)** : 6 délégations spatiales du controller sont 100% pures (`_restore_spatial_config`, `_capture_spatial_config`, `_apply_favorite_subsets_directly`, `_ensure_applicable_groupbox_for_favorite`, `_restore_filtering_ui_from_favorite`, `_backfill_legacy_predicate_default`). Inline les 5-6 callers, drop. ~30 LOC.
- **UI-6 (M)** : `dialog.favoriteApplied.connect(self.apply_favorite)` ligne 607 sans disconnect. Symétrique de F13. Cleanup au close.
- **UI-7 (M)** : `_restored_task_features` / `_restored_predicates` écrits depuis handler, lus depuis dockwidget. Encapsuler `RestoredSpatialState` dataclass owned by handler.
- **UI-8 (M)** : `favorites_menu_builder.build()` lit `controller._is_sharing_extension_active`, `_extension_bridge.get_menu_actions`, `_get_global_favorites` (3 private). Le Protocol `MenuActionsContext` existe mais n'est pas utilisé. Wire BuilderContext explicite.
- **UI-9 (M)** : `_cleanup_orphan_projects` / `_show_database_stats` répètent 10 LOC bootstrap migration_service. Helper `_get_migration_service()`. ~15 LOC.
- **UI-10 (S)** : `_show_database_stats` finit en `QMessageBox.information` blocking. Convertir en `show_info` (F11 alignment).
- **UI-11 (S)** : 5 lignes blank vestigiales après extractions F4 step 3 stage 5 (controller:889-897).
- **UI-12 (S)** : `MenuActionsContext` Protocol manque `is_sharing_active()`.
- **UI-13 (S)** : `_show_global_favorites_dialog` redondant avec `show_manager_dialog` + scope filter (post-F10). Router `ACTION_SHOW_GLOBAL` via scope preset, drop dialog dédié.

### Couche EXTENSION (12 findings — 2L + 5M + 5S, ~250 LOC + restructuration ~1400 LOC)
- **EXT-1 (L)** : `PublishFavoritesDialog` god-dialog 844 LOC, 5 responsabilités (defaults, UI build, target resolution, metadata collect, git lifecycle). Extraire `PublishDialogModel` (~250 testable sans Qt) + `PublishController` (~150). Vue → ~400 LOC.
- **EXT-2 (L)** : `FavoritesSharingService` god-class 607 LOC, 5 domaines (scan, fork, publish targets, bundle production, helpers). Splitter en `SharedFavoritesQuery` + `FavoritesForkService` + `BundlePublisher`. Service final = facade ~80 LOC.
- **EXT-3 (M)** : XCUT-2 (≡ UI-4).
- **EXT-4 (M)** : `publish_dialog.py:354` reach-into `service._scanner.get_collections_root()`. Ajouter `service.has_configured_collections_root()`.
- **EXT-5 (M)** : 10× `return False` dans extension, 0 usage `FavoritesError` (livré F16). Result-types OK pour worker mais validation paths devraient lever. ~30 LOC re-mapping.
- **EXT-6 (M)** : legacy `auth_header` partout (RemoteRepo, serdes, prepare_clone, test_connection, publish_to_remote, GitClient._resolve_auth_header, _auth_label, RepoEditDialog prefill). Deadline 5.0.0 mais aucun test fail-fast. Ajouter guard test + planifier suppression ~80 LOC au bump majeur.
- **EXT-7 (M)** : restes duplications post-F17 entre `publish_dialog`/`repo_manager_dialog`/`git_binary_dialog` (worker strong-ref + closeEvent wait + 16 callsites QMessageBox warning/critical). Extraire `WorkerLifecycleMixin` + `_show_git_error()` helper. ~60 LOC.
- **EXT-8 (S)** : `RemoteRepoManager._git_binary_or_default` (l.311) + `git_binary_dialog._refresh_status` ré-implémentent ce que `git_resolver.resolve_for_extension` fait déjà. Centraliser via cache mémoïsé. ~12 LOC.
- **EXT-9 (S)** : validator accepte v1/v2/v3 + warn>3, mais tests couvrent uniquement v3. Ajouter cas v1, v2, v4.
- **EXT-10 (S)** : `path_utils.py` 81 LOC, tout utilisé. **Garder.**
- **EXT-11 (S)** : `git_worker.py` (post-F17), abstraction propre. **Garder.**
- **EXT-12 (S)** : scanner ↔ validator integration correcte. `_extra` round-trip non implémenté (acceptable). **OK structurellement.**

## Plan en 4 vagues recommandé

### Vague 1 — XCUTs critiques (3-4 jours)
1. XCUT-1 / CORE-12 : DI orchestrator → 1 instance Service.
2. XCUT-2 / UI-4 / EXT-3 : drop fallback imports dialog.
3. XCUT-3 / UI-1 : poser `DockwidgetSurface` Protocol + facade.
**Why:** ces 3 sont des invariants F5/CRIT-4 cassés ou sprints F4 inachevés.

### Vague 2 — Quick wins delete-only (4-5 jours)
- CORE-3 (~250 LOC orphans + signals)
- CORE-4 (~30 LOC no-op aliases)
- CORE-6 (~25 LOC duplicate aliases)
- CORE-8 (3 LOC unused constants)
- CORE-11 (~40 LOC orphan migration helper)
- UI-5 (~30 LOC delegations)
- UI-11 + UI-13 (~15 LOC cleanup)
- EXT-8 (~12 LOC duplicate git resolution)
**Total ~400 LOC delete pure.** 0 risque.

### Vague 3 — Harmonisation contracts (5-7 jours)
- CORE-1 : rename `_favorites_manager` → `_favorites_service` + drop hasattr guards (~120 LOC).
- CORE-2 : router 4 sites SQL via `add_favorite/update_favorite` (audit F7 honoré).
- CORE-7 : décider une stratégie d'erreur unique (recommend : domain raise typed, service convert to result-dataclass pour Qt boundary).
- CORE-10 : extraire `_merge_favorites()` shared.
- UI-6 / UI-7 : signal hygiene + `RestoredSpatialState`.
- UI-8 / UI-12 : honorer `MenuActionsContext` Protocol existant.
- UI-9 + UI-10 : helper migration_service + alignement feedback.
- EXT-4 / EXT-5 : drop reach-into + propager `FavoritesError` aux validation paths.
- EXT-7 : `WorkerLifecycleMixin` + helper git error.
- EXT-9 : tests v1/v2/v4 validator.

### Vague 4 — Décompositions god-class (10-15 jours)
- UI-2 + UI-3 : décomposer `FavoritesManagerDialog` 1347 LOC + extraire QSS dialog vers `favorites_styles.py`.
- EXT-1 : `PublishFavoritesDialog` → Model + Controller + View.
- EXT-2 : `FavoritesSharingService` → 3 services + facade.
- CORE-5 : `fm_meta(schema_version)` + version-bump guards backfills.
**Restructuration majeure** (~3000 LOC touchées, ~1400 LOC réorganisées).

### Décisions différées
- **EXT-6 auth_header purge** : à faire au bump 5.0.0 (deadline existante). Ajouter test guard maintenant.
- **F4 step 3 cleanup final** : Vague 1 (XCUT-3) + Vague 2 (UI-5).

## Récap chiffré
- **37 findings** : 6 L · 16 M · 15 S
- **~1635 LOC supprimables** (CORE 600 + UI 785 + EXT 250)
- **~1400 LOC à restructurer** (3 god-classes : FavoritesManagerDialog, PublishFavoritesDialog, FavoritesSharingService)
- **3 cross-cutting CRITs** (F5/F4 invariants cassés ou sprint inachevé) → Vague 1 obligatoire avant nouveau feature
- Effort total : 22-31 jours (3 dev semaines + 1.5 semaines facultatif Vague 4)

## Anti-patterns à mémoriser

1. **Service ↔ Manager attribute lie** (CORE-1) : un attribut nommé `_xxx_manager` qui contient en réalité un `XxxService` est un piège diagnostique récurrent. Refuser cette indirection.
2. **Bridge bypass via fallback** (XCUT-2) : un import direct guardé par `if extension_bridge is None` annule le bénéfice du bridge — le `None` n'arrive jamais en prod, donc le fallback n'est qu'une back door.
3. **Protocol promis non posé** (XCUT-3) : extraire une classe sans définir le seam (Protocol/facade) = code displacement. Mesure : si le test headless du nouveau module a besoin de `MagicMock` au lieu d'une dataclass typée, le seam manque.
4. **SQL inline qui bypass policy domain** (CORE-2) : 4 sites SQL ont raté F7 (timestamp policy) parce qu'ils écrivent directement la table au lieu de passer par le manager. Toute écriture sur `fm_favorites` doit passer par add_favorite/update_favorite/remove_favorite.

## Fichiers neufs/à créer (Vague 1+3)
- `ui/controllers/favorites_dockwidget_surface.py` — Protocol DockwidgetSurface (XCUT-3)
- `ui/widgets/favorites_list_view.py` (UI-2)
- `ui/widgets/favorite_detail_editor.py` (UI-2)
- `extensions/favorites_sharing/publish/model.py` (EXT-1)
- `extensions/favorites_sharing/publish/controller.py` (EXT-1)
- `extensions/favorites_sharing/services/{shared_query,fork,bundle_publisher}.py` (EXT-2)
