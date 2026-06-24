"""Runtime compatibility checks for Silmari Auth API."""
from __future__ import annotations

import sys


MINIMUM_PYTHON = (3, 10)


def ensure_supported_python() -> None:
    """Stop early when the API is started on an unsupported interpreter."""
    if sys.version_info < MINIMUM_PYTHON:
        version = '.'.join(map(str, sys.version_info[:3]))
        raise RuntimeError(
            f"Silmari Auth API requires Python 3.10 or newer; current interpreter is {version}."
        )
