"""
NTDS icon set for OpenRadar.

This icon set uses NTDS symbology-inspired shapes and colors.
"""

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

        # Fixed wing aircraft
        if object_type == GameObjectType.FIXEDWING:
            if "Blue" in coalition or "US" in coalition:
                return (Shapes.SQUARE, (0, 100, 255, 255))  # Blue square
            elif "Red" in coalition or "OPFOR" in coalition:
                return (Shapes.DIAMOND, (255, 50, 50, 255))  # Red diamond
            else:
                return (Shapes.CIRCLE, (255, 255, 0, 255))  # Yellow circle for unknown

        # Rotary wing aircraft (helicopters)
        elif object_type == GameObjectType.ROTARYWING:
            if "Blue" in coalition or "US" in coalition:
                return (Shapes.SEMICIRCLE, (0, 150, 255, 255))  # Blue semicircle
            elif "Red" in coalition or "OPFOR" in coalition:
                return (Shapes.HALF_DIAMOND, (255, 50, 50, 255))  # Red half diamond
            else:
                return (Shapes.SEMICIRCLE, (255, 255, 0, 255))  # Yellow semicircle

        # Missiles
        elif object_type == GameObjectType.MISSILE:
            if "Blue" in coalition or "US" in coalition:
                return (Shapes.TOP_BOX, (100, 200, 255, 255))  # Light blue top box
            elif "Red" in coalition or "OPFOR" in coalition:
                return (Shapes.TOP_BOX, (255, 100, 100, 255))  # Light red top box
            else:
                return (Shapes.TOP_BOX, (255, 255, 100, 255))  # Light yellow top box

        # Ground units
        elif object_type == GameObjectType.GROUND:
            if "Blue" in coalition or "US" in coalition:
                return (Shapes.SQUARE, (0, 100, 200, 255))  # Dark blue square
            elif "Red" in coalition or "OPFOR" in coalition:
                return (Shapes.SQUARE, (200, 50, 50, 255))  # Dark red square
            else:
                return (Shapes.SQUARE, (150, 150, 0, 255))  # Dark yellow square

        # Sea units
        elif object_type == GameObjectType.SEA:
            if "Blue" in coalition or "US" in coalition:
                return (Shapes.SHIP, (0, 150, 255, 255))  # Blue ship
            elif "Red" in coalition or "OPFOR" in coalition:
                return (Shapes.SHIP, (255, 50, 50, 255))  # Red ship
            else:
                return (Shapes.SHIP, (255, 255, 0, 255))  # Yellow ship

        # Bullseye reference points
        elif object_type == GameObjectType.BULLSEYE:
            return (Shapes.CIRCLE, (255, 255, 255, 255))  # White circle

        # Unknown or fallback
        else:
            return (Shapes.CIRCLE, (128, 128, 128, 255))  # Gray circle
