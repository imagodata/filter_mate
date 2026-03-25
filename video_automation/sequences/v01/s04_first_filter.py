"""
V01 Sequence 4 — PREMIER FILTRAGE : SHAPEFILE LOCAL
====================================================
Demo live : naviguer avec next/prev, configurer le filtre
(couche cible communes, prédicat Intersects), exécuter,
puis montrer Undo/Redo/Unfilter pour la réversibilité.

Les boutons de la barre latérale (Identify, Zoom, Track…)
ont déjà été présentés dans s03 — pas de re-démo ici.

Uses TimelineSequence for narration-synchronized execution.
"""
from __future__ import annotations

import time

import pyautogui

from core.timeline import NarrationCue
from sequences.base import TimelineSequence


class V01S04FirstFilter(TimelineSequence):
    name = "V01 — Premier filtrage Shapefile"
    sequence_id = "v01_s04"
    duration_estimate = 75.0
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

        def click_prev_feature():
            btn = regions.get("exploring_feature_prev_btn")
            if btn:
                pyautogui.click(btn["x"], btn["y"], duration=move_dur)

        def navigate_to_entity():
            """Use next/prev to land on a department — no typing."""
            self._log.info("Navigating with next/prev buttons")
            click_next_feature()
            qgis.wait(1.5)
            click_next_feature()
            qgis.wait(1.5)

        def setup_filter():
            self._log.info("Switching to FILTERING tab")
            qgis.select_tab("FILTERING")
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
            # Cue 1: Navigate with next/prev to pick an entity
            NarrationCue(
                label="Navigation entité",
                text=(
                    "Avec les boutons suivant et précédent, "
                    "je me place sur un département."
                ),
                sync="during",
                actions=lambda: navigate_to_entity(),
                post_delay=0.5,
            ),
            # Cue 2: Switch to FILTERING tab
            NarrationCue(
                label="Onglet FILTERING",
                text=(
                    "Dans l'onglet FILTERING, FilterMate a reconnu ma sélection."
                ),
                sync="during",
                actions=lambda: setup_filter(),
                post_delay=0.3,
            ),
            # Cue 3: Target layer
            NarrationCue(
                label="Couche cible communes",
                text="En couche cible, je choisis communes.",
                sync="during",
                actions=lambda: select_target(),
                post_delay=0.3,
            ),
            # Cue 4: Predicate
            NarrationCue(
                label="Prédicat Intersects",
                text="Prédicat spatial : Intersects.",
                sync="during",
                actions=lambda: select_predicate(),
                post_delay=0.3,
            ),
            # Cue 5: Execute filter
            NarrationCue(
                label="Clic Filter",
                text="Je clique sur Filter.",
                sync="during",
                actions=lambda: execute_filter(),
                post_delay=0.5,
            ),
            # Cue 6: Show results
            NarrationCue(
                label="Résultat filtrage",
                text=(
                    "Les 35 000 communes sont filtrées instantanément. "
                    "Seules celles qui intersectent le département sélectionné "
                    "restent visibles."
                ),
                sync="during",
                actions=lambda: show_result(),
                post_delay=0.5,
            ),
            # Cue 7: Undo
            NarrationCue(
                label="Démonstration Undo",
                text="Undo. Toutes les communes réapparaissent.",
                sync="during",
                actions=lambda: execute_undo(),
                post_delay=0.3,
            ),
            # Cue 8: Redo
            NarrationCue(
                label="Démonstration Redo",
                text="Redo. Le filtre est rétabli.",
                sync="during",
                actions=lambda: execute_redo(),
                post_delay=0.3,
            ),
            # Cue 9: Unfilter
            NarrationCue(
                label="Démonstration Unfilter",
                text=(
                    "Unfilter retire tous les filtres d'un coup. "
                    "Chaque action est réversible."
                ),
                sync="during",
                actions=lambda: execute_unfilter(),
                post_delay=0.5,
            ),
            # Cue 10: Backend detection + diagram
            NarrationCue(
                label="Détection backend OGR",
                text="FilterMate a détecté le backend OGR automatiquement.",
                sync="during",
                actions=lambda: show_backend_and_diagram(),
                post_delay=1.0,
            ),
        ]
