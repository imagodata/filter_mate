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
    node = next(item for item in tree.body if isinstance(item, ast.FunctionDef) and item.name == "setup_cards")
    namespace = {}
    exec(compile(ast.Module([node], []), str(SOURCE), "exec"), namespace)  # noqa: S102 - the source of the repository
    return namespace


def _run(cards):
    """Play the clip as run_steps does: the step at ``RUN['at']`` runs, the steps it inserts follow it."""
    state = SimpleNamespace(cards=list(cards), answered=[], captions=[])
    namespace = _setup_cards()
    before, after = (lambda: None), (lambda: None)
    steps = [(0, before), (0, namespace["setup_cards"]()), (0, after)]

    def answer(card):
        def run():
            state.answered.append(card)
            state.cards.pop(0)
        return (0, run)

    def setup_card(layout=False):
        card = state.cards[0] if state.cards else None
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


def test_the_caption_of_the_layout_comes_with_the_card_that_asks_it_only():
    state, _steps = _run([("features",), ("look",), ("layout", "In panels of QGIS"), ("exploring",), ("exporting",)])
    assert state.captions == ["3 · The layout: sections in panels, buttons under each"]
    assert len(state.answered) == 5
