# Audit Deep General — FilterMate (2026-04-29)

4 audits parallèles (architecture, sécurité, threading, tests) sur ~200k LOC.

**3 findings exploitables à distance** + **1 SQLi confirmée live** + **0 test sur 900 LOC livrées ce sprint**.

## P0 — À traiter immédiatement

### S1 · API ships unauthenticated by default + CORS `*` 🚨
- `filtermate_api/config.py:22-32` + `filtermate_api/server.py:104-117`
- Fresh install → `api_key=None` → `auth.py:55-57` court-circuite l'auth. CORS `["*"]` + `allow_credentials=True`.
- N'importe quel site web visité peut driver la session QGIS via `fetch('http://localhost:8000/filters/apply')`.
- CWE-306 / CWE-942.
- **Statut : FIXÉ 2026-04-29** — `APIConfig.validate()` refuse non-loopback sans auth ou non-loopback + wildcard CORS. `create_app` force `allow_credentials=False` si CORS `*`. Escape hatch via `FILTERMATE_API_ALLOW_INSECURE=1`. 18 tests ajoutés.

### S2 · SQLi `_execute_direct` confirmée live (PostgreSQL backend)
- `adapters/backends/postgresql/backend.py:709,740`
- `f"SELECT * FROM {table_name} WHERE {expression.sql}"` — sanitizer = best-effort, pas un parser.
- Reachable via REST `/filters/apply` → public_api → strategy.
- CWE-89.
- **Statut : FIXÉ 2026-04-29** — nouveau module `sql_safety.py` avec `validate_where_clause()` (refuse `;`, commentaires, DDL/DML, fonctions PG escalation) + `validate_identifier()` (shape `[A-Za-z_][A-Za-z0-9_]{0,62}`). Branchés en pré-execute dans `_execute_direct` et `_execute_with_mv`. 69 tests (59 unit + 10 intégration). Strings/identifiers quotés sont scrubés avant pattern matching → noms légitimes (`deleted_at`, `'DROP request'`) préservés.

### S3 · Sanitizer `_BOOLEAN_FUNCTION_RE` permissif
- `core/filter/expression_sanitizer.py:130` — `^(EXISTS|NOT)\s*\(` court-circuite tout le reste.
- `NOT(1=1); DELETE FROM x; --` matche et bypasse le strip.
- Régression du fix 2026-04-27 (memory `project_sanitizer_exists_regression_2026_04_27.md`).
- **Statut : FIXÉ 2026-04-29** — nouvelle fonction `_is_balanced_boolean_function_call` valide parens balancées + tail vide après le `)` final ; nouvelle fonction `_strip_for_op_scan` scrub literals + commentaires SQL pour le top-level operator scan (sans toucher aux literals seuls dans les autres usages). 8 tests régression chained-statement + comment-bypass.

### A1 · `iface` importé au niveau module dans le domaine
- `core/filter/result_processor.py:27`
- Viole strictement la règle hexagonale ; module non testable headless.
- **Statut : FIXÉ 2026-04-29** — adapter `QgisMessageBarFeedback` (implémente `IFeedback` du port existant) wiré dans `FilterMate.__init__` via `set_feedback_adapter`. `result_processor.py` retire `from qgis.utils import iface`, route `_display_warnings` via `get_feedback_adapter().push_message(..., MessageLevel.WARNING)`. Fallback log-only si adapter pas wiré (headless). 6 tests pinnent le contrat.

### T1 · 0 test sur `FavoritesSpatialHandler` (900 LOC livrées en F4 stages 1-5)
- `ui/controllers/favorites_spatial_handler.py`
- Les 5 stages F4 ont déplacé du code, pas couvert. `restore_spatial_config` (cross-layer FID guard) silencieusement bug si `favorite_matches_current_layer` retourne False.
- **Statut : FIXÉ 2026-04-29** — `tests/unit/ui/controllers/test_favorites_spatial_handler.py` charge le handler via importlib (zéro import QGIS top-level grâce au Protocol + helpers purs) avec fakes typés. 14 tests sur `restore_spatial_config` : cross-layer FID guard (same id / cross id / name fallback / signature match), no-current-layer, predicates/buffer/groupbox restore, invalid features (full + partial), exception safety. Le harnais offre une base pour les 4 méthodes restantes du handler (`capture_spatial_config`, `restore_filtering_ui_from_favorite`, `apply_favorite_subsets_directly`, `ensure_applicable_groupbox_for_favorite`).

## P1 — Sprint courant

