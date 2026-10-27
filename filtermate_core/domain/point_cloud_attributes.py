"""
Point Cloud Attributes - Registry of the LAS / COPC dimensions and attribute conditions.

One place for the attribute names used by FilterMate (canonical spelling,
readable label, unit, decimals, integer or not) and for the chained
attribute conditions of the point cloud EXPLORING panel: parsing,
``QgsPointCloudExpression`` rendering and mapping to
:class:`PointCloudFilterCriteria` members.

An attribute missing from the registry stays usable: it gets the default
description (its own name as label, float, 3 decimals).

This is a PURE PYTHON module with NO QGIS dependencies.
"""
import math
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .point_cloud_filter_criteria import AttributeRange, format_number

X = "X"
Y = "Y"
Z = "Z"
INTENSITY = "Intensity"
RETURN_NUMBER = "ReturnNumber"
NUMBER_OF_RETURNS = "NumberOfReturns"
CLASSIFICATION = "Classification"
SCAN_ANGLE = "ScanAngleRank"
GPS_TIME = "GpsTime"
HEIGHT_ABOVE_GROUND = "HeightAboveGround"

DEFAULT_DECIMALS = 3


@dataclass(frozen=True)
class PointCloudAttribute:
    """Description of a point cloud attribute.

    Attributes:
        name: Name used in expressions (the layer's own spelling).
        label: Readable English label, translated by the UI.
        unit: Unit symbol (``"m"``, ``"°"``), empty when none.
        decimals: Decimals of the value fields.
        integer: Whether the attribute only holds integers.
    """
    name: str
    label: str
    unit: str = ""
    decimals: int = DEFAULT_DECIMALS
    integer: bool = False


def _integer(name: str, label: str) -> PointCloudAttribute:
    return PointCloudAttribute(name, label, decimals=0, integer=True)


# Usual LAS / COPC dimensions (QGIS and PDAL spellings), in display order.
KNOWN_ATTRIBUTES: Tuple[PointCloudAttribute, ...] = (
    PointCloudAttribute(X, "X", "m"),
    PointCloudAttribute(Y, "Y", "m"),
    PointCloudAttribute(Z, "Z", "m"),
    _integer(INTENSITY, "Intensity"),
    _integer(RETURN_NUMBER, "Return number"),
    _integer(NUMBER_OF_RETURNS, "Number of returns"),
    _integer(CLASSIFICATION, "Classification"),
    PointCloudAttribute(SCAN_ANGLE, "Scan angle", "°"),
    _integer("UserData", "User data"),
    _integer("PointSourceId", "Point source ID"),
    PointCloudAttribute(GPS_TIME, "GPS time", "s", decimals=6),
    _integer("Red", "Red"),
    _integer("Green", "Green"),
    _integer("Blue", "Blue"),
    _integer("Infrared", "Infrared"),
    _integer("ScanDirectionFlag", "Scan direction"),
    _integer("EdgeOfFlightLine", "Edge of flight line"),
    _integer("Synthetic", "Synthetic"),
    _integer("KeyPoint", "Key point"),
    _integer("Withheld", "Withheld"),
    _integer("Overlap", "Overlap"),
    _integer("ScannerChannel", "Scanner channel"),
    _integer("ClassFlags", "Classification flags"),
    PointCloudAttribute(HEIGHT_ABOVE_GROUND, "Height above ground", "m", decimals=2),
)

# Other spellings of the same dimensions (PDAL, LAS 1.4, older writers).
ATTRIBUTE_ALIASES: Dict[str, str] = {
    "ScanAngle": SCAN_ANGLE,
    "PointSourceID": "PointSourceId",
    "GPSTime": GPS_TIME,
    "NIR": "Infrared",
    "NearInfrared": "Infrared",
    "ScanChannel": "ScannerChannel",
    "ClassificationFlags": "ClassFlags",
    "HAG": HEIGHT_ABOVE_GROUND,
}

_BY_KEY: Dict[str, PointCloudAttribute] = {item.name.lower(): item for item in KNOWN_ATTRIBUTES}
_BY_KEY.update({alias.lower(): _BY_KEY[name.lower()] for alias, name in ATTRIBUTE_ALIASES.items()})

# Not offered as conditions: X / Y are the map. Classification is offered although the
# classes have their own group: the groups are exclusive and the height above the DTM
# belongs to the conditions, so "class AND height" (buildings above 9 m) needs it here.
NON_CONDITION_ATTRIBUTES = (X, Y)
# Offered when the layer does not list its attributes.
FALLBACK_CONDITION_ATTRIBUTES = (Z, INTENSITY, RETURN_NUMBER, NUMBER_OF_RETURNS)


