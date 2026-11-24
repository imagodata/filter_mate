# -*- coding: utf-8 -*-
"""The text of a layer in the lists of the panel (2026-11-24)."""


def layer_label(name: str, authid: str) -> str:
    """Its name and its CRS, ``communes [EPSG:2154]``.

    A CRS without an authority id (a compound CRS, a custom one) gives no ``[]`` after the name: a survey in
    NZGD2000 + NZVD2016 was listed "lhd_vegetation []".
    """
    authid = str(authid or "").strip()
    return f"{name} [{authid}]" if authid else str(name)
