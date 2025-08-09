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

from dataclasses import dataclass
from typing import Any, Dict, Optional
import datetime

from acmi_parse import ACMIObject, Orientation
from game_object_types import GameObjectType, infer_object_type_from_tacview


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
_STRING_FIELDS = {"Coalition", "Color", "LockedTarget", "Name", "Pilot", "Type", "CallSign", "Group"}
_ALL_ACMI_FIELDS = _NUMERIC_FIELDS | _STRING_FIELDS


@dataclass
class GameObjectDataShim:
    """Backwards compatibility shim so existing code that expects obj.data.<field>
    can continue to function while refactoring occurs. Accesses the owning
    GameObject's attributes directly. Do NOT store state here.
    """
    _owner: "GameObject"

    def __getattr__(self, item):  # pragma: no cover - simple delegation
        return getattr(self._owner, item)


class _OrientationView:
    """Property view to emulate previous obj.T.<field> access pattern.
    The underlying values are stored flatly on the GameObject instance.
    """

    def __init__(self, owner: "GameObject"):
        object.__setattr__(self, "_owner", owner)

    def __getattr__(self, name: str):  # pragma: no cover simple delegation
        if name in _ORIENTATION_FIELDS:
            return getattr(self._owner, name)
        raise AttributeError(name)

    def __setattr__(self, name: str, value: Any):  # pragma: no cover simple delegation
        if name in _ORIENTATION_FIELDS:
            setattr(self._owner, name, _coerce_number(value, getattr(self._owner, name)))
        else:
            raise AttributeError(name)


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
    color_rgba: tuple[float, float, float, float]
    visible: bool
    override_name: Optional[str]
    override_color: Optional[tuple[float, float, float, float]]
    locked_target_obj: Optional["GameObject"]  # resolved reference

    # Backwards compatibility property (simulate old obj.data usage)
    @property
    def data(self) -> GameObjectDataShim:  # pragma: no cover - simple shim
        return GameObjectDataShim(_owner=self)

    # Orientation compatibility property
    @property
    def T(self) -> _OrientationView:  # pragma: no cover - simple shim
        return _OrientationView(self)

    # ----------------------------------------------------------------------------------
    # Creation / Update
    # ----------------------------------------------------------------------------------
    def __init__(self,
                 object_id: str,
                 object_type: GameObjectType,
                 initial: ACMIObject | None = None,
                 color: tuple[float, float, float, float] = (255, 0, 255, 255)):
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

        # Special case: Color defaults to "black" not empty
        self.Color = "black"

        # UI / runtime initialization
        self.color_rgba = color
        self.visible = True
        self.override_name = None
        self.override_color = None
        self.locked_target_obj = None

        # Apply initial data if provided
        if initial is not None:
            self.apply_delta(initial)

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
            for k, v in t_delta.items():
                if v in (None, ""):
                    continue  # Skip empty delta values
                if k in _ORIENTATION_FIELDS and hasattr(self, k):
                    setattr(self, k, _coerce_number(v, getattr(self, k, 0.0)))

        # Handle all other ACMI fields systematically
        for field_name, value in props.items():
            if field_name == "T":
                continue  # Already handled above

            if field_name in _ALL_ACMI_FIELDS and hasattr(self, field_name):
                if value in (None, ""):
                    continue  # Skip empty delta values - preserve existing data

                # Apply value based on field type
                if field_name in _NUMERIC_FIELDS:
                    current_val = getattr(self, field_name, 0.0)
                    setattr(self, field_name, _coerce_number(value, current_val))
                elif field_name in _STRING_FIELDS:
                    setattr(self, field_name, str(value))
            # Note: Unknown fields are ignored (not an error in delta updates)

    # ----------------------------------------------------------------------------------
    # API methods (mirroring old implementation)
    # ----------------------------------------------------------------------------------
    def get_display_name(self) -> str:
        """Get the best available display name for this object."""
        if self.override_name:
            return self.override_name
        if self.Pilot:
            return self.Pilot
        if self.CallSign:  # Check CallSign before Name
            return self.CallSign
        if self.Name:
            return self.Name
        return self.Type or self.object_id

    def get_pos(self) -> tuple[float, float]:
        return (self.U, self.V)

    def set_color(self, color: tuple[float, float, float, float]):
        self.color_rgba = color

    def get_color(self) -> tuple[float, float, float, float]:
        return self.override_color if self.override_color is not None else self.color_rgba

    def hide(self):
        self.visible = False

    def show(self):
        self.visible = True

    def change_name(self, name: str):
        self.override_name = name

    def change_color(self, color: tuple[float, float, float, float]):
        self.override_color = color

    # Target lock handling (external resolver should set locked_target_obj)
    def resolve_locked_target(self, resolver: Dict[str, "GameObject"]):
        """Resolve LockedTarget string ID to actual GameObject reference."""
        if self.LockedTarget not in (None, "", "0") and self.LockedTarget in resolver:
            self.locked_target_obj = resolver[self.LockedTarget]
        else:
            self.locked_target_obj = None

    def get_context_items(self) -> list[tuple[str, Any]]:
        """Get context menu items for this object (for UI integration)."""
        return [("Change Color", self.change_color), ("Change Name", self.change_name)]

    def is_air_unit(self) -> bool:
        """Check if this is an air unit (fixed wing, rotary wing, or missile)."""
        return self.object_type in (GameObjectType.FIXEDWING, GameObjectType.ROTARYWING, GameObjectType.MISSILE)

    def is_ground_unit(self) -> bool:
        """Check if this is a ground unit."""
        return self.object_type == GameObjectType.GROUND

    def is_sea_unit(self) -> bool:
        """Check if this is a sea unit."""
        return self.object_type == GameObjectType.SEA

    def _getVelocityVector(self,
                           px_per_nm: float,
                           heading: float | None = None,
                           line_scale: int = 3) -> tuple[float, float]:
        """
        Calculates the end point of a velocity vector line to draw.
        (Compatibility method for existing code that expects this on airUnit)

        Args:
        heading (float): The heading angle in degrees.
        line_scale (int): The scale factor for the velocity vector line. Default is 3.

        Returns:
            tuple[float,float]: The end point of the velocity vector.
        """
        import math
        from util.bms_math import NM_TO_METERS  # Import here to avoid circular deps

        LINE_LEN_SECONDS = 30  # 30 seconds of velocity vector
        px_per_second = px_per_nm * self.CAS / NM_TO_METERS  # Scale the velocity vector
        vel_vec_len_px = px_per_second * LINE_LEN_SECONDS  # Scale the velocity vector

        heading_rad = math.radians(self.Heading - 90)  # -90 rotates north to up
        end_x = vel_vec_len_px * math.cos(heading_rad)
        end_y = vel_vec_len_px * math.sin(heading_rad)
        end_pt = (end_x, end_y)

        return end_pt

    def __str__(self) -> str:
        """String representation for debugging."""
        return f"GameObject({self.object_id}, {self.object_type.name}, {self.get_display_name()})"

    def __repr__(self) -> str:
        """Detailed representation for debugging."""
        return (f"GameObject(id={self.object_id}, type={self.object_type.name}, "
                f"pos=({self.U:.1f}, {self.V:.1f}), name={self.get_display_name()!r})")
