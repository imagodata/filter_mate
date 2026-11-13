# -*- coding: utf-8 -*-
"""ask_user (lot D): the questions parsed and bounded, the shape of the answer (core/agent/questions.py)."""
import pytest

from core.agent.questions import (
    MAX_HEADER, MAX_OTHER, MAX_QUESTION, Option, Question, answers_payload, parse_questions,
)
from core.agent.tool_catalog import ASK_USER, FILTERING_TOOLS, chat_tools

pytestmark = pytest.mark.unit


def _question(**changes):
    question = {"question": "Which roads?", "header": "Roads", "multi_select": False,
                "options": [{"label": "Main only", "description": "The classified network"},
                            {"label": "All", "description": ""}]}
    question.update(changes)
    return question


class TestParseQuestions:
    def test_a_plain_question(self):
        assert parse_questions([_question()]) == [
            Question("Roads", "Which roads?", (Option("Main only", "The classified network"), Option("All")), False)]

    def test_multi_select_and_four_questions(self):
        parsed = parse_questions([_question(multi_select=True)] * 4)
        assert len(parsed) == 4 and all(question.multi_select for question in parsed)

    @pytest.mark.parametrize("value, message", [
        (None, "one to four"), ([], "one to four"), ("Which?", "one to four"),
        ([_question()] * 5, "at most 4"),
        (["Which?"], "a question is an object"),
        ([_question(question="  ")], "question: required"),
        ([_question(header="")], "header: required"),
        ([_question(multi_select="yes")], "multi_select: true or false"),
        ([_question(options=[{"label": "One"}])], "2 to 4 options"),
        ([_question(options=[{"label": str(n)} for n in range(5)])], "2 to 4 options"),
        ([_question(options=["One", "Two"])], "an option is an object"),
        ([_question(options=[{"label": ""}, {"label": "Two"}])], "label: required"),
        ([_question(options=[{"label": "Same"}, {"label": "same"}])], "two options are called"),
    ])
    def test_refused(self, value, message):
        with pytest.raises(ValueError, match=message):
            parse_questions(value)

    def test_cleaned_to_one_line_and_bounded(self):
        parsed = parse_questions([_question(question=" Which\n  roads\t here? " + "x" * 400,
                                            header="  My very long header  ")])
        assert parsed[0].question.startswith("Which roads here?") and len(parsed[0].question) <= MAX_QUESTION
        assert len(parsed[0].header) <= MAX_HEADER and "\n" not in parsed[0].header

    def test_invisible_characters_are_dropped(self):
        parsed = parse_questions([_question(question="Which\u200broads\u202e?")])
        assert parsed[0].question == "Whichroads?"


class TestAnswersPayload:
    def test_selected_labels_and_other(self):
        questions = parse_questions([_question(), _question(header="Look", question="Which look?")])
        payload = answers_payload(questions, [(["All"], ""), ([], "the dark one")])
        assert payload == {"answers": [
            {"header": "Roads", "question": "Which roads?", "selected": ["All"]},
            {"header": "Look", "question": "Which look?", "selected": [], "other": "the dark one"}]}

    def test_a_label_the_question_did_not_offer_is_dropped_and_other_is_bounded(self):
        questions = parse_questions([_question()])
        payload = answers_payload(questions, [(["Forged"], "y" * (MAX_OTHER + 50))])
        assert payload["answers"][0]["selected"] == [] and len(payload["answers"][0]["other"]) == MAX_OTHER


class TestCatalogEntry:
    def test_neither_served_to_another_application_nor_kept_in_a_recipe(self):
        # The MCP bridge serves the tools that are neither chat_only nor history (agent_mcp_bridge); a recipe
        # keeps no read-only chat-only call (recipes.kept): asking cannot be replayed without the user.
        from core.agent.recipes import kept, steps_of
        tools = {tool.name: tool for tool in chat_tools()}
        served = [tool for tool in chat_tools() if not tool.manages_history and not tool.chat_only]
        assert ASK_USER not in {tool.name for tool in served}
        assert not kept(ASK_USER, tools[ASK_USER], failed=False)
        assert steps_of([(ASK_USER, {"questions": []}, False, "Ask the user")], tools) == []

    def test_ask_user_is_a_chat_tool_kept_for_a_local_model(self):
        tools = {tool.name: tool for tool in chat_tools()}
        spec = tools[ASK_USER]
        assert spec.chat_only and spec.read_only and not spec.requires_confirmation
        assert ASK_USER in FILTERING_TOOLS
        questions = spec.input_schema["properties"]["questions"]
        assert (questions["minItems"], questions["maxItems"]) == (1, 4)
        option = questions["items"]["properties"]["options"]
        assert (option["minItems"], option["maxItems"]) == (2, 4)
