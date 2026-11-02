"""What the house's hourly history says about its inertia, once there is enough of it. Does not import Home Assistant.

Input: one row per hour (time, local hour, local date, room mean, highest setpoint of the hour, outdoor mean, flow mean)
from the recorder's statistics of the first heating circuit. The controller shows a setpoint of 8 °C (frost protection)
whenever the circuit is off, room warm enough included, so the setpoint says whether it heats, not the target.
Measured, without a physical model:
- cooling: night hours (0-7 h) with the circuit off the whole hour, by room - outdoor gap;
- warm-up: hours in a run of heating hours, by outdoor temperature (the run's last hour, cut short, left out).
Evenings where the room runs more than 1 K over the day's highest setpoint (wood stove, sun) are left out with the night after.
Nothing is given before NEEDED is reached.
"""

from __future__ import annotations

from collections import defaultdict
from statistics import mean
from typing import NamedTuple

NEEDED = {"days": 30, "nights": 15, "warmups": 10, "span": 5}  # heating days, nights, warm-up runs, outdoor °C span
HEATING_SET = 15  # setpoint from which the circuit is on (8 = off)
COOL_GAPS = ((3, 8), (8, 12), (12, 16), (16, 40))
OVER = 1.0  # room over the day's comfort: wood stove or sun


class Hour(NamedTuple):
    ts: float
    hour: int
    day: str  # local date, ISO
    room: float
    set: float  # highest setpoint of the hour
    out: float
    flow: float


def _heating(h: Hour) -> bool:
    return h.set >= HEATING_SET and h.flow > h.room + 6


def _fit(points: list[tuple[float, float]]) -> tuple[float, float]:
    """Least squares rate = a + b * outdoor (flat mean if the outdoor values do not spread)."""
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    mx, my = mean(xs), mean(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    b = sum((x - mx) * (y - my) for x, y in points) / sxx if sxx else 0.0
    return my - b * mx, b


def learn(rows: list[Hour]) -> dict:
    rows = sorted(rows, key=lambda h: h.ts)
    at = {h.ts: h for h in rows}
    comfort, heating_hours = defaultdict(float), defaultdict(int)
    for h in rows:
        comfort[h.day] = max(comfort[h.day], h.set)
        heating_hours[h.day] += _heating(h)
    heating_days = {d for d, n in heating_hours.items() if n >= 4}
    # evenings over the day's comfort (from 15 h) and the night after, up to 8 h
    stove = {h.day for h in rows if h.hour >= 15 and comfort[h.day] >= HEATING_SET and h.room - comfort[h.day] > OVER}
    ok = lambda h: not (h.day in stove and h.hour >= 15 or h.hour < 8 and (at.get(h.ts - (h.hour + 1) * 3600) or h).day in stove)  # noqa: E731

    cooling, nights = defaultdict(list), set()
    for h in rows:
        n = at.get(h.ts + 3600)
        if (n and h.hour < 7 and h.set < HEATING_SET and n.set < HEATING_SET and h.out < 12 and h.room - h.out > 3
                and h.day in heating_days and ok(h) and ok(n)):
            gap = h.room - h.out
            cooling[next(i for i, (_, hi) in enumerate(COOL_GAPS) if gap < hi or hi == COOL_GAPS[-1][1])].append(n.room - h.room)
            nights.add(h.day)

    warmups, run = [], []
    for h in [*rows, None]:
        if h and _heating(h) and ok(h) and (not run or h.ts - run[-1].ts == 3600):
            run.append(h)
            continue
        gains = [b.room - a.room for a, b in zip(run, run[1:-1])]  # the last hour, when it stopped, left out
        if len(gains) >= 2 and max(gains) <= 1:
            warmups.append((mean(r.out for r in run), mean(gains)))
        run = [h] if h and _heating(h) and ok(h) else []

    span = max((w[0] for w in warmups), default=0) - min((w[0] for w in warmups), default=0)
    progress = {"days": len(heating_days), "nights": len(nights), "warmups": len(warmups), "span": round(span, 1)}
    out = {"state": "learning", "progress": progress, "needed": NEEDED}
    if any(progress[k] < v for k, v in NEEDED.items()):
        return out
    a, b = _fit(warmups)
    return out | {
        "state": "ready",
        "cooling": [[lo, hi, round(mean(v), 3), len(v)] for i, (lo, hi) in enumerate(COOL_GAPS) if (v := cooling.get(i))],
        # hours of heating to gain 1 K (Réduit -> Normal) at a few outdoor temperatures
        "hours_per_k": [[t, round(1 / max(a + b * t, 0.05), 1)] for t in (-5, 0, 5, 10)],
    }


if __name__ == "__main__":
    import datetime as dt

    # 40 synthetic winter days: comfort 20 from 6 h, reduced 18 from 21 h; the room loses 0.25 K/h with the circuit off
    # and gains 0.4 - 0.02 * outdoor K/h heating; the setpoint reads 8 whenever the circuit is off
    rows, room, t0 = [], 18.0, dt.datetime(2026, 12, 1)
    for i in range(40 * 24):
        t = t0 + dt.timedelta(hours=i)
        out = -4 + (i // 24) % 12  # -4 to 7 °C over the days
        sp = 20.0 if 6 <= t.hour < 21 else 18.0
        heat = room < sp - 0.05
        rows.append(Hour(t.timestamp(), t.hour, t.date().isoformat(), room, sp if heat else 8, out, 45.0 if heat else room + 1))
        room = min(room + 0.4 - 0.02 * out, sp + 0.5) if heat else room - 0.25
    r = learn(rows)
    assert r["state"] == "ready", r["progress"]
    assert all(abs(c[2] + 0.25) < 0.01 for c in r["cooling"]), r["cooling"]
    assert dict(r["hours_per_k"])[0] == 2.5, r["hours_per_k"]  # 1 / 0.4
    assert learn(rows[: 10 * 24])["state"] == "learning"
    # a stove evening: room 2 K over the comfort at 19 h, that evening and the night after are left out
    stove = [h._replace(room=h.room + 2) if h.day == "2026-12-05" and h.hour == 19 else h for h in rows]
    assert learn(stove)["progress"]["nights"] == r["progress"]["nights"] - 1
    print("ok", r["progress"], r["hours_per_k"])
