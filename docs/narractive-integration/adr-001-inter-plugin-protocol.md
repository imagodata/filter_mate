# ADR-001 — Inter-plugin communication protocol (FilterMate ↔ Narractive)

- **Status** : Accepted (2026-04-27). Closes issue #6.
- **Date** : 2026-04-27
- **Deciders** : Simon Ducornau
- **Context** : Sprint 1 (#5, closed 2026-04-27). Narractive integration work has since been deprioritised at the project level (see #46 sibling tracking); this ADR is preserved as the formal contract any future Narractive (or other-plugin) integration will inherit.

## Context

Narractive is a hypothetical sibling QGIS plugin that would orchestrate a "narrative" walkthrough (a sequence of map states), with each step potentially carrying a filter to apply to one or more layers. It needs to drive FilterMate from outside.

Two communication patterns were on the table:

1. **Direct calls** — Narractive imports FilterMate's API and calls methods synchronously.
2. **Pure Qt signals** — Narractive only listens to broadcasts; FilterMate exposes no callable.

Each on its own is incomplete. Direct calls cover the "do this" half (apply filter, read state) but offer no notification when state changes from elsewhere (the FilterMate UI itself, or another consumer). Pure signals cover the broadcast half but require either polling or a stateful adapter on the consumer side just to issue a command.

## Decision

**Hybrid : direct calls for actions, Qt signals for notifications.**

### Direct calls (synchronous, request/response)

A `FilterMatePublicAPI` façade exposes a small port of methods that perform an action and return immediately :

- `apply_filter(layer_name, expression, source_plugin=...) -> bool`
- `clear_filter(layer_name) -> bool`
- `clear_all_filters() -> int`
- `get_active_filters() -> Dict[str, str]`
- `get_filter_for_layer(layer_name) -> Optional[str]`
- `version : str` (semver) and `capabilities : Dict[str, Any]` properties

Resolution uses `QgsProject.instance()` (case-insensitive layer name), validation via `QgsExpression`, and execution is delegated to the existing `FilterExecutorPort` so there is no parallel filtering pipeline.

### Qt signals (asynchronous, broadcast)

The same façade exposes signals that fire whenever the underlying state changes — regardless of whether the change originated from the public API, FilterMate's own dock UI, or any other path :

- `filter_applied(layer_name : str, expression : str)`
- `filter_cleared(layer_name : str)`
- `error_occurred(error_code : str, message : str, layer_name : str)`
- `about_to_unload()`

Error codes are normalised : `LAYER_NOT_FOUND`, `INVALID_EXPRESSION`, `BACKEND_ERROR`, `PERMISSION_DENIED`.

### Entry point + lifecycle

```python
qgis.utils.plugins["filter_mate"].get_public_api()
```

returns a singleton-per-session instance. Consumers connect signals at startup and listen for `about_to_unload` to disconnect cleanly before FilterMate is destroyed.

### Versioning

The façade carries a semver `version` property. Consumers compare against their `MINIMUM_API_VERSION` and degrade gracefully when the installed FilterMate is too old (`get_public_api` missing, or version below the floor).

## Consequences

### Positive

- **Loose coupling** : Narractive (or any consumer) only depends on the `FilterMatePublicAPI` contract, not on FilterMate's internal layout. The hexagonal architecture stays clean.
- **Both push and pull** : actions are synchronous and predictable ; state changes notify everyone interested without polling.
- **Source-tracking** : `source_plugin` parameter means FilterMate logs and audit can distinguish UI-originated filters from API-driven ones.
- **Versionable** : the contract is small and stable enough to be promised under semver. Internal refactors don't break consumers as long as the façade is preserved.
- **Tests stay light** : signal contracts test via `pytest-qt` `qtbot.waitSignal`, action contracts test via direct call. No QGIS runtime needed once PyQt is mocked.

### Negative

- **Two entry points to maintain** : direct methods AND signals. A semantic divergence (e.g. signal fires but method returned False) is a real risk — every public method that mutates state must emit the corresponding signal in the same path.
- **Singleton scope** : one instance per session. Good for the simple case, but means future multi-tenant scenarios (concurrent narratives, per-project state) would need a redesign.
- **Qt5/Qt6 surface** : signals must be declared with `pyqtSignal` and the signature has to be compatible with both. `qgis.PyQt` re-exports cover this today, but every new signal carries that compatibility burden.

### Neutral

- The REST API delivered later (Epic #35, closed 2026-04-27) sits *on top of* the same `FilterMatePublicAPI`. It is not an alternative protocol — it is a transport for the same façade. Consumers that cannot run inside the QGIS Python process (external services, automation tooling) get the same contract over HTTP.

## Compatibility

- **QGIS** : ≥ 3.22, including QGIS 4.x.
- **Qt** : 5 and 6, via `qgis.PyQt`.
- **Python** : 3.10+ (matches FilterMate's floor).

## Status of related issues at this ADR's acceptance

- ✅ Foundations shipped: `FilterMatePublicAPI` (Epic #13, closed) + REST API bridge (Epic #35 + #45, closed).
- ❌ Narractive plugin not built. Issues #5, #9, #10, #11, #12, #18, #19, #20, #21, #22, #24, #25 closed as out-of-scope on the same date as this ADR. The contract documented here is preserved so a future re-prioritisation can resume from a known foundation.

## References

- Sprint 1 design notes : [sprint-1.md](./sprint-1.md) (historical, contains the full per-method acceptance criteria)
- Issue : [#6 — Protocole d'API inter-plugin](https://github.com/imagodata/filter_mate/issues/6)
- Public API source : [adapters/public_api/filter_mate_public_api.py](../../adapters/public_api/filter_mate_public_api.py)
- Public API port : [core/ports/public_api_port.py](../../core/ports/public_api_port.py)
- REST bridge : [filtermate_api/](../../filtermate_api/)
