# -*- coding: utf-8 -*-
"""Selection modes of the EXPLORING panel: the groups of each layer kind and the rail tools tied to them.

One table for the three kinds (2026-10-18), read by the vector dock (the Link button), the raster
and point cloud rails and the tests, so the same rules hold everywhere:

- R1: a tool tied to a group is available only while that group is active.
- R2: a tool put on makes its group the active one.
- R3: the active group and the tool on the map come back with the layer.
- R4: the rail and the group show one sub-mode (the pipette targets, the class / value pipette, the
  targets of the point cloud detector); a target chosen on the rail (a button, a menu) puts its tool on.
- R5: a tool QGIS drops releases its button; the group stays.

The vector groups are also chosen by the number of features (:func:`group_for_count`): the rule
is the same from the widgets and from the map.
"""
from typing import Dict, Optional, Tuple

VECTOR_GROUPS = ('single_selection', 'multiple_selection', 'custom_selection')

# kind -> group -> the rail buttons that belong to it. A button absent from a kind is shared (zoom,
# the preview, reset, the "Select" mode of a vector layer, which works in the three groups).
GROUP_TOOLS: Dict[str, Dict[str, Tuple[str, ...]]] = {
    'vector': {
        'single_selection': ('pushButton_checkable_exploring_linking_widgets',
                             'pushButton_checkable_exploring_vector_similar'),
        'multiple_selection': ('pushButton_checkable_exploring_linking_widgets',
                               'pushButton_checkable_exploring_vector_similar'),
        'custom_selection': (),
    },
    'raster': {
        'pipette': ('pushButton_checkable_exploring_raster_pipette', 'pushButton_checkable_exploring_raster_detector',
                    'pushButton_checkable_exploring_raster_similar'),
        'range': ('pushButton_checkable_exploring_raster_link',),
        'expression': (),
    },
    'point_cloud': {
        # The Identify button is the class pipette, put on when CLASSES is chosen; the object detector is the
        # other tool of the group (it makes CLASSES active, choosing CLASSES does not put it on).
        'classes': ('pushButton_exploring_identify', 'pushButton_checkable_exploring_point_cloud_object'),
        'ranges': ('pushButton_checkable_exploring_point_cloud_value_pipette',
                   'pushButton_checkable_exploring_point_cloud_zone'),
        'expression': (),
    },
}


def groups_of(kind: str, tool: str) -> Tuple[str, ...]:
    """The groups ``tool`` belongs to for a layer kind; empty for a shared button."""
    return tuple(group for group, tools in GROUP_TOOLS.get(kind, {}).items() if tool in tools)


def tool_available(kind: str, group: Optional[str], tool: str) -> bool:
    """R1: a tool tied to groups is available only while one of them is active; a shared one always is."""
    groups = groups_of(kind, tool)
    return not groups or group in groups


def group_for_tool(kind: str, tool: str) -> Optional[str]:
    """R2: the group a tool put on makes active (the first of its groups), None for a shared button."""
    groups = groups_of(kind, tool)
    return groups[0] if groups else None


def group_for_count(current: Optional[str], count: int, from_map: bool) -> Optional[str]:
    """The vector group the number of selected features asks for.

    Args:
        current: The active group.
        count: Features selected (from the widgets or from the map).
        from_map: The selection was made on the map.

    Returns:
        The group to make active: several features move the single selection to the multiple
        one; one feature selected on the map moves the multiple selection back to the single
        one. From the widgets the multiple list is never left (checking its first item must not
        change the group), and the custom selection is never left by a count.
    """
    if current == 'single_selection' and count > 1:
        return 'multiple_selection'
    if current == 'multiple_selection' and count == 1 and from_map:
        return 'single_selection'
    return current
