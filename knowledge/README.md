# FilterMate Knowledge Base

> Everything an AI agent needs to understand FilterMate as a user, not as a developer.

## Files

| File | Lines | What It Covers |
|---|---|---|
| [OVERVIEW.md](OVERVIEW.md) | ~114 | What FilterMate is, key features, supported data sources |
| [UI_GUIDE.md](UI_GUIDE.md) | ~549 | Every button, widget, zone, toggle — the complete visual reference |
| [INTERACTIONS.md](INTERACTIONS.md) | ~314 | How panels work together: Exploring ↔ Filtering ↔ Action Bar |
| [SIGNALS.md](SIGNALS.md) | ~264 | All signal connections: what triggers what, event chains |
| [WORKFLOWS.md](WORKFLOWS.md) | ~294 | 10 step-by-step user workflows |
| [EXPORT_PIPELINE.md](EXPORT_PIPELINE.md) | ~130 | Full export system: flow, formats, styles, batch mode, streaming |
| [CONFIGURATION.md](CONFIGURATION.md) | ~240 | All configurable settings, performance tuning, icon mapping |
| [SYSTEMS.md](SYSTEMS.md) | ~215 | Backend selection, favorites, history, optimization engines |
| [LIFECYCLE.md](LIFECYCLE.md) | ~145 | Plugin init sequence, layer add/remove lifecycle, display field selection |
| [ACTION_WIDGETS.md](ACTION_WIDGETS.md) | ~377 | Action Bar, History, Favorites, Backend Indicator — full UI + behavior |
| [THEMING.md](THEMING.md) | ~225 | QSS stylesheets, icon theming, button styling, QGIS theme watcher |
| [GLOSSARY.md](GLOSSARY.md) | ~280 | 45+ key terms defined |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | ~223 | 20+ common issues with fixes |
| [FEEDBACK.md](FEEDBACK.md) | ~115 | Feedback levels, message categories, error messages, log panel |

## Reading Order

1. **OVERVIEW.md** — Start here to understand what FilterMate does
2. **UI_GUIDE.md** — Learn the interface layout and every widget
3. **INTERACTIONS.md** — Understand how panels cooperate
4. **WORKFLOWS.md** — See it in action with concrete use cases
5. **EXPORT_PIPELINE.md** — Deep dive into the export system (optional)
6. **SIGNALS.md** — Deep dive into reactive behavior (optional)
7. **CONFIGURATION.md** — What can be customized (optional)
8. **SYSTEMS.md** — Backend/optimization internals (optional)
9. **LIFECYCLE.md** — Plugin init and layer tracking internals (optional)
10. **GLOSSARY.md** — Reference when terms are unclear
11. **TROUBLESHOOTING.md** — When things go wrong
12. **FEEDBACK.md** — Understanding notifications and verbosity levels (optional)

## Quick Reference

**3 main zones:** Exploring (top) → Filtering/Exporting (bottom tabs) → Action Bar

**The filter pipeline:** Select features (Exploring) → Configure spatial filter (Filtering) → Click Filter (Action Bar)

**4 backends:** PostgreSQL, Spatialite, OGR, Memory — auto-selected per data source

**3 selection modes:** Single (one feature), Multiple (checkable list), Custom (write expression) — mutually exclusive
