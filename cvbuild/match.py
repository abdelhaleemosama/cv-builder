"""Comparing a job description with a CV."""

from __future__ import annotations

from .master import Master
from .vocabulary import terms_in


def keyword_report(job_text: str, cv_text: str, master: Master, extra: list[str] | None = None) -> dict[str, list[str]]:
    """Sorts the job description's terms: in the CV, true but not shown, and real gaps.

    "addable" terms are in the master profile but not on this CV: consider adding them.
    "gaps" are in neither: the person lacks them, so they must not be added.
    """
    wanted = terms_in(job_text, extra)
    in_cv = terms_in(cv_text, extra)
    in_master = terms_in(master.corpus, extra)
    return {
        "covered": sorted(wanted & in_cv, key=str.lower),
        "addable": sorted((wanted - in_cv) & in_master, key=str.lower),
        "gaps": sorted(wanted - in_cv - in_master, key=str.lower),
    }
