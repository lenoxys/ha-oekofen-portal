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


def pretty(key: str) -> str:
    """'LOCAL.L_hk[0].raumtemp_ist' -> 'hk[0] raumtemp ist'."""
    name = key.removeprefix("LOCAL.")
    name = re.sub(r"(^|\.)L_", r"\1", name)
    return name.replace("_", " ").replace(".", " ")
