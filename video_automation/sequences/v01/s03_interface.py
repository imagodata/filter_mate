"""
V01 Sequence 3 — DÉCOUVERTE DE L'INTERFACE : 3 ZONES + ACTION BAR
===================================================================
Présentation des 3 zones (Exploring, Toolbox, Action Bar) avec
highlight progressif, puis détail des 6 boutons de l'Action Bar
avec survol et démonstration du switch FILTERING/EXPORTING.

Merge de l'ancienne séquence « Architecture interface » et
de l'ancienne séquence « Action Bar ».

Uses TimelineSequence for narration-synchronized execution.
"""
from __future__ import annotations

from core.timeline import NarrationCue
from sequences.base import TimelineSequence


class V01S03Interface(TimelineSequence):
    name = "V01 — Découverte interface (3 zones + Action Bar)"
    sequence_id = "v01_s03"
    duration_estimate = 90.0
    obs_scene = "QGIS + FilterMate"
    diagram_ids = ["v01_interface_zones", "v01_action_bar_context"]
    narration_text = ""  # Narration is now in the cues

    def build_timeline(self, obs, qgis, config):
        def show_tab_context_switch():
            """Demonstrate button activation/deactivation when switching tabs."""
            qgis.select_tab("EXPORTING")
            qgis.wait(1.0)
            qgis.highlight_area("action_bar_zone", duration=2.0)
            qgis.select_tab("FILTERING")
            qgis.wait(0.5)
            qgis.highlight_area("action_bar_zone", duration=1.5)

        return [
            # ── PARTIE 1 : LES 3 ZONES ──────────────────────────

            # Cue 0: Introduction
            NarrationCue(
                label="Introduction interface",
                text=(
                    "Prenons un moment pour comprendre l'interface. "
                    "Elle est divisée en 3 zones principales, "
                    "séparées par un splitter vertical."
                ),
                sync="during",
                actions=lambda: (
                    qgis.focus_qgis(),
                    qgis.focus_filtermate(),
                ),
                post_delay=0.5,
            ),
            # Cue 1: Zone A — Exploring Zone
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
            # Cue 2: Zone B — Toolbox
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
            # Cue 3: Header — badges
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
            # Cue 4: Diagram — 3 zones
            NarrationCue(
                label="Diagramme zones",
                text="",
                actions=lambda: self.show_diagram_and_return(
                    obs, qgis, "v01_interface_zones", duration=5.0
                ),
                post_delay=0.5,
            ),

            # ── PARTIE 2 : L'ACTION BAR ─────────────────────────

            # Cue 5: Intro Action Bar
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
            # Cue 6: Filter
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
            # Cue 7: Undo + Redo
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
            # Cue 8: Unfilter
            NarrationCue(
                label="Bouton Unfilter",
                text="Unfilter retire tous les filtres actifs de toutes les couches.",
                sync="during",
                actions=lambda: qgis.hover_region("unfilter_button", duration=2.0),
                post_delay=0.2,
            ),
            # Cue 9: Export
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
            # Cue 10: About
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
            # Cue 11: Contextual activation demo
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
            # Cue 12: Diagram — Action Bar
            NarrationCue(
                label="Diagramme Action Bar",
                text="",
                actions=lambda: self.show_diagram_and_return(
                    obs, qgis, "v01_action_bar_context", duration=5.0
                ),
                post_delay=0.5,
            ),
        ]