| ID | Titre | Localisation | Effort |
|---|---|---|---|
| S4 | API key persistée plaintext dans `config/config.json` | `filtermate_api/config.py:73-81` | **FIXÉ `42918655`** — `from_json` warning quand key chargée depuis JSON, recommande `FILTERMATE_API_KEY` env. |
| S5 | `host=0.0.0.0` accepté via env sans warning | `filtermate_api/config.py:49` | **FIXÉ par S1** |
| S6 | PortableGit `_verify_sha256` silencieux si `expected_hex=""` → exécute `.exe` non vérifié | `extensions/favorites_sharing/portable_git_installer.py:307-348` | **FIXÉ `f2110df2`** — raise `ChecksumMismatchError` au lieu de log warning. |
| C1 | PushWorker `terminate()` + drop ref si `wait(10s)` timeout → orphan QThread | `extensions/qfieldcloud/ui/push_dialog.py:476-482` | M |
| H1 | Auto-zoom stale-state race favorite vs filter (commit 9bd78d2b) | `ui/controllers/favorites_spatial_handler.py:888` + `adapters/filter_result_handler.py:362` | **FIXÉ** — `bump_subset_change_token()` global thread-safe ; `FilterEngineTask.__init__` snapshote le token, `FilterResultHandler._handle_auto_zoom` le passe en `expected_token` ; favori synchrone bump et passe son propre token. `auto_zoom_to_filtered` skip si token courant > expected. 8 tests. |
| A2 | `core/domain/layer_signature.py` — `QgsDataSourceUri` + `QgsProject.instance()` dans domain | `core/domain/layer_signature.py:55,107` | **FIXÉ** — `LayerSignatureIndex.__init__` retire le fallback `QgsProject.instance()` ; les 3 callers passent le projet explicitement (services/extension via `QgsProject.instance()`, domain `_backfill_remote_layer_signatures` documente la dette restante avec lazy import). 6 tests régression, suite 1317/1317. `QgsDataSourceUri` (lazy dans `compute()`) reste — futur port parser à envisager. |
| A3 | 5 paires de services dupliqués post-revert toujours actives | `core/services/` | M×5 |
| A4 | `FavoritesNotInitialized` jamais catchée dans `favorites_controller.py` (F11 policy non appliquée) | `ui/controllers/favorites_controller.py` | **FIXÉ `dde30f5d`** (embarqué dans CORE-1a par concurrence d'agents) — `apply_favorite` et `remove_favorite` catchent `FavoritesNotInitialized` → `_show_warning`. `mark_favorite_used` / `save` failures dégradés en log (non-critique). 5 tests régression. |
| T2 | `auto_zoom.py` (144 LOC, commit 9bd78d2b) — 0 test | `adapters/auto_zoom.py` | S |
| T3 | `history_service.py` (680 LOC, undo/redo critique) — 0 test | `core/services/history_service.py` | L |
| T4 | Config rebind (486ac81a, 77a6de1e) — pas de test sur la mutation-in-place de `CONFIG_DATA` | `tests/unit/.../test_config_migration.py` | S |

## P2 — Dette à backloguer

- **A5** Dockwidget stagne à 6892 LOC — F4 step 3 a déplacé code mais wrappers de délégation préservent la surface. Groupes restants : Dimensions/Layout (~270 LOC), Groupbox/Signal (~750 LOC), Layer Change Orchestrator (~500 LOC).
- **A6** `video_automation/` + `video_toolkit/` trackés en git (exclus du ZIP via 3dede39f mais polluent le repo).
- **S7** PortableGit `_download` follow redirects sans re-check scheme (CWE-601).
- **S8** `git_client._run` `extra_env` non filtré → futur RCE si valeurs user-controlled.
- **C2** `applySubsetRequest` signal déclaré dans `filter_task.py:220` mais jamais connecté → dead code trompeur.
- **C3** `FilterEngineTask._geometry_cache` class-level sans lock — masqué actuellement, latent crash si refactor.
- **T5** Tests fragiles en CI : `test_remote_repo_manager.py`, `test_git_client.py`, `test_portable_git_installer.py` invoquent `subprocess.run(["git", ...])` réel → flaky selon PATH/permissions.
- **T6** `test_signal_manager.py` mock intégral PyQt → ne détecte aucun leak réel.

## Score & priorisation

| Dimension | État | Tendance |
|---|---|---|
| Sécurité | ⚠️ S1 fixé ; S2/S3 ouverts | Régressé puis stabilisé |
| Architecture hexagonale | 🟡 54 fichiers core avec QGIS imports (vs 52 le 2026-04-23) | Stagne |
| Threading | 🟢 H5 fix 2026-04-27 tient ; C1 partiellement résolu | Amélioré |
| Test coverage nouveaux livrables | 🔴 F4/F11/F15/F16 livrés sans tests | Régressé |

**Recommandation** : geler les nouvelles features F-series. Sprint exclusivement P0 (S2 + S3 + A1 + T1) avant tout autre travail.
