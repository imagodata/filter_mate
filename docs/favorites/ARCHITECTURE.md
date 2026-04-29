# Favorites system — developer guide

Last refreshed: **2026-04-29** after the deep audit (24 commits, 1424/1424
tests). Read this before editing anything under `core/services/favorites*`,
`core/domain/favorit*`, `ui/controllers/favorites*`, `ui/dialogs/favorites*`,
or `extensions/favorites_sharing/`.

---

## TL;DR

- **One service instance.** `FilterMateApp.favorites_manager =
  FavoritesService()` is the only one. The `_favorites_service` slot on
  the dockwidget / controller / dialog points to this same object.
- **`_favorites_service`, not `_favorites_manager`** on the controller /
  dialog / dockwidget. The Service-internal `_favorites_manager` (the
  one that holds the real domain `FavoritesManager`) is the *only*
  legitimate use of the old name.
- **Single coupling point with the sharing extension** =
  `FavoritesExtensionBridge`. The dialog's `_on_shared_clicked` /
  `_on_publish_clicked` / `_is_sharing_active` route through it; if you
  see a fresh `from ...extensions.favorites_sharing.ui import ...` in a
  core file you broke F5 — fix it, don't add a fallback.
- **All writes to `fm_favorites`** go through
  `FavoritesManager.add_favorite()` or `update_favorite()`. The
  timestamp + owner auto-stamp policy lives there. SQL inline that
  bypasses these is a regression of CORE-2.

---

## Layout

```
core/
  services/
    favorites_service.py             # FavoritesService — public API for UI
    favorites_migration_service.py   # orphan-favorites migration on project switch
  domain/
    favorites_manager.py             # FavoritesManager — SQLite + cache
    favorite_import_handler.py       # rebind import payloads to current project
    layer_signature.py               # portable layer signatures (CRIT-3)
    remote_layers_normalizer.py      # 4-mode normaliser (F3)
    schema_constants.py              # GLOBAL_PROJECT_UUID
    exceptions.py                    # FavoritesError family (F16)

ui/
  controllers/
    favorites_controller.py            # ~1100 LOC orchestrator (post F4)
    favorites_spatial_handler.py       # capture/restore/apply spatial config
    favorites_spatial_helpers.py       # pure-function helpers
    favorites_menu_builder.py          # context menu (BuilderContext Protocol, UI-8)
    favorites_extension_bridge.py      # F5 single coupling point with sharing
    favorites_dockwidget_surface.py    # DockwidgetSurface + ControllerSurface Protocols
  dialogs/
    favorites_manager.py             # FavoritesManagerDialog — 1347 LOC, MVP refacto pending
  styles/
    favorites_styles.py              # QSS + icon registry (F12)

extensions/favorites_sharing/
  service.py                         # 156 LOC FACADE
  services/                          # split per responsibility (EXT-2)
    shared_query.py                  # read path (list / filter / cache)
    fork.py                          # trust boundary (third-party → local DB)
    bundle_publisher.py              # writer path (produce v3 bundle on disk)
  scanner.py / validator.py / extension.py
  remote_repo_manager.py             # git-backed repos
  git_client.py / git_resolver.py / portable_git_installer.py
  ui/
    publish_dialog.py                # 779 LOC, MVP refacto stages 2-4 pending
    publish_model.py                 # headless config helpers (EXT-1 stage 1)
    repo_manager_dialog.py
    git_binary_dialog.py
    shared_picker_dialog.py
    git_worker.py                    # start_git_worker + gracefully_close_worker (EXT-7)
```

---

## Invariants you must not break

These were codified by the 2026-04-29 audit. Each has a memo trail.

1. **No second `FavoritesService` instance.** The `DockWidgetOrchestrator`
   is mostly orphan code — do not let it (or anything else) instantiate a
   second one. Sync the controller with `sync_with_dockwidget_manager()`.
   *Origin*: XCUT-1 / CRIT-4.

2. **Bridge is the single coupling point with `extensions/favorites_sharing`.**
   Any UI core file importing `extensions.favorites_sharing.ui` directly
   is a bug. The fallback pattern `if bridge is None: import_directly()`
   was deliberately removed — `bridge=None` only happens in headless
   tests that don't exercise sharing. *Origin*: F5, R1, XCUT-2.

3. **Writes to `fm_favorites` go through the policy layer.**
   `add_favorite(target_project_uuid=...)` for INSERTs (handles owner
   auto-stamp + F7 timestamp policy), `update_favorite()` for partial
   updates (handles `bump_updated_at`). Inline SQL escapes both.
   *Origin*: F7, CORE-2.

