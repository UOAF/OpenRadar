"""
Classic radar icon set for OpenRadar.

This icon set mimics classic radar display symbology with traditional shapes.
"""

from game_object_types import GameObjectType
from draw.shapes import Shapes


class ClassicIconSet:
    """Classic radar icon set with traditional radar symbology."""

    name = "classic"
    display_name = "Classic OpenRadar"

    @staticmethod
    def get_icon_style(game_object, coalition: str,
                       object_type: GameObjectType) -> tuple[Shapes | None, tuple[int, int, int, int] | None]:
        """
        Get the icon shape and optional color override for a game object.
        
        Args:
            game_object: The game object to get icon for
            coalition: Coalition string (e.g., "Blue", "Red", "Neutral")
            object_type: The GameObjectType enum value
            
        Returns:
            Tuple of (shape, color_override)
            color_override is (R, G, B, A) values 0-255, or None for default color
        """

        # Use the tacview color
        base_color = None

        # Classic radar shape conventions
        if object_type == GameObjectType.FIXEDWING:
            return (Shapes.SQUARE, base_color)

        elif object_type == GameObjectType.ROTARYWING:
            return (Shapes.SQUARE, base_color)

        elif object_type == GameObjectType.MISSILE:
            return (Shapes.SMALL_DIAMOND, base_color)

        elif object_type == GameObjectType.GROUND:
            return (Shapes.CIRCLE, base_color)

        elif object_type == GameObjectType.SEA:
            return (Shapes.SHIP, base_color)

        elif object_type == GameObjectType.BULLSEYE:
            return (None, base_color)

        else:
            # Unknown gets a half diamond
            return (Shapes.HALF_DIAMOND, None)
