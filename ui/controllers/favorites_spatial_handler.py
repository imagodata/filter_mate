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

    # ── method 4 — restore_spatial_config -----------------------------

    def restore_spatial_config(self, favorite: "FilterFavorite") -> bool:
        """Restore spatial configuration from favorite to dockwidget.

        Ensures task_features (selected FIDs) are available when
        ``launchTaskEvent`` is called, so the filter task can rebuild
        EXISTS expressions correctly.

        Returns True if config was restored successfully.
        """
        from .favorites_spatial_helpers import favorite_matches_current_layer

        if not favorite.spatial_config:
            logger.warning(
                f"Favorite '{favorite.name}' has no spatial_config to restore"
            )
            return False

        dw = self._dockwidget

        try:
            config = favorite.spatial_config

            # FIX 2026-04-21: restore the exploring groupbox mode FIRST
            # so downstream widgets (picker, multi-select combo, custom
            # selection expression) are in the right state when
            # task_features / predicates are read back.
            saved_groupbox = config.get("exploring_groupbox")
            if saved_groupbox and hasattr(dw, "_restore_groupbox_ui_state"):
                try:
                    dw._restore_groupbox_ui_state(saved_groupbox)
                    logger.info(f"  ✓ Restored exploring_groupbox = {saved_groupbox}")
                except (AttributeError, RuntimeError) as e:
                    logger.debug(f"Could not restore exploring_groupbox: {e}")

            # Repopulate the EXPLORING custom_selection expression widget
            # when the favorite was saved in that mode.
            custom_expr = config.get("custom_selection_expression")
            if custom_expr:
                try:
                    widget = dw.widgets.get("EXPLORING", {}) \
                        .get("CUSTOM_SELECTION_EXPRESSION", {}).get("WIDGET")
                    if widget is not None and hasattr(widget, "setExpression"):
                        widget.setExpression(custom_expr)
                        logger.info("  ✓ Restored custom_selection_expression")
                except (AttributeError, KeyError, RuntimeError) as e:
                    logger.debug(f"Could not restore custom_selection_expression: {e}")

            # Restore selected feature IDs (task_features)
            if "task_feature_ids" in config and dw.current_layer:
                feature_ids = config["task_feature_ids"]
                logger.info(
                    f"Restoring {len(feature_ids)} task_feature IDs from favorite"
                )

                source_layer = dw.current_layer

                # FIX 2026-04-21: only push IDs / fetch features when the
                # current layer is the same one the favorite was captured
                # against. Cross-layer apply must not corrupt another
                # layer's selection with foreign FIDs.
                if favorite_matches_current_layer(favorite, source_layer):
                    # Push feature IDs into QGIS layer selection so the
                    # feature picker / multi-select widgets surface them.
                    try:
                        source_layer.selectByIds(feature_ids)
                        logger.info(
                            f"  ✓ Pushed {len(feature_ids)} feature IDs to QGIS "
                            f"selection on '{source_layer.name()}'"
                        )
                    except (AttributeError, RuntimeError) as e:
                        logger.debug(f"Could not selectByIds on source layer: {e}")

                    # Fetch actual QgsFeature objects from the source layer
                    features = []
                    for fid in feature_ids:
                        feature = source_layer.getFeature(fid)
                        if feature and feature.isValid():
                            features.append(feature)
                        else:
                            logger.warning(
                                f"  ⚠️ Could not fetch feature {fid} from "
                                f"{source_layer.name()}"
                            )

                    if features:
                        logger.info(
                            f"  → Loaded {len(features)} features from "
                            f"{len(feature_ids)} FIDs"
                        )
                        # Store in dockwidget for get_current_features() to pick up
                        dw._restored_task_features = features
                        logger.info(
                            f"  ✓ Stored {len(features)} features in "
                            f"dockwidget._restored_task_features"
                        )
                    else:
                        logger.warning(
                            f"  ⚠️ Could not load any features from "
                            f"{len(feature_ids)} FIDs!"
                        )
                else:
                    logger.info(
                        f"  ↪ Skipping selectByIds: current layer "
                        f"'{source_layer.name()}' does not match favorite's "
                        f"source layer — FIDs would be meaningless."
                    )

            # Restore predicates if present
            if "predicates" in config:
                predicates = config["predicates"]
                logger.info(f"Restoring predicates: {list(predicates.keys())}")
                # Store in dockwidget for task to pick up
                dw._restored_predicates = predicates

            # Restore buffer settings if present
            if "buffer_value" in config:
                buffer_value = config["buffer_value"]
                logger.info(f"Restoring buffer_value: {buffer_value}")
                # v5.0: Set buffer widget value
                if hasattr(dw, "mQgsDoubleSpinBox_filtering_buffer_value"):
                    dw.mQgsDoubleSpinBox_filtering_buffer_value.setValue(
                        float(buffer_value)
                    )
                    logger.info(f"  ✓ Buffer widget set to {buffer_value}")

            logger.info(
                f"✓ Spatial config restored from favorite '{favorite.name}'"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to restore spatial_config: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    # ── method 5 — restore_filtering_ui_from_favorite -----------------

    def restore_filtering_ui_from_favorite(
        self, favorite: "FilterFavorite"
    ) -> None:
        """Restore filtering UI state from a favorite.

        Mirrors the non-UI restoration done in :meth:`restore_spatial_config`
        but actually ticks the widgets (Intersect predicate button,
        layers_to_filter combobox, has_layers_to_filter button,
        has_buffer_value button) and persists into ``PROJECT_LAYERS`` so
        ``sync_ui_to_project_layers`` sees a coherent state on
        ``launchTaskEvent``.
        """
        from qgis.PyQt.QtCore import Qt
        from .favorites_spatial_helpers import layer_signature_for

        dw = self._dockwidget
        if not dw or not getattr(dw, "widgets_initialized", False):
            logger.debug("Skipping UI restore: dockwidget not ready")
            return

        spatial_config = favorite.spatial_config or {}

        # FIX 2026-04-23: resolve geometric predicates from the canonical
        # fields first. Fall back to the legacy ``predicates`` dict shape
        # (written by pre-fix favorites and a handful of portability
        # tests) so existing favorites keep restoring without a manual
        # rebuild.
        predicate_list = spatial_config.get("geometric_predicates")
        if isinstance(predicate_list, (list, tuple)):
            predicate_list = list(predicate_list)
            predicate_explicit = True
        else:
            legacy_predicates = spatial_config.get("predicates") or {}
            if isinstance(legacy_predicates, dict) and legacy_predicates:
                predicate_list = list(legacy_predicates.keys())
                predicate_explicit = True
            elif isinstance(legacy_predicates, (list, tuple)) and legacy_predicates:
                predicate_list = list(legacy_predicates)
                predicate_explicit = True
            else:
                predicate_list = []
                predicate_explicit = False

        has_predicates_flag = spatial_config.get("has_geometric_predicates")
        if has_predicates_flag is None:
            has_predicates_flag = bool(predicate_list)
        else:
            has_predicates_flag = bool(has_predicates_flag)
            predicate_explicit = True

        # FIX 2026-04-27: when the favorite carries no predicate info at
        # all, leave the live combobox / toggle untouched instead of
        # silently clearing them. ``apply_favorite`` already backfills
        # legacy favorites with an "Intersect" default, so reaching this
        # branch means a portability path bypassed the heal — preserve
        # the user's manual selection rather than regressing.

        buffer_value = spatial_config.get("buffer_value")

        current_layer = getattr(dw, "current_layer", None)
        layer_props = None
        if current_layer is not None and hasattr(dw, "PROJECT_LAYERS"):
            try:
                layer_props = dw.PROJECT_LAYERS.get(current_layer.id())
            except (RuntimeError, AttributeError):
                layer_props = None

        # --- 1. Resolve target layer ids from remote_layers payload ---
        resolved_layer_ids: list = []
        try:
            from qgis.core import QgsProject
            project = QgsProject.instance()
            name_to_id = {}
            signature_to_id = {}
            for lid, lobj in project.mapLayers().items():
                try:
                    name_to_id[lobj.name()] = lid
                    signature_to_id[layer_signature_for(lobj)] = lid
                except (RuntimeError, AttributeError):
                    continue
            for key, payload in (favorite.remote_layers or {}).items():
                resolved = None
                # Signature stored in payload (v2+) — portable across projects
                if isinstance(payload, dict) and payload.get("layer_signature"):
                    resolved = signature_to_id.get(payload["layer_signature"])
                # FIX 2026-04-23 (CRIT-3): when dict key itself is a
                # signature (v3 canonical form produced by
                # ``_create_favorite``), resolve directly from the
                # signature->id map.
                if not resolved and isinstance(key, str) and "::" in key:
                    resolved = signature_to_id.get(key)
                # Legacy format: key is layer name, payload carries layer_id
                if not resolved and isinstance(payload, dict):
                    legacy_id = payload.get("layer_id")
                    if legacy_id and legacy_id in project.mapLayers():
                        resolved = legacy_id
                # Last-chance resolution by display name. Skip when key
                # is a signature (contains "::") — that lookup would
                # always miss and might accidentally hit a user-named
                # layer called "postgres::..." — unlikely but not worth
                # risking.
                if not resolved:
                    candidate_name = None
                    if isinstance(payload, dict):
                        candidate_name = payload.get("display_name")
                    if not candidate_name and isinstance(key, str) and "::" not in key:
                        candidate_name = key
                    if candidate_name:
                        resolved = name_to_id.get(candidate_name)
                if resolved and resolved != getattr(current_layer, "id", lambda: None)():
                    resolved_layer_ids.append(resolved)
        except Exception as e:
            logger.debug(f"Could not resolve favorite target layers: {e}")

        # --- 2. Tick the layers_to_filter combobox ---
        try:
            layers_widget = dw.widgets.get("FILTERING", {}) \
                .get("LAYERS_TO_FILTER", {}).get("WIDGET")
            if layers_widget is not None and resolved_layer_ids:
                resolved_set = set(resolved_layer_ids)
                for i in range(layers_widget.count()):
                    data = layers_widget.itemData(i, Qt.ItemDataRole.UserRole)
                    lid = data.get("layer_id") if isinstance(data, dict) else data
                    state = (
                        Qt.CheckState.Checked
                        if lid in resolved_set
                        else Qt.CheckState.Unchecked
                    )
                    layers_widget.model().item(i).setCheckState(state)
                logger.info(
                    f"  ✓ Favorite restore: ticked {len(resolved_set)} target layer(s)"
                )
        except Exception as e:
            logger.debug(f"Could not tick layers_to_filter: {e}")

        # --- 3. Tick the HAS_LAYERS_TO_FILTER button ---
        try:
            has_layers_btn = getattr(
                dw, "pushButton_checkable_filtering_layers_to_filter", None
            )
            if has_layers_btn is not None:
                has_layers_btn.setChecked(bool(resolved_layer_ids))
        except Exception as e:
            logger.debug(f"Could not toggle HAS_LAYERS_TO_FILTER: {e}")

        # --- 4. Tick HAS_GEOMETRIC_PREDICATES + propagate predicates ---
        #
        # FIX 2026-04-23: previously only the push-button was toggled,
        # so the combobox items came from whatever QGIS had persisted
        # at the project level — typically out-of-sync with the
        # favorite. We now drive both widgets from the favorite's
        # ``geometric_predicates`` list so ``sync_ui_to_project_layers``
        # / task_builder see a consistent state.
        if predicate_explicit:
            try:
                combo_widget = getattr(
                    dw, "comboBox_filtering_geometric_predicates", None
                )
                if combo_widget is not None and hasattr(combo_widget, "setCheckedItems"):
                    combo_widget.setCheckedItems(predicate_list)
            except Exception as e:
                logger.debug(
                    f"Could not set checkedItems on geometric_predicates combobox: {e}"
                )

            try:
                has_pred_btn = getattr(
                    dw, "pushButton_checkable_filtering_geometric_predicates", None
                )
                if has_pred_btn is not None:
                    has_pred_btn.setChecked(bool(has_predicates_flag))
            except Exception as e:
                logger.debug(f"Could not toggle HAS_GEOMETRIC_PREDICATES: {e}")
        else:
            logger.info(
                "  ↪ Favorite carries no predicate info — leaving live "
                "geometric_predicates widgets untouched."
            )

        # --- 5. Tick the HAS_BUFFER_VALUE button ---
        # FIX 2026-04-21: the spinbox value is set in restore_spatial_config,
        # but sync_ui_to_project_layers reads has_buffer_value from the
        # ``pushButton_checkable_filtering_buffer_value`` toggle state, not
        # from the spinbox. Without this, a favorite with buffer_value=2.0
        # restored as expected in the spinbox but has_buffer_value stayed
        # False — meaning the buffer was silently ignored in the filter.
        try:
            has_buffer_btn = getattr(
                dw, "pushButton_checkable_filtering_buffer_value", None
            )
            if has_buffer_btn is not None:
                wants_buffer = buffer_value is not None and float(buffer_value) != 0.0
                has_buffer_btn.setChecked(bool(wants_buffer))
        except (AttributeError, TypeError, ValueError) as e:
            logger.debug(f"Could not toggle HAS_BUFFER_VALUE: {e}")

        # --- 6. Persist restored state into PROJECT_LAYERS ---
        #
        # FIX 2026-04-23: write to the canonical keys
        # (``has_geometric_predicates`` + ``geometric_predicates`` list)
        # that task_builder + filtering orchestrator actually read. The
        # previous ``filtering_props["predicates"] = dict`` write was
        # dead: nothing in the task pipeline ever reads it.
        if layer_props is not None:
            filtering_props = layer_props.setdefault("filtering", {})
            filtering_props["has_layers_to_filter"] = bool(resolved_layer_ids)
            filtering_props["layers_to_filter"] = resolved_layer_ids
            if predicate_explicit:
                filtering_props["has_geometric_predicates"] = bool(has_predicates_flag)
                filtering_props["geometric_predicates"] = list(predicate_list)
            if buffer_value is not None:
                filtering_props["has_buffer_value"] = float(buffer_value) != 0.0
                filtering_props["buffer_value"] = float(buffer_value)
            logger.debug(
                f"Favorite restore persisted into PROJECT_LAYERS"
                f"[{current_layer.id()}]: "
                f"layers={len(resolved_layer_ids)}, "
                f"geometric_predicates={predicate_list} "
                f"(has_geometric_predicates={bool(has_predicates_flag)})"
            )
