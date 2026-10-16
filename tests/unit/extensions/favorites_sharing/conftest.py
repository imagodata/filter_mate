# -*- coding: utf-8 -*-
"""Shared fixtures for the favorites sharing tests."""
import pytest


@pytest.fixture(autouse=True)
def _local_test_remotes(monkeypatch):
    """The git tests use bare repos in ``tmp_path`` as remotes: let git reach them.

    In production git only talks https and ssh (``git_client.ALLOWED_PROTOCOLS``):
    a local path is the ``file`` transport, refused there.
    """
    from extensions.favorites_sharing import git_client
    monkeypatch.setattr(git_client, "ALLOWED_PROTOCOLS", git_client.ALLOWED_PROTOCOLS + ":file")
