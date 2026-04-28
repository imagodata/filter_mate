# -*- coding: utf-8 -*-
"""Spatial-config orchestration for favorites — capture/restore/apply.

F4 step 3 phase 3 (2026-04-28): the controller used to host five
heavyweight methods (~660 LOC total) that wrote into Qt widgets,
mutated dockwidget state and orchestrated multi-layer subset writes.
They moved here so ``FavoritesController`` shrinks back toward an
orchestrator role and the spatial-config surface gains a single
testable seam.

Design choice (vs. the formal ``DockwidgetSurface`` Protocol the
original memo proposed): we mirror the ``FavoritesExtensionBridge``
pattern — the handler holds a reference to the owning controller and
reads back ``self._controller.dockwidget``, ``_favorites_manager``,
``_show_warning``, ``tr``. The dockwidget surface is too wide and Qt-
coupled to Protocol-test in headless mode anyway; existing tests use
``MagicMock()`` and that pattern keeps working.

Stage-1 extraction policy: the controller still exposes the old
underscore methods as one-line delegations, so internal callers and
tests don't break. A later cleanup will drop the delegations once the
test rig has migrated to ``ctrl._spatial.method(...)`` calls.

See ``project_f4_step3_spatial_handler_design_2026_04_28.md``.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from .favorites_controller import FavoritesController
    from ...core.services.favorites_service import FilterFavorite


class FavoritesSpatialHandler:
    """Orchestrate capture/restore/apply of a favorite's spatial config.

    Owns:
      - ``capture_spatial_config()`` — read the dockwidget filtering
        widgets, return a serialisable ``spatial_config`` dict.
      - ``restore_spatial_config(favorite)`` — push a saved config back
        into the dockwidget (selection FIDs, predicates, buffer).
      - ``apply_favorite_subsets_directly(favorite)`` — write the
        favorite's source + remote_layers subsets onto QGIS layers
        without re-running the filter task.
      - ``restore_filtering_ui_from_favorite(favorite)`` — tick UI
        controls + persist into ``PROJECT_LAYERS`` so
        ``sync_ui_to_project_layers`` sees a coherent state.
      - ``ensure_applicable_groupbox_for_favorite(favorite)`` —
        downgrade ``single_selection`` -> ``custom_selection`` when no
        source feature is available.
      - ``backfill_legacy_predicate_default(favorite)`` — heal
        pre-fix favorites that lack ``geometric_predicates``.

    Reads back into the controller for ``dockwidget``,
    ``_favorites_manager``, ``_show_warning`` and ``tr``. Direction
    stays controller -> handler -> dockwidget; the handler never
    imports controller types except for type-checking.
    """

    def __init__(self, controller: "FavoritesController") -> None:
        self._controller = controller

    # ── shorthands -----------------------------------------------------

    @property
    def _dockwidget(self):
        return self._controller.dockwidget

    @property
    def _favorites_manager(self):
        return self._controller._favorites_manager

    # ── method 1 — backfill_legacy_predicate_default -------------------

    def backfill_legacy_predicate_default(
        self, favorite: "FilterFavorite"
    ) -> bool:
        """Heal pre-fix favorites that lack ``geometric_predicates`` in
        ``spatial_config``.

        Favorites saved before commit ``10d35be1`` captured nothing for
        the predicate combobox even when the user had ``Intersect``
        ticked. On apply, the post-fix restore would push
        ``setCheckedItems([])`` and clear the live selection. We default
        such favorites to ``["Intersect"]`` (the most common case, and
        the predicate the already-baked ``remote_layers`` SQL was
        generated against) and persist the patched ``spatial_config``
        so the heal is one-shot.

        Returns ``True`` when the favorite was patched and persisted.
        """
        if not favorite or not getattr(favorite, "remote_layers", None):
            return False

        spatial_config = dict(favorite.spatial_config or {})
        if (
            "geometric_predicates" in spatial_config
            or "has_geometric_predicates" in spatial_config
        ):
            return False

        spatial_config["geometric_predicates"] = ["Intersect"]
        spatial_config["has_geometric_predicates"] = True

        favorite.spatial_config = spatial_config

        persisted = False
        manager = self._favorites_manager
        try:
            if manager and hasattr(manager, "update_favorite"):
                persisted = bool(
                    manager.update_favorite(
                        favorite.id,
                        bump_updated_at=False,
                        spatial_config=spatial_config,
                    )
                )
        except Exception as exc:
            logger.debug(f"Could not persist legacy-predicate backfill: {exc}")

        logger.info(
            f"Favorite '{favorite.name}': backfilled missing geometric_predicates "
            f"with default ['Intersect'] (persisted={persisted})"
        )
        ctrl = self._controller
        ctrl._show_warning(
            ctrl.tr(
                "Favorite '{0}' was missing predicate info — defaulting to 'Intersect'. "
                "Re-save it after adjusting if you need a different predicate."
            ).format(favorite.name)
        )
        return True

    # ── method 2 — ensure_applicable_groupbox_for_favorite -------------

    def ensure_applicable_groupbox_for_favorite(
        self, favorite: "FilterFavorite"
    ) -> None:
        """Downgrade the exploring groupbox when the favorite cannot
        supply a source feature, so ``launchTaskEvent`` doesn't abort
        in ``single_selection``.
        """
        # Imported here so this module stays loadable in headless tests
        # that don't pull in the full helpers chain at import time.
        from .favorites_spatial_helpers import should_downgrade_single_selection

        dw = self._dockwidget
        if not dw or not getattr(dw, "widgets_initialized", False):
            return

        current_groupbox = getattr(dw, "current_exploring_groupbox", None)
        has_restored = bool(getattr(dw, "_restored_task_features", None))

        picker_feature = None
        try:
            picker = dw.widgets.get("EXPLORING", {}) \
                .get("SINGLE_SELECTION_FEATURES", {}).get("WIDGET")
            if picker is not None and hasattr(picker, "feature"):
                picker_feature = picker.feature()
        except (AttributeError, KeyError, RuntimeError):
            picker_feature = None

        picker_valid = bool(
            picker_feature
            and getattr(picker_feature, "isValid", lambda: False)()
        )

        selected_count = 0
        current_layer = getattr(dw, "current_layer", None)
        if current_layer is not None:
            try:
                selected_count = current_layer.selectedFeatureCount()
            except (AttributeError, RuntimeError):
                selected_count = 0

        if not should_downgrade_single_selection(
            current_groupbox=current_groupbox,
            has_restored_features=has_restored,
            picker_feature_valid=picker_valid,
            selected_feature_count=selected_count,
        ):
            return

        if not hasattr(dw, "_restore_groupbox_ui_state"):
            logger.debug("Cannot downgrade groupbox: _restore_groupbox_ui_state missing")
            return

        logger.info(
            f"Favorite '{favorite.name}': single_selection has no feature — "
            "downgrading to custom_selection so the filter doesn't abort."
        )
        try:
            dw._restore_groupbox_ui_state("custom_selection")
        except (AttributeError, RuntimeError) as e:
            logger.debug(f"Could not downgrade groupbox to custom_selection: {e}")

    # ── method 3 — capture_spatial_config -----------------------------

    def capture_spatial_config(self) -> Optional[dict]:
        """Capture the current spatial configuration for favorite restoration.

        Reads the dockwidget filtering widgets to build a serialisable
        ``spatial_config`` dict. Returns ``None`` when nothing worth
        capturing was present (callers must handle ``None`` — matches
        the contract used by ``_create_favorite``).
        """
        config: dict = {}
        dw = self._dockwidget

        try:
            # FIX 2026-04-21: capture the exploring groupbox mode so the
            # favorite restores into the same selection context on apply.
            # Without this, a favorite created in custom_selection fires
            # after reopen with the default single_selection mode and
            # aborts because no source feature is selected.
            groupbox = getattr(dw, "current_exploring_groupbox", None)
            if groupbox:
                config["exploring_groupbox"] = groupbox
                logger.info(f"Captured exploring_groupbox: {groupbox}")

                # For custom_selection, also capture the expression
                # driving source feature selection so the exploring
                # widget can be repopulated on apply.
                if groupbox == "custom_selection":
                    try:
                        widget = dw.widgets.get("EXPLORING", {}) \
                            .get("CUSTOM_SELECTION_EXPRESSION", {}).get("WIDGET")
                        if widget is not None and hasattr(widget, "expression"):
                            custom_expr = widget.expression()
                            if custom_expr and custom_expr.strip():
                                config["custom_selection_expression"] = custom_expr
                                logger.info(
                                    f"Captured custom_selection_expression "
                                    f"({len(custom_expr)} chars)"
                                )
                    except (AttributeError, KeyError, RuntimeError) as e:
                        logger.debug(f"Could not capture custom_selection_expression: {e}")

            # Capture task_features (selected feature IDs)
            features, _ = dw.get_current_features()
            if features:
                feature_ids = [f.id() for f in features if f.isValid()]
                if feature_ids:
                    config["task_feature_ids"] = feature_ids
                    logger.info(
                        f"Captured {len(feature_ids)} task_feature IDs for favorite"
                    )

            # Capture geometric predicates from the actual filtering widgets.
            #
            # FIX 2026-04-23: read from the canonical widgets
            # (``comboBox_filtering_geometric_predicates`` checkedItems +
            # ``pushButton_checkable_filtering_geometric_predicates``
            # isChecked), with a PROJECT_LAYERS fallback for headless /
            # test contexts. The previous implementation read a dict from
            # ``PROJECT_LAYERS[layer_id]['filtering']['predicates']`` —
            # but that key is never populated anywhere in the codebase.
            predicate_list: list = []
            has_predicates: bool = False

            combo_widget = getattr(
                dw, "comboBox_filtering_geometric_predicates", None
            )
            if combo_widget is not None and hasattr(combo_widget, "checkedItems"):
                try:
                    predicate_list = list(combo_widget.checkedItems() or [])
                except (RuntimeError, AttributeError) as e:
                    logger.debug(f"Could not read checkedItems from combobox: {e}")

            has_pred_btn = getattr(
                dw, "pushButton_checkable_filtering_geometric_predicates", None
            )
            if has_pred_btn is not None and hasattr(has_pred_btn, "isChecked"):
                try:
                    has_predicates = bool(has_pred_btn.isChecked())
                except (RuntimeError, AttributeError) as e:
                    logger.debug(
                        f"Could not read isChecked from geometric predicates button: {e}"
                    )

            # Fallback to PROJECT_LAYERS when the widgets are unavailable.
            if (not predicate_list or not has_predicates) and \
                    hasattr(dw, "PROJECT_LAYERS") and \
                    dw.current_layer:
                layer_id = dw.current_layer.id()
                layer_data = dw.PROJECT_LAYERS.get(layer_id, {})
                filtering_data = layer_data.get("filtering", {}) \
                    if isinstance(layer_data, dict) else {}
                if not predicate_list:
                    stored_list = filtering_data.get("geometric_predicates", [])
                    if isinstance(stored_list, (list, tuple)):
                        predicate_list = list(stored_list)
                if not has_predicates:
                    has_predicates = bool(
                        filtering_data.get("has_geometric_predicates", False)
                    )

            if predicate_list or has_predicates:
                config["geometric_predicates"] = predicate_list
                config["has_geometric_predicates"] = bool(
                    has_predicates or predicate_list
                )
                logger.info(
                    f"Captured geometric_predicates: {predicate_list} "
                    f"(has_geometric_predicates={config['has_geometric_predicates']})"
                )

            # Capture buffer value if set (v5.0 read from widget)
            if hasattr(dw, "mQgsDoubleSpinBox_filtering_buffer_value"):
                buffer_value = dw.mQgsDoubleSpinBox_filtering_buffer_value.value()
                if buffer_value != 0.0:
                    config["buffer_value"] = buffer_value
                    logger.info(f"Captured buffer_value: {buffer_value}")

            logger.info(f"Spatial config captured: {list(config.keys())}")

        except Exception as e:
            logger.warning(f"Failed to capture spatial config: {e}")

        return config if config else None
