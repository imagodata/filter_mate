# -*- coding: utf-8 -*-
"""QGIS names that changed between 3.22 and 4.x, resolved once."""

from qgis.core import Qgis, QgsVectorLayer


def enum_member(owner, enum_name: str, member: str):
    """``owner.enum_name.member`` where enums are scoped, ``owner.member`` where they are flat."""
    scope = getattr(owner, enum_name, None)
    if scope is not None and hasattr(scope, member):
        return getattr(scope, member)
    return getattr(owner, member)


def select_behavior(name: str):
    """``Qgis.SelectBehavior.<name>`` (3.30 and later), ``QgsVectorLayer.<name>`` before."""
    scope = getattr(Qgis, "SelectBehavior", None)
    if scope is not None and hasattr(scope, name):
        return getattr(scope, name)
    return enum_member(QgsVectorLayer, "SelectBehavior", name)


def layer_type(name: str):
    """``Qgis.LayerType.<name>`` (3.30 and later), ``QgsMapLayerType.<name>Layer`` before."""
    scope = getattr(Qgis, "LayerType", None)
    if scope is not None and hasattr(scope, name):
        return getattr(scope, name)
    from qgis.core import QgsMapLayerType
    return getattr(QgsMapLayerType, name + "Layer", None)


def message_level(name: str):
    scope = getattr(Qgis, "MessageLevel", None)
    if scope is not None and hasattr(scope, name):
        return getattr(scope, name)
    return getattr(Qgis, name)
