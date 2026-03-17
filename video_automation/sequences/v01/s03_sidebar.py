"""
V01 Sequence 3 — BARRE LATÉRALE : 6 BOUTONS (DÉMO LIVE)
==========================================================
Démonstration live de chaque bouton avec clic ou activation :
  1. Identify → clic → flash rouge de l'entité
  2. Zoom → clic → carte centrée
  3. Select + Track → CAPTURE MANUELLE (bug connu avec pyautogui)
  4. Link → toggle OFF/ON pour montrer l'effet
  5. Reset → décrit seulement (pas déclenché)
  6. Diagramme récapitulatif

NOTE: Select et Track nécessitent une capture manuelle car les
interactions pyautogui avec le feature picker ne déclenchent pas
correctement les signaux featureChanged de QgsFeaturePickerWidget.
La narration audio est quand même générée pour ces cues, il suffit
de réaliser les actions manuellement pendant la lecture.

Uses TimelineSequence for narration-synchronized execution.
"""
from __future__ import annotations

from core.timeline import NarrationCue
from sequences.base import TimelineSequence


class V01S03Sidebar(TimelineSequence):
    name = "V01 — Barre latérale (6 boutons)"
    sequence_id = "v01_s03"
    duration_estimate = 55.0
    obs_scene = "QGIS + FilterMate"
    diagram_ids = ["v01_sidebar_buttons"]
    narration_text = ""  # Narration is now in the cues

    def build_timeline(self, obs, qgis, config):

        def demo_identify():
            """Identify: click → flash the current entity."""
            qgis.click_at("sidebar_identify")
            qgis.wait(2.0)

        def demo_zoom():
            """Zoom: click → center and fit map."""
            qgis.click_at("sidebar_zoom")
            qgis.wait(2.0)

        def demo_link():
            """Link: toggle OFF then back ON to show the effect."""
            qgis.click_at("sidebar_link")
            qgis.wait(1.0)
            qgis.click_at("sidebar_link")
            qgis.wait(1.0)

        return [
            # Cue 0: Introduction — single focus, no extra hover
            NarrationCue(
                label="Intro barre latérale",
                text=(
                    "La Zone d'Exploration possède 6 boutons "
                    "dans sa barre latérale. Voyons-les en action."
                ),
                sync="during",
                actions=lambda: qgis.focus_filtermate(),
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
            # Cue 3: Select — CAPTURE MANUELLE
            # BUG: pyautogui ne déclenche pas featureChanged sur QgsFeaturePickerWidget.
            # Actions manuelles : Select ON → next → surbrillance visible → Select OFF.
            NarrationCue(
                label="Bouton Select (MANUEL)",
                text=(
                    "Select. J'active le bouton, puis je passe "
                    "au département suivant avec le bouton next. "
                    "Le département apparaît en surbrillance sur la carte. "
                    "Je désactive : la surbrillance disparaît."
                ),
                sync="after",
                actions=None,
                post_delay=0.3,
            ),
            # Cue 4: Track — CAPTURE MANUELLE
            # BUG: même problème, pyautogui + featureChanged incompatible.
            # Actions manuelles : Track ON → next → carte recentrée → next → recentrée.
            NarrationCue(
                label="Bouton Track (MANUEL)",
                text=(
                    "Track. J'active le suivi automatique. "
                    "Maintenant, à chaque changement d'entité "
                    "dans le sélecteur, la carte se recentre "
                    "automatiquement."
                ),
                sync="after",
                actions=None,
                post_delay=0.3,
            ),
            # Cue 5: Link — toggle OFF/ON to demo
            NarrationCue(
                label="Bouton Link",
                text=(
                    "Link. Celui-ci est déjà activé par défaut. "
                    "Il synchronise les trois groupes de sélection, "
                    "simple, multiple et personnalisé, "
                    "entre eux automatiquement."
                ),
                sync="during",
                actions=lambda: demo_link(),
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
