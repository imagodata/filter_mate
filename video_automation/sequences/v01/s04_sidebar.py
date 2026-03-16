"""
V01 Sequence 4 — BARRE LATÉRALE : 6 BOUTONS (DÉMO LIVE)
==========================================================
Démonstration live de chaque bouton avec clic ou activation :
  1. Identify → clic → flash rouge de l'entité
  2. Zoom → clic → carte centrée
  3. Select → ON, sélectionner Seine-et-Marne, OFF
  4. Track → activation → suivi automatique
  5. Link → déjà actif par défaut (pas de clic)
  6. Reset → décrit seulement (pas déclenché)
  7. Diagramme récapitulatif

Uses TimelineSequence for narration-synchronized execution.
"""
from __future__ import annotations

import pyautogui

from core.timeline import NarrationCue
from sequences.base import TimelineSequence


class V01S04Sidebar(TimelineSequence):
    name = "V01 — Barre latérale (6 boutons)"
    sequence_id = "v01_s04"
    duration_estimate = 55.0
    obs_scene = "QGIS + FilterMate"
    diagram_ids = ["v01_sidebar_buttons"]
    narration_text = ""  # Narration is now in the cues

    def build_timeline(self, obs, qgis, config):
        regions = config["qgis"]["regions"]
        move_dur = config["timing"].get("mouse_move_duration", 0.5)

        def click_next_feature():
            btn = regions.get("exploring_feature_next_btn")
            if btn:
                pyautogui.click(btn["x"], btn["y"], duration=move_dur)

        def demo_identify():
            """Identify: flash the current entity in red on the map."""
            qgis.toggle_sidebar_button("sidebar_identify")
            qgis.wait(2.0)

        def demo_zoom():
            """Zoom: center and fit the map to the current entity."""
            qgis.toggle_sidebar_button("sidebar_zoom")
            qgis.wait(2.0)

        def demo_select_seine_et_marne():
            """Select ON, pick Seine-et-Marne, show highlight, then OFF."""
            qgis.toggle_sidebar_button("sidebar_select")
            qgis.wait(0.5)
            # Navigate to Seine-et-Marne
            qgis.select_combobox_item(
                "exploring_feature_selector", "Seine-et-Marne"
            )
            qgis.wait(2.0)
            # Toggle off — highlight disappears
            qgis.toggle_sidebar_button("sidebar_select")
            qgis.wait(1.0)

        def demo_track():
            """Track ON, navigate to show auto-zoom."""
            qgis.toggle_sidebar_button("sidebar_track")
            qgis.wait(0.5)
            click_next_feature()
            qgis.wait(2.0)
            click_next_feature()
            qgis.wait(2.0)

        return [
            # Cue 0: Introduction
            NarrationCue(
                label="Intro barre latérale",
                text=(
                    "La Zone d'Exploration possède 6 boutons "
                    "dans sa barre latérale. Voyons-les en action."
                ),
                sync="during",
                actions=lambda: (
                    qgis.focus_filtermate(),
                    qgis.hover_region("exploring_feature_selector", duration=1.5),
                ),
                post_delay=0.3,
            ),
            # Cue 1: Identify — click → flash
            NarrationCue(
                label="Bouton Identify",
                text=(
                    "Identify. Je clique : l'entité clignote en rouge "
                    "sur la carte. Un flash visuel pour la repérer "
                    "instantanément."
                ),
                sync="during",
                actions=lambda: demo_identify(),
                post_delay=0.3,
            ),
            # Cue 2: Zoom — click → center
            NarrationCue(
                label="Bouton Zoom",
                text=(
                    "Zoom. Je clique : la carte se centre "
                    "et zoome sur l'entité en cours."
                ),
                sync="during",
                actions=lambda: demo_zoom(),
                post_delay=0.3,
            ),
            # Cue 3: Select — ON, Seine-et-Marne, OFF
            NarrationCue(
                label="Bouton Select",
                text=(
                    "Select. J'active le bouton, puis je sélectionne "
                    "la Seine-et-Marne dans le sélecteur. "
                    "Le département apparaît en surbrillance sur la carte, "
                    "juste à côté de Paris. "
                    "Je désactive : la surbrillance disparaît."
                ),
                sync="during",
                actions=lambda: demo_select_seine_et_marne(),
                post_delay=0.3,
            ),
            # Cue 4: Track — activate + navigate
            NarrationCue(
                label="Bouton Track",
                text=(
                    "Track. J'active le suivi automatique. "
                    "Maintenant, à chaque changement d'entité "
                    "dans le sélecteur, la carte se recentre "
                    "automatiquement."
                ),
                sync="during",
                actions=lambda: demo_track(),
                post_delay=0.3,
            ),
            # Cue 5: Link — already active by default
            NarrationCue(
                label="Bouton Link",
                text=(
                    "Link. Celui-ci est déjà activé par défaut. "
                    "Il synchronise les trois groupes de sélection, "
                    "simple, multiple et personnalisé, "
                    "entre eux automatiquement."
                ),
                sync="during",
                actions=lambda: qgis.hover_region("sidebar_link", duration=2.5),
                post_delay=0.3,
            ),
            # Cue 6: Reset — describe only, don't trigger
            NarrationCue(
                label="Bouton Reset",
                text=(
                    "Reset réinitialise toutes les propriétés "
                    "d'exploration de la couche active. "
                    "Un retour à zéro propre. "
                    "On ne le déclenche pas maintenant "
                    "pour garder notre contexte."
                ),
                sync="during",
                actions=lambda: qgis.hover_region("sidebar_reset", duration=2.5),
                post_delay=0.3,
            ),
            # Cue 7: Diagram recap
            NarrationCue(
                label="Diagramme sidebar",
                text="",
                actions=lambda: self.show_diagram_and_return(
                    obs, qgis, "v01_sidebar_buttons", duration=5.0
                ),
                post_delay=0.5,
            ),
        ]
