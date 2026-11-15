"""Turning a selection into the document to render, and refusing anything the profile does not back.

A selection never adds facts. It picks bullets from the master profile by id, may reword one
(`text`), and lists skills. `resolve` returns the document and every problem it found: unknown ids,
skills that are nowhere in the profile, and numbers or technologies in reworded text that the
profile does not back.
"""

from __future__ import annotations

from typing import Any

from . import rules
from .master import Master
from .text import bold_terms, numbers_in, plain
from .vocabulary import has_term, terms_in

SECTIONS = ["summary", "education", "experience", "projects", "skills", "certifications"]
HEADINGS = {
    "summary": "Professional Summary",
    "education": "Education",
    "experience": "Professional Experience",
    "projects": "Projects",
    "skills": "Technical Skills",
    "certifications": "Certifications and Languages",
}


def blocking(problems: list[str]) -> list[str]:
    return [p for p in problems if not p.startswith("note:")]


def _check_free_text(label: str, text: str, backing: str, master: Master, problems: list[str], source: str = "the master profile for this item") -> None:
    """Reworded text may not carry a number or a technology that its source does not."""
    unbacked = sorted(numbers_in(plain(text)) - numbers_in(plain(backing)))
    if unbacked:
        problems.append(f"{label}: the number(s) {', '.join(unbacked)} are not in {source}")
    unknown = sorted(term for term in terms_in(plain(text)) if term not in master.terms)
    if unknown:
        problems.append(f"{label}: mentions {', '.join(unknown)}, which the master profile does not contain")


def _bullets(kind: str, entry: dict, chosen: list | None, default_variant: str, master: Master, problems: list[str]) -> list[str]:
    wanted = chosen if chosen is not None else [i["id"] for i in entry.get("items", []) if i.get(default_variant) or i.get("short")]
    out: list[str] = []
    for ref in wanted:
        ref = {"id": ref} if isinstance(ref, str) else ref
        item = master.item(entry, ref.get("id", ""))
        where = f"{kind} '{entry['id']}' bullet '{ref.get('id')}'"
        if item is None:
            problems.append(f"{where}: no such bullet in the master profile")
            continue
        if ref.get("text"):
            source = " ".join(str(item.get(v, "")) for v in ("short", "long"))
            source += " " + " ".join(str(entry.get(k, "")) for k in ("title", "name", "blurb", "intro"))
            _check_free_text(where, ref["text"], source, master, problems)
            out.append(ref["text"])
            continue
        variant = ref.get("variant", default_variant)
        if not item.get(variant):
            problems.append(f"note: {where} has no '{variant}' wording; used the other one")
        out.append(item.get(variant) or item.get("short") or item.get("long"))
    return out


def _summary(master: Master, selection: dict, problems: list[str]) -> str | None:
    summaries = master.data.get("summaries", {})
    wanted = selection.get("summary", "default")
    if wanted in summaries:
        return summaries[wanted]
    if wanted:
        # A number elsewhere in the profile ("9 partners") must not back a claim about the person
        # ("9 years"), so a custom summary may only reuse figures the stored summaries state.
        stored = " ".join(summaries.values())
        _check_free_text("summary", wanted, stored, master, problems, "any summary in the master profile (add a summary variant there first)")
        return wanted
    return None


def _education(master: Master, selection: dict, variant: str, problems: list[str]) -> list[dict]:
    options = selection.get("education", {})
    entries = []
    for edu in master.education.values():
        coursework = options.get("coursework")
        if coursework is None:
            coursework = edu.get("coursework_short" if variant == "short" else "coursework", [])
        else:
            known = {c.lower() for c in edu.get("coursework", []) + edu.get("coursework_short", [])}
            problems.extend(f"education: course '{c}' is not in the master profile" for c in coursework if c.lower() not in known)
        school = edu.get("school_short" if variant == "short" else "school", edu.get("school"))
        entries.append({**edu, "coursework_shown": coursework, "school_shown": school})
    return entries


def _entries(name: str, master: Master, selection: dict, variant: str, bold: list[str], bolded: set[str], problems: list[str]) -> list[dict]:
    index = master.experience if name == "experience" else master.projects
    chosen = selection.get(name)
    if chosen is None:
        chosen = [{"id": ident} for ident in index]
    entries = []
    for ref in chosen:
        ref = {"id": ref} if isinstance(ref, str) else ref
        entry = index.get(ref.get("id", ""))
        if entry is None:
            problems.append(f"{name}: no '{ref.get('id')}' in the master profile")
            continue
        shown = dict(entry)
        entry_variant = ref.get("variant", variant)
        shown["bullets"] = _bullets(name, entry, ref.get("items"), entry_variant, master, problems)
        if entry_variant == "long" and entry.get("blurb_long"):
            shown["blurb"] = entry["blurb_long"]
        for field in ("intro", "blurb"):
            if ref.get(field) is False:
                shown[field] = ""
            elif isinstance(ref.get(field), str):
                _check_free_text(f"{name} '{entry['id']}' {field}", ref[field], master.corpus, master, problems)
                shown[field] = ref[field]
        shown["bullets"] = [bold_terms(b, bold, bolded) for b in shown["bullets"]]
        entries.append(shown)
    return entries


def _skills(master: Master, selection: dict, problems: list[str]) -> list[tuple[str, list[str], list[str]]]:
    groups = selection.get("skills")
    if groups is None:
        groups = master.data.get("skills", [])
    shown = []
    for group in groups:
        items, also = group.get("items", []), group.get("also", [])
        problems.extend(f"skills: '{s}' is not in the master profile. Add it there first if it is true." for s in [*items, *also] if not master.knows(s))
        shown.append((group["group"], items, also))
    return shown


def _certifications(master: Master, selection: dict, problems: list[str]) -> list[str]:
    wanted = selection.get("certifications")
    if wanted is None:
        wanted = list(master.certifications)
    lines = []
    for ident in wanted:
        cert = master.certifications.get(ident)
        if cert is None:
            problems.append(f"certifications: no '{ident}' in the master profile")
        else:
            lines.append(cert["text"])
    languages = master.data.get("languages", {}).get("text")
    if languages and selection.get("languages", True):
        lines.append(f"**Languages:** {languages}")
    return lines


def resolve(master: Master, selection: dict[str, Any]) -> tuple[dict, list[str]]:
    """Returns (document, problems). Problems starting with "note:" do not block a build."""
    problems = list(master.problems)
    variant = selection.get("variant", "short")
    sections = selection.get("sections", SECTIONS)
    problems.extend(f"sections: unknown section '{s}' (known: {', '.join(SECTIONS)})" for s in sections if s not in SECTIONS)

    bold = [t for t in selection.get("bold", []) if isinstance(t, str) and t.strip()]
    problems.extend(f"bold: '{t}' is not in the master profile, so there is nothing to bold" for t in bold if not has_term(master.corpus, t))
    bolded: set[str] = set()

    doc: dict = {"basics": master.data["basics"], "sections": []}
    for name in (s for s in sections if s in SECTIONS):
        if name == "summary":
            text = _summary(master, selection, problems)
            if text:
                doc["sections"].append((name, text))
        elif name == "education":
            doc["sections"].append((name, _education(master, selection, variant, problems)))
        elif name in ("experience", "projects"):
            doc["sections"].append((name, _entries(name, master, selection, variant, bold, bolded, problems)))
        elif name == "skills":
            doc["sections"].append((name, _skills(master, selection, problems)))
        elif name == "certifications":
            doc["sections"].append((name, _certifications(master, selection, problems)))

    problems.extend(rules.check(doc, selection))
    return doc, problems
