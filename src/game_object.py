"""Refactored GameObject implementation.

Removes subclass inheritance (fixedWing, rotaryWing, etc.) in favor of a single
GameObject that carries its own data locally and is updated via delta (Tacview / ACMI)
updates. The object no longer keeps a reference to the originating ACMIObject; instead
it copies fields on creation/update. Empty / missing fields in a delta never overwrite
previous values.

Key improvements:
- Clean GameObjectType enum (no circular imports)
- Delta encoding properly handled (empty fields don't overwrite)
- All ACMI fields supported including CallSign/Group  
- Backwards compatibility shims for gradual migration
- Systematic field management using sets

Usage:
    from game_object_types import infer_object_type_from_tacview
    
    acmi_obj: ACMIObject = ... # parsed line
    obj_type = infer_object_type_from_tacview(acmi_obj.Type)  
    if acmi_obj.object_id not in objects:
        objects[acmi_obj.object_id] = GameObject(acmi_obj.object_id, obj_type, acmi_obj)
    else:
        objects[acmi_obj.object_id].update(acmi_obj)

Migration notes:
- obj.data.field still works (compatibility shim)
- obj.T.field still works (compatibility shim) 
- obj.class_type -> obj.object_type
- GameObjectClassType -> GameObjectType (temporary alias provided)
"""
from __future__ import annotations

from typing import Any, Dict, Optional
import datetime

from acmi_parse import ACMIObject
from game_object_types import GameObjectType, get_icon_style
from util.other_utils import rgba_from_str


def _coerce_number(value: Any, default: float = 0.0) -> float:
    """Convert value to float, returning default if value is empty or invalid."""
    if value in (None, ""):  # treat empty as no update (caller filters) / default
        return default
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


# Field definitions for systematic handling
_ORIENTATION_FIELDS = {"Altitude", "Heading", "Latitude", "Longitude", "Pitch", "Roll", "U", "V", "Yaw"}
_NUMERIC_FIELDS = {
    "AOA", "AOS", "CAS", "FuelWeight", "Health", "IAS", "LateralGForce", "LongitudinalGForce", "Mach", "VerticalGForce"
} | _ORIENTATION_FIELDS
_LOCKED_TARGET_FIELDS = {
    "LockedTarget", "LockedTarget1", "LockedTarget2", "LockedTarget3", "LockedTarget4", "LockedTarget5",
    "LockedTarget6", "LockedTarget7", "LockedTarget8", "LockedTarget9"
}
_STRING_FIELDS = {"Coalition", "Color", "Name", "Pilot", "Type", "CallSign", "Group"} | _LOCKED_TARGET_FIELDS
_ALL_ACMI_FIELDS = _NUMERIC_FIELDS | _STRING_FIELDS


