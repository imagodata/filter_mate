# -*- coding: utf-8 -*-
"""The buttons of the EXPLORING rail a user may hide, by the short name of the setting.

The names and the rule (which ones can be hidden) are plain Python in ``core/domain/exploring_tools.py``; here is what
each name stands for in the dock (the object name of its Qt button, one table for the three kinds of layer) and the
words that name it, for the right-click menu of the rail and for the cards of the setup.
"""
from __future__ import annotations

from typing import Dict

from qgis.PyQt.QtCore import QCoreApplication

from ...core.domain import exploring_tools as tools

# Shared by the three kinds: the buttons of the dock itself (the others are built by coverage_dock_extras).
ZOOM = 'pushButton_exploring_zoom'
SELECTING = 'pushButton_checkable_exploring_selecting'  # sync (vector), preview (raster, point cloud)
IDENTIFY = 'pushButton_exploring_identify'  # identify (vector), the class pipette (point cloud)
RESET = 'pushButton_exploring_reset_layer_properties'

BUTTONS: Dict[str, Dict[str, str]] = {
    tools.VECTOR: {
        'zoom': ZOOM,
        'sync': SELECTING,
        'identify': IDENTIFY,
        'follow': 'pushButton_checkable_exploring_tracking',
        'zone': 'pushButton_checkable_exploring_vector_zone',
        'link': 'pushButton_checkable_exploring_linking_widgets',
        'more': 'pushButton_exploring_vector_more',
        'reset': RESET,
    },
    tools.RASTER: {
        'zoom': ZOOM,
        'preview': SELECTING,
        'pipette': 'pushButton_checkable_exploring_raster_pipette',
        'detector': 'pushButton_checkable_exploring_raster_detector',
        'similar': 'pushButton_checkable_exploring_raster_similar',
        'link': 'pushButton_checkable_exploring_raster_link',
        'more': 'pushButton_exploring_raster_more',
        'reset': RESET,
    },
    tools.POINT_CLOUD: {
        'zoom': ZOOM,
        'preview': SELECTING,
        'identify': IDENTIFY,
        'object': 'pushButton_checkable_exploring_point_cloud_object',
        'value_pipette': 'pushButton_checkable_exploring_point_cloud_value_pipette',
        'zone': 'pushButton_checkable_exploring_point_cloud_zone',
        'more': 'pushButton_exploring_point_cloud_more',
        'reset': RESET,
    },
}

# The buttons that start a tool on the map: when the button goes, the tool is put down (a tool on the map with no
# button to show it, nor to put it off, would stay on the map unseen). The other toggles (sync, follow, link,
# preview) are modes of the layer: they keep their state while their button is hidden (audit 24/11 #10), and
# nothing turns a tool or a mode on again while its button is hidden.
MAP_TOOLS = frozenset({'identify', 'pipette', 'detector', 'similar', 'object', 'value_pipette', 'zone'})
MODES = frozenset({'sync', 'follow', 'link', 'preview'})


def _tr(text: str) -> str:
    return QCoreApplication.translate("ExploringTools", text)


def labels(kind: str) -> Dict[str, str]:
    """The name of each button of the rail of ``kind`` in words, for a menu and a card (one short line each)."""
    if kind == tools.RASTER:
        return {
            'zoom': _tr("Zoom to the selected pixels"),
            'preview': _tr("Preview: hide the pixels outside the selection"),
            'pipette': _tr("Pipette: select the pixels like the one clicked"),
            'detector': _tr("Object detector"),
            'similar': _tr("Similar objects"),
            'link': _tr("Link the range to the style"),
            'more': _tr("More tools (always shown)"),
            'reset': _tr("Reset the raster selection"),
        }
    if kind == tools.POINT_CLOUD:
        return {
            'zoom': _tr("Zoom to the layer"),
            'preview': _tr("Live preview: show only the points kept"),
            'identify': _tr("Class pipette"),
            'object': _tr("Object detector"),
            'value_pipette': _tr("Value pipette"),
            'zone': _tr("Zone"),
            'more': _tr("More tools (always shown)"),
            'reset': _tr("Reset the point cloud criteria"),
        }
    return {
        'zoom': _tr("Zoom to the selected features"),
        'sync': _tr("Keep the map selection and the widgets in sync"),
        'identify': _tr("Identify the selected features"),
        'follow': _tr("Follow the features on the map"),
        'zone': _tr("Zone"),
        'link': _tr("Link the single and multiple selections"),
        'more': _tr("More tools (always shown)"),
        'reset': _tr("Reset the layer properties"),
    }


def menu_title() -> str:
    return _tr("Tools shown for this type of layer")
