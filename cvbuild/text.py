"""Small text helpers shared by the checks and the renderer.

Text in the master profile may carry light markup: `*italic*`, `**bold**` and `[label](https://...)`.
"""

from __future__ import annotations

import re

_LINK = re.compile(r"\[([^\]]+)\]\((?:https?://|mailto:)[^)\s]+\)")


def plain(text: str) -> str:
    """The text without emphasis marks or link targets."""
    return _LINK.sub(r"\1", text).replace("*", "")


def squash(text: str) -> str:
    """Lower-case, markup-free text with runs of whitespace collapsed, for comparing quotes."""
    return re.sub(r"\s+", " ", plain(text)).strip().lower()


def numbers_in(text: str) -> set[str]:
    return {n.replace(",", "") for n in re.findall(r"\d+(?:[.,]\d+)?", text)}


def bold_terms(text: str, terms: list[str], used: set[str]) -> str:
    """Bolds the first appearance of each term across the CV, never inside bold text or a link label."""
    for term in terms:
        if term.lower() in used:
            continue
        flags = 0 if len(term) <= 3 else re.IGNORECASE
        for match in re.finditer(r"(?<![A-Za-z0-9.*])" + re.escape(term) + r"(?![A-Za-z0-9+#*])", text, flags):
            before = text[: match.start()]
            if before.count("**") % 2 == 1 or before.count("[") > before.count("]"):
                continue
            text = f"{before}**{match.group(0)}**{text[match.end() :]}"
            used.add(term.lower())
            break
    return text
