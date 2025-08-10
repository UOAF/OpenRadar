"""Game Object Type definitions.

This module defines the types of game objects that can exist in the radar system.
Separated from other modules to avoid circular imports.
"""
from enum import Enum, auto

import config


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
_TYPE_DISPLAY_NAMES: dict[GameObjectType, str] = {
    GameObjectType.FIXEDWING: "Fixed Wing",
    GameObjectType.ROTARYWING: "Helicopter",
    GameObjectType.MISSILE: "Missile",
    GameObjectType.GROUND: "Ground",
    GameObjectType.SEA: "Sea",
    GameObjectType.BULLSEYE: "Bullseye",
    GameObjectType.UNKNOWN: "Unknown",
}

# Tacview type string mappings (for parsing)
_TYPE_TACVIEW_MAP: dict[GameObjectType, str] = {
    GameObjectType.FIXEDWING: "FixedWing",
    GameObjectType.ROTARYWING: "Rotorcraft",
    GameObjectType.MISSILE: "Missile",
    GameObjectType.GROUND: "Ground+Vehicle",
    GameObjectType.SEA: "Watercraft",
    GameObjectType.BULLSEYE: "Navaid+Static+Bullseye",
}

# Reverse mapping for efficient lookup during parsing
_TACVIEW_TO_TYPE: dict[str, GameObjectType] = {
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


def get_icon_style(game_object) -> tuple[int | None, tuple[int, int, int, int] | None]:
    """
    Get the icon shape ID and optional color override for a game object.
    
    Args:
        game_object: The game object to get icon for (must have object_type, Coalition attributes)
        config: Configuration object to get icon set preference from
        
    Returns:
        Tuple of (shape_id, color_override)
        shape_id: Integer ID corresponding to Shapes enum value
        color_override: (R, G, B, A) values 0-255, or None for default color
    """
    # Import here to avoid circular imports
    from icons import get_icon_set, DEFAULT_ICON_SET
    from draw.shapes import Shapes

    # Get icon set preference from config or use default
    icon_set_name = config.app_config.get_str('display', 'icon_set')
    # Get the icon set class
    icon_set_class = get_icon_set(icon_set_name)

    # Get the shape and color from the icon set
    shape, color_override = icon_set_class.get_icon_style(game_object, game_object.Coalition, game_object.object_type)

    # Convert Shapes enum to integer ID (shapes use .value.idx for the ID)
    if shape is None:
        shape_id = None
    else:
        shape_id = shape.value.idx

    return shape_id, color_override
