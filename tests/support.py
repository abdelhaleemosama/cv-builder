"""Test support. Every test runs against the fictional example profile, never against real data."""

from __future__ import annotations

import contextlib
import io
import json
import os
import tempfile
import unittest
from collections.abc import Iterator
from pathlib import Path
from unittest import mock

from cvbuild import cli, render

ROOT = Path(__file__).resolve().parent.parent
MASTER_FILE = ROOT / "examples" / "master.toml"
GENERAL_FILE = ROOT / "examples" / "general.json"


def general() -> dict:
    return json.loads(GENERAL_FILE.read_text(encoding="utf-8"))


needs_browser = unittest.skipUnless(render.find_browser(), "no Chromium-based browser on this machine")


@contextlib.contextmanager
def cv_home() -> Iterator[Path]:
    """A temporary home for personal data, so tests never touch the real profile."""
    with tempfile.TemporaryDirectory(prefix="cv-test-") as folder:
        env = {key: value for key, value in os.environ.items() if key not in ("CV_PROFILE", "CV_HOME")}
        env["CV_HOME"] = folder
        with mock.patch.dict(os.environ, env, clear=True):
            yield Path(folder)


def run(*args: str, stdin: str = "") -> tuple[int, str, str]:
    """Runs `cv <args>` in-process. Returns (exit code, standard output, standard error)."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err), mock.patch("sys.stdin", io.StringIO(stdin)):
        code = cli.main(list(args))
    return code, out.getvalue(), err.getvalue()
