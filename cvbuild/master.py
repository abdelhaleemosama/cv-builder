"""The master profile: every fact about a person, written once, with ids so a CV can select from it."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path
from typing import Any

from .errors import ProfileError
from .text import plain
from .vocabulary import has_term, terms_in


class Master:
    def __init__(self, path: Path | str):
        self.path = Path(path)
        try:
            self.data: dict[str, Any] = tomllib.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            raise ProfileError(f"No master profile at {self.path}. Run `cv init` to create one from the example.") from None
        except tomllib.TOMLDecodeError as error:
            raise ProfileError(f"{self.path} is not valid TOML: {error}") from None
        if "basics" not in self.data:
            raise ProfileError(f"{self.path} has no [basics] table (name, location, phone, email).")
        self.problems: list[str] = []
        self.experience = self._index("experience")
        self.projects = self._index("projects")
        self.education = self._index("education", items=False)
        self.certifications = self._index("certifications", items=False)
        # Everything the profile says, as plain text: what a CV is allowed to claim.
        self.corpus = plain(self._all_text(self.data))
        self.terms = terms_in(self.corpus)

    def _index(self, key: str, items: bool = True) -> dict[str, dict]:
        out: dict[str, dict] = {}
        for entry in self.data.get(key, []):
            ident = entry.get("id")
            if not ident or ident in out:
                self.problems.append(f"master: every [[{key}]] needs a unique id (got {ident!r})")
                continue
            out[ident] = entry
            if items:
                seen: set[str] = set()
                for item in entry.get("items", []):
                    if not item.get("id") or item["id"] in seen:
                        self.problems.append(f"master: {key} '{ident}' has a bullet with a missing or repeated id")
                    seen.add(item.get("id"))
                    if not (item.get("short") or item.get("long")):
                        self.problems.append(f"master: {key} '{ident}' bullet '{item.get('id')}' has no text")
        return out

    def _all_text(self, node: Any) -> str:
        if isinstance(node, str):
            return node
        if isinstance(node, list):
            return "\n".join(self._all_text(n) for n in node)
        if isinstance(node, dict):
            return "\n".join(self._all_text(v) for k, v in node.items() if k not in ("id", "tags"))
        return ""

    def item(self, entry: dict, item_id: str) -> dict | None:
        return next((i for i in entry.get("items", []) if i.get("id") == item_id), None)

    def knows(self, skill: str) -> bool:
        """A skill may be listed if the profile mentions it anywhere (skills, bullets, certifications)."""
        core = re.sub(r"\s*\(.*?\)\s*", " ", skill).strip() or skill
        return has_term(self.corpus, skill) or has_term(self.corpus, core)

    def outline(self) -> str:
        lines = [f"Master profile: {self.path}", ""]
        for key, label in (("experience", "EXPERIENCE"), ("projects", "PROJECTS")):
            lines.append(label)
            for ident, entry in getattr(self, key).items():
                title = entry.get("title") or entry.get("name")
                lines.append(f"  {ident}  {title}  [{entry.get('dates', '')}]")
                for item in entry.get("items", []):
                    variants = "/".join(v for v in ("short", "long") if item.get(v))
                    words = plain(item.get("short") or item.get("long")).split()
                    lines.append(f"    {item['id']:<24} ({variants}) tags: {', '.join(item.get('tags', []))}")
                    lines.append(f"        {' '.join(words[:16])}...")
            lines.append("")
        lines.append("SKILLS")
        lines.extend(f"  {group['group']}: {', '.join(group['items'])}" for group in self.data.get("skills", []))
        lines.append("")
        lines.append("CERTIFICATIONS: " + ", ".join(self.certifications))
        lines.append("SUMMARIES: " + ", ".join(self.data.get("summaries", {})))
        return "\n".join(lines)
