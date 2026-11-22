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

``--conversation --memory`` replays it with the memory kept from one project to the next as full as a request may
carry it (core/agent/memory.py, ``MAX_MEMORY_BLOCK``), and prints what that costs against the same conversation
without it: the price of the worst case, which the budget is set on. An empty memory weighs nothing.

    python scripts/agent_request_weight.py --conversation --memory

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
from agent.tool_catalog import LOAD_SKILL, RUN_PYTHON, USE_TOOLS, ToolSpec, chat_tools, with_skill_tool  # noqa: E402
from agent.chat_setup import SOURCE_TOOLS, chat_instructions, stable_order  # noqa: E402
from agent.families import bringing, split_tools, use_tools_handler  # noqa: E402
from agent.session import STATUS_DONE, AgentLimits, AgentSession, history_budget, run_exchange  # noqa: E402
from agent.skills import SKILLS  # noqa: E402
from agent.tool_executor import ToolExecutor  # noqa: E402
from agent_eval import (  # noqa: E402
    ScriptedTransport, SimulatedProject, project_context, project_state_of, project_update_of, skill_loader)
from agent.memory import MAX_MEMORY_BLOCK, SCOPE_SOURCE, Memory, added, chosen, memory_block  # noqa: E402
from agent.project_notes import notes_block  # noqa: E402
from agent.request_context import ContextMemory, ContextParts, compose, widgets_part  # noqa: E402


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
    """The parts of a request in the order its server reads them for its cache.

    Anthropic documents tools, system, messages. Ollama renders the instructions (the first message), then the tools
    (the templates of qwen3 and its kin put them in the system block), then the other messages. OpenAI documents no
    order: taken as tools first, as its JSON's order would count tools left unchanged as not cached (an assumption)."""
    if kind == "anthropic":
        return "".join(_compact(body.get(part, [])) for part in ("tools", "system", "messages"))
    messages = body.get("messages", [])
    if kind == "ollama" and messages and messages[0].get("role") == "system":
        return _compact(messages[:1]) + _compact(body.get("tools", [])) + _compact(messages[1:])
    return _compact(body.get("tools", [])) + _compact(messages)


def common_prefix(a: str, b: str) -> int:
    """How many characters ``a`` and ``b`` start with in common."""
    size = 0
    for left, right in zip(a, b):
        if left != right:
            break
        size += 1
    return size


def anthropic_entries(body: Dict[str, Any]) -> List[str]:
    """What an Anthropic request writes to the cache, in its order: up to the instructions when their block carries
    cache_control (since lot 4), and up to its last block (the top-level cache_control)."""
    entries = []
    system = body.get("system", [])
    if system and isinstance(system[-1], dict) and system[-1].get("cache_control"):
        entries.append(_compact(body.get("tools", [])) + _compact(system))
    entries.append(cache_order("anthropic", body)[:-1])  # the provider always sends the top-level cache_control
    return entries


def cached_prefix(kind: str, earlier: Sequence[Dict[str, Any]], body: Dict[str, Any]) -> int:
    """The characters of ``body`` the cache of the provider ``kind`` can serve after ``earlier``, the requests of the
    conversation sent to it before, in order.

    Anthropic (cache_control on the whole request) writes each request up to its last block and serves only such an
    entry whole: the longest earlier request ``body`` starts with, without the "]" that closed its messages; a tool
    added, or the history rewritten, and nothing is read. Since lot 4 a second breakpoint ends the instructions: the
    tools and the instructions of an earlier request are an entry too, read after a rewrite of the history and by the
    next conversation of the same settings. OpenAI serves the start in common with the request before. Ollama too,
    unless num_ctx changed: it loads the model again."""
    if not earlier:
        return 0
    order = cache_order(kind, body)
    if kind == "anthropic":
        written = (entry for before in earlier for entry in anthropic_entries(before))
        return max((len(entry) for entry in written if order.startswith(entry)), default=0)
    before = earlier[-1]
    if kind == "ollama" and before.get("options", {}).get("num_ctx") != body.get("options", {}).get("num_ctx"):
        return 0
    return common_prefix(cache_order(kind, before), order)


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
    ordered: Dict[str, int] = field(default_factory=dict)  # the characters of the request in each cache's order
    # The start a tool added at the end leaves alike: the tools before it (and for Ollama the instructions first);
    # nothing for Anthropic, which reads only an entry written whole. And the instructions, which never change.
    kept: Dict[str, int] = field(default_factory=dict)
    system: str = ""

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
    tools = stable_order([tool for tool in chat_tools() if tool.name not in SOURCE_TOOLS and tool.name != RUN_PYTHON])
    tools = with_skill_tool(tools, {tool.name for tool in tools})
    brought = bringing(tools, SKILLS.values())
    start, available = split_tools(tools)
    held = {tool.name: brought.get(tool.name, []) for tool in available}
    instructions = chat_instructions([], offered=[tool.name for tool in tools], available=available)
    return instructions, tuple(start), held


