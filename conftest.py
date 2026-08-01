"""Pytest configuration for OpenRadar.

Puts ``src/`` on sys.path so tests can import application modules the same way the app
does (``import config``, ``from game_object import GameObject``, ...) without every test
file having to set the path up itself.
"""
import sys
from pathlib import Path

SRC = Path(__file__).parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
