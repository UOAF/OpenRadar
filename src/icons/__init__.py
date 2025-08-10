"""
Icon sets for OpenRadar.

This module contains different icon styling systems that can be selected by the user.
Each icon set defines how game objects should be rendered based on their type and coalition.
"""

from .NTDS import NTDSIconSet
from .classic import ClassicIconSet

# Registry of all available icon sets
ICON_SETS = {'NTDS': NTDSIconSet, 'classic': ClassicIconSet}

# Default icon set
DEFAULT_ICON_SET = 'classic'


def get_available_icon_sets():
    """Get a list of all available icon sets."""
    return [(name, icon_set.display_name) for name, icon_set in ICON_SETS.items()]


def get_icon_set(name: str):
    """Get an icon set by name, falling back to default if not found."""
    return ICON_SETS.get(name, ICON_SETS[DEFAULT_ICON_SET])
