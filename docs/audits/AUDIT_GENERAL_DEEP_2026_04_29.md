# Deep General Audit — FilterMate v4.7.0 — 2026-04-29 (session 2)

> **Pre-context.** Earlier today the same project shipped 24+ commits closing 5 P0s
> (S1/S2/S3/A1/T1) and 6 P1s (A4 partial / H1 / A2 / T2 / T3 / C1 / A3 paire 4). See
> `AUDIT_GENERAL_2026_04_29.md` and `AUDIT_A3_PAIRS_2026_04_29.md` for the prior pass.
>
> This second-pass deep audit was run by **4 parallel specialised agents** (security &
> concurrency, architecture, test-coverage, cross-cutting/history) and verified by
> direct code reads where claims looked load-bearing. Read-only investigation; no
> code changes.

## TL;DR — what this audit changes

| Severity | Count | Examples |
|---|---|---|
| 🔴 NEW P0 | **2** | C-bug: `spatialite_persistent_cache.py` SQL identifier interpolation broken (silent feature loss, 100+ days). API thread-safety: `QgsVectorLayer.setSubsetString()` called from FastAPI worker thread. |
| 🟠 NEW/CONFIRMED P1 | **8** | S4 plaintext api_key, optimizer cache invalidation, hexagonal violations cluster (20+ sites), filtermate_api hardening (rate-limit/size-limit/A4-at-API), EXT-6 fail-fast guard test, sanitizer whitespace gap, 3 mega-controllers (>3000 LOC), filter_config_builder.py edge cases (no test file post-merge). |
| 🟡 P2 / housekeeping | **5** | Dead caches deletion (~628 LOC), `video_automation/` + `video_toolkit/` purge, CORE-5 fm_meta decision, stale `.serena/memories/`, untestable god-dialogs (favorites_manager 1307, publish 774). |

**Verdict on prior P0/P1 fixes**: all SAFE — no plausible bypass for S1/S2/S3 found.
S2 deny-list survives ~10 mental fuzz attempts. S3 sanitizer holds for security but has
one functional gap (whitespace tab/`\v`/`\f` not normalised → false-negative drops).

---

## 🔴 P0 — NEW

### P0-A — `spatialite_persistent_cache.py` table-name interpolation broken

**File**: `infrastructure/cache/spatialite_persistent_cache.py:237-296,379-405,445-448,498-504,585-590,656-658,681-684`

8+ `cursor.execute('''CREATE TABLE … {CACHE_TABLE_NAME} …''')` statements use
**plain triple-quoted strings**, *not* f-strings, with no `.format()` call. The string
`{CACHE_TABLE_NAME}` reaches SQLite verbatim. SQLite rejects `{` in identifiers →
`OperationalError`. Two later statements at lines 698, 718 are correct f-strings.

**Impact**: at startup, `SpatialitePersistentCache.get_instance()._init_database()`
raises immediately. Caught at `filter_mate_app.py:468`, logged at **DEBUG level** so
users never see it, then `self._spatialite_cache = None`. The persistent multi-step
cache has been silently disabled since at least **2026-01-19** (100+ days).

**Why not earlier-discovered**: zero integration test exercises store→retrieve.
`tests/unit/infrastructure/cache/` does not test this module end-to-end.

**Fix scope**: add `f` prefix to the 8 templates *or* convert to `.format()` so all
SQL templates resolve consistently; add an end-to-end test
`test_spatialite_cache_roundtrip` that calls `store_filter_result(...)` then
`get_cached_result(...)` and asserts a round-trip; **and** raise the swallow at
`filter_mate_app.py:468` from DEBUG to WARNING when cache init fails.

**Severity**: feature loss + dishonest telemetry. Not a security issue. Patch effort
~½ day.

### P0-B — REST API calls QGIS APIs from non-main thread

**File**: `filtermate_api/qgis_accessor.py:124` calls
`self._public_api.apply_filter(...)` directly from the FastAPI worker pool. PublicAPI
ultimately invokes `QgsVectorLayer.setSubsetString()` (see
`filtermate_api/qgis_accessor.py:243`). QGIS Vector layer mutations are **not
thread-safe outside the main thread** — undefined behaviour, including silent state
corruption or QGIS crashes.

**Impact**: any non-loopback deployment with API key set is one POST away from
crashing the QGIS process or corrupting subsetString state. Loopback dev usage may
work most of the time and fail under load.

**Fix scope**: marshall the call through the Qt main thread via
`QMetaObject.invokeMethod(..., Qt.BlockingQueuedConnection)` or via a producer/queue
the plugin polls in `QgsApplication.instance()`. ~1 day. Add a test that asserts the
accessor cannot run apply_filter on a fake non-main thread.

