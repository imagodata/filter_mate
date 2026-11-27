"""Discovery requests stay geographically coherent, varied and bounded, without a provider or network."""
import random

import pytest

from core.agent.example_places import PLACES, draw_places, view_place
from core.agent.example_prompts import CATALOG, Facts, pick


def test_worldwide_draws_bind_every_recipe_to_a_real_compatible_place():
    catalog = {example.key: example for example in CATALOG}
    recent = []
    rng = random.Random(42)
    for _ in range(100):
        keys = pick('fr_FR', facts=Facts(known=True), rng=rng)
        bound = draw_places([catalog[key] for key in keys], recent, rng=rng)
        assert len(bound) == len({p.id for p in bound.values()}) == 4
        assert len({p.continent for p in bound.values()}) >= 2
        assert all(not catalog[key].regions or place.country in catalog[key].regions for key, place in bound.items())
        assert all(place in PLACES and 1 <= place.radius <= 10 for place in bound.values())
        assert all(-180 <= p.longitude <= 180 and -90 <= p.latitude <= 90 for p in bound.values())
        # The immediately preceding destinations are avoidable, including the limited national sources.
        # Longer history may be exhausted for a country, in which case compatible destinations win.
        recent = [p.id for p in bound.values()]


def test_location_variety_includes_cities_countryside_mountains_and_coasts():
    examples = [example for example in CATALOG if example.key in ('osm_cycle', 'osm_trees', 'population_grid', 'sentinel')]
    bound = draw_places(examples, rng=random.Random(8))
    assert {place.landscape for place in bound.values()} == {'city', 'rural', 'mountain', 'coast'}
    assert len({place.continent for place in bound.values()}) == 4
    assert len({place.country for place in bound.values()}) == 4


def test_recent_places_are_avoided_and_unrelated_updates_keep_the_destinations():
    examples = [example for example in CATALOG if example.key in ('osm_cycle', 'population_grid', 'relief', 'sentinel')]
    before = draw_places(examples, rng=random.Random(2))
    recent = [p.id for p in before.values()]
    assert draw_places(examples, recent, current=before, rng=random.Random(9)) == before
    after = draw_places(examples, recent, rng=random.Random(4))
    assert not set(recent) & {p.id for p in after.values()}
    assert after['relief'].landscape in ('rural', 'mountain')


def test_an_old_project_view_is_not_reused_as_a_discovery_destination():
    example = next(example for example in CATALOG if example.key == 'osm_cycle')
    old = view_place((31.01, -0.12, 31.03, -0.10))
    places = draw_places([example], current={example.key: old}, rng=random.Random(2))
    assert places[example.key] in PLACES and not places[example.key].id.startswith('view:')


@pytest.mark.parametrize('bounds', [(-180, -85, 180, 85), (0, 0, 0, 0), (2, 2, 1, 1),
                                   (0, -91, 1, -90), (179, -1, 181, 1), (0, 0, float('nan'), 1)])
def test_invalid_or_world_views_are_not_a_focus(bounds):
    assert view_place(bounds) is None


def test_a_map_focus_keeps_actual_coordinates_instead_of_inventing_a_town():
    focus = view_place((31.01, -0.12, 31.03, -0.10))
    assert focus is not None and focus.country == ''
    assert 'WGS 84' in focus.label and '31.020' in focus.label
    kyoto = view_place((135.76, 35.00, 135.78, 35.02))
    assert kyoto.country == 'jp' and 'Kyoto' in kyoto.label
    assert '135.770' in kyoto.label
