"""Game Object Type definitions.

This module defines the types of game objects that can exist in the radar system.
Separated from other modules to avoid circular imports.
"""
from enum import Enum, auto
from typing import Dict


class GameObjectType(Enum):
    """Enumeration of game object types supported by the radar system."""
    FIXEDWING = auto()
    ROTARYWING = auto()
    MISSILE = auto()
    GROUND = auto()
    SEA = auto()
    BULLSEYE = auto()
    UNKNOWN = auto()

    @property
    def display_name(self) -> str:
        """Human-readable display name for this type."""
        return _TYPE_DISPLAY_NAMES.get(self, self.name.title())

    @property
    def tacview_class(self) -> str:
        """Tacview class string that maps to this type."""
        return _TYPE_TACVIEW_MAP.get(self, "")


# Display name mappings
_TYPE_DISPLAY_NAMES: Dict[GameObjectType, str] = {
    GameObjectType.FIXEDWING: "Fixed Wing",
    GameObjectType.ROTARYWING: "Helicopter",
    GameObjectType.MISSILE: "Missile",
    GameObjectType.GROUND: "Ground",
    GameObjectType.SEA: "Sea",
    GameObjectType.BULLSEYE: "Bullseye",
    GameObjectType.UNKNOWN: "Unknown",
}

# Tacview type string mappings (for parsing)
_TYPE_TACVIEW_MAP: Dict[GameObjectType, str] = {
    GameObjectType.FIXEDWING: "FixedWing",
    GameObjectType.ROTARYWING: "Rotorcraft",
    GameObjectType.MISSILE: "Missile",
    GameObjectType.GROUND: "Ground+Vehicle",
    GameObjectType.SEA: "Watercraft",
    GameObjectType.BULLSEYE: "Navaid+Static+Bullseye",
}

# Reverse mapping for efficient lookup during parsing
_TACVIEW_TO_TYPE: Dict[str, GameObjectType] = {
    tacview_class: obj_type
    for obj_type, tacview_class in _TYPE_TACVIEW_MAP.items()
}


def infer_object_type_from_tacview(type_field: str) -> GameObjectType:
    """Infer GameObjectType from Tacview Type field string.
    
    Args:
        type_field: The Type field from Tacview/ACMI data (e.g. "Air+FixedWing")
        
    Returns:
        The corresponding GameObjectType, or UNKNOWN if no match found.
    """
    # Check each known Tacview class to see if it appears in the type field
    for tacview_class, obj_type in _TACVIEW_TO_TYPE.items():
        if tacview_class in type_field:
            return obj_type

    return GameObjectType.UNKNOWN


def get_all_object_types() -> list[GameObjectType]:
    """Get list of all defined object types except UNKNOWN."""
    return [t for t in GameObjectType if t != GameObjectType.UNKNOWN]
