"""
V01 Sequence 3 — ARCHITECTURE DE L'INTERFACE (raccourci ~45s)
==============================================================
3 zones annotées : Exploring Zone, Toolbox, Action Bar.
Header bar avec pastilles Favoris + Backend.

Migrated to TimelineSequence for narration-synchronized execution.
"""
from __future__ import annotations

from core.timeline import NarrationCue
from sequences.base import TimelineSequence


class V01S03Interface(TimelineSequence):
    name = "V01 — Architecture interface (3 zones)"
    sequence_id = "v01_s03"
    duration_estimate = 45.0
    obs_scene = "QGIS + FilterMate"
    diagram_ids = ["v01_interface_zones"]
    narration_text = ""  # Narration is now in the cues

    def build_timeline(self, obs, qgis, config):
        return [
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
            # Cue 3: Zone C — Action Bar + Header
            NarrationCue(
                label="Action Bar + Header",
                text=(
                    "Et enfin, l'Action Bar. Ce sont les 6 boutons d'action. "
                    "Remarquez aussi le header : la pastille orange indique vos favoris, "
                    "et la pastille bleue affiche le backend actif."
                ),
                sync="during",
                actions=lambda: (
                    qgis.highlight_area("action_bar_zone", duration=2.5),
                    qgis.hover_region("badge_favorites", duration=1.2),
                    qgis.hover_region("badge_backend", duration=1.2),
                ),
                post_delay=0.3,
            ),
            # Cue 4: Diagram recap
            NarrationCue(
                label="Diagramme zones",
                text="",
                actions=lambda: self.show_diagram_and_return(
                    obs, qgis, "v01_interface_zones", duration=5.0
                ),
                post_delay=0.5,
            ),
        ]