# A conversation on the simulated project of agent_eval.py, the calls taken from cases of its bench:
# filters on attributes, a filter across layers, a statistic, a style, the view, an export.
CONVERSATION_SETUP = {"selected": ["communes"]}
# Lot 3 (2026-11-16): five layers like those of the network project of the user (12 fields each, a zone id that links
# them), two notes and two widgets, so that the bench sees what sending less of the state and of the data saves.
_CITIES = ["Toulouse", "Muret", "Blagnac", "Colomiers", "Tournefeuille", "Balma", "L'Union", "Cugnaux", "Ramonville",
           "Castanet", "Portet", "Plaisance", "Saint-Orens", "Launaguet", "Aucamville", "Fenouillet", "Seilh",
           "Pibrac", "Cornebarrieu", "Beauzelle", "Villeneuve", "Escalquens", "Labège", "Auzeville", "Quint",
           "Fonsorbes", "Frouzins", "Roques", "Seysses", "Villate"]


def _network_layer(layer_id: str, geometry: str, count: int, kind_values) -> dict:
    return {"id": layer_id, "kind": "vector", "geometry": geometry, "count": count, "fields": {
        "identifier": [f"{layer_id.upper()}-{number:05d}" for number in range(1, 6)],
        "zone_pop_id": [f"POP_{number:03d}" for number in range(1, 41)],
        "zone_mro_id": [f"MRO_{number:02d}" for number in range(1, 11)],
        "status": ["TODO", "CONSTRUCTED", "AS_BUILT", "BLOWN"], "type": list(kind_values),
        "city": list(_CITIES), "postal_code": ["31000", "31100", "31200", "31300", "31400", "31500"],
        "owner": ["Acme Fiber", "Orange", "Free"], "comment": ["", "à revoir", "accès difficile"],
        "created_at": ["2025-01-12", "2025-06-30"], "updated_at": ["2026-10-01", "2026-11-12"],
        "length": [0.5, 2400.0]}}


EXTRA_LAYERS = {
    "zones_pop": _network_layer("zones_pop_j1", "MultiPolygon", 106, ["POP"]),
    "points_demande": _network_layer("points_demande_k2", "Point", 22166, ["HP", "N-HP"]),
    "cables": _network_layer("cables_l3", "MultiLineString", 3103, ["FO-12", "FO-24", "FO-48", "FO-144"]),
    "conduites": _network_layer("conduites_m4", "MultiLineString", 33883, ["PVC-42", "PEHD-45", "Aérien"]),
    "structures": _network_layer("structures_n5", "Point", 22185, ["PBO", "PM", "BPE", "Chambre", "Poteau"]),
}
BENCH_NOTES = ["Les couches du réseau se rattachent aux zones POP par le champ zone_pop_id.",
               "Le statut TODO veut dire à construire ; CONSTRUCTED, posé ; AS_BUILT, récolé."]
BENCH_WIDGETS = [{"id": "w1", "kind": "range", "layer": "cables", "field": "length", "low": 0, "high": 1200},
                 {"id": "w2", "kind": "values", "layer": "points_demande", "field": "status", "ticked": ["HP"]}]


def bench_project() -> SimulatedProject:
    """The simulated project of agent_eval.py and the five layers of a network: 14 layers."""
    import copy
    project = SimulatedProject(CONVERSATION_SETUP)
    for name, layer in EXTRA_LAYERS.items():
        project.layers[name] = copy.deepcopy(layer)
        project.by_ref[name] = name
        project.by_ref[layer["id"]] = name
    return project


def full_memory_block(project: SimulatedProject) -> str:
    """The notes kept from one project to the next as a request carries them when they fill their budget: notes for
    every project and for each layer of the bench, more than fit (core/agent/memory.py)."""
    kept = Memory()
    for rank in range(12):
        kept, _note = added(kept, f"Terme métier {rank} : " + BENCH_NOTES[rank % 2], today="2026-11-22")
    sources = [(f"ogr::{name}", name) for name in project.layers]
    for signature, name in sources:
        for rank in range(3):
            kept, _note = added(kept, f"Dans {name}, le mot d'usage {rank} désigne le champ status = 'AS_BUILT'.",
                                SCOPE_SOURCE, signature, name, today="2026-11-22")
    return memory_block(chosen(kept, sources, active=sources[0][0]))


