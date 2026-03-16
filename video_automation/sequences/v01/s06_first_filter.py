"""
V01 Sequence 6 — PREMIER FILTRAGE : SHAPEFILE LOCAL
====================================================
Demo live : départements + communes. Sélectionner Gironde, clignotement
+ zoom via boutons exploring, activer auto-canvas, filtrer Intersects.
Démo Undo pour montrer l'historique, puis Unfilter pour la réversibilité.

Fixes applied:
- sidebar_identify for flash (was incorrectly using sidebar_select)
- sidebar_select for persistent QGIS selection
- Added next/prev navigation to switch entity before filtering
- Added Undo demonstration

Uses TimelineSequence for narration-synchronized execution.
"""
from __future__ import annotations

import time

import pyautogui

from core.timeline import NarrationCue
from sequences.base import TimelineSequence


class V01S06FirstFilter(TimelineSequence):
    name = "V01 — Premier filtrage Shapefile"
    sequence_id = "v01_s06"
    duration_estimate = 120.0
    obs_scene = "QGIS + FilterMate"
    diagram_ids = ["v01_first_filter_workflow"]
    narration_text = ""  # Narration is now in the cues

    def build_timeline(self, obs, qgis, config):
        regions = config["qgis"]["regions"]
        move_dur = config["timing"].get("mouse_move_duration", 0.5)
        canvas = regions.get("main_canvas", {})
        if canvas:
            cx = canvas["x"] + canvas["width"] // 2
            cy = canvas["y"] + canvas["height"] // 2
        else:
            cx, cy = 960, 540

        def click_next_feature():
            btn = regions.get("exploring_feature_next_btn")
            if btn:
                pyautogui.click(btn["x"], btn["y"], duration=move_dur)

        def select_gironde():
            self._log.info("Selecting exploring layer 'departements'")
            # Click the exploring layer combo + press Down to reach 'departements'
            layer_combo = regions.get("exploring_layer_combo")
            if layer_combo:
                pyautogui.click(layer_combo["x"], layer_combo["y"], duration=move_dur)
                qgis.wait(0.3)
                pyautogui.press("down")
                qgis.wait(0.3)
                pyautogui.press("enter")
            else:
                qgis.select_exploring_layer("departements", index=2)
            qgis.wait(0.5)
            self._log.info("Navigating to 'Gironde'")
            qgis.select_combobox_item("exploring_feature_selector", "Gironde")

        def flash_and_zoom_gironde():
            """Use Identify (flash) + Zoom (center) — correct button usage."""
            # Identify = flash the entity in red on the map (visual highlight)
            self._log.info("Flashing Gironde with sidebar_identify")
            qgis.toggle_sidebar_button("sidebar_identify")
            qgis.wait(1.5)

            # Zoom = center the map on Gironde
            self._log.info("Zooming to Gironde with sidebar_zoom")
            qgis.toggle_sidebar_button("sidebar_zoom")
            qgis.wait(2.0)

        def activate_auto_canvas():
            """Activate auto-move canvas: Track enables auto-zoom on selection change."""
            self._log.info("Activating auto-canvas (sidebar_track)")
            qgis.toggle_sidebar_button("sidebar_track")
            qgis.wait(0.5)

        def navigate_to_another_department():
            """Use next/prev to switch to a neighboring department, showing navigation."""
            self._log.info("Navigating with next button to show entity switching")
            click_next_feature()
            qgis.wait(2.0)  # Track auto-zooms to new entity
            # Go back to Gironde
            self._log.info("Navigating back to Gironde")
            qgis.select_combobox_item("exploring_feature_selector", "Gironde")
            qgis.wait(1.5)

        def setup_filter():
            self._log.info("Switching to FILTERING tab")
            qgis.select_tab("FILTERING")
            qgis.wait(0.5)
            # Click source layer combo + press Down to select the layer
            src = regions.get("source_layer_combo")
            if src:
                pyautogui.click(src["x"], src["y"], duration=move_dur)
                qgis.wait(0.3)
                pyautogui.press("down")
                qgis.wait(0.2)
                pyautogui.press("down")
                qgis.wait(0.3)
                pyautogui.press("enter")
            qgis.wait(0.5)

        def select_target():
            self._log.info("Selecting target layer 'communes'")
            qgis.select_target_layer("communes")

        def select_predicate():
            self._log.info("Selecting predicate 'Intersects'")
            qgis.select_predicate("intersects")

        def execute_filter():
            self._log.info("Clicking FILTER")
            qgis.click_action_button("filter")
            time.sleep(3.0)  # Wait for query completion

        def show_result():
            self._log.info("Showing result on map")
            qgis.move_mouse_to(cx - 200, cy, duration=1.5)
            qgis.wait(1.0)
            qgis.move_mouse_to(cx + 200, cy, duration=1.5)

        def execute_undo():
            """Demonstrate Undo — restore previous state."""
            self._log.info("Clicking UNDO to demonstrate history")
            qgis.click_action_button("undo")
            time.sleep(2.0)

        def execute_redo():
            """Demonstrate Redo — re-apply filter."""
            self._log.info("Clicking REDO to re-apply filter")
            qgis.click_action_button("redo")
            time.sleep(2.0)

        def execute_unfilter():
            self._log.info("Clicking UNFILTER to show reversibility")
            qgis.click_action_button("unfilter")
            time.sleep(2.0)

        def show_backend_and_diagram():
            qgis.hover_region("badge_backend", duration=2.0)
            self.show_diagram(obs, "v01_first_filter_workflow", duration=6.0)
            qgis.focus_qgis()

        return [
            # Cue 0: Introduce the demo
            NarrationCue(
                label="Introduction démo",
                text=(
                    "Passons à la pratique. Nos deux couches sont chargées : "
                    "les départements et les communes."
                ),
                sync="during",
                actions=lambda: qgis.focus_filtermate(),
                post_delay=0.5,
            ),
            # Cue 1: Select layer + feature
            NarrationCue(
                label="Sélection Gironde",
                text=(
                    "Dans la Zone d'Exploration, je sélectionne la couche "
                    "départements. Je choisis Gironde."
                ),
                sync="during",
                actions=lambda: select_gironde(),
                post_delay=0.5,
            ),
            # Cue 2: Flash + zoom using CORRECT buttons (Identify + Zoom)
            NarrationCue(
                label="Clignotement + Zoom Gironde",
                text=(
                    "J'utilise les boutons de la barre latérale. "
                    "Identify fait clignoter la Gironde en rouge sur la carte. "
                    "Zoom centre la vue dessus."
                ),
                sync="during",
                actions=lambda: flash_and_zoom_gironde(),
                post_delay=0.5,
            ),
            # Cue 3: Activate auto-canvas tracking
            NarrationCue(
                label="Activation auto-canvas",
                text=(
                    "J'active le suivi automatique avec Track. "
                    "Désormais, la carte suivra chaque sélection."
                ),
                sync="during",
                actions=lambda: activate_auto_canvas(),
                post_delay=0.3,
            ),
            # Cue 4: Navigate to another department then back (show next/prev)
            NarrationCue(
                label="Navigation next/prev",
                text=(
                    "Avec le bouton suivant, je peux passer au département voisin. "
                    "La carte suit automatiquement. "
                    "Je reviens sur la Gironde."
                ),
                sync="during",
                actions=lambda: navigate_to_another_department(),
                post_delay=0.3,
            ),
            # Cue 5: Configure filter
            NarrationCue(
                label="Onglet FILTERING",
                text=(
                    "Dans l'onglet FILTERING, FilterMate a reconnu ma sélection."
                ),
                sync="during",
                actions=lambda: setup_filter(),
                post_delay=0.3,
            ),
            # Cue 6: Target layer
            NarrationCue(
                label="Couche cible communes",
                text="En couche cible, je choisis communes.",
                sync="during",
                actions=lambda: select_target(),
                post_delay=0.3,
            ),
            # Cue 7: Predicate
            NarrationCue(
                label="Prédicat Intersects",
                text="Prédicat spatial : Intersects.",
                sync="during",
                actions=lambda: select_predicate(),
                post_delay=0.3,
            ),
            # Cue 8: Execute filter
            NarrationCue(
                label="Clic Filter",
                text="Je clique sur Filter.",
                sync="during",
                actions=lambda: execute_filter(),
                post_delay=0.5,
            ),
            # Cue 9: Show results
            NarrationCue(
                label="Résultat filtrage",
                text=(
                    "Les 35 000 communes sont filtrées instantanément. "
                    "Seules celles qui intersectent la Gironde restent visibles. "
                    "La carte s'est recentrée automatiquement."
                ),
                sync="during",
                actions=lambda: show_result(),
                post_delay=0.5,
            ),
            # Cue 10: Undo — demonstrate history
            NarrationCue(
                label="Démonstration Undo",
                text=(
                    "Undo annule le filtre. Les communes réapparaissent."
                ),
                sync="during",
                actions=lambda: execute_undo(),
                post_delay=0.3,
            ),
            # Cue 11: Redo — re-apply
            NarrationCue(
                label="Démonstration Redo",
                text=(
                    "Redo le rétablit immédiatement. "
                    "100 états d'historique sont conservés."
                ),
                sync="during",
                actions=lambda: execute_redo(),
                post_delay=0.3,
            ),
            # Cue 12: Unfilter to show full reversibility
            NarrationCue(
                label="Démonstration Unfilter",
                text=(
                    "Et Unfilter retire tous les filtres d'un coup. "
                    "Chaque action est réversible."
                ),
                sync="during",
                actions=lambda: execute_unfilter(),
                post_delay=0.5,
            ),
            # Cue 13: Backend detection + diagram
            NarrationCue(
                label="Détection backend OGR",
                text="FilterMate a détecté le backend OGR automatiquement.",
                sync="during",
                actions=lambda: show_backend_and_diagram(),
                post_delay=1.0,
            ),
        ]