def canonical_attribute_name(name: str) -> Optional[str]:
    """Registry spelling of ``name`` (case and aliases ignored), None when unknown."""
    known = _BY_KEY.get(str(name).strip().lower())
    return known.name if known is not None else None


def attribute_info(name: str) -> PointCloudAttribute:
    """Description of ``name``; the default one (float, 3 decimals) when it is not registered.

    The returned ``name`` is always ``name`` itself: expressions use the
    layer's spelling, the registry only brings label, unit and decimals.
    """
    name = str(name).strip()
    known = _BY_KEY.get(name.lower())
    if known is None:
        return PointCloudAttribute(name, name)
    return PointCloudAttribute(name, known.label, known.unit, known.decimals, known.integer)


def condition_attributes(attributes: Sequence[str], extra: Sequence[str] = ()) -> List[str]:
    """Attributes offered in a condition, in layer order, X / Y / Classification left out.

    Args:
        attributes: Attributes of the layer; empty when the layer does not list them.
        extra: Used instead of an empty ``attributes`` (the attributes with
            statistics), before the usual fallback ones.
    """
    names = list(attributes) or [*extra, *FALLBACK_CONDITION_ATTRIBUTES]
    skipped = {name.lower() for name in NON_CONDITION_ATTRIBUTES}
    result: List[str] = []
    for name in names:
        name = str(name).strip()
        if name and name.lower() not in skipped and name not in result:
            result.append(name)
    return result


# ---------------------------------------------------------------------------
# Conditions
# ---------------------------------------------------------------------------

OP_BETWEEN = "between"
OP_EQUAL = "="
OP_NOT_EQUAL = "<>"
OP_GREATER_OR_EQUAL = ">="
OP_LESS_OR_EQUAL = "<="
OP_GREATER = ">"
OP_LESS = "<"
OPERATORS = (OP_BETWEEN, OP_EQUAL, OP_NOT_EQUAL, OP_GREATER_OR_EQUAL, OP_LESS_OR_EQUAL, OP_GREATER, OP_LESS)
OPERATOR_SYMBOLS = {OP_BETWEEN: "between", OP_EQUAL: "=", OP_NOT_EQUAL: "≠", OP_GREATER_OR_EQUAL: "≥",
                    OP_LESS_OR_EQUAL: "≤", OP_GREATER: ">", OP_LESS: "<"}
_OPERATOR_ALIASES = {"!=": OP_NOT_EQUAL, "≠": OP_NOT_EQUAL, "≥": OP_GREATER_OR_EQUAL, "≤": OP_LESS_OR_EQUAL,
                     "==": OP_EQUAL}

JOIN_AND = "AND"
JOIN_OR = "OR"

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def normalize_operator(value: Any) -> Optional[str]:
    """Operator key of ``value`` (``"≥"`` -> ``">="``, ``"BETWEEN"`` -> ``"between"``), None when unknown."""
    text = str(value).strip() if value is not None else ""
    text = _OPERATOR_ALIASES.get(text, text)
    if text.lower() == OP_BETWEEN:
        return OP_BETWEEN
    return text if text in OPERATORS else None


def quote_attribute(name: str) -> str:
    """Bare name when it is a plain identifier, else between double quotes (``"Scan Angle"``)."""
    name = str(name)
    if _IDENTIFIER_RE.match(name):
        return name
    return '"' + name.replace('"', '""') + '"'


def _number(value: Any) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def parse_condition(value: Any) -> Optional[Dict[str, Any]]:
    """Normalise a condition ``{attribute, op, low, high, join}``; None when unusable.

    ``low`` is the lower bound of ``between`` or the operand of every other
    operator: a number, or the name of another attribute (``ReturnNumber =
    NumberOfReturns``). ``high`` is only kept for ``between``, whose bounds
    are ordered; a None bound means "no bound". ``join`` (``AND`` / ``OR``)
    links the condition to the previous one. The function is idempotent.
    """
    if not isinstance(value, dict):
        return None
    attribute = value.get("attribute")
    if not isinstance(attribute, str) or not attribute.strip():
        return None
    op = normalize_operator(value.get("op", OP_BETWEEN))
    if op is None:
        return None
    raw_low = value.get("low")
    if op == OP_BETWEEN:
        low, high = _number(raw_low), _number(value.get("high"))
        if low is not None and high is not None and low > high:
            low, high = high, low
    else:
        high = None
        low = _number(raw_low)
        if low is None and isinstance(raw_low, str) and raw_low.strip():
            low = raw_low.strip()
    join = JOIN_OR if str(value.get("join") or "").strip().upper() == JOIN_OR else JOIN_AND
    return {"attribute": attribute.strip(), "op": op, "low": low, "high": high, "join": join}