def bench_context(project: SimulatedProject, before, memory: Optional[ContextMemory] = None, full: bool = True,
                  kept: str = "") -> str:
    """The context a request carries, as the chat composes it (core/agent/request_context.py): the whole of it, or what
    changed since ``before`` when ``memory`` says what was sent already (lot 3). ``kept``: the notes kept from one
    project to the next (``full_memory_block``); none by default, as for a user who wrote none."""
    memory = memory if memory is not None else ContextMemory()
    full = full or memory.empty or before is None
    summary = project_context(project, before=before) if full else project_update_of(project, before)
    return compose(memory.delta(ContextParts(summary=summary, notes=notes_block(BENCH_NOTES), memory=kept,
                                             widgets=widgets_part(BENCH_WIDGETS)), full))


# The requests: 13 since lot 3 (three of them read data).
CONVERSATION = (
    ("Ne garde que les communes de Haute-Garonne (département 31).",
     (("apply_filter", {"layer_name": "communes", "expression": "\"dept\" = '31'"}),)),
    ("Quels champs a la couche des câbles ?", (("describe_layer", {"layer": "cables"}),)),
    ("Quels champs a la couche des routes ?", (("describe_layer", {"layer": "routes"}),)),
    ("Filtre les bâtiments qui sont dans la commune sélectionnée.",
     (("cross_filter", {"source_layer": "communes", "target_layers": ["batiments"], "predicates": ["Are within"]}),)),
    ("Quels statuts prennent les câbles ?", (("field_values", {"layer": "cables", "field": "status"}),)),
    ("Combien y a-t-il de communes par département ?",
     (("layer_statistics", {"layer": "communes", "group_by": "dept"}),)),
    ("Colore les communes selon leur population, en 5 classes.",
     (("set_layer_style", {"layer": "communes", "mode": "graduated", "field": "population", "classes": 5}),)),
    ("Parmi ces communes, garde seulement celles de plus de 10000 habitants.",
     (("apply_filter", {"layer_name": "communes", "expression": "\"population\" > 10000", "operator": "AND"}),)),
    ("Zoome sur la commune sélectionnée.", (("zoom_to", {"layer": "communes", "selected_only": True}),)),
    ("Hide the parcels layer.", (("set_layers_visibility", {"layers": ["parcelles"], "visible": False}),)),
    ("Montre-moi quelques points de demande.", (("sample_features", {"layer": "points_demande"}),)),
    ("Exporte les bâtiments en GeoJSON.", (("export_layers", {"layers": ["batiments"], "vector_format": "GeoJSON"}),)),
    ("Retire le filtre sur les communes.", (("clear_filters", {"layers": ["communes"]}),)),
)
# The conversation of the main branch before lot 1 (2026-11-16), set by lot 0: each lot must lower the cost and the
# largest request, neither rising more than 5 % above (docs/superpowers/specs/2026-11-16-agent-token-diet-design.md).
# Taken again on 2026-11-16 for lot 3 (14 layers, notes, widgets, 13 requests), on the code of main after lots 0 and 1
# (867c4f24). The first one, for lot 0 (10 requests, 9 layers, main b77dea9c before lot 1): fingerprint 3a596d972f4d,
# 21 calls, 1,381,796 characters sent, largest 80,432, cost 291,616.
REFERENCE: Optional[Dict[str, Any]] = {  # 2026-11-17: the fields of the active layer in the state (+0.2 %);
    # lot 4 of the token diet (the cache): the breakpoint of the instructions
    # weighs 37 characters a call, read back by a new conversation and after a compaction, neither replayed here;
    # lot 2 with its review: sent 784,859, largest 35,602, cost 184,870; before (867c4f24): 1,408,656, 67,413, 340,333
    "date": "2026-11-16", "commit": "40d4e3ef", "fingerprint": "16efd34dcb03",  # with lot 4 and its review
    "calls": 28, "sent": 787631, "largest": 35701, "cost": 185489,
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
    bodies: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)  # every request, by provider
    memory_chars: int = 0  # the notes kept from one project to the next the conversation carried (--memory)


def tools_start(kind: str, body: Dict[str, Any]) -> int:
    """The characters of ``body``, in the order of the cache of ``kind``, that a tool added at the end of its list
    leaves alike: the tools but the "]" that closes them, after the instructions for Ollama; 0 for Anthropic."""
    if kind == "anthropic" or not body.get("tools"):
        return 0
    tools = len(_compact(body["tools"])) - 1
    messages = body.get("messages", [])
    if kind == "ollama" and messages and messages[0].get("role") == "system":
        return len(_compact(messages[:1])) + tools
    return tools


