"""
V01 Sequence 5 — L'ACTION BAR : 6 BOUTONS CONTEXTUELS
=======================================================
Présentation de l'Action Bar avec démonstration contextuelle :
- Survol de chaque bouton avec description corrigée
- Démonstration live du switch FILTERING/EXPORTING (activation/désactivation)
- Explication du système d'historique (Undo/Redo : 100 états)

Uses TimelineSequence for narration-synchronized execution.
"""
from __future__ import annotations

from core.timeline import NarrationCue
from sequences.base import TimelineSequence


class V01S05ActionBar(TimelineSequence):
    name = "V01 — Action Bar (6 boutons)"
    sequence_id = "v01_s05"
    duration_estimate = 40.0
    obs_scene = "QGIS + FilterMate"
    diagram_ids = ["v01_action_bar_context"]
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
            # Cue 0: Introduction
            NarrationCue(
                label="Intro Action Bar",
                text=(
                    "L'Action Bar est le centre de commande de FilterMate. "
                    "Six boutons, toujours accessibles."
                ),
                sync="during",
                actions=lambda: (
                    qgis.focus_filtermate(),
                    qgis.highlight_area("action_bar_zone", duration=2.0),
                ),
                post_delay=0.3,
            ),
            # Cue 1: Filter
            NarrationCue(
                label="Bouton Filter",
                text="Filter lance le filtrage spatial avec votre configuration actuelle.",
                sync="during",
                actions=lambda: qgis.hover_region("filter_button", duration=2.0),
                post_delay=0.2,
            ),
            # Cue 2: Undo + Redo together (tell the history story)
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
            # Cue 3: Unfilter
            NarrationCue(
                label="Bouton Unfilter",
                text="Unfilter retire tous les filtres actifs de toutes les couches.",
                sync="during",
                actions=lambda: qgis.hover_region("unfilter_button", duration=2.0),
                post_delay=0.2,
            ),
            # Cue 4: Export
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
            # Cue 5: About
            NarrationCue(
                label="Bouton About",
                text="About est le seul bouton toujours actif, quel que soit l'onglet.",
                sync="during",
                actions=lambda: qgis.hover_region("about_button", duration=1.5),
                post_delay=0.2,
            ),
            # Cue 6: Contextual activation demo
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
            # Cue 7: Diagram
            NarrationCue(
                label="Diagramme action bar",
                text="",
                actions=lambda: self.show_diagram_and_return(
                    obs, qgis, "v01_action_bar_context", duration=5.0
                ),
                post_delay=0.5,
            ),
        ]
