# -*- coding: utf-8 -*-
"""The questions the agent asks the user with ``ask_user``: what a question may hold, and the answer's shape.

Plain Python, like the skills: the card of the panel draws what this module cleaned, and the model reads what
it builds. An answer is data for the model, never an agreement: an action that follows still goes through the
permissions.
"""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from typing import Any, Dict, List, Sequence, Tuple

MAX_QUESTIONS = 4
MIN_OPTIONS = 2
MAX_OPTIONS = 4
MAX_QUESTION = 300
MAX_HEADER = 12
MAX_LABEL = 60
MAX_DESCRIPTION = 200
MAX_OTHER = 1000  # the free text of "Other": a data, never an instruction

# Format characters (joiners, direction marks) that a written language needs: kept, as in the skills from elsewhere.
_KEPT_FORMAT = {"\u200c", "\u200d", "\u061c"}


@dataclass(frozen=True)
class Option:
    """One choice of a question: its label, and what choosing it means."""

    label: str
    description: str = ""


@dataclass(frozen=True)
class Question:
    """One question of a card: a short header, the text, its options, one answer or several."""

    header: str
    question: str
    options: Tuple[Option, ...]
    multi_select: bool = False


def _clean(value: Any, limit: int) -> str:
    """``value`` as one line the user reads as the model wrote it: blanks in single spaces, nothing invisible."""
    text = "".join(char for char in str(value) if unicodedata.category(char) != "Cf" or char in _KEPT_FORMAT)
    return " ".join(text.split())[:limit].strip()


def parse_questions(value: Any) -> List[Question]:
    """The questions of an ``ask_user`` call, cleaned and bounded; ``ValueError`` says what the model must fix.

    The executor already checked the schema of the tool; this is the same reading, for a caller that would not,
    and the one place the bounds live beside the schema.
    """
    if not isinstance(value, list) or not value:
        raise ValueError("questions: one to four questions")
    if len(value) > MAX_QUESTIONS:
        raise ValueError(f"questions: at most {MAX_QUESTIONS}")
    questions = []
    for position, item in enumerate(value):
        where = f"questions[{position}]"
        if not isinstance(item, dict):
            raise ValueError(f"{where}: a question is an object")
        question = _clean(item.get("question", ""), MAX_QUESTION)
        if not question:
            raise ValueError(f"{where}.question: required")
        header = _clean(item.get("header", ""), MAX_HEADER)
        if not header:
            raise ValueError(f"{where}.header: required")
        multi = item.get("multi_select", False)
        if not isinstance(multi, bool):
            raise ValueError(f"{where}.multi_select: true or false")
        raw_options = item.get("options")
        if not isinstance(raw_options, list) or not MIN_OPTIONS <= len(raw_options) <= MAX_OPTIONS:
            raise ValueError(f"{where}.options: {MIN_OPTIONS} to {MAX_OPTIONS} options")
        options, labels = [], set()
        for index, raw in enumerate(raw_options):
            if not isinstance(raw, dict):
                raise ValueError(f"{where}.options[{index}]: an option is an object")
            label = _clean(raw.get("label", ""), MAX_LABEL)
            if not label:
                raise ValueError(f"{where}.options[{index}].label: required")
            if label.casefold() in labels:
                raise ValueError(f"{where}.options: two options are called {label!r}")
            labels.add(label.casefold())
            options.append(Option(label, _clean(raw.get("description", ""), MAX_DESCRIPTION)))
        questions.append(Question(header, question, tuple(options), multi))
    return questions


def answers_payload(questions: Sequence[Question], chosen: Sequence[Tuple[Sequence[str], str]]) -> Dict[str, Any]:
    """What the model reads of the card, one entry per question, in their order.

    ``chosen`` holds, per question, the labels ticked and the text of "Other" ("" when unused); a label the
    question did not offer is dropped, the free text is bounded here too.
    """
    answers = []
    for question, (selected, other) in zip(questions, chosen):
        offered = {option.label for option in question.options}
        entry: Dict[str, Any] = {"header": question.header, "question": question.question,
                                 "selected": [label for label in selected if label in offered]}
        other = _clean(other, MAX_OTHER)
        if other:
            entry["other"] = other
        answers.append(entry)
    return {"answers": answers}
