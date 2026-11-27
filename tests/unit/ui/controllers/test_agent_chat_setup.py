# -*- coding: utf-8 -*-
"""The instructions of the chat, built in core (core/agent/chat_setup.py) for the measuring scripts.

Lot 0 of the token diet (2026-11-16) moved them out of the controller without changing a character; lot 1 changed the
text on purpose and took the digests again. Any other change of the text must show here. QGIS stays mocked by the root
conftest.
"""
import hashlib
import importlib
import pathlib
import sys
import types
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

_ROOT = pathlib.Path(__file__).resolve().parents[4]
_PKG = "fm_agent_chat_setup_test"


def _load():
    for name, path in (("", _ROOT), (".ui", _ROOT / "ui"), (".ui.controllers", _ROOT / "ui" / "controllers")):
        package = types.ModuleType(_PKG + name)
        package.__path__ = [str(path)]
        sys.modules[_PKG + name] = package
    stubs = [name for name in ("qgis.PyQt.QtNetwork", "qgis.PyQt.QtXml") if name not in sys.modules]
    sys.modules.update({name: MagicMock() for name in stubs})
    try:  # bound at import; taken out again so that no other test sees them
        return (importlib.import_module(f"{_PKG}.ui.controllers.agent_chat_controller"),
                importlib.import_module(f"{_PKG}.adapters.agent.settings"),
                importlib.import_module(f"{_PKG}.core.agent.sources"))
    finally:
        for name in stubs:
            sys.modules.pop(name, None)


chat_controller, agent_settings, sources = _load()
Controller = chat_controller.AgentChatController

GOLDEN = {  # (length, sha256 of the UTF-8 text); 2026-11-16, lot 1 of the token diet: the instructions without the
    # paragraphs that described a tool one by one (12,076 characters before for the default); then the way of working
    # starts from the state of the project sent, not from list_layers and map_context (review of lot 1); lot 2: the
    # sources not ticked in one paragraph, a shorter way of working. 2026-11-26: Esri and regional basemap IDs, then explicit layer/output hyperlink syntax; condensed for the model designer entry.
    "default": (3989, "f299220a66e2637f989fa50f5e33fd436cc279e388cc01f66e1e79ace4729167"),
    "no_values_local": (4473, "02f4960027d911a9fa9b16ad16cca54195797853094e7e3f2611233e674c5291"),
    # 2026-11-27: the optional web-search source adds its explicit scope; default sources remain unchanged.
    "every_source": (6023, "c02a9c1ba8363e95bc14fb1580314ddb3eeecdb21723414179e98376536454d9"),
}
_EVERY = tuple(source.id for source in sources.BUILT_IN)
CONFIGS = {
    "default": (agent_settings.AgentSettings(preset="anthropic", model="m"), []),
    "no_values_local": (agent_settings.AgentSettings(preset="ollama", model="m", send_values=False,
                                                     local_filtering_only=True), []),
    "every_source": (agent_settings.AgentSettings(preset="anthropic", model="m", enabled_sources=_EVERY),
                     list(sources.BUILT_IN)),
}


def _digest(text):
    return len(text), hashlib.sha256(text.encode("utf-8")).hexdigest()


@pytest.mark.parametrize("name", sorted(GOLDEN))
def test_the_prompt_is_unchanged(name):
    values, active = CONFIGS[name]
    assert _digest(Controller._prompt(values, active)) == GOLDEN[name]


@pytest.mark.parametrize("name", sorted(GOLDEN))
def test_chat_instructions_give_the_same_text(name):
    chat_setup = importlib.import_module(f"{_PKG}.core.agent.chat_setup")
    values, active = CONFIGS[name]
    text = chat_setup.chat_instructions(active, send_values=values.send_values,
                                        filtering=Controller.local_filtering(values))
    assert _digest(text) == GOLDEN[name]


def test_source_tools():
    chat_setup = importlib.import_module(f"{_PKG}.core.agent.chat_setup")
    assert chat_setup.SOURCE_TOOLS == {"search_open_data", "add_service_layer", "search_imagery", "add_basemap",
                                       "add_elevation", "add_osm_features", "add_population", "find_place",
                                       "list_database_tables", "add_database_table", 'search_data_sources'}


def test_a_settings_link_turned_off_in_the_tools_tab_is_not_named_by_the_note():
    """Review 2026-11-18: the note sent the model to a tool the user turned off."""
    values = agent_settings.AgentSettings(preset="anthropic", model="m",
                                          tool_rules='{"show_settings_link": "never"}')
    text = Controller._prompt(values, [])
    assert "never guess coordinates" in text and "call show_settings_link" not in text
    assert "call show_settings_link" in Controller._prompt(CONFIGS["default"][0], [])


def test_a_web_search_tool_turned_off_is_not_advertised_as_available():
    setup = importlib.import_module(f'{_PKG}.core.agent.chat_setup')
    active = [source for source in sources.BUILT_IN if source.id == 'web_search']
    assert 'Web source discovery is enabled' in setup.chat_instructions(active, offered={'search_data_sources'})
    assert 'Web source discovery is enabled' not in setup.chat_instructions(active, offered={'agent_options'})