---

## 🟠 P1 — NEW / CONFIRMED

### P1-S4 — `api_key` plaintext in `config.json`
**File**: `filtermate_api/config.py:97-106`. Profile dirs are commonly mirrored to
OneDrive/Dropbox. Fix ladder (smallest first):
1. Refuse to load `api_key` from JSON; require env or `QgsAuthManager`.
2. Hash-at-rest: store `sha256(key)`, compare via `hmac.compare_digest` in
   `filtermate_api/auth.py:63`.
3. Route through `QgsAuthManager` (already in use at
   `extensions/favorites_sharing/git_client.py:108-127`).

### P1-OPT-INV — Optimizer caches never invalidate on layer change
None of the 6 optimizers (`adapters/qgis/filter_optimizer.py:67-71`,
`core/optimization/combined_query_optimizer.py:65-66`,
`adapters/backends/postgresql/filter_chain_optimizer.py:82`,
`adapters/backends/postgresql/optimizer.py:58`,
`core/services/auto_optimizer.py:80`,
`adapters/backends/ogr/geometry_optimizer.py:17`) listens to
`QgsProject.layersWillBeRemoved` / `dataChanged`. Stale stats serve filters silently
when a layer is edited or replaced in-place. Several also lack `layer.isValid()`
guards. OGR simplification uses BBox/1000 tolerance with no CRS-awareness — for
geographic CRS that's ~40 km tolerance.

### P1-API-HARDEN — filtermate_api hardening (3 sub-findings)
- **Rate-limit & body-size missing** at `filtermate_api/server.py:128`. POST
  `/filters/apply` accepts arbitrary expression strings, no Content-Length cap.
- **A4 at API boundary**: `filtermate_api/routers/favorites.py:26` doesn't
  catch `FavoritesNotInitialized`; today the QgisAccessor swallow at
  `filtermate_api/qgis_accessor.py:35` returns "no favorites" silently — wrong UX,
  should be 503 + Retry-After.
- **Reflected error info-leak**: `filtermate_api/routers/filters.py:67-70`
  echoes user input into 404 body.

### P1-HEX — Hexagonal violations cluster (20+ sites)
Beyond A1, `core/` still has **20+ direct `QgsProject.instance()` / `iface` /
`QApplication` references**, including in **domain layer** (`core/domain/favorites_manager.py:406`).
Worst offenders: `core/services/app_initializer.py` (8 sites), `core/services/favorites_service.py` (3),
`core/services/layer_lifecycle_service.py` (3),
`core/tasks/filter_task.py` (4),
`core/geometry/*`, `core/export/*`. All should route via the existing
`core/ports/qgis_port.py`.

### P1-EXT6 — `LEGACY_AUTH_HEADER_DEADLINE` is folklore
**File**: `extensions/favorites_sharing/remote_repo_manager.py:34,239`. Constant
declared, only `logger.warning` enforces. No fail-fast test guards the 5.0.0 bump.
Add `test_legacy_auth_header_rejected_at_5_0_0` that monkeypatches `metadata.txt`
version. Cheap (~30 min).

### P1-SAN-WS — Sanitizer whitespace gap (functional, not security)
**File**: `core/filter/expression_sanitizer.py:57`. `_TOPLEVEL_BOOLEAN_MARKERS`
matches literal spaces around `AND`/`OR`. A tab- or `\v`-separated
`field\tAND\tvalue` survives as-is and may be dropped as "display expression".
Replace with `\s+` regex or pre-normalise.

### P1-MEGA-CTRL — 3 mega-controllers (>3000 LOC each)
`ui/controllers/exploring_controller.py:1` (3248 LOC, 1 class),
`ui/controllers/integration.py:1` (3011 LOC),
`core/tasks/filter_task.py:1` (3015 LOC). All single classes. None has tests.
Dwarf the documented backlog UI-2/3 (favorites_manager 1307). Headless-testability
blocked. Plan EXT-2-style decomposition sprints.

### P1-FCB-TESTS — `filter_config_builder.py` post-merge edge cases
The 2026-04-29 merge `a32026ec` consolidated two builders. Fix-commit `9814bb40`
("strip stray tool-call tags breaking import") suggests messy state. Zero dedicated
test file. **10 concrete edge cases** identified (NULL infos, zero-field layer,
`<NULL>` literal subset, schema-with-quote regex, schema mismatch silent log,
`provider_type='unknown'` fallthrough, non-dict forced_backends, primaryKeyAttributes
out-of-range, source_layer None ordering, mid-iteration mutation race). Add
`tests/unit/core/services/test_filter_config_builder.py` covering scenarios 1/2/6/7/8
(~½ day).

