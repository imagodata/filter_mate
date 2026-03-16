"""
V01 Sequence 4 — EXPLORATION : NAVIGATION & BARRE LATÉRALE
============================================================
Démonstration contextuelle des outils d'exploration.
Au lieu de lister les boutons, on raconte un scénario :
  1. Navigation ← → (next/prev) dans le sélecteur d'entités
  2. Track activé → chaque changement d'entité recentre la carte
  3. Identify → flash visuel de l'entité courante
  4. Zoom → centrage précis
  5. Select → sélection QGIS persistante sur le canevas
  6. Link → synchronisation des sélecteurs
  7. Reset → réinitialisation
  8. Diagramme récapitulatif

Uses TimelineSequence for narration-synchronized execution.
"""
from __future__ import annotations

import pyautogui

from core.timeline import NarrationCue
from sequences.base import TimelineSequence


class V01S04Sidebar(TimelineSequence):
    name = "V01 — Exploration & Navigation"
    sequence_id = "v01_s04"
    duration_estimate = 55.0
    obs_scene = "QGIS + FilterMate"
    diagram_ids = ["v01_sidebar_buttons"]
    narration_text = ""  # Narration is now in the cues

    def build_timeline(self, obs, qgis, config):
        regions = config["qgis"]["regions"]
        move_dur = config["timing"].get("mouse_move_duration", 0.5)

        def click_next_feature():
            """Click the → button in the feature picker to go to next entity."""
            btn = regions.get("exploring_feature_next_btn")
            if btn:
                pyautogui.click(btn["x"], btn["y"], duration=move_dur)

        def click_prev_feature():
            """Click the ← button in the feature picker to go to previous entity."""
            btn = regions.get("exploring_feature_prev_btn")
            if btn:
                pyautogui.click(btn["x"], btn["y"], duration=move_dur)

        def navigate_features_demo():
            """Step through 3 features using → button to show browsing."""
            click_next_feature()
            qgis.wait(1.5)
            click_next_feature()
            qgis.wait(1.5)
            click_next_feature()
            qgis.wait(1.0)

        def activate_track_and_navigate():
            """Turn on Track, then use ← → to show auto-zoom in action."""
            qgis.toggle_sidebar_button("sidebar_track")
            qgis.wait(0.5)
            # Navigate with auto-zoom active — map follows each selection
            click_next_feature()
            qgis.wait(2.0)
            click_next_feature()
            qgis.wait(2.0)
            click_prev_feature()
            qgis.wait(1.5)

        def demo_identify():
            """Identify: flash the current entity in red on the map."""
            qgis.toggle_sidebar_button("sidebar_identify")
            qgis.wait(2.0)

        def demo_zoom():
            """Zoom: center and fit the map to the current entity."""
            qgis.toggle_sidebar_button("sidebar_zoom")
            qgis.wait(2.0)

        def demo_select():
            """Select: create a persistent QGIS selection on the canvas."""
            qgis.toggle_sidebar_button("sidebar_select")
            qgis.wait(2.0)

        def demo_link():
            """Link: show synchronization between single and multiple pickers."""
            qgis.toggle_sidebar_button("sidebar_link")
            qgis.wait(1.5)

        return [
            # Cue 0: Introduction — set context from previous sequence
            NarrationCue(
                label="Intro exploration",
                text=(
                    "Maintenant que l'interface est en place, "
                    "voyons comment explorer vos données. "
                    "Le sélecteur d'entités possède des boutons "
                    "précédent et suivant pour naviguer une par une."
                ),
                sync="during",
                actions=lambda: (
                    qgis.focus_filtermate(),
                    qgis.hover_region("exploring_feature_selector", duration=1.5),
                ),
                post_delay=0.3,
            ),
            # Cue 1: Next/Prev navigation demo
            NarrationCue(
                label="Navigation ← →",
                text=(
                    "Je clique sur suivant : l'entité change. "
                    "Encore. Et encore. "
                    "C'est la façon la plus rapide de parcourir vos données."
                ),
                sync="during",
                actions=lambda: navigate_features_demo(),
                post_delay=0.3,
            ),
            # Cue 2: Track + navigation combo — the killer feature
            NarrationCue(
                label="Track + Navigation",
                text=(
                    "Activons Track. "
                    "Maintenant, à chaque changement d'entité, "
                    "la carte se recentre automatiquement. "
                    "Suivant… la carte suit. Précédent… elle revient."
                ),
                sync="during",
                actions=lambda: activate_track_and_navigate(),
                post_delay=0.5,
            ),
            # Cue 3: Identify — flash visual
            NarrationCue(
                label="Bouton Identify",
                text=(
                    "Identify fait clignoter l'entité en rouge sur la carte. "
                    "Un repère visuel immédiat."
                ),
                sync="during",
                actions=lambda: demo_identify(),
                post_delay=0.2,
            ),
            # Cue 4: Zoom — precise centering
            NarrationCue(
                label="Bouton Zoom",
                text="Zoom recentre la vue sur l'entité sélectionnée.",
                sync="during",
                actions=lambda: demo_zoom(),
                post_delay=0.2,
            ),
            # Cue 5: Select — QGIS persistent selection
            NarrationCue(
                label="Bouton Select",
                text=(
                    "Select crée une sélection QGIS persistante sur le canevas. "
                    "L'entité reste surlignée tant que vous ne désélectionnez pas."
                ),
                sync="during",
                actions=lambda: demo_select(),
                post_delay=0.2,
            ),
            # Cue 6: Link — sync pickers
            NarrationCue(
                label="Bouton Link",
                text=(
                    "Link synchronise le sélecteur simple et le sélecteur multiple. "
                    "Quand vous changez le champ d'affichage dans l'un, "
                    "l'autre se met à jour."
                ),
                sync="during",
                actions=lambda: demo_link(),
                post_delay=0.2,
            ),
            # Cue 7: Reset — hover only
            NarrationCue(
                label="Bouton Reset",
                text=(
                    "Et Reset réinitialise toutes les propriétés "
                    "d'exploration de la couche."
                ),
                sync="during",
                actions=lambda: qgis.hover_region("sidebar_reset", duration=2.0),
                post_delay=0.3,
            ),
            # Cue 8: Diagram recap
            NarrationCue(
                label="Diagramme sidebar",
                text="",
                actions=lambda: self.show_diagram_and_return(
                    obs, qgis, "v01_sidebar_buttons", duration=5.0
                ),
                post_delay=0.5,
            ),
        ]
