# -*- coding: utf-8 -*-
"""
Provider keys are compared case-insensitively (2026-10-17).

QGIS names its web providers ``'WFS'`` and ``'OAPIF'`` (checked in QGIS
3.44: ``QgsVectorLayer(uri, 'x', 'OAPIF').providerType() == 'OAPIF'``);
the lists of FilterMate were written in lower case, so an OGC API Features
layer was never recognized as remote.

Module tested: infrastructure.constants
"""
from infrastructure.constants import PROVIDER_OGR, REMOTE_PROVIDERS, get_provider_name


def test_remote_provider_set_is_lower_case():
    assert all(key == key.lower() for key in REMOTE_PROVIDERS)
    assert {'wfs', 'oapif', 'arcgisfeatureserver'} <= REMOTE_PROVIDERS


def test_get_provider_name_matches_qgis_keys_whatever_their_case():
    assert get_provider_name('OAPIF') == PROVIDER_OGR
    assert get_provider_name('WFS') == PROVIDER_OGR
    assert get_provider_name('postgres') == 'postgresql'
    assert get_provider_name('something_else') == 'something_else'
