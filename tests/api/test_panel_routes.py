"""The routes of the options of FilterMate's panels, on the in-memory accessor (2026-11-16, review: they answered 500)."""


def test_layer_options_set_then_read(client, sample_layers):
    name = sample_layers[0].name
    answer = client.post("/panels/layer", json={"layers": [{"layer": name, "exploring": {"is_tracking": True}}]})
    assert answer.status_code == 200, answer.text
    assert answer.json()["changed"][0]["layer_name"] == name
    read = client.get("/panels/layer", params={"layer": name})
    assert read.status_code == 200 and read.json()["exploring"] == {"is_tracking": True}


def test_export_options_set_then_read(client):
    assert client.post("/panels/export", json={"changes": {"batch_zip": True}}).status_code == 200
    assert client.get("/panels/export").json()["batch_zip"] is True


def test_an_unknown_layer_is_a_bad_request(client):
    assert client.post("/panels/layer", json={"layers": [{"layer": "nowhere"}]}).status_code == 400


def test_map_context_did_not_grow(accessor):
    from dataclasses import asdict
    assert "panel_layers" not in asdict(accessor.map_context()) and "export_panel" not in asdict(accessor.map_context())
