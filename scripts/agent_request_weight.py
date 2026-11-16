#!/usr/bin/env python3
"""What a request of the agent weighs with every tool of the chat, and the context a local model is asked for.

Ollama loads a model again at each new context size, and a larger one takes more memory: every tool of the chat
with the instructions must stay within the 32k step (``core/agent/providers/ollama_chat.CONTEXT_STEPS``), with room
left for the next tool. Run it after a change of a tool description or of the instructions:

    python scripts/agent_request_weight.py [--top 10]

``--conversation`` replays, with the scripted model of agent_eval.py and no network, ten requests in one session of
the chat as the default settings make it (the families on, no source ticked), and prints for each call to the model
the characters of the instructions, the tools and the history, the start of it each provider's cache can serve
(Anthropic, OpenAI, Ollama: the same start as the call before, the tools first), and the num_ctx Ollama is asked for;
then the totals, an estimated cost at the prices of Anthropic, and how far they are from ``REFERENCE``. It fails when
the cost or the largest request rises more than 5 % above the reference:

    python scripts/agent_request_weight.py --conversation

Not weighed: the notes about the sources the user ticked, which core/agent/chat_setup.py adds to the instructions
(--conversation weighs the history, with no source ticked), and, without --conversation, the history. Measured on 2026-11-15, these notes are 864 characters for a basemap, a
geocoder, an elevation source, an OpenStreetMap server and a population grid, 2,086 with one source of every kind:
the room printed here must hold them too for a first request to stay in the step with everything ticked and the
families off.
"""
import argparse
import hashlib
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "core"))  # core/__init__.py imports QGIS; core/agent itself does not
sys.path.insert(0, str(ROOT / "scripts"))  # the simulated project and the scripted model of agent_eval.py

from agent.messages import ROLE_USER, Message, TextPart  # noqa: E402
from agent.providers import PRESETS, create_provider  # noqa: E402
from agent.providers.base import Provider, ProviderConfig  # noqa: E402
from agent.providers.ollama_chat import ANSWER_ROOM, CHARS_PER_TOKEN, CONTEXT_STEPS  # noqa: E402
from agent.system_prompt import SYSTEM_PROMPT  # noqa: E402
from agent.tool_catalog import LOAD_SKILL, RUN_PYTHON, ToolSpec, chat_tools, with_skill_tool  # noqa: E402
from agent.chat_setup import SOURCE_TOOLS, chat_instructions  # noqa: E402
from agent.families import bringing  # noqa: E402
from agent.session import AgentLimits, AgentSession, run_exchange  # noqa: E402
from agent.skills import SKILLS  # noqa: E402
from agent.tool_executor import ToolExecutor  # noqa: E402
from agent_eval import ScriptedTransport, SimulatedProject, project_context, project_state_of, skill_loader  # noqa: E402


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


def default_setup() -> Tuple[str, Tuple[ToolSpec, ...], Dict[str, List[str]]]:
    """``(instructions, tools offered at the start, tools held back with the skills that bring them)`` as the chat
    builds them with the default settings: the families on, no source ticked, the values shared, neither the expert
    mode nor the filtering tools alone (tests/unit/ui/controllers/test_agent_request_weight_default.py checks it)."""
    tools = [tool for tool in chat_tools() if tool.name not in SOURCE_TOOLS and tool.name != RUN_PYTHON]
    tools = with_skill_tool(tools, {tool.name for tool in tools})
    held = bringing(tools, SKILLS.values())
    instructions = chat_instructions([], offered=[tool.name for tool in tools])
    return instructions, tuple(tool for tool in tools if tool.name not in held), held


# A conversation of ten requests on the simulated project of agent_eval.py, the calls taken from cases of its bench:
# filters on attributes, a filter across layers, a statistic, a style, the view, an export.
CONVERSATION_SETUP = {"selected": ["communes"]}
CONVERSATION = (
    ("Ne garde que les communes de Haute-Garonne (département 31).",
     (("apply_filter", {"layer_name": "communes", "expression": "\"dept\" = '31'"}),)),
    ("Quels champs a la couche des routes ?", (("describe_layer", {"layer": "routes"}),)),
    ("Filtre les bâtiments qui sont dans la commune sélectionnée.",
     (("cross_filter", {"source_layer": "communes", "target_layers": ["batiments"], "predicates": ["Are within"]}),)),
    ("Combien y a-t-il de communes par département ?",
     (("layer_statistics", {"layer": "communes", "group_by": "dept"}),)),
    ("Colore les communes selon leur population, en 5 classes.",
     (("set_layer_style", {"layer": "communes", "mode": "graduated", "field": "population", "classes": 5}),)),
    ("Parmi ces communes, garde seulement celles de plus de 10000 habitants.",
     (("apply_filter", {"layer_name": "communes", "expression": "\"population\" > 10000", "operator": "AND"}),)),
    ("Zoome sur la commune sélectionnée.", (("zoom_to", {"layer": "communes", "selected_only": True}),)),
    ("Hide the parcels layer.", (("set_layers_visibility", {"layers": ["parcelles"], "visible": False}),)),
    ("Exporte les bâtiments en GeoJSON.", (("export_layers", {"layers": ["batiments"], "vector_format": "GeoJSON"}),)),
    ("Retire le filtre sur les communes.", (("clear_filters", {"layers": ["communes"]}),)),
)
# The conversation of the main branch before lot 1 (2026-11-16), set by lot 0: each lot must lower the cost and the
# largest request, neither rising more than 5 % above (docs/superpowers/specs/2026-11-16-agent-token-diet-design.md).
REFERENCE: Optional[Dict[str, Any]] = {
    "date": "2026-11-16", "commit": "b77dea9c", "fingerprint": "3a596d972f4d",
    "calls": 21, "sent": 1381796, "largest": 80432, "cost": 251284,
}
MAX_RISE = 0.05