4. **`remote_layers` is keyed by `layer_signature`, never by `layer.name()`.**
   Every produce/consume path must round-trip through
   `RemoteLayersNormalizer`. *Origin*: CRIT-3, F3.

5. **`FavoritesSpatialHandler` reads dockwidget through Protocols.**
   `DockwidgetSurface` documents the slice the handler may touch.
   Adding a new attribute access there means widening the Protocol —
   make it a deliberate decision. *Origin*: F4 step 3, XCUT-3.

6. **Worker close = `gracefully_close_worker()`** in
   `extensions/favorites_sharing/ui/git_worker.py`. Three dialogs share
   it — don't roll your own `worker.wait()` again. *Origin*: H5, EXT-7.

---

## Patterns that worked

### God-class service decomposition (proven on EXT-2)

When a service hits ~600 LOC with multiple unrelated responsibilities,
split in 4 stages — each stage = 1 commit + tests verts:

1. **Read path** out first (it's almost always the simplest).
2. **Trust boundary / business critical** path next (own helpers).
3. **Writer path** last (largest, often needs sub-helpers).
4. **Facade cleanup** (drop orphan imports, rewrite docstring).

Keep the public surface as one-line delegations on the original class
so callers (dialogs, extension entry, tests) need no migration. Use
`safe_delete_symbol` to force traceability of remaining references —
it refuses to delete while callers exist. Reference: commits
`6632f320` → `74106c05` → `ae9b5f63` → `5712a28d`.

### God-class UI dialog decomposition (NOT yet proven)

The same pattern does **not** apply directly to a Qt dialog — its
methods are widget-coupled. A dialog at >800 LOC needs a real MVP
(Model headless + Controller Qt-aware + View). EXT-1 stage 1 only
extracted the two true headless helpers; stages 2-4 are deferred for a
sprint that decides the MVP shape.

---

## Open chantiers (sprints dédiés requis)

| ID | Scope | Why it's blocked from a session |
|---|---|---|
| CORE-7 | Unify error contract (5 contracts coexist: `Optional[str]`, raise, result-dataclass, `bool`, `None`) | Breaking change to public dataclasses (`FavoriteImportResult`, `FavoriteApplyResult`) consumed by UI |
| UI-7 | `RestoredSpatialState` dataclass owned by handler instead of dockwidget attrs | 12 tests + Qt event-order semantics around `launchTaskEvent` |
| UI-2/3 | Decompose `FavoritesManagerDialog` 1347 LOC | MVP design required (see EXT-1 lesson above) |
| EXT-1 stages 2-4 | Decompose `PublishFavoritesDialog` 779 LOC | Same MVP requirement |
| CORE-2 reste | `migrate_orphan_favorites` batch UPDATE → policy-aware | Low payoff, schedule with another orphan-favorites change |
| CORE-5 | `fm_meta(schema_version)` table + version-bump guarded backfills | Adds a real schema migration framework |

---

## Testing

- 1424 tests pass on the suite (`python3 -m pytest`). Favorites alone:
  ~245 across `tests/unit/core/domain/test_favorites_*`,
  `tests/unit/core/services/test_favorites_*`,
  `tests/unit/ui/controllers/test_favorites_*`,
  `tests/unit/ui/test_favorites_*`,
  `tests/unit/extensions/favorites_sharing/`.
- The handler tests use a typed double matching `DockwidgetSurface` —
  mirror that approach when adding new spatial-handler tests rather
  than going back to `MagicMock(spec=...)`.
- `FavoritesController` tests build via `__new__` (bypass `__init__`)
  so the spatial handler is lazy via `_spatial` property — no need to
  wire it manually.

---

## Memory trail

Reading order if you need the audit context:

1. `~/.claude/.../memory/project_favorites_audit_2026_04_23.md` — CRIT/HIGH security fixes
2. `~/.claude/.../memory/project_favorites_consolidation_audit_2026_04_27.md` — F1..F19 consolidation backlog
3. `~/.claude/.../memory/project_favorites_consolidation_2026_04_28.md` — R1+D1+P2 livrés
4. `~/.claude/.../memory/project_f4_step3_spatial_handler_design_2026_04_28.md` — design memo F4 step 3
5. `~/.claude/.../memory/project_favorites_deep_audit_2026_04_29.md` — **the full 4-vague consolidated picture; start here**

The Serena memories under `.serena/memories/` mirror the same content
for editor LSP integration.