def broken_starts(calls: Sequence[CallWeight]) -> List[str]:
    """Lot 4: the starts that changed. Between two calls of one request, each provider's cache must serve the whole
    call before (without the "]" that closed it) when the tools are the same, and the tools before when one was
    added at the end; Ollama only at the same num_ctx (another loads the model again). The instructions of a
    conversation never change."""
    broken = []
    for before, call in zip(calls, calls[1:]):
        if call.system != before.system:
            broken.append(f"request {call.request}: the instructions changed")
        if call.request != before.request:
            continue
        for kind, read in call.prefix.items():
            if kind == "ollama" and call.num_ctx != before.num_ctx:
                continue
            if call.tool_count == before.tool_count:
                needed = before.ordered[kind] - 1
            elif call.tool_count > before.tool_count:
                needed = before.kept.get(kind, 0)
            else:
                continue  # tools taken out: only at a compaction, which rewrites the history anyway
            if read < needed:
                broken.append(f"request {call.request}: {kind} reads {read} of the {needed} it should")
    return broken


class _Measured:
    """The scripted model, after weighing the request it is sent as each provider would build it."""

    def __init__(self, inner, kinds: Dict[str, Provider], rank: int, run: Replay,
                 before: Dict[str, List[Dict[str, Any]]]) -> None:
        self._inner, self._kinds, self._rank, self._run, self._before = inner, kinds, rank, run, before

    def send(self, request, session):
        bodies = {kind: json.loads(provider.build_request(session.system, session.messages, session.tools).body)
                  for kind, provider in self._kinds.items()}
        anthropic = bodies["anthropic"]
        self._run.calls.append(CallWeight(
            self._rank, len(_compact(anthropic["system"])), len(_compact(anthropic.get("tools", []))),
            len(_compact(anthropic["messages"])), len(session.tools),
            {kind: cached_prefix(kind, self._before.setdefault(kind, []), body) for kind, body in bodies.items()},
            bodies["ollama"]["options"]["num_ctx"], {kind: len(cache_order(kind, body)) for kind, body in bodies.items()},
            {kind: tools_start(kind, body) for kind, body in bodies.items()}, _compact(anthropic["system"])))
        for kind, body in bodies.items():
            self._before[kind].append(body)
        return self._inner.send(request, session)


def replay(with_memory: bool = False) -> Replay:
    """The conversation played by the scripted model in one session of the chat, every call weighed.
    ``with_memory``: with the memory kept from one project to the next as full as a request carries it."""
    instructions, tools, held = default_setup()
    kinds = providers()
    run = Replay()
    project = bench_project()
    kept = full_memory_block(project) if with_memory else ""
    run.memory_chars = len(kept)
    project.offered = {tool.name for tool in tools} | set(held)
    hidden = {tool.name: tool for tool in chat_tools() if tool.name in held}
    known = {tool.name for tool in tools} | set(hidden)
    session = AgentSession(kinds["anthropic"], tools, instructions, AgentLimits(
        max_history_chars=history_budget("anthropic", 0)))  # as the chat gives a remote provider (lot 3)
    handlers = project.handlers()
    handlers[USE_TOOLS] = use_tools_handler(hidden, lambda now: (session.offer(now), executor.offer(now)), known=known,
                                            skills=held)
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
    before: Dict[str, List[Dict[str, Any]]] = {}
    seen = None
    memory = ContextMemory()
    for rank, (text, steps) in enumerate(CONVERSATION, 1):
        scripted = ScriptedTransport([{"tool": tool, "args": args} for tool, args in steps])
        scripted.use_first({name: held[name] for name in hidden})  # a tool added before is not added again
        exchange = run_exchange(session, text, _Measured(scripted, kinds, rank, run, before), executor,
                                confirm=lambda call: True,
                                context=lambda full, seen=seen: bench_context(project, seen, memory, full, kept))
        memory.sent()
        seen = project_state_of(project)
        if exchange.error is not None:
            run.errors.append(f"request {rank}: {exchange.error.message}")
        elif exchange.decision is None or exchange.decision.status != STATUS_DONE:  # its steps left would weigh too
            reason = exchange.decision.reason if exchange.decision is not None else "no answer"
            run.errors.append(f"request {rank}: stopped ({reason})")
        run.skills_loaded += [str(call.arguments.get("name", "")) for call in exchange.calls if call.name == LOAD_SKILL]
    run.summarized = session.summarized
    run.bodies = before
    return run


