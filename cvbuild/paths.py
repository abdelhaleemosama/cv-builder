"""Where things live. Personal data is kept under one folder (the "home") that is not part of the code.

By default the home is the repository itself, whose .gitignore keeps `profile/`, `selections/` and
`applications/` out of git. Set CV_HOME to keep them somewhere else, or CV_PROFILE to point at a
different master profile file.
"""

from __future__ import annotations

import os
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def home() -> Path:
    return Path(os.environ.get("CV_HOME") or REPO)


def profile_path() -> Path:
    override = os.environ.get("CV_PROFILE")
    return Path(override) if override else home() / "profile" / "master.toml"


def selections_dir() -> Path:
    return home() / "selections"


def applications_dir() -> Path:
    return home() / "applications"


def examples_dir() -> Path:
    return REPO / "examples"
