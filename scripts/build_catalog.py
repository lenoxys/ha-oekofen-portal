"""Rebuild custom_components/okofen_portal/catalog.json.

The portal's web app loads a public configuration file listing every variable of the controller.
This extracts the read-only ones (names starting with ``L_``): names only, no values.

    python scripts/build_catalog.py
"""

from __future__ import annotations

import json
import pathlib
import re
import urllib.request

URL = "https://my.oekofen.info/app/assets/maintenance/config/3.11.json"
OUT = pathlib.Path(__file__).parent.parent / "custom_components/okofen_portal/catalog.json"
NAME = re.compile(r"(?:CAPPL:)?((?:LOCAL|FA\[\d+\])\.[A-Za-z_][A-Za-z_0-9\[\]\.]*)")
# arrays and text-only variables that make no useful entity, and anything that could identify a person or an installation
SKIP = re.compile(
    r"fehlerlog|estrich|fernwartung|customer|rfusb|touch\[|weather\[|lade_aufzeichnung|serial|seriennr|"
    r"\bmac|_ip\b|ssid|wlan|wifi|pass|pwd|token|mail|kunde|name$|alias$|datum|zeit_sek|_select$|code",
    re.I,
)


def main() -> None:
    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
    text = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")
    names = sorted(
        n
        for n in {m.group(1) for m in NAME.finditer(text)}
        if any(part.startswith("L_") for part in n.split(".")) and not SKIP.search(n)
    )
    OUT.write_text(json.dumps(names, indent=0) + "\n", encoding="utf-8")
    print(len(names), "variables written to", OUT)


if __name__ == "__main__":
    main()
