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


_INDEXED = re.compile(r"(?:L_)?([a-z0-9]+)\[(\d+)\]")


def group_of(key: str) -> str:
    """Group id of a variable ('hk0', 'boiler'...): one Home Assistant device per function."""
    fa = re.match(r"FA\[(\d+)\]\.", key)
    if fa:
        return f"fa{fa.group(1)}"
    segment = key.removeprefix("LOCAL.").split(".")[0]
    indexed = _INDEXED.fullmatch(segment)
    if indexed:
        return f"{indexed.group(1)}{indexed.group(2)}"
    segment = segment.removeprefix("L_")
    if segment.startswith(("ke_", "bestke_")):
        return "boiler"
    if segment.startswith("weather"):
        return "weather"
    return "system"


def split_group(group_id: str) -> tuple[str, int | None]:
    """'hk0' -> ('hk', 0), 'boiler' -> ('boiler', None)."""
    match = re.fullmatch(r"([a-z0-9]+?)(\d+)", group_id)
    return (match.group(1), int(match.group(2))) if match else (group_id, None)


def pretty(key: str) -> str:
    """'LOCAL.L_hk[0].raumtemp_ist' -> 'raumtemp ist' (the group is already the device name)."""
    name = key.removeprefix("LOCAL.")
    if name.startswith("FA[") or re.match(r"(?:L_)?[a-z0-9]+\[\d+\]\.", name):
        name = name.split(".", 1)[1]
    name = re.sub(r"^L_", "", name)
    return name.replace("_", " ").replace(".", " ")
