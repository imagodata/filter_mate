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
    # paragraphs that described a tool one by one (12,076 characters before for the default)
    "default": (6357, "111ca6bcc8b38352582a4fe4b97660c21833a3e4e1ef563c6b875526309ac554"),
    "no_values_local": (6841, "0f72b1b59a0e6aff60b4d9dfae646ad9b54b9ced2471276f524a982cb1e52499"),
    "every_source": (6933, "07a04f553220042019f86ca8966c7cd4afcf2a92d4ec5924febb6ad08d8fb0c6"),
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
                                       "list_database_tables", "add_database_table"}
