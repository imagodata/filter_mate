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
