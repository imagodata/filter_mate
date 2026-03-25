"""
V01 Sequence 1 — ACTIVATION COUCHES + INSTALLATION (0:15 - 0:45)
=================================================================
1. Activer les couches departements et communes dans le panneau Layers.
2. Ouvrir le gestionnaire d'extensions, rechercher FilterMate, montrer le bouton Installer.

Uses TimelineSequence for narration-synchronized execution.
"""
from __future__ import annotations

import pyautogui

from core.timeline import NarrationCue
from sequences.base import TimelineSequence


class V01S01Install(TimelineSequence):
    name = "V01 — Activation couches + Installation"
    sequence_id = "v01_s01"
    duration_estimate = 30.0
    obs_scene = "QGIS Fullscreen"
    diagram_ids = ["v01_install_flow"]
    narration_text = ""  # Narration is now in the cues

    def build_timeline(self, obs, qgis, config):
        regions = config["qgis"]["regions"]

        def toggle_layer_departements():
            self._log.info("Toggling visibility for 'departements'")
            pyautogui.click(
                regions["layer_panel_visibility_departements"]["x"],
                regions["layer_panel_visibility_departements"]["y"],
            )

        def toggle_layer_communes():
            self._log.info("Toggling visibility for 'communes'")
            pyautogui.click(
                regions["layer_panel_visibility_communes"]["x"],
                regions["layer_panel_visibility_communes"]["y"],
            )

        def open_plugin_manager():
            self._log.info("Opening Plugin Manager")
            qgis.open_plugin_manager()

        def click_all_tab():
            self._log.info("Clicking 'All' tab")
            all_tab = regions.get("plugin_manager_all_tab")
            if all_tab:
                pyautogui.click(all_tab["x"], all_tab["y"])
                qgis.wait(0.5)

        def search_filtermate():
            self._log.info("Searching 'FilterMate'")
            search_bar = regions.get("plugin_manager_search")
            if search_bar:
                pyautogui.click(search_bar["x"], search_bar["y"])
                qgis.wait(0.3)
            pyautogui.hotkey("ctrl", "a")
            pyautogui.typewrite("FilterMate", interval=0.08)

        def select_and_hover_install():
            self._log.info("Selecting plugin entry")
            plugin_entry = regions.get("plugin_manager_entry")
            if plugin_entry:
                pyautogui.click(plugin_entry["x"], plugin_entry["y"])
            qgis.wait(1.0)
            self._log.info("Hovering Install button")
            qgis.hover_region("plugin_manager_install_btn", duration=1.5)

        def show_diagram_and_close():
            self.show_diagram(obs, "v01_install_flow", duration=5.0)
            qgis.close_dialog()

        return [
            # Cue 0: Introduce the project layers
            NarrationCue(
                label="Presentation couches",
                text=(
                    "Notre projet QGIS contient déjà deux couches : "
                    "les départements de France et les communes."
                ),
                sync="during",
                actions=lambda: qgis.focus_qgis(),
                post_delay=0.5,
            ),
            # Cue 1: Activate layers
            NarrationCue(
                label="Activation couches",
                text=(
                    "Activons-les dans le panneau de couches "
                    "pour les rendre visibles sur la carte."
                ),
                sync="during",
                actions=lambda: (
                    toggle_layer_departements(),
                    qgis.wait(1.0),
                    toggle_layer_communes(),
                ),
                post_delay=0.5,
            ),
            # Cue 2: Open plugin manager
            NarrationCue(
                label="Ouverture gestionnaire extensions",
                text=(
                    "L'installation se fait en 3 clics depuis QGIS. "
                    "Allez dans le menu Extensions, puis Gérer les extensions."
                ),
                sync="during",
                actions=lambda: open_plugin_manager(),
                post_delay=0.5,
            ),
            # Cue 3: Search for FilterMate
            NarrationCue(
                label="Recherche FilterMate",
                text=(
                    "Dans l'onglet Toutes, tapez FilterMate dans la barre de recherche."
                ),
                sync="during",
                actions=lambda: (
                    click_all_tab(),
                    search_filtermate(),
                ),
                post_delay=0.5,
            ),
            # Cue 4: Show plugin and Install button
            NarrationCue(
                label="Plugin trouve + Install",
                text=(
                    "Le plugin apparaît. Cliquez sur Installer. C'est tout."
                ),
                sync="during",
                actions=lambda: select_and_hover_install(),
                post_delay=0.3,
            ),
            # Cue 5: Closing statement + diagram
            NarrationCue(
                label="Conclusion installation",
                text=(
                    "FilterMate est gratuit, open source, et disponible "
                    "sur le dépôt officiel QGIS."
                ),
                sync="during",
                actions=lambda: show_diagram_and_close(),
                post_delay=0.5,
            ),
        ]
