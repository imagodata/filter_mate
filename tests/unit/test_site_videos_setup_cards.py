# -*- coding: utf-8 -*-
"""scripts/site_videos.py: the take of the setup answers every card of the setup, however many steps it has.

The script needs QGIS and a GeoPackage of 3 GB, so only ``setup_cards`` is run here, extracted from the source, with
stand-ins for the cards: it must keep going while a card waits (the setup gained a step in November 2026, which a
count of five cards left unanswered), put the caption and the ticks of the layout on the card that asks it only, and
stop when the cards are over."""
import ast
from pathlib import Path
from types import SimpleNamespace

import pytest

pytestmark = pytest.mark.unit

SOURCE = Path(__file__).resolve().parents[2] / "scripts" / "site_videos.py"


def _setup_cards():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    nodes = [item for item in tree.body
             if (isinstance(item, ast.FunctionDef) and item.name == "setup_cards")
             or (isinstance(item, ast.Assign) and any(getattr(target, "id", None) == "SETUP_CARDS"
                                                      for target in item.targets))]
    namespace = {}
    exec(compile(ast.Module(nodes, []), str(SOURCE), "exec"), namespace)  # noqa: S102 - the source of the repository
    namespace.setdefault("SETUP_CARDS", ())
    return namespace


def _run(cards):
    """Play the clip as run_steps does: the step at ``RUN['at']`` runs, the steps it inserts follow it."""
    state = SimpleNamespace(cards=list(cards), answered=[], captions=[], unticked=[])
    namespace = _setup_cards()
    before, after = (lambda: None), (lambda: None)
    steps = [(0, before), (0, namespace["setup_cards"]()), (0, after)]

    def answer(card):
        def run():
            state.answered.append(card)
            state.cards.pop(0)
        return (0, run)

    def setup_card(untick=()):
        card = state.cards[0] if state.cards else None
        state.unticked.append(tuple(untick))
        return [answer(card)] if card is not None else []

    namespace.update(
        STEPS=steps, RUN={"at": 1}, wizard_card=lambda: state.cards[0] if state.cards else None,
        card_button=lambda label: object() if state.cards and label in state.cards[0] else None,
        caption=lambda text: (0, lambda: state.captions.append(text)), setup_card=setup_card)
    index = 1
    while index < len(steps):
        namespace["RUN"]["at"] = index
        steps[index][1]()
        index += 1
    state.edges = (before, after)
    return state, steps


@pytest.mark.parametrize("count", [0, 1, 5, 6, 9])
def test_every_card_of_the_setup_is_answered_whatever_their_number(count):
    cards = [("step %d" % number,) for number in range(count)]
    state, steps = _run(cards)
    assert state.answered == cards and state.cards == []
    assert steps[0][1] is state.edges[0] and steps[-1][1] is state.edges[1]  # what follows the cards still follows them


def test_a_card_of_setup_cards_gets_its_caption_and_its_unticks_the_others_none():
    marked = _setup_cards()["SETUP_CARDS"]
    assert marked, "SETUP_CARDS lists the cards the take explains"
    marker, text, labels = marked[0]
    state, _steps = _run([("features", marker), ("look",), ("other",)])
    assert state.captions == [text]
    assert state.unticked == [tuple(labels), (), ()]
    assert len(state.answered) == 3
