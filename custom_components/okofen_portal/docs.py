"""ÖkoFEN's own labels and help texts, read from the portal's public files at start-up.

Nothing from them is stored in this repository: the status-word decoding and the help
texts are downloaded (and cached by Home Assistant) in the language of Home Assistant.
Does not import Home Assistant.
"""

from __future__ import annotations

import asyncio
import html
import re
from dataclasses import dataclass, field
from typing import Any

import aiohttp

from .api import BASE

CONFIG_URL = f"{BASE}/app/assets/maintenance/config/3.11.json"
I18N_URL = BASE + "/app/assets/i18n/{lang}.json"
HELP_URL = BASE + "/app/assets/maintenance/help/{lang}.json"
_PREFIX = "CAPPL:"
_TIMEOUT = aiohttp.ClientTimeout(total=60)


@dataclass
class Docs:
    """What the portal says about the variables."""

    status: dict[str, dict[int, str]] = field(default_factory=dict)  # variable -> bit -> text
    help: dict[str, str] = field(default_factory=dict)  # setting -> help text

    def decode(self, key: str, raw: int) -> str | None:
        """Texts of the bits set in a status word, joined with ' | '."""
        bits = self.status.get(key)
        if bits is None:
            return None
        texts = [bits.get(i, f"bit {i}") for i in range(32) if raw >> i & 1]
        return " | ".join(texts) if texts else None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": {k: {str(i): t for i, t in v.items()} for k, v in self.status.items()},
            "help": self.help,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Docs:
        return cls(
            {k: {int(i): t for i, t in v.items()} for k, v in data.get("status", {}).items()},
            data.get("help", {}),
        )


async def _get_json(session: aiohttp.ClientSession, url: str) -> Any:
    async with session.get(url, timeout=_TIMEOUT) as resp:
        resp.raise_for_status()
        return await resp.json(content_type=None)


def _flatten(obj: Any, path: str = "") -> dict[str, str]:
    out: dict[str, str] = {}
    if isinstance(obj, dict):
        for key, value in obj.items():
            out.update(_flatten(value, f"{path}.{key}"))
    elif isinstance(obj, str):
        out[path] = obj
    return out


def _walk(obj: Any):
    if isinstance(obj, dict):
        yield obj
        for value in obj.values():
            yield from _walk(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from _walk(value)


def _plain(text: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", text.replace("<br>", " ")))).strip()


async def async_fetch_docs(
    session: aiohttp.ClientSession, lang: str, wanted: set[str]
) -> Docs:
    """Download the portal's description files; ``wanted`` are the settings to keep help for."""
    config = await _get_json(session, CONFIG_URL)
    texts: dict[str, str] = {}
    help_json: dict[str, Any] = {}
    for candidate in (lang, "en"):
        try:
            texts = _flatten(await _get_json(session, I18N_URL.format(lang=candidate)))
            help_json = await _get_json(session, HELP_URL.format(lang=candidate))
            break
        except (aiohttp.ClientError, asyncio.TimeoutError):
            continue
    docs = Docs()
    for node in _walk(config):
        for group in node.get("statusGroups", []) or []:
            variable = str(group.get("variable", "")).removeprefix(_PREFIX)
            bits = {
                int(bit): texts.get("." + str(info.get("text")), str(info.get("text")))
                for bit, info in (group.get("status") or {}).items()
                if str(bit).isdigit()
            }
            if variable and bits:
                docs.status[variable] = bits
        variable = str(node.get("variable", "")).removeprefix(_PREFIX)
        if variable in wanted:
            entry = help_json.get(str(node.get("help"))) if node.get("help") else None
            if isinstance(entry, dict) and entry.get("text"):
                docs.help[variable] = _plain(entry["text"])
    return docs
