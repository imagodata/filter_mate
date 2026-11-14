# -*- coding: utf-8 -*-
"""The connector loader: connects when a connector-… entry is loaded, lists and bounds its tools, offers them."""
import pytest

from core.agent.connectors import LOADED_NOTE, MAX_CONNECTOR_TOOLS, ConnectorLoader, connector_entries
from core.agent.mcp_client import McpError, tools_from_listing
from core.agent.sources import BUILT_IN, Source
from core.agent.tool_executor import ToolFailure

pytestmark = pytest.mark.unit

EMPTY = {"type": "object", "properties": {}}


class Fake:
    """Makes the connections: what each source lists, which fail to connect, which refuse a call."""

    def __init__(self, tools, fail=None, call_fail=None):
        self.tools = tools
        self.fail = dict(fail or {})
        self.call_fail = call_fail
        self.made = []
        self.calls = []

    def connect(self, source):
        self.made.append(source.id)
        if source.id in self.fail:
            raise self.fail[source.id]
        fake = self

        class Connection:
            def list_tools(self):
                listing = {"tools": [{"name": name, "inputSchema": EMPTY} for name in fake.tools[source.id]]}
                return tools_from_listing(source.id, source.title, listing)

            def call_tool(self, remote, arguments):
                fake.calls.append((remote, arguments))
                if fake.call_fail is not None:
                    raise fake.call_fail
                return "answer of " + remote
        return Connection()


def loader(fake, room=MAX_CONNECTOR_TOOLS, ids=("datagouv_mcp", "osm_mcp", "geocontext")):
    offered = []
    entries = connector_entries([source for source in BUILT_IN if source.id in ids])
    made = ConnectorLoader(entries, fake.connect,
                           lambda source, tools, handlers: offered.append(
                               (source.id, [tool.spec.name for tool in tools], handlers)),
                           room=room)
    return made, offered


def test_loading_connects_lists_and_offers_the_tools():
    fake = Fake({"datagouv_mcp": ["search", "query"]})
    made, offered = loader(fake)
    assert made.load("connector-datagouv_mcp") == {
        "connector": "connector-datagouv_mcp", "title": "data.gouv.fr (MCP)",
        "tools_now_offered": ["mcp_datagouv_mcp__query", "mcp_datagouv_mcp__search"], "note": LOADED_NOTE}
    handlers = offered[0][2]
    assert handlers["mcp_datagouv_mcp__search"]({"q": "x"}) == "answer of search" and fake.calls == [("search", {"q": "x"})]
    assert made.source("connector-datagouv_mcp").id == "datagouv_mcp" and made.source("connector-nope") is None


def test_nothing_connects_before_a_load():
    fake = Fake({"datagouv_mcp": ["search"]})
    loader(fake)
    assert fake.made == []


def test_a_connector_loaded_answers_at_once_without_connecting_again():
    fake = Fake({"datagouv_mcp": ["search"]})
    made, offered = loader(fake)
    first = made.load("connector-datagouv_mcp")
    assert made.load("connector-datagouv_mcp") == first and fake.made == ["datagouv_mcp"] and len(offered) == 1


def test_a_connector_that_does_not_answer_says_so_and_is_tried_again():
    fake = Fake({"geocontext": ["geocode"]}, fail={"geocontext": McpError("IGN geocontext (MCP local): refused")})
    made, offered = loader(fake)
    with pytest.raises(ToolFailure) as failure:
        made.load("connector-geocontext")
    assert str(failure.value).startswith("IGN geocontext (MCP local) does not answer")
    assert "Start it first" in str(failure.value) and offered == []
    assert str(failure.value).endswith("Tell the user; nothing is kept, so loading it again tries again.")
    del fake.fail["geocontext"]
    assert made.load("connector-geocontext")["tools_now_offered"] == ["mcp_geocontext__geocode"]
    assert fake.made == ["geocontext", "geocontext"]


def test_a_remote_connector_that_does_not_answer_gives_no_hint():
    fake = Fake({}, fail={"datagouv_mcp": McpError("data.gouv.fr (MCP): timed out")})
    made, _offered = loader(fake)
    with pytest.raises(ToolFailure) as failure:
        made.load("connector-datagouv_mcp")
    assert str(failure.value) == ("data.gouv.fr (MCP) does not answer: data.gouv.fr (MCP): timed out. Tell the user; "
                                  "nothing is kept, so loading it again tries again.")


def test_the_room_is_for_the_whole_conversation():
    fake = Fake({"datagouv_mcp": ["a", "b"], "osm_mcp": ["c", "d"], "geocontext": ["e"]})
    made, offered = loader(fake, room=3)
    made.load("connector-datagouv_mcp")
    second = made.load("connector-osm_mcp")
    assert second["tools_now_offered"] == ["mcp_osm_mcp__c"] and second["left_out"] == 1
    with pytest.raises(ToolFailure, match="new conversation"):
        made.load("connector-geocontext")
    assert [item[0] for item in offered] == ["datagouv_mcp", "osm_mcp"]
    assert "geocontext" not in fake.made  # no room: refused without connecting
    assert made.load("connector-datagouv_mcp")["tools_now_offered"] == ["mcp_datagouv_mcp__a", "mcp_datagouv_mcp__b"]


def test_what_a_connector_refuses_is_said_to_the_model():
    fake = Fake({"datagouv_mcp": ["search"]}, call_fail=McpError("quota exceeded"))
    made, offered = loader(fake)
    made.load("connector-datagouv_mcp")
    with pytest.raises(ToolFailure, match="quota exceeded"):
        offered[0][2]["mcp_datagouv_mcp__search"]({})


def test_an_unknown_entry_and_an_empty_listing_are_refused_and_nothing_is_kept():
    fake = Fake({"datagouv_mcp": []})
    made, offered = loader(fake)
    with pytest.raises(ToolFailure, match="connector-datagouv_mcp"):
        made.load("connector-nope")
    with pytest.raises(ToolFailure, match="lists no tool"):
        made.load("connector-datagouv_mcp")
    fake.tools["datagouv_mcp"] = ["search"]
    assert made.load("connector-datagouv_mcp")["tools_now_offered"] == ["mcp_datagouv_mcp__search"]


def test_a_failed_offer_keeps_nothing():
    fake = Fake({"datagouv_mcp": ["a", "b"]})
    calls = []

    def offer(source, tools, handlers):
        calls.append(source.id)
        if len(calls) == 1:
            raise RuntimeError("the conversation is gone")
    made = ConnectorLoader(connector_entries(BUILT_IN), fake.connect, offer, room=2)
    with pytest.raises(RuntimeError):
        made.load("connector-datagouv_mcp")
    assert made.load("connector-datagouv_mcp")["tools_now_offered"] == ["mcp_datagouv_mcp__a", "mcp_datagouv_mcp__b"]
    assert calls == ["datagouv_mcp", "datagouv_mcp"]  # the room was not spent by the failure


def test_a_title_that_hides_a_character_is_not_sent_to_the_model():
    source = Source("mcp_mcp_example_org_mcp_abc123", "Team​data", "mcp", "https://mcp.example.org/mcp")
    fake = Fake({source.id: ["t"]})
    made = ConnectorLoader(connector_entries([source]), fake.connect, lambda *args: None)
    assert made.load("connector-" + source.id)["title"] == "mcp.example.org"
