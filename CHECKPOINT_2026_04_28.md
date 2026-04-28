# Checkpoint — Consolidation Favoris + Resource Sharing

**Date** : 2026-04-28
**Branche** : `main`
**Commits poussés** : 22
**Tests** : 1113/1113 ✓ à chaque commit

---

## Vue d'ensemble

Session de consolidation/harmonisation complète sur le périmètre **favoris + Resource Sharing** de FilterMate. Tous les findings de l'audit interne `project_favorites_consolidation_audit_2026_04_27` ont été traités. Le sprint architectural F4 step 3 (12-14j prévu) a été abattu en autonomie.

**Bilan global** : ~1 100 LOC nettes supprimées, controller `FavoritesController` allégé de 42% (2015 → 1170 LOC), 3 nouveaux modules extraits, +8 tests unitaires.

---

## Commits — chronologique

### Cleanup pré-existant (3 commits)

| Hash | Sujet |
|---|---|
| `3eb92085` | chore: drop stale BACKLOG_RASTER_POINTCLOUD_V1.md |
| `2e4fba54` | fix(config): preserve EXTENSIONS panel label across config migrations |

### R1 + D1 — Bridge sovereign + dead widget (1 commit)

| Hash | Sujet | Net |
|---|---|---|
| `eacb5c2a` | refactor(favorites): route manager dialog via bridge + drop dead widget | +90 / -590 |

- **R1** : `FavoritesManagerDialog` reçoit le `FavoritesExtensionBridge` en injection, ses 3 méthodes sharing routent via le bridge. Restaure l'invariant F5 « single coupling point ».
- **D1** : suppression de `ui/widgets/favorites_widget.py` (564 LOC, jamais instancié, contenait un bug CRIT-3 latent).

### P1 — Rename `publish_bundle` (1 commit)

| Hash | Sujet |
|---|---|
| `a9cb13a9` | refactor(favorites-sharing): rename publish_bundle + flag auth_header deadline |

- `RemoteRepoManager.publish_bundle` → `publish_to_remote` (disambig de `FavoritesSharingService.publish_bundle`).
- Constante `LEGACY_AUTH_HEADER_DEADLINE = "5.0.0"` posée au scope module + nommée dans le warning per-repo + docstring.

### P2 — Wrappers BC purgés (2 commits)

| Hash | Sujet |
|---|---|
| `09d89f74` | refactor(favorites): drop BC wrappers, migrate to FavoriteImportHandler (P2) |
| `4b61e9fc` | chore(favorites): tidy P2 fallout — orphan import + blank lines |

