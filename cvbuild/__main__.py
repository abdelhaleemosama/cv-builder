import sys

if sys.version_info < (3, 11):  # noqa: UP036  (a friendly message for an older interpreter)
    sys.exit("cv needs Python 3.11 or later.")

from .cli import main

sys.exit(main())
