# -*- coding: utf-8 -*-
"""The requests of the welcome of AGENT: drawn at random over the sources, never the same set twice in a row."""
import random
import re
from pathlib import Path

import pytest

from core.agent import example_prompts as ex

PANEL = Path(__file__).resolve().parents[3] / "ui" / "widgets" / "agent_panel.py"


def _by_key():
    return {example.key: example for example in ex.CATALOG}


def test_keys_are_unique_and_every_one_has_its_words_in_the_panel():
    assert len(set(ex.KEYS)) == len(ex.KEYS)
    words = dict(re.findall(r'^\s+"(\w+)": _tr\("([^"]+)"\),$', PANEL.read_text(encoding="utf-8"), re.MULTILINE))
    assert set(words) == set(ex.KEYS)
    assert all(len(text) <= 45 for text in words.values()), "a request must fit on one button of the dock"


@pytest.mark.parametrize("locale, expected", [
    ("fr_FR", {"fr"}), ("fr", {"fr"}), ("fr_CA", {"ca"}), ("en_GB", {"gb"}), ("en_UK", {"gb"}), ("pt_BR", {"br"}),
    ("pt_PT", set()), ("de_DE", {"de"}), ("de", {"de"}), ("de_AT", set()), ("ja", {"jp"}), ("en", set()),
    ("en_US", set()), ("", set()), ("en-AU", {"au"}), (None, set()), ("C", set()), ("C.UTF-8", set()),
    ("fr_FR.UTF-8", {"fr"}), ("fr_FR@euro", {"fr"}), ("hi_Deva_IN", set()), ("ja_Jpan_JP", {"jp"}),
    ("zh_Hans_CN", set()), ("es_419", set()), ("uk_UA", set()), ("fr_419", set()),
])
def test_regions_of_a_locale(locale, expected):
    assert ex.regions(locale) == expected


def test_a_country_request_is_offered_only_in_its_country():
    keys = {example.key for example in ex.eligible("en_US")}
    assert not any(ex.CATALOG[ex.KEYS.index(key)].regions for key in keys)
    assert "fr_flood" in {example.key for example in ex.eligible("fr_FR")}
    assert "fr_flood" not in {example.key for example in ex.eligible("de_DE")}


@pytest.mark.parametrize("locale", ["fr_FR", "en_US", "en_GB", "ja_JP", "pt_BR", "zz"])
def test_a_set_is_one_project_request_and_data_of_other_kinds(locale):
    catalog = _by_key()
    for seed in range(200):
        keys = ex.pick(locale, rng=random.Random(seed))
        assert len(keys) == ex.SHOWN == len(set(keys))
        picked = [catalog[key] for key in keys]
        assert [example.group for example in picked].count(ex.PROJECT) == 1
        kinds = [example.kind for example in picked]
        assert len(set(kinds)) == len(kinds)
        here = ex.regions(locale)
        assert all(not example.regions or set(example.regions) & here for example in picked)


@pytest.mark.parametrize("locale", ["fr_FR", "en_GB", "en_CA", "en_AU", "de_DE", "it_IT", "nl_NL", "ja_JP", "pt_BR",
                                    "pl_PL", "fr_CA"])
def test_a_country_of_the_catalog_gets_one_of_its_requests_in_every_set(locale):
    catalog = _by_key()
    here = ex.regions(locale)
    rng = random.Random(5)
    previous = ()
    for _ in range(200):
        keys = ex.pick(locale, previous, rng=rng)
        assert any(set(catalog[key].regions) & here for key in keys)
        assert len(keys) == ex.SHOWN == len(set(keys))
        previous = keys


@pytest.mark.parametrize("locale", ["fr_FR", "en_US", "en_GB"])
def test_the_next_set_shares_nothing_with_the_one_before_but_the_only_request_of_a_country(locale):
    catalog = _by_key()
    alone = sum(1 for example in ex.eligible(locale) if example.regions) == 1
    rng = random.Random(7)
    previous = ex.pick(locale, rng=rng)
    for _ in range(300):
        keys = ex.pick(locale, previous, rng=rng)
        assert all(alone and catalog[key].regions for key in set(keys) & set(previous))
        previous = keys


def test_sets_vary():
    rng = random.Random(3)
    assert len({ex.pick("en_US", rng=rng) for _ in range(50)}) > 30
    assert len({key for _ in range(200) for key in ex.pick("en_US", rng=rng)}) == len(ex.eligible("en_US"))


def test_unknown_previous_keys_are_ignored():
    keys = ex.pick("en", ["", "gone", "layers"], rng=random.Random(1))
    assert "layers" not in keys and len(keys) == ex.SHOWN
