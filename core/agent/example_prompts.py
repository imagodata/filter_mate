# -*- coding: utf-8 -*-
"""The requests offered on the welcome of AGENT: a catalog over the sources of the agent, drawn at random.

Plain Python, no QGIS. Each new conversation shows a few requests drawn from the catalog: one about the layers of the
project, the others each from another kind of source (elevation, OpenStreetMap, population, basemaps, open data...),
none of the set shown before when the catalog allows it. A request about the data of one country (IGN, Géorisques,
GovData...) is drawn only when the locale of QGIS points to that country. The words are in ui/widgets/agent_panel.py
(``example_text``), translated; here, only their keys.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import FrozenSet, Iterable, List, Optional, Sequence, Tuple

PROJECT = "project"  # about the layers already in the project
DATA = "data"  # brings data in from a source of the agent

SHOWN = 4  # requests on the welcome


@dataclass(frozen=True)
class Example:
    """One request: its key, what it is about (``PROJECT`` or ``DATA``), its kind, and the countries it needs."""

    key: str
    group: str
    kind: str
    regions: Tuple[str, ...] = ()  # empty: anywhere


CATALOG: Tuple[Example, ...] = (
    Example("layers", PROJECT, "layers"),
    Example("fields", PROJECT, "layers"),
    Example("tall_buildings", PROJECT, "filter"),
    Example("roads_inside", PROJECT, "filter"),
    Example("visible", PROJECT, "filter"),
    Example("color_by", PROJECT, "style"),
    Example("labels", PROJECT, "style"),
    Example("export_gpkg", PROJECT, "export"),
    Example("relief", DATA, "elevation"),
    Example("elevation_view", DATA, "elevation"),
    Example("people_selected", DATA, "population"),
    Example("population_grid", DATA, "population"),
    Example("osm_cafes", DATA, "osm"),
    Example("osm_cycle", DATA, "osm"),
    Example("osm_trees", DATA, "osm"),
    Example("dark_basemap", DATA, "basemap"),
    Example("sentinel", DATA, "satellite"),
    Example("zoom_park", DATA, "places"),
    Example("ods_toilets", DATA, "open_data"),
    Example("eurostat", DATA, "statistics"),
    Example("fr_communes", DATA, "open_data", ("fr",)),
    Example("fr_bikes", DATA, "open_data", ("fr",)),
    Example("fr_buildings", DATA, "reference", ("fr",)),
    Example("fr_photos_1950", DATA, "imagery", ("fr",)),
    Example("fr_flood", DATA, "risks", ("fr",)),
    Example("fr_clay", DATA, "risks", ("fr",)),
    Example("fr_town_hall", DATA, "places", ("fr",)),
    Example("gb_flood", DATA, "open_data", ("gb",)),
    Example("ca_parks", DATA, "open_data", ("ca",)),
    Example("au_bushfire", DATA, "open_data", ("au",)),
    Example("de_charging", DATA, "open_data", ("de",)),
    Example("it_schools", DATA, "open_data", ("it",)),
    Example("nl_bike_parking", DATA, "open_data", ("nl",)),
    Example("jp_shelters", DATA, "open_data", ("jp",)),
    Example("br_municipalities", DATA, "reference", ("br",)),
    Example("pl_municipalities", DATA, "reference", ("pl",)),
)
KEYS: Tuple[str, ...] = tuple(example.key for example in CATALOG)
_COUNTRIES = frozenset(region for example in CATALOG for region in example.regions)
# A language that is spoken in one of these countries mostly: "fr" alone is France, "fr_CA" is Canada.
_LANGUAGE_COUNTRY = {"fr": "fr", "de": "de", "it": "it", "nl": "nl", "ja": "jp", "pl": "pl"}


def regions(locale: str) -> FrozenSet[str]:
    """The countries a locale of QGIS points to: ``fr_FR`` and ``fr`` give France, ``en_GB`` the United Kingdom,
    ``pt_BR`` Brazil, ``fr_CA`` Canada only, ``en`` and ``en_US`` none of the catalog."""
    text = str(locale or "").replace("-", "_").split(".")[0].split("@")[0].strip()
    language, *rest = text.split("_")
    # The country is the part of two letters after the language: a script comes between them (``zh_Hans_CN``).
    countries = [part.lower() for part in rest if len(part) == 2 and part.isalpha()]
    if countries:
        country = "gb" if countries[-1] == "uk" else countries[-1]
        return frozenset({country} & _COUNTRIES)
    if rest:  # a region the catalog cannot read (``es_419``): no country
        return frozenset()
    found = _LANGUAGE_COUNTRY.get(language.lower())
    return frozenset({found}) if found else frozenset()


def eligible(locale: str) -> Tuple[Example, ...]:
    """The requests that can be offered under this locale."""
    here = regions(locale)
    return tuple(example for example in CATALOG if not example.regions or set(example.regions) & here)


def pick(locale: str, previous: Iterable[str] = (), count: int = SHOWN,
         rng: Optional[random.Random] = None) -> Tuple[str, ...]:
    """The keys of ``count`` requests for a new conversation, in a random order.

    One is about the project, the others bring data in, each of another kind; none was in ``previous`` (the set shown
    before) when enough are left without them. A request about the data of the country of the locale always takes one
    of the places, even one shown in the set before when it is the only one of its country."""
    rng = rng or random.Random()  # nosec B311 - which requests are shown, nothing secret
    seen = set(previous)
    offered = eligible(locale)
    fresh = [example for example in offered if example.key not in seen]
    pool = fresh if len(fresh) >= count else list(offered)
    chosen: List[Example] = []

    def take(candidates: Sequence[Example]) -> None:
        kinds = {example.kind for example in chosen}
        left = [example for example in candidates if example not in chosen and example.kind not in kinds]
        if not left:
            left = [example for example in candidates if example not in chosen]
        if left and len(chosen) < count:
            chosen.append(rng.choice(left))

    take([example for example in pool if example.group == PROJECT])
    # The country of the locale always has its place, even when its only request was in the set before.
    take([example for example in pool if example.regions] or [example for example in offered if example.regions])
    while len(chosen) < count:
        before = len(chosen)
        take([example for example in pool if example.group == DATA] or pool)
        if len(chosen) == before:
            take(pool)
        if len(chosen) == before:
            break
    rng.shuffle(chosen)
    return tuple(example.key for example in chosen)
