# -*- coding: utf-8 -*-
"""Small offline gazetteer for welcome requests, not a geocoder or a source of country boundaries.

Coordinates are approximate centres. The radius bounds a discovery request, including in rural areas; a whole
country is never downloaded. Language does not choose the destination. No network or provider is needed to draw.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Iterable, Mapping, Optional, Sequence, Tuple


@dataclass(frozen=True)
class Place:
    id: str
    name: str
    country: str
    continent: str
    landscape: str
    longitude: float
    latitude: float
    radius: int = 5

    @property
    def label(self) -> str:
        # ISO country codes disambiguate names in every UI language.
        return f"{self.name} ({self.country.upper()})" if self.country and not self.id.startswith('view:') else self.name


PLACES: Tuple[Place, ...] = (
    Place('kyoto', 'Kyoto', 'jp', 'asia', 'city', 135.77, 35.01),
    Place('matsumoto', 'Matsumoto', 'jp', 'asia', 'mountain', 137.97, 36.24, 8),
    Place('pokhara', 'Pokhara', 'np', 'asia', 'mountain', 83.99, 28.21, 10),
    Place('hoi_an', 'Hội An', 'vn', 'asia', 'coast', 108.33, 15.88),
    Place('ubud', 'Ubud', 'id', 'asia', 'rural', 115.26, -8.51),
    Place('chiang_mai', 'Chiang Mai', 'th', 'asia', 'city', 98.99, 18.79),
    Place('pienza', 'Pienza', 'it', 'europe', 'rural', 11.68, 43.08, 8),
    Place('bologna', 'Bologna', 'it', 'europe', 'city', 11.34, 44.49),
    Place('die', 'Die', 'fr', 'europe', 'rural', 5.37, 44.75, 8),
    Place('annecy', 'Annecy', 'fr', 'europe', 'mountain', 6.13, 45.90, 8),
    Place('nantes', 'Nantes', 'fr', 'europe', 'city', -1.55, 47.22),
    Place('lyme_regis', 'Lyme Regis', 'gb', 'europe', 'coast', -2.94, 50.73),
    Place('york', 'York', 'gb', 'europe', 'city', -1.08, 53.96),
    Place('freiburg', 'Freiburg im Breisgau', 'de', 'europe', 'city', 7.85, 48.00),
    Place('spreewald', 'Lübbenau, Spreewald', 'de', 'europe', 'rural', 13.97, 51.87, 8),
    Place('utrecht', 'Utrecht', 'nl', 'europe', 'city', 5.12, 52.09),
    Place('giethoorn', 'Giethoorn', 'nl', 'europe', 'rural', 6.08, 52.72),
    Place('krakow', 'Kraków', 'pl', 'europe', 'city', 19.94, 50.06),
    Place('zakopane', 'Zakopane', 'pl', 'europe', 'mountain', 19.95, 49.30, 8),
    Place('ronda', 'Ronda', 'es', 'europe', 'rural', -5.16, 36.74, 8),
    Place('bergen', 'Bergen', 'no', 'europe', 'coast', 5.32, 60.39),
    Place('cuenca', 'Cuenca', 'ec', 'south_america', 'city', -79.00, -2.90),
    Place('cochamo', 'Cochamó', 'cl', 'south_america', 'mountain', -72.31, -41.49, 10),
    Place('salento', 'Salento', 'co', 'south_america', 'rural', -75.57, 4.64, 8),
    Place('paraty', 'Paraty', 'br', 'south_america', 'coast', -44.71, -23.22),
    Place('curitiba', 'Curitiba', 'br', 'south_america', 'city', -49.27, -25.43),
    Place('mendoza', 'Mendoza', 'ar', 'south_america', 'city', -68.85, -32.89),
    Place('quebec', 'Québec', 'ca', 'north_america', 'city', -71.21, 46.81),
    Place('baie_saint_paul', 'Baie-Saint-Paul', 'ca', 'north_america', 'rural', -70.50, 47.44, 8),
    Place('victoria', 'Victoria', 'ca', 'north_america', 'coast', -123.37, 48.43),
    Place('oaxaca', 'Oaxaca', 'mx', 'north_america', 'city', -96.73, 17.06),
    Place('sedona', 'Sedona', 'us', 'north_america', 'mountain', -111.76, 34.87, 8),
    Place('saint_louis', 'Saint-Louis', 'sn', 'africa', 'coast', -16.49, 16.03),
    Place('chefchaouen', 'Chefchaouen', 'ma', 'africa', 'mountain', -5.27, 35.17, 8),
    Place('arusha', 'Arusha', 'tz', 'africa', 'city', 36.68, -3.37),
    Place('cilaos', 'Cilaos, La Réunion', 're', 'africa', 'mountain', 55.47, -21.14, 8),
    Place('clarens', 'Clarens', 'za', 'africa', 'rural', 28.42, -28.52, 8),
    Place('hobart', 'Hobart', 'au', 'oceania', 'coast', 147.33, -42.88),
    Place('bright', 'Bright', 'au', 'oceania', 'rural', 146.96, -36.73, 8),
    Place('wellington', 'Wellington', 'nz', 'oceania', 'city', 174.78, -41.29),
    Place('wanaka', 'Wānaka', 'nz', 'oceania', 'mountain', 169.14, -44.70, 8),
)


def view_place(bounds: Sequence[float]) -> Optional[Place]:
    """Name a small, valid WGS84 map view; coordinates remain the anchor, never an inferred country boundary.

    World/default views, reversed extents and non-finite coordinates are not a geographical focus. Rounding avoids
    redrawing for a tiny pan. A nearby gazetteer entry is used only within its small discovery radius.
    """
    if len(bounds) != 4 or not all(math.isfinite(value) for value in bounds):
        return None
    west, south, east, north = bounds
    if not (-180 <= west < east <= 180 and -85 <= south < north <= 85):
        return None
    width = (east - west) * 111.32 * math.cos(math.radians((north + south) / 2))
    height = (north - south) * 111.32
    if max(width, height) > 100:
        return None
    lon, lat = round((west + east) / 2, 3), round((south + north) / 2, 3)
    radius = max(1, min(50, math.ceil(math.hypot(width, height) / 2)))
    # A name helps recognition, but the request always includes the actual centre of the view.
    nearby = min(PLACES, key=lambda p: (p.latitude - lat) ** 2 + ((p.longitude - lon) * math.cos(math.radians(lat))) ** 2)
    distance = math.hypot((nearby.longitude - lon) * math.cos(math.radians(lat)), nearby.latitude - lat) * 111.32
    label = f'{lat:.3f}, {lon:.3f} (WGS 84)'
    country = ''
    if distance + radius <= nearby.radius:
        label = f'{nearby.label}; {label}'
        country = nearby.country
    return Place(f'view:{lat}:{lon}:{radius}', label, country, '', '', lon, lat, radius)


def draw_places(examples: Sequence, previous: Iterable[str] = (), current: Optional[Mapping[str, Place]] = None,
                rng: Optional[random.Random] = None) -> dict:
    """Bind discovery recipes to compatible destinations. Keep bindings during unrelated project changes.

    Prefer new countries, continents and landscapes, and avoid recently seen destinations when possible. National
    data recipes travel only to their country. Relief favours hills; cafés favour towns.
    """
    rng = rng or random.Random()  # nosec B311 - welcome variety, not security
    seen, current = set(previous), current or {}
    chosen = {example.key: current[example.key] for example in examples
              if example.key in current and current[example.key] in PLACES
              and (not example.regions or current[example.key].country in example.regions)}
    for example in examples:
        if example.key in chosen:
            continue
        pool = [p for p in PLACES if not example.regions or p.country in example.regions]
        if example.key in ('relief', 'elevation_view'):
            pool = [p for p in pool if p.landscape in ('mountain', 'rural')]
        elif example.key == 'osm_cafes':
            pool = [p for p in pool if p.landscape == 'city']
        fresh = [p for p in pool if p.id not in seen and p.id not in {q.id for q in chosen.values()}]
        pool = fresh or [p for p in pool if p.id not in {q.id for q in chosen.values()}] or pool
        countries = {p.country for p in chosen.values()}
        continents = {p.continent for p in chosen.values()}
        landscapes = {p.landscape for p in chosen.values()}

        def score(place):
            return (place.continent not in continents, place.country not in countries, place.landscape not in landscapes)
        best = max(map(score, pool))
        chosen[example.key] = rng.choice([p for p in pool if score(p) == best])
    return chosen
