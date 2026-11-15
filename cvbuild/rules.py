"""House rules for every CV: a short summary, nothing said twice, numbers that prove the work.

Problems are blocking (the build refuses). Problems starting with "note:" are judgment calls
worth a look but never block a build.
"""

from __future__ import annotations

import re

from .text import plain

SUMMARY_WORDS = 60
BOLD_TERMS = 10
OPENING_REPEATS = 3
PHRASE_WORDS = 5


def _bullets(doc: dict) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for name, content in doc["sections"]:
        if name in ("experience", "projects"):
            for entry in content:
                label = entry.get("company") or entry.get("name", "").split(" - ")[0]
                found.extend((label, bullet) for bullet in entry["bullets"])
    return found


def check(doc: dict, selection: dict) -> list[str]:
    problems: list[str] = []
    bullets = _bullets(doc)

    for name, content in doc["sections"]:
        if name == "summary":
            words = len(plain(content).split())
            if words > SUMMARY_WORDS:
                problems.append(f"summary: {words} words; keep it to {SUMMARY_WORDS} or fewer (two or three lines)")
        elif name == "skills":
            listed: dict[str, str] = {}
            for group, items, also in content:
                for item in [*items, *also]:
                    key = item.lower()
                    if key in listed:
                        problems.append(f"skills: '{item}' is listed twice ({listed[key]} and {group})")
                    listed[key] = group

    seen: dict[str, str] = {}
    for label, bullet in bullets:
        key = plain(bullet).lower()
        if key in seen:
            problems.append(f"the same bullet appears twice ({seen[key]} and {label}): {plain(bullet)[:50]}...")
        seen[key] = label

    bold = selection.get("bold", [])
    if len(bold) > BOLD_TERMS:
        problems.append(f"bold: {len(bold)} keywords; bold at most {BOLD_TERMS}, or nothing stands out")

    problems.extend(_notes(bullets))
    return problems


def _notes(bullets: list[tuple[str, str]]) -> list[str]:
    notes: list[str] = []
    unproven = [f"{label}: {' '.join(plain(b).split()[:6])}..." for label, b in bullets if not re.search(r"\d", plain(b))]
    if unproven:
        notes.append(f"note: no number to prove it in {len(unproven)} bullet(s): " + " | ".join(unproven))

    openings: dict[str, int] = {}
    for _label, bullet in bullets:
        words = plain(bullet).split(":", 1)[-1].split()
        if words:
            openings[words[0].lower()] = openings.get(words[0].lower(), 0) + 1
    repeated = [f"{word} (x{count})" for word, count in openings.items() if count >= OPENING_REPEATS]
    if repeated:
        notes.append("note: several bullets open with the same word: " + ", ".join(repeated))

    phrases: dict[str, set[int]] = {}
    for index, (_label, bullet) in enumerate(bullets):
        words = re.findall(r"[a-z0-9']+", plain(bullet).lower())
        for at in range(len(words) - PHRASE_WORDS + 1):
            phrases.setdefault(" ".join(words[at : at + PHRASE_WORDS]), set()).add(index)
    twice = sorted(phrase for phrase, where in phrases.items() if len(where) > 1)
    if twice:
        notes.append("note: said in more than one bullet: " + "; ".join(f'"{p}"' for p in twice[:4]))
    return notes
