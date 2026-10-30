"""Variable catalog and how to turn a reading into an entity. Does not import Home Assistant."""

from __future__ import annotations

import json
import pathlib
import re

from .api import Reading

CATALOG_FILE = pathlib.Path(__file__).parent / "catalog.json"


def load_catalog() -> list[str]:
    """Names of every read-only variable the portal knows (see scripts/build_catalog.py)."""
    return json.loads(CATALOG_FILE.read_text(encoding="utf-8"))


def kind(reading: Reading) -> str:
    """'binary' (2 states), 'enum' (3+ states), 'number' or 'text' (not exposed)."""
    if isinstance(reading.value, str):
        return "text"
    states = reading.states
    if states and all(states) and len(set(states)) == len(states):  # labels usable as options
        return "binary" if len(states) == 2 else "enum"
    return "number"


# prefix of an indexed group, e.g. hk[0] -> "Heating circuit 1"
GROUP_LABELS = {
    "hk": "Heating circuit",
    "ww": "Hot water",
    "pu": "Buffer",
    "sk": "Solar circuit",
    "ertrag": "Solar yield",
    "heater": "Heater",
    "batt": "Battery",
    "car": "Charging station",
    "p2h": "Power2heat",
    "wp": "Heat pump",
}
_INDEXED = re.compile(r"(?:L_)?([a-z0-9]+)\[(\d+)\]")


def group_of(key: str) -> tuple[str, str]:
    """(group id, group name) of a variable: one Home Assistant device per function."""
    fa = re.match(r"FA\[(\d+)\]\.", key)
    if fa:
        return f"fa{fa.group(1)}", f"Pellet boiler {int(fa.group(1)) + 1}"
    segment = key.removeprefix("LOCAL.").split(".")[0]
    indexed = _INDEXED.fullmatch(segment)
    if indexed:
        kind, index = indexed.group(1), int(indexed.group(2))
        return f"{kind}{index}", f"{GROUP_LABELS.get(kind, kind.title())} {index + 1}"
    segment = segment.removeprefix("L_")
    if segment.startswith(("ke_", "bestke_")):
        return "boiler", "Existing boiler"
    if segment.startswith("weather"):
        return "weather", "Weather"
    return "system", "System"


def pretty(key: str) -> str:
    """'LOCAL.L_hk[0].raumtemp_ist' -> 'raumtemp ist' (the group is already the device name)."""
    name = key.removeprefix("LOCAL.")
    if name.startswith("FA[") or re.match(r"(?:L_)?[a-z0-9]+\[\d+\]\.", name):
        name = name.split(".", 1)[1]
    name = re.sub(r"^L_", "", name)
    return name.replace("_", " ").replace(".", " ")
