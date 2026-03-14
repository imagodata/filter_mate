# FilterMate — Feedback & Notifications

How FilterMate communicates with the user: message bar notifications, log output, and feedback verbosity control.

---

## Feedback System

FilterMate uses QGIS's message bar (`iface.messageBar()`) for user notifications. The amount of information shown is controlled by the **Feedback Level** setting in the CONFIGURATION tab.

---

## Feedback Levels

| Level | What's Shown | Use Case |
|---|---|---|
| **minimal** | Only errors + warnings + performance warnings + export success | Production use, minimal distraction |
| **normal** *(default)* | Above + generic success messages + export results + error warnings | Balanced everyday use |
| **verbose** | Everything: filter counts, undo/redo confirmations, backend info, config changes, layer loading, progress, history status, initialization info | Debugging or learning the plugin |

---

## Message Categories — What Shows at Each Level

| Category | Minimal | Normal | Verbose | Example Message |
|---|---|---|---|---|
| `error` / `error_critical` | ✅ | ✅ | ✅ | "Initialization error: ...", "Layer invalid" |
| `warning` / `error_warning` | ✅/❌ | ✅ | ✅ | "PostgreSQL layers detected but psycopg2 not installed" |
| `success` | ❌ | ✅ | ✅ | "Forced POSTGRESQL backend for 3 layers" |
| `export_success` | ✅ | ✅ | ✅ | "Export completed successfully" |
| `performance_warning` | ✅ | ✅ | ✅ | "Large dataset warning" |
| `filter_count` | ❌ | ❌ | ✅ | "15 features match filter" |
| `filter_success` | ❌ | ❌ | ✅ | "Filter applied successfully" |
| `undo_redo` | ❌ | ❌ | ✅ | "Undo applied - restored filter" |
| `backend_info` / `backend_startup` | ❌ | ❌ | ✅ | "Using PostgreSQL backend" |
| `config_changes` | ❌ | ❌ | ✅ | "Theme changed to dark" |
| `layer_loaded` | ❌ | ❌ | ✅ | "Layer loaded: communes" |
| `layer_reset` | ❌ | ❌ | ✅ | "Layer properties reset to defaults" |
| `progress_info` | ❌ | ❌ | ✅ | Progress during long operations |
| `history_status` | ❌ | ❌ | ✅ | "No more undo history" |
| `init_info` | ❌ | ❌ | ✅ | Startup/initialization messages |

> **Note on `warning` / `error_warning`:** `warning` shows at minimal; `error_warning` requires normal or above.

---

## Key Error Messages Users May See

| Message | Meaning |
|---|---|
| `"Initialization error: {error}"` | Plugin failed to initialize — critical failure |
| `"The selected layer is invalid or its source cannot be found"` | Layer source is broken, offline, or file missing |
| `"PostgreSQL layers detected but psycopg2 not installed"` | PostgreSQL layers can't use native backend; falling back |
| `"Layer is in edit mode"` | Popup dialog (not message bar) — user must resolve edit mode before filtering |
| `"UI configuration incomplete"` | Dimensions/layout couldn't be fully applied |
| `"Favorites manager not available"` | SQLite issue preventing favorites access |
| `"No PostgreSQL connection available"` | Connection was lost or never established |
| `"Schema cleanup failed"` | Materialized view cleanup failed after query |
| `"Backend controller not available"` | Internal initialization issue; restart QGIS |
| `"Theme adapted: Dark mode / Light mode"` | Auto theme change triggered by QGIS theme switch |
| `"Layer properties reset to defaults"` | After clicking Reset button (shown at normal+ level) |

---

## Where Messages Appear

### QGIS Message Bar
- Location: top of the QGIS window, just below the menu bar
- Color-coded by severity:
  - 🟢 **Green** — success
  - 🟡 **Yellow** — warning
  - 🔴 **Red** — critical error
  - 🔵 **Blue** — info
- Duration: ~5 seconds for info/success messages; longer for warnings and errors
- Messages can be dismissed manually by clicking the ✕ on the notification

### QGIS Log Messages Panel
- All FilterMate messages are **also written to the QGIS log**
- Access: View → Panels → Log Messages → **FilterMate** tab
- Useful for reviewing the full history of messages, especially when the message bar auto-dismisses too quickly
- Shows all messages regardless of feedback level setting

---

## Edit Mode Conflict

Special case: when a user tries to filter a layer that is currently **in edit mode**:

- A **popup dialog** appears (not a message bar notification)
- Asks the user to **save or discard edits** before filtering can proceed
- The filter operation is **blocked** until edit mode is resolved — FilterMate cannot modify a Subset String while the layer is being edited

This is a QGIS constraint, not a FilterMate limitation.

---

## Changing the Feedback Level

The Feedback Level is a setting in the CONFIGURATION tab. Options:

- `minimal` — for quiet, distraction-free production use
- `normal` — the default; recommended for most users
- `verbose` — for troubleshooting, first-time setup, or understanding what FilterMate is doing internally

The setting takes effect immediately — no restart required.