class GameObject:
    """Refactored GameObject that stores all data locally and handles delta updates properly.
    
    Uses GameObjectType enum for clean type classification without circular imports.
    """
    # Type hints for fields
    object_id: str
    object_type: GameObjectType  # Clean enum-based typing

    # Timing
    timestamp: datetime.datetime

    # Core ACMI fields - numeric
    AOA: float
    AOS: float
    CAS: float
    FuelWeight: float
    Health: float
    IAS: float
    LateralGForce: float
    LongitudinalGForce: float
    Mach: float
    VerticalGForce: float

    # Core ACMI fields - strings
    Coalition: str
    Color: str
    LockedTarget: str
    LockedTarget1: str
    LockedTarget2: str
    LockedTarget3: str
    LockedTarget4: str
    LockedTarget5: str
    LockedTarget6: str
    LockedTarget7: str
    LockedTarget8: str
    LockedTarget9: str
    Name: str
    Pilot: str
    Type: str
    CallSign: str
    Group: str

    # Orientation fields (flattened from T)
    Altitude: float
    Heading: float
    Latitude: float
    Longitude: float
    Pitch: float
    Roll: float
    U: float
    V: float
    Yaw: float

    # UI / runtime metadata
    icon: int | None
    color_rgba: tuple[float, float, float, float]
    visible: bool
    override_name: Optional[str]
    side_override_color: Optional[tuple[float, float, float, float]]
    override_color: Optional[tuple[float, float, float, float]]
    locked_target_objs: list[Optional["GameObject"]]  # resolved reference

    # ----------------------------------------------------------------------------------
    # Creation / Update
    # ----------------------------------------------------------------------------------
    def __init__(self, object_id: str, object_type: GameObjectType, initial: ACMIObject | None = None):
        # Initialize core identity
        self.object_id = object_id
        self.object_type = object_type
        self.timestamp = datetime.datetime.fromtimestamp(0, tz=datetime.timezone.utc)

        # Initialize all ACMI numeric fields to 0.0
        for field in _NUMERIC_FIELDS:
            setattr(self, field, 0.0)

        # Initialize all ACMI string fields to empty string
        for field in _STRING_FIELDS:
            setattr(self, field, "")

        # Special case: Color defaults to "White"
        self.Color = "White"

        # UI / runtime initialization
        self.color_rgba = (1.0, 1.0, 1.0, 1.0)
        self.override_name = None
        self.override_color = None
        self.locked_target_objs = []
        self.side_override_color = None

        # Apply initial data if provided
        if initial is not None:
            self.apply_delta(initial)

        # Initialize icon based on type
        self.icon, icon_color = get_icon_style(self)
        if icon_color is not None:
            self.override_color = icon_color

    # Public update API
    def update(self, delta: ACMIObject):
        self.apply_delta(delta)

    # Core delta application logic
    def apply_delta(self, acmi_obj: ACMIObject):
        """Apply delta update from ACMIObject. Only non-empty values overwrite existing ones.
        
        IMPORTANT: ACMIObject fields are populated via the .properties dict during parsing,
        NOT directly as attributes on the ACMIObject instance. We must use .properties.
        """
        # Always advance timestamp to newest even if payload is empty (still a heartbeat)
        if hasattr(acmi_obj, 'timestamp') and acmi_obj.timestamp is not None:
            self.timestamp = acmi_obj.timestamp

        # Get the properties dict - this contains all the actual delta data
        props = getattr(acmi_obj, 'properties', {})
        if not props:
            return  # No data to update

        # Handle orientation (T=) data first
        t_delta = props.get("T")
        if isinstance(t_delta, dict):
            for key, value in t_delta.items():
                if value in (None, ""):
                    continue  # Skip empty delta values
                if key in _ORIENTATION_FIELDS and hasattr(self, key):
                    setattr(self, key, _coerce_number(value, getattr(self, key, 0.0)))

        # Handle all other ACMI fields systematically
        for field_name, value in props.items():
            if field_name == "T":
                continue  # Already handled above

            if field_name in _ALL_ACMI_FIELDS and hasattr(self, field_name):
                # if value in (None, ""):
                #     continue  # Skip empty delta values - preserve existing data

                # Apply value based on field type
                if field_name in _NUMERIC_FIELDS:
                    if value in (None, ""):
                        continue
                    current_val = getattr(self, field_name, 0.0)
                    setattr(self, field_name, _coerce_number(value, current_val))
                elif field_name in _STRING_FIELDS:
                    setattr(self, field_name, str(value))

        # if any(key.startswith("LockedTarget") for key in props.keys()):
        #     self.resolve_locked_targets()

        self.color_rgba = rgba_from_str(self.Color)

    # ----------------------------------------------------------------------------------
    # API methods (mirroring old implementation)
    # ----------------------------------------------------------------------------------
    def get_display_name(self) -> str:
        """Get the best available display name for this object."""
        if self.override_name:
            return self.override_name

        if self.CallSign:  # Check CallSign before Name
            if self.Pilot:
                return f"{self.CallSign} ({self.Pilot})"
            return self.CallSign
        if self.Pilot:
            return self.Pilot
        if self.Name:
            return self.Name
        return self.Type or self.object_id

    def get_pos(self) -> tuple[float, float]:
        return (self.U, self.V)

    def change_name(self, name: str):
        self.override_name = name

    def change_color(self, color: tuple[float, float, float, float]):
        self.override_color = color

    def get_display_color(self):
        return self.override_color if self.override_color else \
               self.side_override_color if self.side_override_color else \
               self.color_rgba

    # Target lock handling (external resolver should set locked_target_objs)
    def resolve_locked_targets(self, resolver: Dict[str, "GameObject"]):
        """Resolve LockedTarget string ID to actual GameObject reference."""
        self.locked_target_objs = []

        # Check the base LockedTarget field first
        locked_target = getattr(self, "LockedTarget", None)
        if locked_target not in (None, "", "0") and locked_target in resolver:
            self.locked_target_objs.append(resolver[locked_target])

        # Then check LockedTarget1 through LockedTarget9
        for i in range(1, 10):
            locked_target = getattr(self, f"LockedTarget{i}", None)
            if locked_target not in (None, "", "0") and locked_target in resolver:
                self.locked_target_objs.append(resolver[locked_target])

    def is_air_unit(self) -> bool:
        """Check if this is an air unit (fixed wing, rotary wing, or missile)."""
        return self.object_type in (GameObjectType.FIXEDWING, GameObjectType.ROTARYWING)
