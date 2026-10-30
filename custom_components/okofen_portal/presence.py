"""Which circuits and devices the controller really has. Does not import Home Assistant.

The portal answers for every circuit a controller could have (6 heating circuits, 4 pellet boilers...)
whether it is installed or not. The controller says what is present with ``vorhanden`` flags.
"""

from __future__ import annotations

import re

from .api import Reading
from .catalog import group_of

# groups with their own flag: LOCAL.<kind>[<n>].vorhanden
FLAGGED = ("hk", "ww", "pu", "sk", "ertrag", "zirkp", "zubrp")
# groups that follow a pellet boiler: LOCAL.pellematic_vorhanden[<n>]
PELLET = ("fa", "lambda")
ALWAYS = ("system", "weather")
FLAG_KEYS = (
    [f"LOCAL.{kind}[{n}].vorhanden" for kind in FLAGGED for n in range(6)]
    + [f"LOCAL.pellematic_vorhanden[{n}]" for n in range(4)]
    + ["LOCAL.ke_vorhanden", "LOCAL.bestke_vorhanden"]
)


def _kind_index(group_id: str) -> tuple[str, int | None]:
    match = re.fullmatch(r"([a-z0-9]+?)(\d+)", group_id)
    return (match.group(1), int(match.group(2))) if match else (group_id, None)


def hidden_groups(flags: dict[str, Reading], readings: dict[str, Reading]) -> set[str]:
    """Group ids with no equipment behind them. A missing flag never hides a group."""

    def flag(key: str) -> int | None:
        reading = flags.get(key)
        return None if reading is None else int(reading.value)

    hidden: set[str] = set()
    for group_id in {group_of(key)[0] for key in readings}:
        kind, index = _kind_index(group_id)
        if group_id in ALWAYS:
            continue
        if kind in FLAGGED:
            present = flag(f"LOCAL.{kind}[{index}].vorhanden")
        elif kind in PELLET:
            present = flag(f"LOCAL.pellematic_vorhanden[{index}]")
        elif group_id == "boiler":
            values = [flag("LOCAL.ke_vorhanden"), flag("LOCAL.bestke_vorhanden")]
            known = [v for v in values if v is not None]
            present = int(any(known)) if known else None
        else:  # no flag known: an idle device shows nothing but zeros
            values = [
                r.value
                for key, r in readings.items()
                if group_of(key)[0] == group_id and isinstance(r.value, (int, float))
            ]
            present = int(any(values))
        if present == 0:
            hidden.add(group_id)
    return hidden
