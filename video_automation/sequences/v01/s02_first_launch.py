"""
V01 Sequence 2 — PREMIER LANCEMENT + DÉCOUVERTE INTERFACE + ACTION BAR
========================================================================
Ouvrir FilterMate (dock vide), charger les données de démo,
découvrir les 3 zones de l'interface (Exploring, Toolbox, Header),
présenter l'Action Bar (6 boutons + activation contextuelle),
puis sélectionner la couche source, changer le champ d'affichage,
naviguer avec next/prev et montrer la détection automatique (diagramme).

Uses TimelineSequence for narration-synchronized execution.
"""
from __future__ import annotations

import pyautogui

from core.timeline import NarrationCue
from sequences.base import TimelineSequence


class V01S02FirstLaunch(TimelineSequence):
    name = "V01 — Premier lancement"
    sequence_id = "v01_s02"
    duration_estimate = 140.0
    obs_scene = "QGIS + FilterMate"
    diagram_ids = ["v01_interface_zones", "v01_action_bar_context", "v01_display_field_detection"]
    narration_text = ""  # Narration is now in the cues

    def build_timeline(self, obs, qgis, config):
        regions = config["qgis"]["regions"]
        move_dur = config["timing"].get("mouse_move_duration", 0.5)

        def show_tab_context_switch():
            """Demonstrate button activation/deactivation when switching tabs."""
            qgis.select_tab("EXPORTING")
            qgis.wait(1.0)
            qgis.highlight_area("action_bar_zone", duration=2.0)
            qgis.select_tab("FILTERING")
            qgis.wait(0.5)
            qgis.highlight_area("action_bar_zone", duration=1.5)

        def click_prev_then_next():
            """Click prev to go to previous department, then next to return."""
            btn_prev = regions.get("exploring_feature_prev_btn")
            btn_next = regions.get("exploring_feature_next_btn")
            if btn_prev:
                pyautogui.click(btn_prev["x"], btn_prev["y"], duration=move_dur)
            qgis.wait(1.5)
            if btn_next:
                pyautogui.click(btn_next["x"], btn_next["y"], duration=move_dur)
            qgis.wait(1.0)

        def activate_auto_current_layer():
            """Enable auto-sync between layer tree and source layer combo."""
            self._log.info("Activating auto current layer sync")
            qgis.click_at("btn_auto_current_layer")
            qgis.wait(0.5)

        def click_layer_communes():
            """Click communes in QGIS layer panel to switch source layer."""
            self._log.info("Clicking communes in layer panel")
            qgis.click_at("layer_panel_name_communes")
            qgis.wait(1.0)

        def click_layer_departements():
            """Click departements in QGIS layer panel to switch back."""
            self._log.info("Clicking departements in layer panel")
            qgis.click_at("layer_panel_name_departements")
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
            # ── DÉCOUVERTE INTERFACE : LES 3 ZONES ─────────────

            # Cue 2: Introduction interface
            NarrationCue(
                label="Introduction interface",
                text=(
                    "Prenons un moment pour comprendre l'interface. "
                    "Elle est divisée en 3 zones principales, "
                    "séparées par un splitter vertical."
                ),
                sync="during",
                actions=lambda: qgis.focus_filtermate(),
                post_delay=0.5,
            ),
            # Cue 3: Zone A — Exploring Zone
            NarrationCue(
                label="Zone d'Exploration",
                text=(
                    "En haut, la Zone d'Exploration. "
                    "C'est ici que vous parcourez et sélectionnez "
                    "les entités de vos couches."
                ),
                sync="during",
                actions=lambda: (
                    qgis.highlight_area("exploring_zone", duration=3.0),
                    qgis.hover_region("exploring_layer_combo", duration=1.0),
                    qgis.hover_region("exploring_feature_selector", duration=1.0),
                ),
                post_delay=0.3,
            ),
            # Cue 4: Zone B — Toolbox
            NarrationCue(
                label="Toolbox",
                text=(
                    "En bas, la Toolbox. "
                    "Elle contient deux onglets : FILTERING et EXPORTING."
                ),
                sync="during",
                actions=lambda: (
                    qgis.highlight_area("toolbox_zone", duration=2.5),
                    qgis.select_tab("FILTERING"),
                    qgis.wait(1.0),
                    qgis.select_tab("EXPORTING"),
                    qgis.wait(1.0),
                    qgis.select_tab("FILTERING"),
                ),
                post_delay=0.3,
            ),
            # Cue 5: Header — badges
            NarrationCue(
                label="Header badges",
                text=(
                    "Remarquez aussi le header : "
                    "la pastille orange indique vos favoris, "
                    "et la pastille bleue affiche le backend actif."
                ),
                sync="during",
                actions=lambda: (
                    qgis.hover_region("badge_favorites", duration=1.5),
                    qgis.hover_region("badge_backend", duration=1.5),
                ),
                post_delay=0.3,
            ),
            # Cue 6: Diagram — 3 zones
            NarrationCue(
                label="Diagramme zones",
                text="",
                actions=lambda: self.show_diagram_and_return(
                    obs, qgis, "v01_interface_zones", duration=5.0
                ),
                post_delay=0.5,
            ),

            # ── L'ACTION BAR ──────────────────────────────────

            # Cue 7: Intro Action Bar
            NarrationCue(
                label="Intro Action Bar",
                text=(
                    "Et enfin, l'Action Bar. "
                    "C'est le cœur de l'interaction : "
                    "tout le reste de l'interface sert à configurer "
                    "ce que ces 6 boutons vont exécuter."
                ),
                sync="during",
                actions=lambda: (
                    qgis.focus_filtermate(),
                    qgis.highlight_area("action_bar_zone", duration=2.5),
                ),
                post_delay=0.3,
            ),
            # Cue 8: Filter
            NarrationCue(
                label="Bouton Filter",
                text=(
                    "Filter applique le filtre que vous avez configuré. "
                    "C'est le bouton principal."
                ),
                sync="during",
                actions=lambda: qgis.hover_region("filter_button", duration=2.0),
                post_delay=0.2,
            ),
            # Cue 9: Undo + Redo
            NarrationCue(
                label="Boutons Undo / Redo",
                text=(
                    "Undo annule le dernier filtre, Redo le rétablit. "
                    "FilterMate conserve jusqu'à 100 états d'historique."
                ),
                sync="during",
                actions=lambda: (
                    qgis.hover_region("undo_button", duration=1.5),
                    qgis.hover_region("redo_button", duration=1.5),
                ),
                post_delay=0.2,
            ),
            # Cue 10: Unfilter
            NarrationCue(
                label="Bouton Unfilter",
                text="Unfilter retire tous les filtres actifs de toutes les couches.",
                sync="during",
                actions=lambda: qgis.hover_region("unfilter_button", duration=2.0),
                post_delay=0.2,
            ),
            # Cue 11: Export
            NarrationCue(
                label="Bouton Export",
                text=(
                    "Export exporte vos données filtrées en GeoPackage, "
                    "avec le projet QGIS embarqué."
                ),
                sync="during",
                actions=lambda: qgis.hover_region("export_button", duration=2.0),
                post_delay=0.2,
            ),
            # Cue 12: About
            NarrationCue(
                label="Bouton About",
                text=(
                    "Et About, le seul bouton toujours actif, "
                    "quel que soit l'état du plugin."
                ),
                sync="during",
                actions=lambda: qgis.hover_region("about_button", duration=1.5),
                post_delay=0.2,
            ),
            # Cue 13: Contextual activation demo
            NarrationCue(
                label="Activation contextuelle",
                text=(
                    "Les boutons s'adaptent à l'onglet actif. "
                    "En EXPORTING, Filter, Undo, Redo et Unfilter se désactivent. "
                    "En FILTERING, c'est Export qui se grise."
                ),
                sync="during",
                actions=lambda: show_tab_context_switch(),
                post_delay=0.3,
            ),
            # Cue 14: Diagram — Action Bar
            NarrationCue(
                label="Diagramme Action Bar",
                text="",
                actions=lambda: self.show_diagram_and_return(
                    obs, qgis, "v01_action_bar_context", duration=5.0
                ),
                post_delay=0.5,
            ),

            # ── SÉLECTION COUCHE SOURCE ────────────────────────

            # Cue 15: Select source layer in FILTERING tab
            NarrationCue(
                label="Sélection couche source",
                text=(
                    "Maintenant, configurons la couche source. "
                    "Je sélectionne la couche départements "
                    "dans l'onglet Filtering."
                ),
                sync="during",
                actions=lambda: (
                    self._log.info("Switching to FILTERING tab"),
                    qgis.select_tab("FILTERING"),
                    qgis.wait(0.5),
                    self._log.info("Selecting source layer 'departements'"),
                    pyautogui.click(
                        regions["source_layer_combo"]["x"],
                        regions["source_layer_combo"]["y"],
                        duration=move_dur,
                    ),
                    qgis.wait(0.3),
                    pyautogui.press("enter"),
                    qgis.wait(0.3),
                    pyautogui.press("down"),
                    qgis.wait(0.3),
                    pyautogui.press("down"),
                    qgis.wait(0.3),
                    pyautogui.press("enter"),
                    qgis.wait(0.5),
                    self._log.info("Switching back to EXPLORING tab"),
                    qgis.select_tab("EXPLORING"),
                    qgis.wait(0.5),
                ),
                post_delay=0.5,
            ),
            # Cue 16: Activate auto current layer sync
            NarrationCue(
                label="Activation synchro couche source",
                text=(
                    "J'active la synchronisation avec le panneau de couches QGIS. "
                    "Ce bouton lie la couche source à la sélection dans l'arbre des couches."
                ),
                sync="during",
                actions=lambda: activate_auto_current_layer(),
                post_delay=0.5,
            ),
            # Cue 17: Click communes in layer panel
            NarrationCue(
                label="Clic couche communes",
                text=(
                    "Je clique sur communes dans le panneau des couches. "
                    "La couche source se met à jour automatiquement."
                ),
                sync="during",
                actions=lambda: click_layer_communes(),
                post_delay=0.5,
            ),
            # Cue 18: Click back on departements
            NarrationCue(
                label="Retour couche départements",
                text=(
                    "Je reviens sur départements. "
                    "La synchronisation est immédiate."
                ),
                sync="during",
                actions=lambda: click_layer_departements(),
                post_delay=0.5,
            ),
            # Cue 19: Change display field via mouse
            NarrationCue(
                label="Changement champ d'affichage",
                text=(
                    "De retour dans l'onglet Exploration, "
                    "je change le champ d'affichage."
                ),
                sync="during",
                actions=lambda: (
                    self._log.info("Setting display field to 'NOM_DEPT'"),
                    pyautogui.click(
                        regions["exploring_display_field_combo"]["x"],
                        regions["exploring_display_field_combo"]["y"],
                        duration=move_dur,
                    ),
                    qgis.wait(0.3),
                    pyautogui.hotkey("ctrl", "a"),
                    qgis.wait(0.1),
                    qgis.type_text_unicode("NOM_DEPT"),
                    qgis.wait(0.5),
                    pyautogui.press("enter"),
                    qgis.wait(0.5),
                ),
                post_delay=0.5,
            ),
            # Cue 20: Browse feature picker with keyboard
            NarrationCue(
                label="Parcours feature picker clavier",
                text=(
                    "Je clique dans le sélecteur d'entités "
                    "et je navigue avec les flèches du clavier."
                ),
                sync="during",
                actions=lambda: (
                    self._log.info("Clicking into feature picker combo"),
                    pyautogui.click(
                        regions["exploring_feature_selector"]["x"],
                        regions["exploring_feature_selector"]["y"],
                        duration=move_dur,
                    ),
                    qgis.wait(0.5),
                    pyautogui.press("down"),
                    qgis.wait(0.8),
                    pyautogui.press("down"),
                    qgis.wait(0.8),
                ),
                post_delay=0.5,
            ),
            # Cue 21: Navigate with next/prev buttons
            NarrationCue(
                label="Navigation next/prev",
                text=(
                    "Avec le bouton précédent, je passe au département d'avant, "
                    "puis suivant pour revenir. "
                    "La navigation est immédiate."
                ),
                sync="during",
                actions=lambda: click_prev_then_next(),
                post_delay=0.5,
            ),
            # Cue 22: Auto-detection intro
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
            # Cue 23: Diagram
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
