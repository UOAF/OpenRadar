"""
NTDS icon set for OpenRadar.

This icon set uses NTDS symbology-inspired shapes and colors.
"""
from coalition_manager import coalition_manager
from typing import Optional, Tuple
from game_object_types import GameObjectType
from draw.shapes import Shapes


class NTDSIconSet:
    """NTDS icon set with Naval-style symbology."""

    name = "NTDS"
    display_name = "NTDS"

    @staticmethod
    def get_icon_style(game_object, coalition: str,
                       object_type: GameObjectType) -> Tuple[Shapes, Optional[Tuple[int, int, int, int]]]:
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

        base_color = None

        # Fixed wing aircraft
        if object_type == GameObjectType.FIXEDWING:

            # coalition contains the country tag
            # example: "USA", "PRC", "ROK", "DPRK"
            # Ask coalition manager for actual relation
            relation = coalition_manager.get_relation(coalition)

            if relation == "friendly":
                return (Shapes.SEMICIRCLE, base_color)  # Friendly
            elif relation == "hostile":
                return (Shapes.DIAMOND, base_color)  # Hostile
            elif relation == "neutral":
                return (Shapes.SQUARE, base_color)  # Neutral / unknown

        # Rotary wing aircraft (helicopters)
        elif object_type == GameObjectType.ROTARYWING:

            relation = coalition_manager.get_relation(coalition)

            if relation == "friendly":
                return (Shapes.TOP_BOX, base_color)  # Blue semicircle
            elif relation == "hostile":
                return (Shapes.HALF_DIAMOND, base_color)  # Red half diamond
            elif relation == "neutral":
                return (Shapes.HALF_DIAMOND, base_color)  # Yellow semicircle

        # Missiles
        elif object_type == GameObjectType.MISSILE:

            relation = coalition_manager.get_relation(coalition)
            if relation == "friendly":
                return (Shapes.SMALL_DIAMOND, base_color)  # Light blue top box
            elif relation == "hostile":
                return (Shapes.SMALL_DIAMOND, base_color)  # Light red top box
            elif relation == "neutral":
                return (Shapes.SMALL_DIAMOND, base_color)  # Light yellow top box

        # Ground units
        elif object_type == GameObjectType.GROUND:

            relation = coalition_manager.get_relation(coalition)
            if relation == "friendly":
                return (Shapes.CIRCLE, base_color)  # Dark blue square
            elif relation == "hostile":
                return (Shapes.CIRCLE, base_color)  # Dark red square
            elif relation == "neutral":
                return (Shapes.CIRCLE, base_color)  # Dark yellow square

        # Sea units
        elif object_type == GameObjectType.SEA:

            relation = coalition_manager.get_relation(coalition)
            if relation == "friendly":
                return (Shapes.SHIP, base_color)  # Blue ship
            elif relation == "hostile":
                return (Shapes.SHIP, base_color)  # Red ship
            elif relation == "neutral":
                return (Shapes.SHIP, base_color)  # Yellow ship

        # Bullseye reference points
        elif object_type == GameObjectType.BULLSEYE:
            return (None, base_color)  # White circle

        # Unknown or fallback
        else:
            return (Shapes.CIRCLE, base_color)  # Gray circle