---

## 🟡 P2 — housekeeping

| ID | Finding | LOC | Effort |
|---|---|---|---|
| P2-DEAD-1 | `infrastructure/cache/wkt_cache.py` (426) + `geometry_cache.py` (202) — never imported. | ~628 | 1 h delete |
| P2-DEAD-2 | `core/services/layer_service.py` (768) — instantiated at `ui/orchestrator.py:255` but `_services['layer']` slot never read anywhere. A3 paire 2 → DELETE. | 768 | ½ day verify+delete |
| P2-VIDEO | `video_automation/`, `video_toolkit/` (3 MB) ship with the plugin per `AUDIT_2026_04_22.md`; still present. Either move to sibling repo or `.gitattributes export-ignore`. | — | ½ day |
| P2-FM-META | CORE-5 `fm_meta(schema_version)` table promised, 0 grep hits. Decide implement-or-WONTFIX. | — | 1 day or close |
| P2-MEM-STALE | `.serena/memories/project_overview.md:24,143` stuck at v4.4.0 / 396 tests; `code_style_conventions.md:20` and `testing_documentation.md:87` undated. | — | 1 h refresh |

---

## What was *verified safe*

- **S1 API auth/CORS** — `filtermate_api/config.py:155`, `server.py:72,121`. ~5
  bypass attempts checked: empty-key, host alias `127.0.0.2`, OPTIONS pre-flight
  order, wildcard CORS + credentials. None plausible without
  `FILTERMATE_API_ALLOW_INSECURE=1`.
- **S2 PG SQLi** — `adapters/backends/postgresql/sql_safety.py`. ~10 bypass
  attempts: `--`, `;`, `/*!50000*/`, `pg_read_file`, doubled-quote escape inside
  literal, unicode homoglyphs, whitespace-split keywords, identifier shape regex.
  Both call paths (`_execute_direct` AND `_execute_with_mv`) confirmed wired.
- **S3 sanitizer NOT/EXISTS** — `core/filter/expression_sanitizer.py`. Comment-bypass,
  nested NOT(NOT(EXISTS())), and trailing-junk attempts all fail through to
  `validate_where_clause` (defense-in-depth).
- **PortableGit S6** — `extensions/favorites_sharing/portable_git_installer.py:269`.
  Scheme-allowlist + sha256-empty-refusal in place. Residual MEDIUM = operator-supplied
  override URL trust.
- **C1 PushWorker** — `extensions/qfieldcloud/ui/push_dialog.py:42,533`. Park
  registry self-cleans via `finished/error` ahead of `destroyed`.
- **H1 auto-zoom** — `adapters/auto_zoom.py:38-53,141-143`. Token semantics
  design-correct under `threading.Lock`.
- **A1 + A2** — both fixes verified non-regressing.
- **XCUT-1/2/3** — verified literally clean (1 `FavoritesService()` instantiation
  in production, 0 `from ...favorites_sharing.ui import` in dialog, Protocol
  `DockwidgetSurface` posed).
- **Subprocess / pickle / yaml.load / eval / path traversal in import-export** — clear.
- **Logging credential leaks** — clear (commands and stderr scrubbed in `git_client.py`).

---

## Skipped / out of scope (this audit)

- Did not run `pytest` (sandbox blocked); 1424/1424 green claim from earlier memo
  not directly re-verified.
- Did not test the running QGIS UI; static read-only only.
- Did not audit BMAD docs (`_bmad/`) or extension QFieldCloud beyond push-worker.

---

## Recommended sprint order

1. **Day 0 (now)**: P0-A spatialite f-string fix + roundtrip test (~½ day).
2. **Day 0**: P0-B API thread-safety marshalling (~1 day).
3. **Day 1**: P1-S4 hash-at-rest + P1-EXT6 fail-fast test (~½ day).
4. **Day 2-3**: P1-API-HARDEN (rate-limit + body-size + 503 on FavoritesNotInitialized).
5. **Day 4**: P1-FCB-TESTS + P1-SAN-WS.
6. **Day 5-7**: P1-OPT-INV (cache-invalidation listeners + CRS-aware OGR tolerance).
7. **Sprint+1**: P1-HEX (port the 20+ violations to `qgis_port`).
8. **Sprint+2**: P1-MEGA-CTRL (decompose `exploring_controller.py` first).

---

*Audit run 2026-04-29 by 4 parallel specialist agents (security/concurrency,
architecture, test-coverage, cross-cutting). Direct code re-verification done on the
P0 findings.*