def parse_conditions(values: Any) -> List[Dict[str, Any]]:
    """Normalised conditions of a list, the unusable ones dropped; the first one joined with AND."""
    if not isinstance(values, (list, tuple)):
        return []
    conditions = [condition for condition in map(parse_condition, values) if condition is not None]
    if conditions:
        conditions[0]["join"] = JOIN_AND
    return conditions


def condition_clause(condition: Dict[str, Any]) -> str:
    """Expression of one parsed condition, ``""`` when it is incomplete.

    ``between`` gives ``Z >= 1 AND Z <= 5`` (one side only when the other
    bound is None); the others ``Intensity >= 100``, ``ReturnNumber =
    NumberOfReturns``.
    """
    name = quote_attribute(condition["attribute"])
    op, low, high = condition["op"], condition["low"], condition["high"]
    if op == OP_BETWEEN:
        clauses = []
        if low is not None:
            clauses.append(f"{name} >= {format_number(low)}")
        if high is not None:
            clauses.append(f"{name} <= {format_number(high)}")
        return " AND ".join(clauses)
    if low is None:
        return ""
    operand = quote_attribute(low) if isinstance(low, str) else format_number(low)
    return f"{name} {op} {operand}"


def _complete(conditions: Sequence[Dict[str, Any]]) -> List[Tuple[Dict[str, Any], str]]:
    pairs = ((condition, condition_clause(condition)) for condition in conditions)
    return [(condition, clause) for condition, clause in pairs if clause]


def _and_groups(conditions: Sequence[Dict[str, Any]]) -> List[List[str]]:
    """Clauses grouped by ``AND`` (AND binds tighter than OR); incomplete conditions are skipped."""
    groups: List[List[str]] = []
    for condition, clause in _complete(conditions):
        if groups and condition["join"] != JOIN_OR:
            groups[-1].append(clause)
        else:
            groups.append([clause])
    return groups


def conditions_have_or(conditions: Sequence[Dict[str, Any]]) -> bool:
    """Whether the complete conditions form more than one AND group."""
    return len(_and_groups(conditions)) > 1


def conditions_expression(conditions: Sequence[Dict[str, Any]]) -> str:
    """Expression of parsed conditions: ``c1 AND c2``, or ``(c1 AND c2) OR (c3)`` with an OR."""
    groups = _and_groups(conditions)
    if len(groups) == 1:
        return " AND ".join(groups[0])
    return " OR ".join(f"({' AND '.join(group)})" for group in groups)


def _as_range(condition: Dict[str, Any]) -> Optional[AttributeRange]:
    """The condition as an :class:`AttributeRange`, None when a range cannot express it."""
    op, low, high = condition["op"], condition["low"], condition["high"]
    if isinstance(low, str) or not _IDENTIFIER_RE.match(condition["attribute"]):
        return None
    if op == OP_BETWEEN:
        return AttributeRange(condition["attribute"], low, high)
    if op == OP_GREATER_OR_EQUAL:
        return AttributeRange(condition["attribute"], low, None)
    if op == OP_LESS_OR_EQUAL:
        return AttributeRange(condition["attribute"], None, low)
    return None


def conditions_criteria(conditions: Sequence[Dict[str, Any]]) -> Tuple[Tuple[AttributeRange, ...], Tuple[str, ...]]:
    """``(ranges, extra_clauses)`` of parsed conditions for :class:`PointCloudFilterCriteria`.

    An AND chain keeps one range per ``between`` / ``>=`` / ``<=`` condition
    and one extra clause per other condition (the criteria render the ranges
    first). With an OR, the whole chain is one extra clause.
    """
    complete = _complete(conditions)
    if conditions_have_or(conditions):
        return (), (conditions_expression(conditions),)
    ranges: List[AttributeRange] = []
    extra: List[str] = []
    for condition, clause in complete:
        item = _as_range(condition)
        if item is None:
            extra.append(clause)
        else:
            ranges.append(item)
    return tuple(ranges), tuple(extra)