def next_conversation(run: Replay) -> Dict[str, int]:
    """What the cache of each provider serves of the first request of a new conversation of the same settings, sent
    after ``run``: the tools and the instructions are the same, the request is another one."""
    instructions, tools, _held = default_setup()
    first = [Message(ROLE_USER, (TextPart("Bonjour, que contient ce projet ?"),))]
    read = {}
    for kind, provider in providers().items():
        body = json.loads(provider.build_request(instructions, first, tools).body)
        earlier = run.bodies.get(kind, [])
        if kind == "openai":  # its cache holds more than the request before: the best start of any
            read[kind] = max((cached_prefix(kind, [before], body) for before in earlier), default=0)
        else:
            read[kind] = cached_prefix(kind, earlier, body)
        read[kind + "_expected"] = len(_compact(body["tools"]) + _compact(body["system"])) if kind == "anthropic" \
            else tools_start(kind, body)
    return read


def _rise(now: float, then: float) -> float:
    return now / then - 1 if then else 0.0


def _totals(run: Replay) -> Dict[str, int]:
    return {"calls": len(run.calls), "sent": sum(call.sent for call in run.calls),
            "largest": max(call.sent for call in run.calls), "cost": round(estimated_cost(run.calls))}


def report_memory() -> int:
    """Print what a full memory costs the conversation, against the same without it; 1 when a replay failed or the
    block passes its budget. Not held to the reference: it is the price of the worst case, to set the budget on."""
    without, with_it = replay(), replay(with_memory=True)
    before, after = _totals(without), _totals(with_it)
    print(f"memory block: {with_it.memory_chars} characters (budget {MAX_MEMORY_BLOCK}), sent once in "
          f"{after['calls']} calls")
    for key in ("sent", "largest", "cost"):
        print(f"  {key:8s} {before[key]:8d} -> {after[key]:8d}  {_rise(after[key], before[key]):+.1%}")
    errors = without.errors + with_it.errors + broken_starts(with_it.calls)
    if not 0 < with_it.memory_chars <= MAX_MEMORY_BLOCK:
        errors.append(f"the block weighs {with_it.memory_chars}: it must fill its budget without passing it")
    for error in errors:
        print(f"  error: {error}")
    return 1 if errors else 0


def report_conversation() -> int:
    """Print the weight of each call and of the conversation; 1 when it rose past the reference, or the reference is of
    another conversation."""
    run = replay()
    print(" req tools  instructions   tools  history   cached: anthropic  openai  ollama  num_ctx")
    for call in run.calls:
        print(f"{call.request:4d} {call.tool_count:5d} {call.instructions:13d} {call.tools:7d} {call.history:8d} "
              f"{call.prefix['anthropic']:19d} {call.prefix['openai']:7d} {call.prefix['ollama']:7d} {call.num_ctx:8d}")
    totals = _totals(run)
    print(f"\n{totals['calls']} calls, {totals['sent']} characters sent, largest request {totals['largest']}, "
          f"estimated cost {totals['cost']} (characters at the price of an input not cached), "
          f"requests summed up {run.summarized}; fingerprint {fingerprint()}")
    fresh = next_conversation(run)
    print("a new conversation of the same settings, first request: cached " + ", ".join(
        f"{kind} {fresh[kind]}" for kind in KINDS))
    broken = broken_starts(run.calls) + [
        f"a new conversation: {kind} reads {fresh[kind]} of the {fresh[kind + '_expected']} it should"
        for kind in KINDS if fresh[kind] < fresh[kind + "_expected"]]
    for error in run.errors + broken:
        print(f"  error: {error}")
    if REFERENCE is None:
        return 1 if run.errors or broken else 0
    if REFERENCE.get("fingerprint") != fingerprint():
        print(f"reference taken on another conversation ({REFERENCE.get('fingerprint')}): take it again")
        return 1
    rises = {key: _rise(totals[key], REFERENCE[key]) for key in ("cost", "largest")}
    print("against the reference of " + str(REFERENCE.get("date", "?")) + ": "
          + ", ".join(f"{key} {rise:+.1%}" for key, rise in rises.items()))
    return 1 if run.errors or broken or any(rise > MAX_RISE for rise in rises.values()) else 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--top", type=int, default=10, help="how many of the heaviest tools to list")
    parser.add_argument("--conversation", action="store_true",
                        help="replay a conversation of ten requests and weigh each call, against the reference")
    parser.add_argument("--memory", action="store_true",
                        help="with --conversation: what a full memory kept from one project to the next costs it")
    args = parser.parse_args(argv)
    if args.memory and not args.conversation:
        parser.error("--memory goes with --conversation")
    if args.conversation:
        return report_memory() if args.memory else report_conversation()
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
