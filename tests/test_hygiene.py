"""Guards against personal data reaching the repository."""

import re
import subprocess
import unittest

from .support import ROOT

# Private data lives in these folders, which .gitignore must keep out of git.
PRIVATE = ["/profile/", "/selections/", "/applications/"]
EMAIL = re.compile(r"[\w.+-]+@([\w-]+\.)+[a-z]{2,}", re.IGNORECASE)
HARMLESS_EMAIL_DOMAINS = ("example.com", "example.org", "users.noreply.github.com")
HOME_FOLDER = "/" + "Users" + "/"  # built in pieces so this file does not match itself


def tracked_files() -> list[str]:
    """Files git tracks or would add (not ignored), or an empty list outside a git checkout."""
    result = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard"], cwd=ROOT, capture_output=True, text=True, check=False)
    return [line for line in result.stdout.splitlines() if line] if result.returncode == 0 else []


class Hygiene(unittest.TestCase):
    def test_private_folders_are_ignored(self):
        ignored = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
        for folder in PRIVATE:
            self.assertIn(folder, ignored)

    def test_no_tracked_file_holds_a_real_email_or_a_personal_path(self):
        for name in tracked_files():
            path = ROOT / name
            if path.suffix in (".png", ".pdf") or not path.is_file():
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            for match in EMAIL.finditer(text):
                self.assertTrue(match.group(0).lower().endswith(HARMLESS_EMAIL_DOMAINS), f"{name} holds an email address: {match.group(0)}")
            self.assertNotIn(HOME_FOLDER, text, f"{name} holds a personal path")

    def test_no_private_file_is_tracked(self):
        for name in tracked_files():
            self.assertFalse(name.startswith(("profile/", "selections/", "applications/")), f"{name} is private data")


if __name__ == "__main__":
    unittest.main()
