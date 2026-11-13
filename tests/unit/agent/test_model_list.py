# -*- coding: utf-8 -*-
"""The chat models of a provider, read from the answer of its list of models."""
import json

import pytest

from core.agent.providers.model_list import KEY_PAGES, MAX_LISTED_MODELS, listing_url, models_from_listing

pytestmark = pytest.mark.unit


def test_chat_models_only():
    openai = b'{"data":[{"id":"gpt-x"},{"id":"gpt-x-mini"},{"id":"text-embedding-3-large"},{"id":"tts-1"},' \
             b'{"id":"whisper-1"},{"id":"dall-e-3"},{"id":"omni-moderation-latest"},{"id":"gpt-image-1"}]}'
    assert models_from_listing("openai_compatible", openai) == ("gpt-x", "gpt-x-mini")


def test_mistral_keeps_chat_capable_models():
    mistral = b'{"data":[{"id":"mistral-small-latest","capabilities":{"completion_chat":true}},' \
              b'{"id":"mistral-embed","capabilities":{"completion_chat":false}}]}'
    assert models_from_listing("openai_compatible", mistral) == ("mistral-small-latest",)


def test_a_model_without_capabilities_is_kept():
    assert models_from_listing("openai_compatible", b'{"data":[{"id":"a"},{"id":"b","capabilities":{}}]}') == ("a", "b")


def test_a_chat_incapable_model_is_dropped_for_every_listing():
    data = b'{"data":[{"id":"a","capabilities":{"completion_chat":false}},{"id":"b"}]}'
    assert models_from_listing("anthropic", data) == ("b",)


def test_anthropic_listing():
    data = b'{"data":[{"id":"claude-haiku-5-5","type":"model"}]}'
    assert models_from_listing("anthropic", data) == ("claude-haiku-5-5",)


@pytest.mark.parametrize("data", [b"<html>", b"", b"[]", b'{"data":"x"}', b'{"data":[1,null,{"id":3},{"id":""}]}',
                                  b"\xff\xfe", b'{"models":[{"id":"a"}]}'])
def test_unreadable_listing_is_empty(data):
    assert models_from_listing("anthropic", data) == ()


def test_order_is_kept_and_duplicates_dropped():
    assert models_from_listing("openai_compatible", b'{"data":[{"id":"b"},{"id":"a"},{"id":"b"}]}') == ("b", "a")


def test_at_most_as_many_models_as_ollama_lists():
    data = json.dumps({"data": [{"id": f"m{index}"} for index in range(MAX_LISTED_MODELS + 20)]}).encode()
    assert len(models_from_listing("openai_compatible", data)) == MAX_LISTED_MODELS == 50


def test_the_newest_models_come_first_before_the_cap():
    """OpenAI lists in no order, and more than 50 models: the cut must keep the recent ones."""
    entries = [{"id": f"old{index}", "created": 1_600_000_000 + index} for index in range(MAX_LISTED_MODELS + 10)]
    entries.insert(5, {"id": "gpt-new", "created": 1_900_000_000})
    entries.insert(9, {"id": "no-date"})
    models = models_from_listing("openai_compatible", json.dumps({"data": entries}).encode())
    assert len(models) == MAX_LISTED_MODELS and models[0] == "gpt-new" and models[1] == f"old{MAX_LISTED_MODELS + 9}"
    assert "no-date" not in models  # an entry without a date comes after the dated ones


def test_the_order_of_a_list_without_dates_is_kept():
    data = b'{"data":[{"id":"b","created":"x"},{"id":"a"},{"id":"c","created":true}]}'
    assert models_from_listing("openai_compatible", data) == ("b", "a", "c")


@pytest.mark.parametrize("name", ["sora-2", "babbage-002", "davinci-002", "gpt-4o-mini-tts", "omni-moderation-latest"])
def test_models_that_do_not_chat_are_dropped(name):
    assert models_from_listing("openai_compatible", json.dumps({"data": [{"id": name}, {"id": "gpt-x"}]}).encode()) \
        == ("gpt-x",)


def test_key_pages_are_https():
    assert set(KEY_PAGES) == {"anthropic", "mistral", "openai"}
    assert all(url.startswith("https://") for url in KEY_PAGES.values())


def test_ollama_listing_is_its_tags_answer():
    tags = (b'{"models":[{"name":"qwen3:4b","details":{"family":"qwen3"}},'
            b'{"name":"nomic-embed-text","details":{"family":"nomic-bert"}}]}')
    assert models_from_listing("ollama", tags) == ("qwen3:4b",)


@pytest.mark.parametrize("kind, base, url", [
    ("anthropic", "https://api.anthropic.com", "https://api.anthropic.com/v1/models?limit=100"),
    ("anthropic", "https://relay.example.com/", "https://relay.example.com/v1/models?limit=100"),
    ("openai_compatible", "https://api.mistral.ai/v1", "https://api.mistral.ai/v1/models"),
    ("openai_compatible", "https://api.openai.com/v1/", "https://api.openai.com/v1/models"),
    ("ollama", "http://localhost:11434", "http://localhost:11434/api/tags"),
    ("ollama", "http://localhost:11434/v1", "http://localhost:11434/api/tags")])
def test_listing_url(kind, base, url):
    assert listing_url(kind, base) == url


def test_an_id_that_is_too_long_or_holds_a_control_character_is_dropped():
    data = json.dumps({"data": [{"id": "x" * 201}, {"id": "ok" + "\x1b[31m"}, {"id": "bad\nline"}, {"id": "x" * 200},
                                {"id": "fine"}]}).encode()
    assert models_from_listing("openai_compatible", data) == ("x" * 200, "fine")


def test_a_mistral_model_that_cannot_call_functions_is_dropped():
    data = json.dumps({"data": [
        {"id": "mistral-small-latest", "capabilities": {"completion_chat": True, "function_calling": True}},
        {"id": "no-tools", "capabilities": {"completion_chat": True, "function_calling": False}},
        {"id": "unsaid", "capabilities": {"completion_chat": True}}]}).encode()
    assert models_from_listing("openai_compatible", data) == ("mistral-small-latest", "unsaid")
