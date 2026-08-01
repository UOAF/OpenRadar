"""Single source of truth for the OpenRadar version.

Deliberately free of imports so that anything (app, UI, logging, build tooling) can read
the version without pulling in modules that do work at import time.

Keep this in sync with the git tag used for a release. Tags are expected to look like
``v1.0.0`` - the build workflow only produces artifacts for tags starting with "v".
"""

__version__ = "1.0.0"

APP_NAME = "OpenRadar"

# Convenience string for window titles, about dialogs and log headers.
VERSION_STRING = f"{APP_NAME} {__version__}"
