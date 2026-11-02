"""The week programs of the heating circuits and hot water, as the controller stores them. Does not import Home Assistant.

Each circuit has 2 programs, 7 days (tag[0] is Sunday) of 3 slots. A slot is one number:
[-][level][day group] HHMM HHMM, e.g. -1100000530 = 00:00 to 05:30, comfort -1 °C; 105302100 = 05:30 to 21:00, comfort.
On a heating circuit a minus sign is comfort -1 °C, a two-digit prefix comfort +1 °C, one digit comfort; hours no slot
covers are setback. On hot water a slot is a time the water is heated. 0 is an empty slot, an end of 0000 is midnight.
"""

from __future__ import annotations

PROGRAMS, DAYS, SLOTS = 2, 7, 3


def keys(group: str) -> list[str]:
    """'hk0' -> the active program and every slot of both programs."""
    g = f"LOCAL.{group[:2]}[{group[2:]}]"
    return [f"{g}.aktives_zeitprogramm"] + [
        f"{g}.zeitprogramm[{p}].tag[{d}].zeitreihe[{i}]" for p in range(PROGRAMS) for d in range(DAYS) for i in range(SLOTS)
    ]


def decode(raw: int) -> list[int] | None:
    """One slot -> [start minute, end minute, level -1 / 0 / +1], None if empty."""
    if not raw:
        return None
    n = abs(int(raw))
    prefix, start, end = n // 10**8, n // 10**4 % 10**4, n % 10**4
    level = -1 if raw < 0 else 1 if prefix >= 10 else 0
    return [start // 100 * 60 + start % 100, end // 100 * 60 + end % 100 or 1440, level]


def week(group: str, values: dict[str, int]) -> dict:
    """The programs of one circuit from the values read for keys(group)."""
    k = keys(group)
    slots = iter(k[1:])
    return {
        "group": group,
        "active": values.get(k[0]),
        "programs": [
            [[s for i in range(SLOTS) if (s := decode(values.get(next(slots)) or 0))] for _ in range(DAYS)]
            for _ in range(PROGRAMS)
        ],
    }


if __name__ == "__main__":
    assert decode(-1100000530) == [0, 330, -1]
    assert decode(105302100) == [330, 1260, 0]
    assert decode(1118000000) == [1080, 1440, 1]
    assert decode(308000900) == [480, 540, 0]
    assert decode(0) is None
    w = week("ww0", {"LOCAL.ww[0].aktives_zeitprogramm": 0, "LOCAL.ww[0].zeitprogramm[0].tag[2].zeitreihe[1]": 318302100})
    assert w["programs"][0][2] == [[1110, 1260, 0]] and w["programs"][1] == [[]] * 7
    print("ok")
