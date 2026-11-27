"""A user can review a source proposal without it being tested, added or enabled automatically."""
from unittest.mock import MagicMock

import pytest

from .test_agent_provider_tab import _APP, _dialog

pytestmark = pytest.mark.unit


def test_pasted_capabilities_url_detects_kind_and_normalizes_only_when_the_user_adds():
    dialog = _dialog()
    tester = dialog._tester = MagicMock(return_value='It answers.')
    dialog.new_address.setText('https://geo.example.org/ows?SERVICE=WFS&REQUEST=GetCapabilities')
    dialog.new_name.setText('Water data')
    assert dialog.new_kind.currentData() == 'wfs' and not dialog._custom
    dialog.add_button.click()
    source = dialog._custom[0]
    assert source.address == 'https://geo.example.org/ows' and source.title == 'Water data'
    assert source.id in dialog.chosen_sources() and dialog._selected_source() == source
    tester.assert_not_called()
    dialog.test_button.click()
    tester.assert_called_once_with(source)
    dialog.close()


def test_an_agent_draft_is_reviewable_without_adding_or_enabling_anything():
    dialog = _dialog()
    before = dialog.chosen_custom_sources(), dialog.chosen_sources()
    dialog.prefill_source({'address': 'https://geo.example.org/wfs', 'kind': 'wfs', 'title': 'Hydrology'})
    assert (dialog.chosen_custom_sources(), dialog.chosen_sources()) == before
    assert dialog.new_name.text() == 'Hydrology' and not dialog.new_enabled.isChecked()
    assert 'Unverified' in dialog.source_result.text()
    dialog.add_button.click()
    assert len(dialog._custom) == 1 and dialog._custom[0].id not in dialog.chosen_sources()
    dialog.close()


def test_unknown_site_requires_a_service_type_and_duplicate_add_does_not_duplicate_sources():
    dialog = _dialog()
    dialog.new_address.setText('https://example.org/catalogue')
    assert not dialog.new_kind.currentData()
    dialog.add_button.click()
    assert not dialog._custom and 'Choose the service type' in dialog.source_result.text()
    for _ in range(2):
        dialog.new_address.setText('https://example.org/wfs')
        dialog.add_button.click()
    assert len(dialog._custom) == 1
    dialog.close()


def test_manual_kind_choice_is_not_replaced_while_editing_the_address():
    dialog = _dialog()
    dialog.new_kind.setCurrentIndex(dialog.new_kind.findData('wms'))
    dialog.new_kind.activated.emit(dialog.new_kind.currentIndex())
    dialog.new_address.setText('https://example.org/wfs')
    assert dialog.new_kind.currentData() == 'wms'
    dialog.close()
