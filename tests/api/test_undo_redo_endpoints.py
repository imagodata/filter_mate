# -*- coding: utf-8 -*-
"""Issue #33 — POST /filters/undo and /filters/redo contract tests."""
from __future__ import annotations


def _apply(client, layer: str, expr: str) -> None:
    response = client.post(
        "/filters/apply",
        json={"layer_name": layer, "expression": expr},
    )
    assert response.status_code == 200


class TestUndo:
    def test_undo_with_empty_history_returns_409(self, client):
        response = client.post("/filters/undo")
        assert response.status_code == 409
        assert "undo" in response.json()["detail"].lower()

    def test_undo_after_single_apply_clears_filter(self, client):
        _apply(client, "communes", '"x" = 1')
        response = client.post("/filters/undo")
        assert response.status_code == 200

        body = response.json()
        # The step we rolled back TO had no expression — clear flag set.
        assert body["step"]["layer_name"] == "communes"
        assert body["step"]["is_clear"] is True
        assert body["active_filters"] == {}

    def test_undo_after_two_applies_restores_first(self, client):
        _apply(client, "communes", '"x" = 1')
        _apply(client, "communes", '"x" = 2')
        body = client.post("/filters/undo").json()

        assert body["step"]["expression"] == '"x" = 1'
        assert body["active_filters"] == {"communes": '"x" = 1'}

    def test_undo_empties_after_consuming_all_steps(self, client):
        _apply(client, "communes", '"x" = 1')
        client.post("/filters/undo")
        # Second undo on an empty stack — 409 again.
        assert client.post("/filters/undo").status_code == 409


class TestRedo:
    def test_redo_with_empty_stack_returns_409(self, client):
        response = client.post("/filters/redo")
        assert response.status_code == 409

    def test_redo_after_undo_restores_state(self, client):
        _apply(client, "communes", '"x" = 1')
        client.post("/filters/undo")  # back to empty
        response = client.post("/filters/redo")
        assert response.status_code == 200
        body = response.json()
        assert body["step"]["expression"] == '"x" = 1'
        assert body["active_filters"] == {"communes": '"x" = 1'}

    def test_apply_after_undo_clears_redo_branch(self, client):
        _apply(client, "communes", '"x" = 1')
        client.post("/filters/undo")
        # New apply invalidates the redo branch — matches typical text-editor
        # undo/redo semantics.
        _apply(client, "communes", '"x" = 99')
        assert client.post("/filters/redo").status_code == 409

    def test_undo_redo_round_trip_is_idempotent(self, client):
        _apply(client, "communes", '"x" = 1')
        _apply(client, "roads", '"y" = 2')
        before = client.get("/filters/status").json()["active_filters"]

        client.post("/filters/undo")
        client.post("/filters/redo")
        after = client.get("/filters/status").json()["active_filters"]

        assert after == before
