# -*- coding: utf-8 -*-
"""Palettes for maps, by the job the colour does, measured instead of eyeballed: design_style and list_palettes.

Plain Python. A colour has a job: ``categorical`` (identity: hues apart, in a fixed order), ``sequential``
(magnitude: one hue, light to dark, its lightness rising evenly), ``diverging`` (a gap from a centre: two hues and a
neutral middle) or ``status`` (good, warning, serious, critical: reserved). The colours are compared in OKLab, the
perceptual space of Björn Ottosson, and through the eyes of the three colour vision deficiencies (Machado, Oliveira and
Fernandes 2009, full severity): two neighbours a reader cannot tell apart are a fault, said in words.

The palettes: FilterMate's own (the 8 hues of its charts, validated in light and dark), ColorBrewer (Cynthia Brewer,
Apache 2.0: its attribution travels with it), Okabe and Ito, viridis, cividis and magma (CC0).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple

ROLES = ("categorical", "sequential", "diverging", "status")
VARIANTS = ("light", "dark", "print", "discreet")
CVD_FLOOR, CVD_TARGET, NORMAL_FLOOR = 6.0, 8.0, 15.0  # ΔE OKLab x 100 between neighbours of a categorical palette
SEQUENTIAL_STEP = 3.0  # ΔE between two classes of a ramp
LIGHT_BACKGROUND, DARK_BACKGROUND = "#ffffff", "#1a1a19"


@dataclass(frozen=True)
class Palette:
    name: str
    role: str
    colors: Tuple[str, ...]
    dark: Tuple[str, ...] = ()  # the same hues stepped for a dark background, when made by hand
    source: str = ""
    licence: str = ""


def _p(name, role, colors, dark=(), source="", licence=""):
    return Palette(name, role, tuple(colors), tuple(dark), source, licence)


BREWER = ("ColorBrewer, Cynthia A. Brewer, Pennsylvania State University", "Apache-2.0")
MPL = ("matplotlib colormaps (Nathaniel Smith, Stéfan van der Walt, Eric Firing)", "CC0-1.0")
PALETTES: Dict[str, Palette] = {palette.name: palette for palette in (
    _p("filtermate", "categorical", ("#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6",
                                     "#e34948"),
       ("#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#0ca30c", "#9085e9", "#e66767"),
       "FilterMate (validated for colour vision deficiencies, light and dark)", "GPL-2.0-or-later"),
    _p("okabe_ito", "categorical", ("#E69F00", "#56B4E9", "#009E73", "#F0E442", "#0072B2", "#D55E00", "#CC79A7"),
       source="Okabe and Ito, Color Universal Design (2008)", licence="public domain (facts)"),
    _p("set2", "categorical", ("#66c2a5", "#fc8d62", "#8da0cb", "#e78ac3", "#a6d854", "#ffd92f", "#e5c494",
                               "#b3b3b3"), source=BREWER[0], licence=BREWER[1]),
    _p("dark2", "categorical", ("#1b9e77", "#d95f02", "#7570b3", "#e7298a", "#66a61e", "#e6ab02", "#a6761d",
                                "#666666"), source=BREWER[0], licence=BREWER[1]),
    _p("paired", "categorical", ("#a6cee3", "#1f78b4", "#b2df8a", "#33a02c", "#fb9a99", "#e31a1c", "#fdbf6f",
                                 "#ff7f00", "#cab2d6", "#6a3d9a", "#ffff99", "#b15928"),
       source=BREWER[0], licence=BREWER[1]),
    _p("blues", "sequential", ("#f7fbff", "#deebf7", "#c6dbef", "#9ecae1", "#6baed6", "#4292c6", "#2171b5",
                               "#08519c", "#08306b"), source=BREWER[0], licence=BREWER[1]),
    _p("greens", "sequential", ("#f7fcf5", "#e5f5e0", "#c7e9c0", "#a1d99b", "#74c476", "#41ab5d", "#238b45",
                                "#006d2c", "#00441b"), source=BREWER[0], licence=BREWER[1]),
    _p("oranges", "sequential", ("#fff5eb", "#fee6ce", "#fdd0a2", "#fdae6b", "#fd8d3c", "#f16913", "#d94801",
                                 "#a63603", "#7f2704"), source=BREWER[0], licence=BREWER[1]),
    _p("purples", "sequential", ("#fcfbfd", "#efedf5", "#dadaeb", "#bcbddc", "#9e9ac8", "#807dba", "#6a51a3",
                                 "#54278f", "#3f007d"), source=BREWER[0], licence=BREWER[1]),
    _p("reds", "sequential", ("#fff5f0", "#fee0d2", "#fcbba1", "#fc9272", "#fb6a4a", "#ef3b2c", "#cb181d",
                              "#a50f15", "#67000d"), source=BREWER[0], licence=BREWER[1]),
    _p("greys", "sequential", ("#ffffff", "#f0f0f0", "#d9d9d9", "#bdbdbd", "#969696", "#737373", "#525252",
                               "#252525", "#000000"), source=BREWER[0], licence=BREWER[1]),
    _p("ylgnbu", "sequential", ("#ffffd9", "#edf8b1", "#c7e9b4", "#7fcdbb", "#41b6c4", "#1d91c0", "#225ea8",
                                "#253494", "#081d58"), source=BREWER[0], licence=BREWER[1]),
    _p("ylorrd", "sequential", ("#ffffcc", "#ffeda0", "#fed976", "#feb24c", "#fd8d3c", "#fc4e2a", "#e31a1c",
                                "#bd0026", "#800026"), source=BREWER[0], licence=BREWER[1]),
    _p("viridis", "sequential", ("#fde725", "#addc30", "#5ec962", "#28ae80", "#21918c", "#2c728e", "#3b528b",
                                 "#472d7b", "#440154"), source=MPL[0], licence=MPL[1]),
    _p("cividis", "sequential", ("#fee838", "#e1cc55", "#c3b369", "#a59c74", "#8a8779", "#6f7273", "#575d6d",
                                 "#3d4a6d", "#00224e"), source=MPL[0], licence=MPL[1]),
    _p("magma", "sequential", ("#fcfdbf", "#fec287", "#fd9668", "#f1605d", "#cd4071", "#9e2f7f", "#721f81",
                               "#440f76", "#180f3d"), source=MPL[0], licence=MPL[1]),
    _p("rdbu", "diverging", ("#67001f", "#b2182b", "#d6604d", "#f4a582", "#fddbc7", "#f7f7f7", "#d1e5f0",
                             "#92c5de", "#4393c3", "#2166ac", "#053061"), source=BREWER[0], licence=BREWER[1]),
    _p("puor", "diverging", ("#7f3b08", "#b35806", "#e08214", "#fdb863", "#fee0b6", "#f7f7f7", "#d8daeb",
                             "#b2abd2", "#8073ac", "#542788", "#2d004b"), source=BREWER[0], licence=BREWER[1]),
    _p("brbg", "diverging", ("#543005", "#8c510a", "#bf812d", "#dfc27d", "#f6e8c3", "#f5f5f5", "#c7eae5",
                             "#80cdc1", "#35978f", "#01665e", "#003c30"), source=BREWER[0], licence=BREWER[1]),
    _p("piyg", "diverging", ("#8e0152", "#c51b7d", "#de77ae", "#f1b6da", "#fde0ef", "#f7f7f7", "#e6f5d0",
                             "#b8e186", "#7fbc41", "#4d9221", "#276419"), source=BREWER[0], licence=BREWER[1]),
    _p("status", "status", ("#0ca30c", "#fab219", "#ec835a", "#d03b3b"),
       source="FilterMate (good, warning, serious, critical)", licence="GPL-2.0-or-later"),
)}
DEFAULT_PALETTE = {"categorical": "filtermate", "sequential": "blues", "diverging": "rdbu", "status": "status"}
OTHERS_LIGHT, OTHERS_DARK = "#a7a6a0", "#6f6e69"
DARK_NEUTRAL = "#383835"  # the middle of a diverging palette on a dark map


class PaletteError(ValueError):
    """A palette that cannot serve: the words are for the model."""


# --- colour spaces -------------------------------------------------------------------------------------------------

def hex_to_rgb(color: str) -> Tuple[float, float, float]:
    text = str(color).strip().lstrip("#")
    if len(text) == 3:
        text = "".join(char * 2 for char in text)
    if len(text) != 6 or any(char not in "0123456789abcdefABCDEF" for char in text):
        raise PaletteError(f"{color!r} is no colour as #rrggbb")
    return tuple(int(text[index:index + 2], 16) / 255.0 for index in (0, 2, 4))


def rgb_to_hex(rgb: Sequence[float]) -> str:
    return "#" + "".join(f"{round(min(1.0, max(0.0, channel)) * 255):02x}" for channel in rgb)


def _linear(channel: float) -> float:
    return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4


def _gamma(channel: float) -> float:
    return 12.92 * channel if channel <= 0.0031308 else 1.055 * (max(channel, 0.0) ** (1 / 2.4)) - 0.055


def _cbrt(value: float) -> float:
    return math.copysign(abs(value) ** (1.0 / 3.0), value)


def linear_to_oklab(rgb: Sequence[float]) -> Tuple[float, float, float]:
    r, g, b = rgb
    l_ = _cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b)
    m_ = _cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b)
    s_ = _cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b)
    return (0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_,
            1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_,
            0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_)


def oklab_to_linear(lab: Sequence[float]) -> Tuple[float, float, float]:
    lightness, a, b = lab
    l_ = (lightness + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m_ = (lightness - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s_ = (lightness - 0.0894841775 * a - 1.2914855480 * b) ** 3
    return (4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_,
            -1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_,
            -0.0041960863 * l_ - 0.7034186147 * m_ + 1.7076147010 * s_)


def to_oklab(color: str) -> Tuple[float, float, float]:
    return linear_to_oklab(tuple(_linear(channel) for channel in hex_to_rgb(color)))


def from_oklab(lab: Sequence[float]) -> str:
    """The colour of ``lab``, its chroma lowered until it fits in sRGB (never clipped: clipping shifts the hue)."""
    lightness, a, b = lab
    lightness = min(1.0, max(0.0, lightness))
    for _ in range(40):
        rgb = oklab_to_linear((lightness, a, b))
        if all(-1e-4 <= channel <= 1.0001 for channel in rgb):
            break
        a, b = a * 0.92, b * 0.92
    return rgb_to_hex([_gamma(channel) for channel in oklab_to_linear((lightness, a, b))])


def to_oklch(color: str) -> Tuple[float, float, float]:
    lightness, a, b = to_oklab(color)
    return lightness, math.hypot(a, b), math.degrees(math.atan2(b, a)) % 360.0


def from_oklch(lightness: float, chroma: float, hue: float) -> str:
    return from_oklab((lightness, chroma * math.cos(math.radians(hue)), chroma * math.sin(math.radians(hue))))


def delta_e(first: str, second: str) -> float:
    """OKLab distance x 100: below 2 alike, 8 apart enough for a legend, 15 plainly different."""
    return 100.0 * math.dist(to_oklab(first), to_oklab(second))


CVD = {  # Machado, Oliveira and Fernandes (2009), severity 1, on linear RGB
    "protan": ((0.152286, 1.052583, -0.204868), (0.114503, 0.786281, 0.099216), (-0.003882, -0.048116, 1.051998)),
    "deutan": ((0.367322, 0.860646, -0.227968), (0.280085, 0.672501, 0.047413), (-0.011820, 0.042940, 0.968881)),
    "tritan": ((1.255528, -0.076749, -0.178779), (-0.078411, 0.930809, 0.147602), (0.004733, 0.691367, 0.303900)),
}


def simulate(color: str, deficiency: str) -> str:
    """How ``color`` looks to a reader with ``deficiency`` (protan, deutan, tritan)."""
    matrix = CVD[deficiency]
    linear = [_linear(channel) for channel in hex_to_rgb(color)]
    seen = [sum(row[index] * linear[index] for index in range(3)) for row in matrix]
    return rgb_to_hex([_gamma(min(1.0, max(0.0, channel))) for channel in seen])


def contrast(first: str, second: str) -> float:
    """WCAG contrast ratio (1 to 21)."""
    def luminance(color):
        r, g, b = (_linear(channel) for channel in hex_to_rgb(color))
        return 0.2126 * r + 0.7152 * g + 0.0722 * b
    high, low = sorted((luminance(first), luminance(second)), reverse=True)
    return (high + 0.05) / (low + 0.05)


# --- colours for a map ---------------------------------------------------------------------------------------------

def palette(name: str = "", role: str = "") -> Palette:
    if name:
        found = PALETTES.get(str(name).strip().lower())
        if found is None:
            raise PaletteError(f"no palette {name!r}: {', '.join(sorted(PALETTES))}")
        if role and found.role != role:
            raise PaletteError(f"{found.name} is a {found.role} palette, not {role}: "
                               f"{', '.join(sorted(p.name for p in PALETTES.values() if p.role == role))}")
        return found
    if role not in ROLES:
        raise PaletteError(f"role is one of {', '.join(ROLES)}")
    return PALETTES[DEFAULT_PALETTE[role]]


def _ramp(stops: Sequence[str], count: int) -> List[str]:
    """``count`` colours taken evenly along ``stops``, mixed in OKLab (a straight mix in sRGB greys the middle)."""
    if count <= 0:
        return []
    if count == 1:
        return [stops[len(stops) // 2]]
    labs = [to_oklab(color) for color in stops]
    made = []
    for index in range(count):
        place = index * (len(labs) - 1) / (count - 1)
        low = min(int(place), len(labs) - 2)
        fraction = place - low
        made.append(from_oklab([labs[low][axis] * (1 - fraction) + labs[low + 1][axis] * fraction
                                for axis in range(3)]))
    return made


def colors_for(role: str, count: int, name: str = "", variant: str = "light", reverse: bool = False
               ) -> Tuple[List[str], Palette, str]:
    """``count`` colours of a palette for its ``role`` and ``variant``; and a note when some had to be folded."""
    if variant not in VARIANTS:
        raise PaletteError(f"variant is one of {', '.join(VARIANTS)}")
    chosen = palette(name, role)
    note = ""
    if chosen.role in ("categorical", "status"):
        source = list(chosen.dark) if variant == "dark" and chosen.dark else list(chosen.colors)
        if count > len(source):
            note = (f"{count} categories, {len(source)} colours: the others share one grey; fewer categories (limit) "
                    "read better")
        colors = source[:count]
    else:
        stops = list(chosen.colors)
        if chosen.role == "sequential" and count <= 7:
            stops = stops[1:]  # the palest step vanishes on a white map
        colors = _ramp(stops, count)
    if reverse:
        colors = colors[::-1]
    if variant == "dark" and chosen.role == "sequential":
        # Turned over, never recoloured: its low values take the dark end, nearest the dark background, and the
        # ramp keeps the hues and the even lightness it was made with (inverting the lightness of viridis bent it).
        colors = colors[::-1]
    elif variant == "dark" and chosen.role == "diverging":
        # The neutral middle of a light map is a bright spot on a dark one: a dark grey instead.
        colors = [DARK_NEUTRAL if to_oklch(color)[1] < 0.02 else color for color in colors]
    elif variant == "dark" and not (chosen.role in ("categorical", "status") and chosen.dark):
        colors = [dark_step(color, chosen.role) for color in colors]
    elif variant == "print":
        colors = [print_step(color) for color in colors]
    elif variant == "discreet":
        colors = [discreet_step(color) for color in colors]
    return colors, chosen, note


def others_color(variant: str = "light") -> str:
    return OTHERS_DARK if variant == "dark" else OTHERS_LIGHT


def dark_step(color: str, role: str = "categorical") -> str:
    """``color`` for a dark background: a categorical hue brought into a middle lightness it stays visible at."""
    lightness, chroma, hue = to_oklch(color)
    if role == "sequential":
        return from_oklch(1.05 - lightness * 0.9, chroma, hue)
    return from_oklch(min(0.78, max(0.58, lightness)), chroma, hue)


def print_step(color: str) -> str:
    """``color`` for paper: no step too pale to print, a little more chroma (ink and paper dull colours)."""
    lightness, chroma, hue = to_oklch(color)
    return from_oklch(min(lightness, 0.93), chroma * 1.1, hue)


def discreet_step(color: str) -> str:
    """``color`` for a background layer: paler and greyer, so that a thematic layer above it stands out."""
    lightness, chroma, hue = to_oklch(color)
    return from_oklch(0.72 + lightness * 0.22, chroma * 0.35, hue)


def outline_of(color: str, variant: str = "light") -> str:
    """The outline of a fill: the same hue, darker (lighter on a dark map)."""
    lightness, chroma, hue = to_oklch(color)
    if variant == "dark":
        return from_oklch(min(0.95, lightness + 0.16), chroma * 0.8, hue)
    return from_oklch(max(0.12, lightness - 0.2), chroma * 0.9, hue)


def tint_of(color: str, amount: float = 0.45) -> str:
    """A lighter tint of ``color`` (the inside of an outlined polygon, the core of a road)."""
    lightness, chroma, hue = to_oklch(color)
    return from_oklch(lightness + (1.0 - lightness) * amount, chroma * (1.0 - amount * 0.6), hue)


def validate(colors: Sequence[str], role: str, background: str = LIGHT_BACKGROUND, marks: str = "fill"
             ) -> Dict[str, object]:
    """What a reader can tell apart: problems in words (empty when the colours serve), and the measures."""
    problems: List[str] = []
    report: Dict[str, object] = {"role": role, "colors": len(colors)}
    if role in ("categorical", "status") and len(colors) > 1:
        normal = min(delta_e(first, second) for first, second in zip(colors, colors[1:]))
        seen = {}
        for deficiency in CVD:
            simulated = [simulate(color, deficiency) for color in colors]
            seen[deficiency] = min(delta_e(first, second) for first, second in zip(simulated, simulated[1:]))
        # Protan and deutan readers (8 % of men) set the floors; tritan (about 1 in 10,000) is measured and told.
        worst = min(("protan", "deutan"), key=seen.get)
        report.update(min_delta_e=round(normal, 1), min_delta_e_cvd=round(seen[worst], 1), worst_cvd=worst,
                      min_delta_e_tritan=round(seen["tritan"], 1))
        if normal < NORMAL_FLOOR:
            problems.append(f"two neighbouring colours are close for every reader (ΔE {normal:.1f} < {NORMAL_FLOOR:g})")
        if seen[worst] < CVD_FLOOR:
            problems.append(f"two neighbouring colours look alike to a {worst} reader (ΔE {seen[worst]:.1f}): a "
                            "validated palette (filtermate, okabe_ito, dark2) or fewer categories")
        elif seen[worst] < CVD_TARGET:
            problems.append(f"two neighbours are near for a {worst} reader (ΔE {seen[worst]:.1f}): labels help")
    elif role in ("sequential", "diverging") and len(colors) > 1:
        lightness = [to_oklab(color)[0] for color in colors]
        steps = [delta_e(first, second) for first, second in zip(colors, colors[1:])]
        report.update(min_step=round(min(steps), 1))
        if role == "sequential":
            rising = all(b > a for a, b in zip(lightness, lightness[1:]))
            falling = all(b < a for a, b in zip(lightness, lightness[1:]))
            if not (rising or falling):
                problems.append("the lightness of the ramp does not change in one direction: the classes do not read "
                                "as more and less")
        if min(steps) < SEQUENTIAL_STEP:
            problems.append(f"two classes are too close (ΔE {min(steps):.1f}): fewer classes")
    if marks in ("line", "point"):
        weakest = min(contrast(color, background) for color in colors)
        report["min_contrast"] = round(weakest, 2)
        if weakest < 1.5:
            problems.append(f"a colour hardly stands out of the background (contrast {weakest:.2f}): thin lines and "
                            "small points need an outline or the dark variant")
    report["problems"] = problems
    return report


def describe(role: str = "") -> List[Dict[str, object]]:
    """The palettes, of one role or all, with their colours, source, licence and what the validator measures."""
    rows = []
    for item in PALETTES.values():
        if role and item.role != role:
            continue
        measured = validate(list(item.colors[:8]), item.role)
        rows.append({"name": item.name, "role": item.role, "colors": list(item.colors), "dark": list(item.dark),
                     "source": item.source, "licence": item.licence,
                     "checked": {key: value for key, value in measured.items() if key not in ("role", "colors")}})
    return rows
