"""
V01 Sequence 2 — PREMIER LANCEMENT
====================================
Ouvrir FilterMate (dock vide), charger les données de démo,
changer le champ d'affichage, taper « Paris » dans le sélecteur,
cliquer suivant puis précédent pour revenir sur Paris.
Puis montrer la détection automatique du champ d'affichage (diagramme).

Uses TimelineSequence for narration-synchronized execution.
"""
from __future__ import annotations

import pyautogui

from core.timeline import NarrationCue
from sequences.base import TimelineSequence


class V01S02FirstLaunch(TimelineSequence):
    name = "V01 — Premier lancement"
    sequence_id = "v01_s02"
    duration_estimate = 45.0
    obs_scene = "QGIS + FilterMate"
    diagram_ids = ["v01_display_field_detection"]
    narration_text = ""  # Narration is now in the cues

    def build_timeline(self, obs, qgis, config):
        regions = config["qgis"]["regions"]
        move_dur = config["timing"].get("mouse_move_duration", 0.5)

        def type_paris_in_selector():
            """Click the feature selector and type 'Paris'."""
            selector = regions.get("exploring_feature_selector")
            if selector:
                pyautogui.click(selector["x"], selector["y"], duration=move_dur)
                qgis.wait(0.3)
                pyautogui.hotkey("ctrl", "a")
                qgis.wait(0.1)
                pyautogui.typewrite("Paris", interval=0.08)
                qgis.wait(0.5)
                pyautogui.press("enter")
            qgis.wait(1.0)

        def click_next_then_prev():
            """Click next to go to next department, then prev to return to Paris."""
            btn_next = regions.get("exploring_feature_next_btn")
            btn_prev = regions.get("exploring_feature_prev_btn")
            if btn_next:
                pyautogui.click(btn_next["x"], btn_next["y"], duration=move_dur)
            qgis.wait(1.5)
            if btn_prev:
                pyautogui.click(btn_prev["x"], btn_prev["y"], duration=move_dur)
            qgis.wait(1.0)

        return [
            # Cue 0: Open FilterMate — dock is empty
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
            # Cue 1: Dock is empty, load demo data
            NarrationCue(
                label="Dock vide + chargement données",
                text=(
                    "Pour l'instant, il est vide. C'est normal. "
                    "FilterMate détecte automatiquement les couches de votre projet. "
                    "Chargeons nos données de démonstration : "
                    "un Shapefile des départements de France, environ 100 entités, "
                    "et un Shapefile des communes, 35 000 entités."
                ),
                sync="during",
                actions=lambda: qgis.wait(3.0),
                post_delay=0.5,
            ),
            # Cue 2: Change display field
            NarrationCue(
                label="Changement champ d'affichage",
                text=(
                    "L'interface se remplit."
                ),
                sync="during",
                actions=lambda: (
                    self._log.info("Setting display field to 'NOM_DEPT'"),
                    qgis.select_combobox_item(
                        "exploring_display_field_combo", "NOM_DEPT"
                    ),
                ),
                post_delay=0.5,
            ),
            # Cue 3: Type Paris + next + prev
            NarrationCue(
                label="Saisie Paris + navigation",
                text=(
                    "Après avoir changé le champ d'affichage, "
                    "je tape Paris dans le sélecteur. "
                    "Le département apparaît. "
                    "Avec le bouton suivant, je passe au département d'après, "
                    "puis précédent pour revenir sur Paris. "
                    "La navigation est immédiate."
                ),
                sync="during",
                actions=lambda: (
                    type_paris_in_selector(),
                    click_next_then_prev(),
                ),
                post_delay=0.5,
            ),
            # Cue 4: Auto-detection intro
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
                actions=lambda: qgis.hover_region(
                    "exploring_feature_selector", duration=2.0
                ),
                post_delay=0.5,
            ),
            # Cue 5: Diagram
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
