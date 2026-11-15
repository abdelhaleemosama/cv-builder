"""Checking a recruiter review against the CV it claims to describe.

The reviewer must quote the CV as evidence for each requirement. A quote that is not in the CV does
not count, so the "requirements with evidence" figure is counted, not estimated, and there is no
score to chase.
"""

from __future__ import annotations

from .text import squash

MAX_REVIEW_ROUNDS = 2


def review_summary(review: dict, cv_text: str) -> dict:
    haystack = squash(cv_text)
    rows, misquoted = [], []
    for item in review.get("requirements", []):
        quote = item.get("evidence")
        found = bool(quote) and squash(quote).strip(" .;,") in haystack
        if quote and not found:
            misquoted.append(item.get("requirement", "?"))
        rows.append(
            {
                "requirement": item.get("requirement", "?"),
                "level": item.get("level", "must"),
                "proved": found,
                "weak": bool(item.get("weak")) and found,
            }
        )
    musts = [r for r in rows if r["level"] == "must"]
    findings = review.get("findings", [])
    must_fix = [f for f in findings if f.get("severity") == "must-fix"]
    return {
        "rows": rows,
        "musts": len(musts),
        "musts_proved": sum(r["proved"] for r in musts),
        "unproved": [r["requirement"] for r in musts if not r["proved"]],
        "weak": [r["requirement"] for r in rows if r["weak"]],
        "misquoted": misquoted,
        "fixable": [f for f in must_fix if f.get("kind") != "gap"],
        "gaps": [f for f in must_fix if f.get("kind") == "gap"],
        "optional": [f for f in findings if f.get("severity") != "must-fix"],
        "keep_reading": review.get("skim", {}).get("keep_reading", True),
        "questions": review.get("questions", []),
    }
