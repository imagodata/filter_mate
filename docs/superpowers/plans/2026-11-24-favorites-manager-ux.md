# Favorites manager UX Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The favorites manager dialog shows no display bug, follows the FilterMate theme, and says in plain words what each favorite does and whether it is shared with the project or kept on this computer.

**Architecture:** The readable text (summary rows, scope badge, dates, counts) is computed by a pure module the dialog calls, so it is unit-tested without QGIS. The dialog's stylesheet comes from the theme tokens (`ui/styles/mockup_design.py` TOKENS) instead of literals, its icons from QGIS theme icons / `render_icon`. The dialog keeps its structure (list left, details right, modal), with General + Expression merged into a summary tab.

**Tech Stack:** Python 3.10+, PyQGIS, `qgis.PyQt` (Qt5 and Qt6), QGIS 3.22 → 4.x, pytest.

**Spec:** `docs/superpowers/specs/2026-11-24-favorites-manager-ux-design.md`

## Global Constraints

- Stays a modal dialog; no card list; no favorites section in the dock; no change to storage or sync (#646).
- Every new or changed user-facing string goes through `self.tr(...)` / `QCoreApplication.translate` and into the 34 catalogs (`i18n-pipeline` skill, lrelease in Docker).
- No emoji in the dialog (they render as empty boxes): QGIS theme icons (`QgsApplication.getThemeIcon`) or `ui/styles/mockup_design.render_icon`.
- Light and dark themes both correct; Qt5 (QGIS 3.22 / 3.44) and Qt6 (QGIS 4.x) both run (`pyqgis-qt-pitfalls` skill for enums and imports).
- Scope badges exactly: **Projet · partagé** (EN source: "Project · shared") and **Global · ce poste** (EN source: "Global · this computer").
- Deleting a project favorite warns it is removed for everyone who opens the project (EN source: "It is removed for everyone who opens this project.").

## Review Focus

1. A favorite with no remote layer and no spatial config → the summary shows only its filter line (no empty "Then 0 layers" / "Spatial: —" rows).
2. A very long expression (a 400-id `IN` list) → the summary wraps and stays selectable; the dialog does not widen past the screen.
3. A legacy favorite with `created_at` empty or not ISO, `spatial_config` with `buffer_value` 0 or missing, predicates unknown to the mapping → no exception, readable fallback.
4. Theme switched while QGIS runs (light ↔ dark) then the dialog opened → the new theme's colors (the stylesheet is computed at open, not cached at import).
5. A global favorite applied twice → one project favorite, not two copies.

Each line is pinned by a test in the task that owns the code (marked "Review Focus n").

---

### Task 1: The readable text of a favorite (pure)

**Files:**
- Create: `ui/dialogs/favorite_summary.py`
- Test: `tests/unit/ui/dialogs/test_favorite_summary.py` (create `tests/unit/ui/dialogs/__init__.py` if absent)

**Interfaces:**
- Produces:
  - `summary_rows(favorite, tr: Callable[[str], str]) -> List[Tuple[str, str]]` — ordered (label, text) rows: filter (`"<layer_name> : <expression>"`), remote layers (`"<n> couches"` → `"name (count) · name (count)"`), spatial (`"<predicates joined ', '> · buffer <value>"`), tags. Rows with nothing to say are left out.
  - `scope_badge(is_global: bool, tr) -> str` — the two exact badges of Global Constraints.
  - `use_text(use_count: int, last_used_at: Optional[str], tr) -> str` — "Never used" / "Used 1 time" / "Used 3 times" (EN sources, plural by count).
  - `date_text(iso: Optional[str]) -> str` — `QLocale` short date of an ISO timestamp; `"-"` when empty or unreadable.
  - `PREDICATE_LABELS: Dict[str, str]` — EN source labels for the predicate keys FilterMate stores (`Intersect`, `Within`, `Contain`, `Touch`, `Cross`, `Overlap`, `Disjoint`, `Equal`; read the real keys in `ui/controllers/favorites_spatial_handler.py` and `core/` predicate constants); an unknown key is shown as is.

- [ ] **Step 1: Write the failing tests** — with a `FilterFavorite` (from `core.domain.favorites_manager`) and `tr = lambda s: s`:
  - `test_full_favorite`: name "Parcelles A > 20 m²", expression `"type" = 'A' AND "surface" > 20`, layer_name "parcelles", remote_layers two entries (troncon_de_route 12, batiment 5, with `display_name`), spatial_config predicates `["Intersect", "Within"]`, buffer_value 25.0, tags `["urbanisme", "PLU"]` → rows labels in order `["Filter", "Then", "Spatial", "Tags"]`; the "Then" text contains `"troncon_de_route (12)"` and `"batiment (5)"`; the spatial text contains `"25"` and not `"25.0"`.
  - `test_bare_favorite` (Review Focus 1): only expression and layer → exactly one row, label "Filter".
  - `test_legacy_values` (Review Focus 3): `created_at=""` → `date_text` gives `"-"`; `created_at="not a date"` → `"-"`; buffer 0 or missing → no buffer in the spatial text; predicates `["Strange"]` → `"Strange"` shown.
  - `test_use_text`: 0 → "Never used"; 1 → "Used 1 time"; 3 → "Used 3 times".
  - `test_scope_badge`: `True` → "Global · this computer"; `False` → "Project · shared".
- [ ] **Step 2:** `QT_QPA_PLATFORM=offscreen python3 -m pytest -q tests/unit/ui/dialogs/test_favorite_summary.py -p no:cacheprovider` → FAIL (module missing).
- [ ] **Step 3:** Implement the functions above in `ui/dialogs/favorite_summary.py`; strings passed through `tr` with EN sources; `display_name` of a remote layer first, else the key after `::`.
- [ ] **Step 4:** Same command → PASS.
- [ ] **Step 5:** Commit `Favorites manager: the readable text of a favorite`.

### Task 2: The theme and the icons

**Files:**
- Modify: `ui/styles/favorites_styles.py` (add the dialog stylesheet builder)
- Modify: `ui/dialogs/favorites_manager.py:202-520` (`_setup_ui`, `_get_dialog_stylesheet`, emoji at 232, 244, 260, 727, 733 and `_SCOPE_BADGES` at 49-55)
- Test: `tests/unit/ui/styles/test_favorites_dialog_stylesheet.py`

**Interfaces:**
- Produces: `favorites_dialog_stylesheet(dark: bool) -> str` in `ui/styles/favorites_styles.py`, built from `mockup_design.TOKENS['dark' | 'light']` (no color literal of its own).
- Consumes: `StyleLoader.get_current_theme()` (`ui/styles/style_loader.py:356`; `'dark'` → dark, anything else → light) read in `_setup_ui` each time the dialog opens (Review Focus 4).

- [ ] **Step 1: Write the failing tests:**
  - `test_dark_and_light_differ`: `favorites_dialog_stylesheet(True) != favorites_dialog_stylesheet(False)`; the dark one contains `TOKENS['dark']['fm_bg']` and `TOKENS['dark']['fm_text']`, the light one `TOKENS['light']['fm_bg']`.
  - `test_no_literal_of_its_own`: every `#rrggbb` in each stylesheet is a value of the matching TOKENS dict.
  - `test_dialog_source_has_no_emoji`: `ui/dialogs/favorites_manager.py` read as text contains none of `🔍 💾 🗑 📡 📤 👥 🌐 🔒 👤 🏷 ★ •`.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement `favorites_dialog_stylesheet`; in the dialog drop `_get_dialog_stylesheet`'s literals for it; buttons get icons (`QgsApplication.getThemeIcon`: `/mActionDeleteSelected.svg` delete, `/mActionFileSave.svg` save, `/mActionFilter2.svg` apply; search box `setClearButtonEnabled(True)` with a leading `/search.svg` action, no label); an icon that comes back null leaves the button text alone. The list items carry the scope as an icon (`render_icon('star', dark)` project, a distinct one for global) and the name only as text.
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit `Favorites manager follows the theme; icons instead of emoji`.

### Task 3: The layout and the summary tab

**Files:**
- Modify: `ui/dialogs/favorites_manager.py` (`_setup_ui` sizes 205-206, splitter 294-308, `_create_left_panel` 522-540, `_create_right_panel` 542-564, `_create_general_tab` 566-668, `_create_expression_tab` 670-687, `_create_remote_tab` 689-713, `_on_selection_changed` 902-1026, `_clear_details` 1199)

**Interfaces:**
- Consumes: Task 1 `summary_rows`, `scope_badge`, `use_text`, `date_text`.

- [ ] **Step 1:** Dialog `resize(900, 620)`, minimum `(720, 500)`; splitter sizes `[300, 600]`; list: `setTextElideMode(ElideRight)`, horizontal scroll bar off, minimum width 240.
- [ ] **Step 2:** Tabs become **Summary** (badge line, the summary rows as a two-column form with labels muted and values word-wrapped, selectable — `Qt.TextSelectableByMouse`; expressions in the mono family `mockup_design.MONO_FAMILY`; then the editable Name, Description — minimum 3 lines high, no spin arrow —, Tags; then "Used … · created …" from `use_text` / `date_text`) and **Layers (N)** (the remote layers table with word-wrapped expression column and the full expression as tooltip). The Expression tab and the owner / project radios and the owner line go. Tab bar `setElideMode(Qt.ElideNone)` and `setUsesScrollButtons(True)` so a selected (bold) tab is never cut.
- [ ] **Step 3:** Long expression (Review Focus 2): the summary value label wraps (`setWordWrap(True)`) inside a `QScrollArea` of the Summary tab; the dialog width does not grow with it.
- [ ] **Step 4:** Run the capture bench of Task 6 on `qgis/qgis:ltr` light theme; read the PNGs: no cut tab, no overlap, names elided with "…", the summary readable.
- [ ] **Step 5:** Commit `Favorites manager: a summary of each favorite, a layout that fits`.

### Task 4: List interactions and global favorites

**Files:**
- Modify: `ui/dialogs/favorites_manager.py` (`_create_left_panel`, `_populate_list` 752-797, `_refresh_filtered_list` 815-851, `_on_apply` 1028, new slots)
- Modify: `ui/controllers/favorites_controller.py` (`show_manager_dialog` 614-667 connects the new signal; `_apply_global_favorite` 1018-1035)
- Test: `tests/unit/ui/controllers/test_favorites_controller.py` (add)

**Interfaces:**
- Produces: dialog signal `globalFavoriteApplied = pyqtSignal(str)` beside `favoriteApplied`; controller connects it to `_apply_global_favorite` for the duration of `exec()` (as `favoriteApplied`, UI-6).

- [ ] **Step 1: Write the failing test** (Review Focus 5) `test_applying_a_global_favorite_twice_keeps_one_copy`: with a service stub whose project list already holds a favorite of the same name and expression as the global one, `_apply_global_favorite(gid)` does not call `import_global_to_project` and applies the existing project favorite.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** In `_apply_global_favorite`, look for a project favorite with the same `name` and `expression` first; import only when there is none.
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5:** The list shows the project favorites then the global ones (`get_global_favorites()`), each with its scope icon; a sort combo beside the scope combo: Name (default) / Last used / Most used. Double-click applies (`itemDoubleClicked`). Context menu (`CustomContextMenu`): Apply, Rename (focus and select the Name field), Duplicate (project favorites: `add_favorite` with name `"<name> (copy)"` EN source), Delete, Copy to global (project) / Copy to project (global). Apply on a global favorite emits `globalFavoriteApplied`.
- [ ] **Step 6:** Commit `Favorites manager: double-click, context menu, sorting, global favorites listed`.

### Task 5: Honest messages and the ★ menu

**Files:**
- Modify: `ui/dialogs/favorites_manager.py` (`_on_save` 1034-1106, `_on_delete` 1108-1197)
- Modify: `ui/controllers/favorites_menu_builder.py:285-302` (Maintenance), `ui/controllers/favorites_controller.py` (`add_current_to_favorites` 258-294, `import_favorites` 566-592, `_handle_menu_action` 725-764)
- Test: `tests/unit/ui/controllers/test_favorites_controller.py`, `tests/unit/ui/controllers/test_favorites_menu_builder.py` (add or create)

- [ ] **Step 1: Write the failing tests:** `test_menu_has_no_project_backup_entries` (the built menu has no action whose data is the backup / restore constants); `test_add_failure_is_said` (service `add_favorite` returns None → `_show_warning` called once); `test_import_has_no_replace_all` (the import question offers no "Replace all" choice, import always skips duplicates).
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Remove the two Maintenance entries and their dispatch (keep the service methods: the sharing extension calls `save_to_project_file`); `add_current_to_favorites` warns when creation fails; import asks nothing about replacing (merge, duplicates skipped) and says how many were imported / skipped; `_on_save` refuses an empty name or a name another favorite has, with a message; `_on_delete` adds the shared warning of Global Constraints for a project favorite.
- [ ] **Step 4:** Run → PASS; `QT_QPA_PLATFORM=offscreen python3 -m pytest -q tests/unit -p no:cacheprovider -k "favorit or Favorit"` → all pass.
- [ ] **Step 5:** Commit `Favorites: honest messages, no project backup entries, import without a replace that did nothing`.

### Task 6: Translations, bench, checks

**Files:**
- Create: `tests/qgis_headless/capture_favorites_manager.py` (from the throwaway script of 2026-11-24: plugin started, three layers, four favorites — remote layers + spatial + tags, a plain one, a 400-id one with a long name, a global one —, the dialog shown non-modally, each tab and the long-name item grabbed to `FM_GRAB_DIR`; `FM_THEME=dark` sets `APP.DOCKWIDGET.COLORS.ACTIVE_THEME` before the plugin starts)
- Modify: `i18n/FilterMate_*.ts` and `.qm` (34 catalogs) via the `i18n-pipeline` skill
- Modify: `CHANGELOG.md` (`## [Unreleased]`)

- [ ] **Step 1:** Run the bench on `qgis/qgis:ltr` and `qgis/qgis:latest`, light and dark (4 runs); read every PNG; fix what shows wrong (back to the owning task).
- [ ] **Step 2:** Translations: all new / changed strings in the 34 catalogs, `.qm` compiled (skill), French checked in the French capture.
- [ ] **Step 3:** GUI smoke: `run_gui_smoke.py` with `FM_ONLY=link` and the default run on `qgis/qgis:ltr`; compare failures with main before blaming the change (the 12 min watchdog fires on main too under load).
- [ ] **Step 4:** CHANGELOG entry: what the user sees change, the bench.
- [ ] **Step 5:** Commit `Favorites manager: translations, capture bench`.
