class CvError(Exception):
    """An expected failure. The command line prints its message and exits with status 1."""


class ProfileError(CvError):
    """The master profile is missing or cannot be read."""


class RenderError(CvError):
    """The PDF could not be produced (no browser, or the browser failed)."""
