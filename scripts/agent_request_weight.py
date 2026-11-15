#!/usr/bin/env python3
"""What a request of the agent weighs with every tool of the chat, and the context a local model is asked for.

Ollama loads a model again at each new context size, and a larger one takes more memory: every tool of the chat
with the instructions must stay within the 32k step (``core/agent/providers/ollama_chat.CONTEXT_STEPS``), with room
left for the next tool. Run it after a change of a tool description or of the instructions:

    python scripts/agent_request_weight.py [--top 10]
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "core"))  # core/__init__.py imports QGIS; core/agent itself does not

from agent.messages import ROLE_USER, Message, TextPart  # noqa: E402
from agent.providers import PRESETS, create_provider  # noqa: E402
from agent.providers.base import ProviderConfig  # noqa: E402
from agent.providers.ollama_chat import ANSWER_ROOM, CHARS_PER_TOKEN, CONTEXT_STEPS  # noqa: E402
from agent.system_prompt import SYSTEM_PROMPT  # noqa: E402
from agent.tool_catalog import chat_tools  # noqa: E402


def weigh():
    """``(characters of the request, characters the 32k step holds, num_ctx asked, [(characters, tool)])``."""
    kind, base = PRESETS["ollama"]
    provider = create_provider(ProviderConfig(kind=kind, model="qwen3:8b", base_url=base, api_key=""))
    request = provider.build_request(SYSTEM_PROMPT, [Message(ROLE_USER, (TextPart("bonjour"),))], chat_tools())
    body = json.loads(request.body)
    tools = sorted(((len(json.dumps(tool, ensure_ascii=False)), tool["function"]["name"]) for tool in body["tools"]),
                   reverse=True)
    return len(request.body), int((CONTEXT_STEPS[1] - ANSWER_ROOM) * CHARS_PER_TOKEN), body["options"]["num_ctx"], tools


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--top", type=int, default=10, help="how many of the heaviest tools to list")
    args = parser.parse_args(argv)
    size, room, context, tools = weigh()
    print(f"{len(tools)} tools and the instructions ({len(SYSTEM_PROMPT)} characters): {size} characters, "
          f"{room - size:+d} under the {room} of the {CONTEXT_STEPS[1]} step; num_ctx asked: {context}")
    for weight, name in tools[:args.top]:
        print(f"  {weight:6d}  {name}")
    return 0 if context <= CONTEXT_STEPS[1] else 1


if __name__ == "__main__":
    sys.exit(main())