def fingerprint() -> str:
    """Of the conversation replayed: a reference taken on another one compares nothing."""
    return hashlib.sha256(json.dumps([CONVERSATION_SETUP, CONVERSATION], sort_keys=True).encode("utf-8")).hexdigest()[:12]


@dataclass
class Replay:
    calls: List[CallWeight] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)  # tool answers in error: the conversation would weigh less
    skills_loaded: List[str] = field(default_factory=list)
    summarized: int = 0  # requests the compaction summed up


class _Measured:
    """The scripted model, after weighing the request it is sent as each provider would build it."""

    def __init__(self, inner, kinds: Dict[str, Provider], rank: int, run: Replay, before: Dict[str, Any]) -> None:
        self._inner, self._kinds, self._rank, self._run, self._before = inner, kinds, rank, run, before

    def send(self, request, session):
        bodies = {kind: json.loads(provider.build_request(session.system, session.messages, session.tools).body)
                  for kind, provider in self._kinds.items()}
        anthropic = bodies["anthropic"]
        self._run.calls.append(CallWeight(
            self._rank, len(_compact(anthropic["system"])), len(_compact(anthropic.get("tools", []))),
            len(_compact(anthropic["messages"])), len(session.tools),
            {kind: cached_prefix(kind, self._before.get(kind), body) for kind, body in bodies.items()},
            bodies["ollama"]["options"]["num_ctx"]))
        self._before.update(bodies)
        return self._inner.send(request, session)


def replay() -> Replay:
    """The conversation played by the scripted model in one session of the chat, every call weighed."""
    instructions, tools, held = default_setup()
    kinds = providers()
    run = Replay()
    project = SimulatedProject(CONVERSATION_SETUP)
    project.offered = {tool.name for tool in tools} | set(held)
    hidden = {tool.name: tool for tool in chat_tools() if tool.name in held}
    session = AgentSession(kinds["anthropic"], tools, instructions, AgentLimits())
    handlers = project.handlers()
    handlers[LOAD_SKILL] = skill_loader(handlers[LOAD_SKILL], hidden,
                                        lambda now: (session.offer(now), executor.offer(now)))
    executor = ToolExecutor(tools, handlers)
    executor.hold(held)
    execute = executor.execute

    def checked(call):
        result = execute(call)
        if result.is_error:
            run.errors.append(f"{call.name}: {result.content[:160]}")
        return result
    executor.execute = checked
    before: Dict[str, Any] = {}
    seen = None
    for rank, (text, steps) in enumerate(CONVERSATION, 1):
        scripted = ScriptedTransport([{"tool": tool, "args": args} for tool, args in steps])
        scripted.load_first({name: held[name] for name in hidden})  # a skill loaded before is not loaded again
        exchange = run_exchange(session, text, _Measured(scripted, kinds, rank, run, before), executor,
                                confirm=lambda call: True, context=project_context(project, before=seen))
        seen = project_state_of(project)
        if exchange.error is not None:
            run.errors.append(f"request {rank}: {exchange.error.message}")
        run.skills_loaded += [str(call.arguments.get("name", "")) for call in exchange.calls if call.name == LOAD_SKILL]
    run.summarized = session.summarized
    return run


def _rise(now: float, then: float) -> float:
    return now / then - 1 if then else 0.0


def report_conversation() -> int:
    """Print the weight of each call and of the conversation; 1 when it rose past the reference, or the reference is of
    another conversation."""
    run = replay()
    print(" req tools  instructions   tools  history   cached: anthropic  openai  ollama  num_ctx")
    for call in run.calls:
        print(f"{call.request:4d} {call.tool_count:5d} {call.instructions:13d} {call.tools:7d} {call.history:8d} "
              f"{call.prefix['anthropic']:19d} {call.prefix['openai']:7d} {call.prefix['ollama']:7d} {call.num_ctx:8d}")
    totals = {"calls": len(run.calls), "sent": sum(call.sent for call in run.calls),
              "largest": max(call.sent for call in run.calls), "cost": round(estimated_cost(run.calls))}
    print(f"\n{totals['calls']} calls, {totals['sent']} characters sent, largest request {totals['largest']}, "
          f"estimated cost {totals['cost']} (characters at the price of an input not cached), "
          f"requests summed up {run.summarized}; fingerprint {fingerprint()}")
    for error in run.errors:
        print(f"  error: {error}")
    if REFERENCE is None:
        return 1 if run.errors else 0
    if REFERENCE.get("fingerprint") != fingerprint():
        print(f"reference taken on another conversation ({REFERENCE.get('fingerprint')}): take it again")
        return 1
    rises = {key: _rise(totals[key], REFERENCE[key]) for key in ("cost", "largest")}
    print("against the reference of " + str(REFERENCE.get("date", "?")) + ": "
          + ", ".join(f"{key} {rise:+.1%}" for key, rise in rises.items()))
    return 1 if run.errors or any(rise > MAX_RISE for rise in rises.values()) else 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--top", type=int, default=10, help="how many of the heaviest tools to list")
    parser.add_argument("--conversation", action="store_true",
                        help="replay a conversation of ten requests and weigh each call, against the reference")
    args = parser.parse_args(argv)
    if args.conversation:
        return report_conversation()
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
