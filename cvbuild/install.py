"""`cv install`: copies the tailor-cv skill and the recruiter agent into Claude Code's folders.

The skill refers to this tool by placeholders; installing fills in the real paths, so nothing in
the repository depends on where one person keeps their files. An existing symlink at the
destination is replaced, never written through (writing through it would overwrite the template).
"""

from __future__ import annotations

import shlex
from pathlib import Path

from . import paths
from .errors import CvError

SKILL_SOURCE = paths.REPO / "skill" / "tailor-cv" / "SKILL.md"
AGENT_SOURCE = paths.REPO / "agents" / "cv-recruiter.md"


def _fill(text: str) -> str:
    filled = text.replace("{{CV_BIN}}", shlex.quote(str(paths.REPO / "bin" / "cv"))).replace("{{CV_HOME}}", str(paths.home()))
    if "{{" in filled:
        raise CvError("The skill template has a placeholder that install does not know how to fill.")
    return filled


def _write(destination: Path, text: str) -> None:
    if destination.is_symlink():
        destination.unlink()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text, encoding="utf-8")


def install(target: Path) -> list[Path]:
    """Installs into `target` (Claude Code's config folder, usually ~/.claude). Returns the files written."""
    skill_dir = target / "skills" / "tailor-cv"
    if skill_dir.is_symlink():
        skill_dir.unlink()
    skill = skill_dir / "SKILL.md"
    agent = target / "agents" / "cv-recruiter.md"
    _write(skill, _fill(SKILL_SOURCE.read_text(encoding="utf-8")))
    _write(agent, _fill(AGENT_SOURCE.read_text(encoding="utf-8")))
    return [skill, agent]
