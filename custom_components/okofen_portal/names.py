"""Readable names and descriptions, read from the language files in ``i18n/``.

Does not import Home Assistant. Each language is one JSON file (``i18n/en.json``, ``i18n/fr.json``...) with
the glossary of the controller's German words, the circuit labels and descriptions, the explanations of the
main variables and the strings of the sidebar panel. A language that lacks a key falls back to English, so a
new language can be added by copying ``en.json`` and translating what it can. Words that are not in the
glossary are kept as they are rather than guessed.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any

from .catalog import group_of, pretty

I18N_DIR = Path(__file__).parent / "i18n"
DEFAULT_LANGUAGE = "en"
SUFFIXES = {"ist", "soll", "act", "set"}  # shown in brackets after the name: "Room temperature (actual)"


def available_languages() -> list[str]:
    """Codes of the language files that ship with the integration."""
    return sorted(path.stem for path in I18N_DIR.glob("*.json"))


def _merge(base: dict[str, Any], over: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for key, value in over.items():
        out[key] = _merge(out[key], value) if isinstance(value, dict) and isinstance(out.get(key), dict) else value
    return out


class Texts:
    """The words of one language."""

    def __init__(self, lang: str, data: dict[str, Any]) -> None:
        self.lang = lang
        self._d = data

    @classmethod
    def load(cls, language: str) -> Texts:
        """Read the language of Home Assistant (``fr``, ``fr-CA``...), English if there is no file for it."""
        base = json.loads((I18N_DIR / f"{DEFAULT_LANGUAGE}.json").read_text(encoding="utf-8"))
        code = re.split(r"[-_]", language or DEFAULT_LANGUAGE)[0].lower()
        path = I18N_DIR / f"{code}.json"
        if code != DEFAULT_LANGUAGE and path.exists():
            return cls(code, _merge(base, json.loads(path.read_text(encoding="utf-8"))))
        return cls(DEFAULT_LANGUAGE, base)

    def panel(self) -> dict[str, Any]:
        """The strings of the sidebar panel."""
        return self._d["panel"]

    def _group(self, group_id: str) -> tuple[str, int | None]:
        match = re.fullmatch(r"([a-z0-9]+?)(\d+)", group_id)
        return (match.group(1), int(match.group(2))) if match else (group_id, None)

    def group_title(self, group_id: str) -> str:
        """'hk0' -> 'Heating circuit 1'."""
        kind, index = self._group(group_id)
        label = self._d["groups"].get(kind, {}).get("label", kind.title())
        return label if index is None else f"{label} {index + 1}"

    def group_description(self, group_id: str) -> str:
        """Short explanation of what the group of entities is."""
        return self._d["groups"].get(self._group(group_id)[0], {}).get("description", "")

    def friendly_name(self, key: str) -> str:
        """'LOCAL.L_hk[0].raumtemp_ist' -> 'Room temperature (actual)'."""
        if key in self._d["names"]:
            return self._d["names"][key]
        glossary = self._d["glossary"]
        words = re.findall(r"[A-Za-z]+|\d+", pretty(key))
        suffix = ""
        if len(words) > 1 and words[-1].lower() in SUFFIXES and words[-1].lower() in glossary:
            suffix = glossary[words.pop().lower()]
        parts = []
        for word in words:
            text = glossary.get(word.lower())
            if text is None:
                text = word.upper() if word.isalpha() and len(word) <= 3 else word
            if text:
                parts.append(text)
        name = " ".join(parts) or key
        if suffix:
            name += f" ({suffix})"
        return name[0].upper() + name[1:]

    def entity_description(self, key: str) -> str:
        """The specific explanation if there is one, otherwise 'Group: name'."""
        if key in self._d["descriptions"]:
            return self._d["descriptions"][key]
        return f"{self.group_title(group_of(key)[0])}: {self.friendly_name(key)}"

    def build_names(self, keys: list[str]) -> dict[str, str]:
        """Names unique inside each group: duplicates get the controller's variable name appended."""
        names = {key: self.friendly_name(key) for key in keys}
        seen: dict[tuple[str, str], list[str]] = {}
        for key, name in names.items():
            seen.setdefault((group_of(key)[0], name), []).append(key)
        for (_, name), same in seen.items():
            if len(same) > 1:
                for key in same:
                    names[key] = f"{name} [{pretty(key)}]"
        return names
