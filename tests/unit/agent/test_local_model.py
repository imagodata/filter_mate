# -*- coding: utf-8 -*-
"""Whether the model of the agent runs on this computer (core/agent/local_model.py)."""
import pytest

from core.agent.local_model import runs_on_this_computer

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("preset, address", [("ollama", ""), ("ollama", "http://localhost:11434"),
                                             ("ollama", "http://127.0.0.1:11434/v1"), ("ollama", "localhost:11434"),
                                             ("ollama", "http://[::1]:11434")])
def test_local(preset, address):
    assert runs_on_this_computer(preset, address)


@pytest.mark.parametrize("preset, address", [("ollama", "http://192.168.1.20:11434"), ("ollama", "https://gpu.example"),
                                             ("anthropic", ""), ("mistral", "http://localhost:8080"),
                                             ("ollama", "http://[bad")])
def test_not_local(preset, address):
    assert not runs_on_this_computer(preset, address)


@pytest.mark.parametrize("address", ["http://127.0.0.1.evil.example:11434", "http://127.1:11434.evil.example",
                                     "http://localhost.evil.example"])
def test_a_host_that_only_starts_like_loopback_is_not_local(address):
    """Audit of 2026-11-24: test startswith("127.") failed open."""
    assert not runs_on_this_computer("ollama", address)


@pytest.mark.parametrize("model", ["qwen3:cloud", "my-cloud-model", "CLOUD", "cloud/bespoke"])
def test_a_cloud_model_through_a_local_ollama_is_not_local(model):
    """Audit of 2026-11-24: the banner promises nothing is sent to an AI service."""
    assert not runs_on_this_computer("ollama", "http://localhost:11434", model)


@pytest.mark.parametrize("model", ["llama3.1", "qwen3-coder", "mistral-small", "cloudy-daydream"])
def test_a_local_model_name_keeps_the_banner(model):
    assert runs_on_this_computer("ollama", "http://localhost:11434", model)
