#!/usr/bin/env python3
"""What a request of the agent weighs with every tool of the chat, and the context a local model is asked for.

Ollama loads a model again at each new context size, and a larger one takes more memory: every tool of the chat
with the instructions must stay within the 32k step (``core/agent/providers/ollama_chat.CONTEXT_STEPS``), with room
left for the next tool. Run it after a change of a tool description or of the instructions:

    python scripts/agent_request_weight.py [--top 10]

Not weighed: the notes about the sources the user ticked, which the chat controller adds to the instructions (it
needs QGIS), and the conversation. Measured on 2026-11-15, these notes are 864 characters for a basemap, a
geocoder, an elevation source, an OpenStreetMap server and a population grid, 2,086 with one source of every kind:
the room printed here must hold them too for a first request to stay in the step with everything ticked and the
families off.
"""
import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "core"))  # core/__init__.py imports QGIS; core/agent itself does not

from agent.messages import ROLE_USER, Message, TextPart  # noqa: E402
from agent.providers import PRESETS, create_provider  # noqa: E402
from agent.providers.base import Provider, ProviderConfig  # noqa: E402
from agent.providers.ollama_chat import ANSWER_ROOM, CHARS_PER_TOKEN, CONTEXT_STEPS  # noqa: E402
from agent.system_prompt import SYSTEM_PROMPT  # noqa: E402
from agent.tool_catalog import chat_tools  # noqa: E402


# What ui/controllers/agent_chat_controller.py adds to the instructions for the sources ticked, measured in QGIS
# on 2026-11-15: (a basemap, a geocoder, an elevation source, an OpenStreetMap server and a population grid; one
# source of every kind).
NOTES_OF_SOURCES = (864, 2086)


def weigh():
    """``(characters of the request, characters the 32k step holds, num_ctx asked, [(characters, tool)])``."""
    kind, base = PRESETS["ollama"]
    provider = create_provider(ProviderConfig(kind=kind, model="qwen3:8b", base_url=base, api_key=""))
    request = provider.build_request(SYSTEM_PROMPT, [Message(ROLE_USER, (TextPart("bonjour"),))], chat_tools())
    body = json.loads(request.body)
    tools = sorted(((len(json.dumps(tool, ensure_ascii=False)), tool["function"]["name"]) for tool in body["tools"]),
                   reverse=True)
    return len(request.body), int((CONTEXT_STEPS[1] - ANSWER_ROOM) * CHARS_PER_TOKEN), body["options"]["num_ctx"], tools


KINDS = ("anthropic", "openai", "ollama")
# What Anthropic charges, relative to an input token the cache does not serve: writing it to the cache, reading it
# from there. Counted on characters. The input the cache does not serve (1) applies to nothing here: the provider puts
# cache_control on the whole request (core/agent/providers/anthropic_messages.py), so what is not read is written.
CACHE_WRITE = 1.25
CACHE_READ = 0.1


def providers() -> Dict[str, Provider]:
    """One provider of each kind, at its usual address, without a key: they only build requests here."""
    made = {}
    for kind in KINDS:
        preset, base = PRESETS[kind]
        made[kind] = create_provider(ProviderConfig(kind=preset, model="qwen3:8b" if kind == "ollama" else "m",
                                                    base_url=base, api_key=""))
    return made


def _compact(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))  # as encode_json writes it


def cache_order(kind: str, body: Dict[str, Any]) -> str:
    """The parts of a request in the order its server reads them for its cache: the tools first at all three, then
    the instructions and the messages (in OpenAI's and Ollama's JSON the tools come after the messages, but their
    servers put them at the head of the prompt; the literal order would count tools left unchanged as not cached)."""
    parts = ("tools", "system", "messages") if kind == "anthropic" else ("tools", "messages")
    return "".join(_compact(body.get(part, [])) for part in parts)


def common_prefix(a: str, b: str) -> int:
    """How many characters ``a`` and ``b`` start with in common."""
    size = 0
    for left, right in zip(a, b):
        if left != right:
            break
        size += 1
    return size


def cached_prefix(kind: str, before: Optional[Dict[str, Any]], body: Dict[str, Any]) -> int:
    """The characters of ``body`` the cache can serve after ``before``, the previous request of the conversation to
    the same provider: none for the first, none at Ollama when num_ctx changed (it loads the model again)."""
    if before is None:
        return 0
    if kind == "ollama" and before.get("options", {}).get("num_ctx") != body.get("options", {}).get("num_ctx"):
        return 0
    return common_prefix(cache_order(kind, before), cache_order(kind, body))


@dataclass(frozen=True)
class CallWeight:
    """One call to the model: the parts of its Anthropic body, and what each provider's cache can serve of it."""

    request: int  # the rank of the user's request in the conversation, from 1
    instructions: int
    tools: int
    history: int
    tool_count: int
    prefix: Dict[str, int]
    num_ctx: int

    @property
    def sent(self) -> int:
        return self.instructions + self.tools + self.history


def estimated_cost(calls: Sequence[CallWeight]) -> float:
    """What the calls would cost at Anthropic, in characters at the price of an input not cached."""
    return sum(CACHE_READ * call.prefix["anthropic"] + CACHE_WRITE * (call.sent - call.prefix["anthropic"])
               for call in calls)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--top", type=int, default=10, help="how many of the heaviest tools to list")
    args = parser.parse_args(argv)
    size, room, context, tools = weigh()
    print(f"{len(tools)} tools and the instructions ({len(SYSTEM_PROMPT)} characters): {size} characters, "
          f"{room - size:+d} under the {room} of the {CONTEXT_STEPS[1]} step; num_ctx asked: {context}")
    print(f"not weighed: the notes about the sources ticked ({NOTES_OF_SOURCES[0]} to {NOTES_OF_SOURCES[1]} "
          "characters), the conversation")
    for weight, name in tools[:args.top]:
        print(f"  {weight:6d}  {name}")
    return 0 if context <= CONTEXT_STEPS[1] else 1


if __name__ == "__main__":
    sys.exit(main())
