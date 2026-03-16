"""
V01 Sequence 2 — PREMIER LANCEMENT + AUTO-DETECTION CHAMP D'AFFICHAGE
======================================================================
Cliquer sur l'icone FilterMate, le dock widget s'ouvre.
Selectionner la couche departements, configurer le champ d'affichage NOM_DEPT.
Montrer la detection automatique du champ d'affichage (6 niveaux de priorite).

Uses TimelineSequence for narration-synchronized execution.
"""
from __future__ import annotations

import pyautogui

from core.timeline import NarrationCue
from sequences.base import TimelineSequence


class V01S02FirstLaunch(TimelineSequence):
    name = "V01 — Premier lancement + Auto-détection affichage"
    sequence_id = "v01_s02"
    duration_estimate = 45.0
    obs_scene = "QGIS + FilterMate"
    diagram_ids = ["v01_display_field_detection"]
    narration_text = ""  # Narration is now in the cues

    def build_timeline(self, obs, qgis, config):
        regions = config["qgis"]["regions"]
        move_dur = config["timing"].get("mouse_move_duration", 0.5)

        def open_feature_selector_and_scroll():
            """Open feature selector to show readable names, scroll to demo."""
            selector = regions.get("exploring_feature_selector")
            if selector:
                qgis.hover_region("exploring_feature_selector", duration=1.0)
                pyautogui.click(selector["x"], selector["y"], duration=move_dur)
            qgis.wait(1.0)
            qgis.scroll_down(3)
            qgis.wait(0.8)
            qgis.scroll_up(3)
            qgis.wait(0.5)
            pyautogui.press("escape")

        return [
            # Cue 0: Open FilterMate
            NarrationCue(
                label="Lancement FilterMate",
                text=(
                    "Pour lancer FilterMate, cliquez sur son icône "
                    "dans la barre d'outils, "
                    "ou allez dans le menu Extensions puis FilterMate."
                ),
                sync="during",
                actions=lambda: (
                    qgis.focus_qgis(),
                    qgis.open_filtermate_toolbar(),
                ),
                post_delay=0.5,
            ),
            # Cue 1: Switch to FILTERING tab
            NarrationCue(
                label="Onglet FILTERING",
                text="Sélectionnons la couche départements comme source,",
                sync="during",
                actions=lambda: (
                    self._log.info("Switching to FILTERING tab"),
                    qgis.select_tab("FILTERING"),
                ),
                post_delay=0.5,
            ),
            # Cue 2: Layers already loaded
            NarrationCue(
                label="Couches détectées",
                text=(
                    "Nos couches de démonstration sont déjà chargées dans le projet : "
                    "un Shapefile des départements de France et un Shapefile des communes. "
                    "FilterMate les détecte automatiquement."
                ),
                sync="during",
                actions=lambda: qgis.wait(1.0),
                post_delay=0.5,
            ),
            # Cue 3: Select source layer
            NarrationCue(
                label="Sélection couche départements",
                text="",
                actions=lambda: (
                    self._log.info("Selecting source layer 'departements'"),
                    qgis.select_combobox_by_arrow("source_layer_combo", 2),
                ),
                post_delay=0.3,
            ),
            # Cue 4: Configure display field
            NarrationCue(
                label="Champ affichage NOM_DEPT",
                text=(
                    "puis configurons le champ d'affichage sur NOM_DEPT "
                    "pour voir les noms des départements dans le sélecteur."
                ),
                sync="during",
                actions=lambda: (
                    self._log.info("Setting display field to 'NOM_DEPT'"),
                    qgis.select_combobox_item("exploring_display_field_combo", "NOM_DEPT"),
                ),
                post_delay=0.8,
            ),
            # Cue 5: Show auto-detection — scroll through readable names
            NarrationCue(
                label="Auto-détection champ d'affichage",
                text=(
                    "Le sélecteur affiche directement le nom des départements, "
                    "pas un identifiant cryptique. "
                    "C'est grâce à la détection automatique du champ d'affichage. "
                    "FilterMate analyse votre couche et choisit intelligemment "
                    "le meilleur champ selon 6 niveaux de priorité."
                ),
                sync="during",
                actions=lambda: open_feature_selector_and_scroll(),
                post_delay=0.5,
            ),
            # Cue 6: Diagram
            NarrationCue(
                label="Diagramme auto-détection",
                text="C'est automatique.",
                sync="during",
                actions=lambda: self.show_diagram(
                    obs, "v01_display_field_detection", duration=5.0
                ),
                post_delay=0.5,
            ),
        ]