- Suppression des 3 wrappers BC `FavoritesService._strip_project_bindings` / `_rebind_imported_favorite` / `_resolve_signature_to_layer_id`.
- Migration de `extensions/favorites_sharing/service.py:fork()` à `FavoriteImportHandler.rebind_to_project` direct (élimine reach into `_private` d'un service).
- Tests `test_favorites_portability.py` migrés à `FavoriteImportHandler.*` direct.

### F11 phase 1 — Politique feedback (1 commit)

| Hash | Sujet |
|---|---|
| `9aafd1ad` | refactor(favorites-ui): F11 phase 1 — feedback policy alignment |

- 5 callsites `QMessageBox` non-bloquants → `infrastructure.feedback.show_*` (messageBar QGIS).
- 2 helpers `_show_info` + `_show_error` ajoutés sur le controller.
- Helper `_show_error` ajouté sur le dialog.
- Bug pré-existant fixé : `_show_warning` / `_show_success` passaient `("FilterMate", message)` au lieu de `(message, "FilterMate")` → titre/message inversés.
- 4 sites `QMessageBox.question` (CONFIRM bloquants) documentés avec la raison.
- Static `FavoritesManagerDialog.show_dialog` (unused depuis R1) supprimé.

### F16 — Famille FavoritesError (4 commits)

| Hash | Sujet |
|---|---|
| `1458555b` | feat(favorites): introduce FavoritesError exception family (F16 phase 1) |
| `ca9b4891` | feat(favorites): wire FavoritesNotInitialized into service Cat A (F16 phase 2) |
| `3298ed06` | feat(favorites): wire FavoritesNotInitialized into manager Cat A (F16 phase 2b) |
| `64079af3` | feat(favorites): wire FavoritePersistenceError into Cat C (F16 phase 4) |

- **Phase 1** : 3 sous-classes (`FavoritesError`, `FavoritesNotInitialized`, `FavoriteNotFound`, `FavoritePersistenceError`) ajoutées à `core/domain/exceptions.py` + 8 tests.
- **Phase 2** : 7 sites service Cat A (precondition `if not self._favorites_manager`) → `raise FavoritesNotInitialized`. UI callers non wrappés (programmer-error tripwire).
- **Phase 2b** : 4 sites manager Cat A → idem, avec splits propres pour les sites mixtes (`remove_favorite` / `update_favorite` / `make_favorite_global` séparent precondition vs id-absent).
- **Phase 4** : 9 sites Cat C (`except Exception: return False`) → `raise FavoritePersistenceError(op, cause)`. 7 UI callers wrappés `_show_error` (controller + dialog).
- **Phase 3** (Cat B data-not-found → `FavoriteNotFound`) délibérément non livrée : `bool` documenté est le bon contrat pour les lookup miss innocents.

### F4 step 3 — God-class découpage (7 commits)

| Hash | Sujet | LOC controller |
|---|---|---|
| `a8ce7c10` | refactor(favorites): extract pure spatial helpers (F4 step 3 phase 1) | -90 |
| `59f8e9b3` | refactor(favorites): extract 4 stateless spatial helpers (F4 step 3 phase 2) | -140 |
| `dec63939` | refactor(favorites): start FavoritesSpatialHandler — extract 2 small methods (stage 1) | -100 |
| `ff29e5ce` | refactor(favorites): extract _capture_spatial_config to handler (stage 2) | -120 |
| `f25e83e7` | refactor(favorites): extract _restore_spatial_config to handler (stage 3) | -120 |
| `37208cf9` | refactor(favorites): extract _restore_filtering_ui_from_favorite (stage 4) | -190 |
| `85ef67df` | refactor(favorites): extract _apply_favorite_subsets_directly (stage 5) | -170 |

**Résultat** : controller passé de **2015 LOC → 1170 LOC** (-845 LOC, -42%).

#### Phase 1 — Helpers purs
Création de `ui/controllers/favorites_spatial_helpers.py` avec 2 fonctions module-level (`exact_filtered_feature_count`, `layer_signature_for`). Drop de `_collect_filtering_widgets_for_favorite` (dead code).

#### Phase 2 — Helpers stateless
4 méthodes stateless ajoutées : `should_downgrade_single_selection`, `resolve_favorite_source_layer`, `resolve_remote_layer_entry`, `favorite_matches_current_layer`. La 5e (`_backfill_legacy_predicate_default`) reportée à phase 3 car elle accède à `self._favorites_manager`.

#### Phase 3 — God-class découpage (5 stages)
Création de `ui/controllers/favorites_spatial_handler.py` (900 LOC). Pattern `FavoritesSpatialHandler(controller_ref)` (mirror `FavoritesExtensionBridge`). 6 méthodes lourdes migrées :

1. `backfill_legacy_predicate_default` (49 LOC) — heal des favorites legacy sans `geometric_predicates`
2. `ensure_applicable_groupbox_for_favorite` (50 LOC) — downgrade single→custom selection
3. `capture_spatial_config` (123 LOC) — read filtering widgets → spatial_config dict
4. `restore_spatial_config` (121 LOC) — push spatial_config back into widgets + `_restored_*` state
5. `restore_filtering_ui_from_favorite` (192 LOC, le plus dense) — 6-step UI orchestration + persist `PROJECT_LAYERS`
6. `apply_favorite_subsets_directly` (172 LOC) — write source + remote_layers subsets, refresh feature_count, auto_zoom

**Politique stage-1** : controller garde des délégations 1-line `def _method(self, ...): return self._spatial.method(...)`. Évite de toucher les callers internes et les tests existants.

`_spatial` est exposé comme **lazy property** sur le controller — eager construction dans `__init__` aurait forcé chaque test bypassant `__init__` via `__new__` à wirer le handler manuellement.

---

## État de l'arborescence — controllers favoris

```
ui/controllers/
├── favorites_controller.py          (1170 LOC) — orchestrateur + délégations
├── favorites_extension_bridge.py    (353 LOC)  — single coupling point avec extension sharing
├── favorites_menu_builder.py        (265 LOC)  — menu builder + ACTION_* sentinels
├── favorites_spatial_handler.py     (900 LOC)  — capture/restore/apply + 2 healers
└── favorites_spatial_helpers.py     (235 LOC)  — pure stateless helpers
                                     ─────────
                                     2923 LOC
```

Avant la session : un seul fichier `favorites_controller.py` à ~2400 LOC + le widget mort de 564 LOC + plusieurs wrappers BC dispersés. Total surface ~3000 LOC pour la même fonctionnalité.

---

## État final findings audit `project_favorites_consolidation_audit_2026_04_27`

| ID | Statut | Notes |
|---|---|---|
| F1, F2, F3, F6, F7, F10, F12, F13, F15, F17, F18, F19 | ✅ livrés | sessions 2026-04-27 |
| F5 stage 2 + R1 | ✅ livré | bridge sovereign |
| F9 / D1 | ✅ livré | widget mort supprimé |
| P1 | ✅ livré | rename `publish_bundle` |
| P2 | ✅ livré | wrappers BC dégagés |
| H5 | ✅ livré | deadline `auth_header` à 5.0.0 |
| F11 phase 1 | ✅ livré | politique feedback appliquée |
| F16 phases 1, 2, 2b, 4 | ✅ livrés | famille d'erreurs complète |
| F4 step 3 phases 1, 2, 3 (5 stages) | ✅ livrés | sprint architectural complet |
| F8 (signaux camelCase) | ⏸ skip délibéré | 92 touch points, gain purement cosmétique |
| F11 phase 3 (DRY mixin `_show_*`) | ⏸ skip | payoff trop faible (~10 LOC) |
| F16 phase 3 (Cat B `FavoriteNotFound`) | ⏸ skip délibéré | id absent reste `bool` documenté |
| F4 phase 4 (tests dédiés) | ⏸ pending | tests existants couvrent par délégation |
| F4 phase 5 (cleanup délégations + docs) | ⏸ pending | optionnel, 1j |

---

## Modules ajoutés / modifiés

### Nouveaux fichiers (production)
- `ui/controllers/favorites_spatial_handler.py` (900 LOC)
- `ui/controllers/favorites_spatial_helpers.py` (235 LOC)
- `core/domain/exceptions.py` — étendu de 4 sous-classes `FavoritesError` (+57 LOC)

### Nouveaux memory files (mémoire projet)
- `project_f11_feedback_policy_spike_2026_04_28.md`
- `project_f16_error_family_audit_2026_04_28.md`
- `project_f4_step3_spatial_handler_design_2026_04_28.md`
- `project_favorites_consolidation_2026_04_28.md`

### Fichiers supprimés
- `ui/widgets/favorites_widget.py` (564 LOC, dead code)
- `BACKLOG_RASTER_POINTCLOUD_V1.md`

### Fichiers modifiés (production)
- `core/domain/exceptions.py` — famille FavoritesError
- `core/domain/favorites_manager.py` — Cat A raise + Cat C raise
- `core/services/favorites_service.py` — Cat A raise + Cat C raise + wrappers BC purgés
- `extensions/favorites_sharing/service.py` — fork() utilise `FavoriteImportHandler` direct
- `extensions/favorites_sharing/remote_repo_manager.py` — rename + deadline
- `extensions/favorites_sharing/ui/publish_dialog.py` — rename caller
- `ui/controllers/favorites_controller.py` — délégations + lazy `_spatial` + UI wraps
- `ui/controllers/favorites_extension_bridge.py` — `parent`/`preselected_ids` kwargs
- `ui/controllers/favorites_spatial_handler.py` — création (Phase 3)
- `ui/controllers/favorites_spatial_helpers.py` — création (Phase 1+2)
- `ui/dialogs/favorites_manager.py` — bridge injection + `_show_error` + lazy import
- `ui/styles/favorites_styles.py` — docstring update post-D1
- `ui/widgets/__init__.py` — drop FavoritesWidget export
- `config/config.py` — _migrate_config strip legacy EXTENSIONS metadata
- `extensions/registry.py` — overlay metadata keys starting with `_`

### Tests modifiés
- `tests/unit/core/domain/test_exceptions.py` — +8 tests `TestFavoritesErrors`
- `tests/unit/core/domain/test_favorites_manager_persistence.py` — flip `returns_false_when_uninitialised` → `raises`
- `tests/unit/core/services/test_favorites_portability.py` — migrate à `FavoriteImportHandler.*`
- `tests/unit/extensions/favorites_sharing/test_security_hardening.py` — fixture stubs adaptés
- `tests/unit/ui/controllers/test_favorites_controller.py` — shim 3-niveaux + monkeypatch helpers binding

---

## Ce qui reste

| Item | Effort | Risque | Quand |
|---|---|---|---|
| F4 phase 4 (tests dédiés `test_favorites_spatial_handler.py`) | 2j | bas | optionnel — tests délégation existants couvrent |
| F4 phase 5 (drop délégations + docs architecture) | 1j | bas | optionnel — cleanup pure |
| F8 (signaux camelCase) | 1j | bas | rejeté définitivement |
| F11 phase 3 (DRY mixin `_show_*`) | 1h | bas | rejeté (payoff trop faible) |
| F16 phase 3 (Cat B `FavoriteNotFound`) | 0.5j | bas | rejeté délibérément |

**Aucune dette critique restante.** Le système favoris/Resource Sharing est dans un état production-clean.

---

## Patterns mémorisés

### Bridge / Handler — single coupling point
- `FavoritesExtensionBridge` : single coupling point UI ↔ extension sharing.
- `FavoritesSpatialHandler` : single seam pour la spatial-config orchestration.
- Pattern : `__init__(self, controller)` → reads back `self._controller.X` pour les dépendances UI (`tr`, `_show_warning`, `dockwidget`, `_favorites_manager`).
- Direction : controller → handler → dockwidget. Les handlers ne doivent jamais importer le controller (sauf TYPE_CHECKING).

### Lazy property pour les services injectés en `__init__`
Quand un service est créé dans `__init__` ET utilisé par des méthodes testées via `__new__`, exposer comme lazy `@property` avec cache `_X_instance` slot. Évite de faire wirer le service manuellement dans chaque test.

### Famille d'exceptions — extending vs new file
Quand une hiérarchie d'exceptions existe déjà (`FilterMateError` dans `core/domain/exceptions.py`), **étendre** ce fichier au lieu de créer un nouveau. Les sous-classes `FavoritesError(FilterMateError)` permettent à `except FilterMateError` de catch les domaines spécifiques sans connaître leur module.

### Programmer-error tripwire vs UX wrapper
Quand une exception signale un programmer-error « should never happen » (precondition non remplie), **ne pas wrapper** dans l'UI. Laisser propager → Qt log panel via exception hook. Wrapper masquerait le bug réel. Quand l'exception signale une infrastructure failure (DB lockée, disk full), wrapper avec `_show_error(...)`.

### Patches monkey vs binding namespace
`from X import Y` à l'intérieur d'une fonction crée une variable locale snapshot. Pour patcher, il faut :
- Soit patcher le module source (`X.Y`) — la prochaine entrée de la fonction re-snapshot.
- Soit hisser l'import au niveau module et patcher le module qui contient l'import.

Pour les tests qui patchaient `favorites_controller.layer_signature_for`, après migration vers `favorites_spatial_helpers`, il faut patcher `favorites_spatial_helpers.layer_signature_for` à la place.

### Stage-1 extraction policy
Lors d'une god-class extraction risquée :
1. Créer le nouveau module/handler.
2. Y déplacer la logique.
3. Garder dans la classe d'origine des **délégations 1-line** (`def _method(self, ...): return self._handler.method(...)`).
4. Tests existants passent sans modification.
5. Cleanup des délégations dans un commit séparé futur (optionnel).

Évite le big-bang testing while preservant la sémantique du diff par commit.

---

## Vérifications

```bash
# État du dépôt
git log --oneline 0c7b8ce9..HEAD  # session 2026-04-28
git status                         # working tree clean
git push --dry-run                 # déjà à jour

# Tests
python3 -m pytest tests/unit/ -q   # 1113 passed, 33 warnings

# Lint scope session
python3 -m flake8 \
  ui/controllers/favorites_*.py \
  ui/dialogs/favorites_manager.py \
  core/services/favorites_service.py \
  core/domain/favorites_manager.py \
  core/domain/exceptions.py \
  extensions/favorites_sharing/ \
  --max-line-length=120 --ignore=E501,W503,E127,E128,E731,E241
```
