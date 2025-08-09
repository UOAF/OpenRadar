"""
Render Data Arrays for GPU-optimized rendering.

This module contains Struct of Arrays (SoA) implementations for efficient GPU rendering:
- IconRenderData: For rendering object icons
- VelocityVectorRenderData: For rendering velocity vectors
- LockLineRenderData: For rendering target lock lines
- RenderDataArrays: Master container for all render arrays

All arrays use numpy for efficient memory layout and GPU compatibility.
"""

import numpy as np
from abc import ABC, abstractmethod
from typing import Optional, Any
from game_object import GameObject


class BaseRenderData(ABC):
    """
    Abstract base class for render data arrays.
    Provides common functionality for array management.
    """

    def __init__(self, initial_capacity: int):
        """Initialize base render data arrays."""
        self.capacity = initial_capacity
        self.count = 0
        self.free_indices = list(range(initial_capacity))

        # Subclasses will initialize their specific arrays
        self._initialize_arrays(initial_capacity)

    @abstractmethod
    def _initialize_arrays(self, capacity: int):
        """Initialize specific arrays for this render data type."""
        pass

    @abstractmethod
    def _resize_arrays(self, new_capacity: int):
        """Resize specific arrays for this render data type."""
        pass

    @abstractmethod
    def _clear_data_at_index(self, index: int):
        """Clear all data at the given index."""
        pass

    def resize(self, new_capacity: int):
        """Resize arrays to accommodate more objects."""
        if new_capacity <= self.capacity:
            return

        self._resize_arrays(new_capacity)
        self.free_indices.extend(range(self.capacity, new_capacity))
        self.capacity = new_capacity

    def _get_free_index(self) -> int:
        """Get a free index, resizing if necessary."""
        if not self.free_indices:
            self.resize(self.capacity * 2)
        return self.free_indices.pop(0)

    def _free_index(self, index: int):
        """Mark an index as free."""
        self._clear_data_at_index(index)
        self.free_indices.append(index)
        self.count -= 1

    def _get_active_indices(self, id_array: list[str]) -> list[int]:
        """Get indices of all active objects (non-empty IDs)."""
        return [i for i, obj_id in enumerate(id_array) if obj_id]


class IconRenderData(BaseRenderData):
    """
    Struct of Arrays for icon rendering.
    Fields: id, position, icon_id, color, scale, altitude, heading, status_flags
    """

    def _initialize_arrays(self, capacity: int):
        """Initialize icon-specific arrays."""
        # Core icon data for shaders
        self.positions = np.zeros((capacity, 2), dtype=np.float32)  # x, y world coords
        self.colors = np.zeros((capacity, 4), dtype=np.float32)  # RGBA normalized 0.0-1.0
        self.icon_ids = np.zeros(capacity, dtype=np.int32)  # Icon type ID for texture/shape selection
        self.scales = np.zeros(capacity, dtype=np.float32)  # Scale factor per icon

        # Additional rendering data
        self.altitudes = np.zeros(capacity, dtype=np.float32)  # For altitude display
        self.headings = np.zeros(capacity, dtype=np.float32)  # For icon rotation
        self.status_flags = np.zeros(capacity, dtype=np.uint32)  # Visibility, etc.

        # Object metadata for lookups
        self.object_ids = [""] * capacity  # String IDs for mapping back
        self.id_to_index: dict[str, int] = {}  # Quick lookup: object_id -> array_index

    def _resize_arrays(self, new_capacity: int):
        """Resize icon-specific arrays."""
        self.positions = np.resize(self.positions, (new_capacity, 2))
        self.colors = np.resize(self.colors, (new_capacity, 4))
        self.icon_ids = np.resize(self.icon_ids, new_capacity)
        self.scales = np.resize(self.scales, new_capacity)
        self.altitudes = np.resize(self.altitudes, new_capacity)
        self.headings = np.resize(self.headings, new_capacity)
        self.status_flags = np.resize(self.status_flags, new_capacity)

        # Extend object metadata
        self.object_ids.extend([""] * (new_capacity - self.capacity))

    def _clear_data_at_index(self, index: int):
        """Clear icon data at the given index."""
        self.positions[index] = [0.0, 0.0]
        self.colors[index] = [0.0, 0.0, 0.0, 0.0]
        self.icon_ids[index] = 0
        self.scales[index] = 0.0
        self.altitudes[index] = 0.0
        self.headings[index] = 0.0
        self.status_flags[index] = 0

    def add_object(self, game_obj: GameObject) -> int:
        """Add a game object to the icon arrays."""
        index = self._get_free_index()
        self.object_ids[index] = game_obj.object_id
        self.id_to_index[game_obj.object_id] = index

        self._update_object_data(index, game_obj)
        self.count += 1

        return index

    def remove_object(self, object_id: str):
        """Remove an object from the icon arrays."""
        if object_id not in self.id_to_index:
            return

        index = self.id_to_index[object_id]

        # Free the slot
        self.object_ids[index] = ""
        del self.id_to_index[object_id]
        self._free_index(index)

    def update_object(self, game_obj: GameObject):
        """Update an existing object in the icon arrays."""
        if game_obj.object_id not in self.id_to_index:
            self.add_object(game_obj)
            return

        index = self.id_to_index[game_obj.object_id]
        self._update_object_data(index, game_obj)

    def _update_object_data(self, index: int, game_obj: GameObject):
        """Update the array data for an icon at the given index."""
        # Position (using U, V world coordinates)
        self.positions[index] = [game_obj.U, game_obj.V]

        # Color (normalize from 0-255 to 0.0-1.0 for shaders)
        color = game_obj.override_color if game_obj.override_color else game_obj.color_rgba
        self.colors[index] = [c / 255.0 if c > 1.0 else c for c in color]

        # Icon ID based on object type and coalition for shader texture/shape selection
        self.icon_ids[index] = self._get_icon_id(game_obj)

        # Scale (could be configurable per object type)
        self.scales[index] = 1.0

        # Additional data
        self.altitudes[index] = game_obj.Altitude
        self.headings[index] = game_obj.Heading

        # Status flags
        flags = 0
        if game_obj.visible:
            flags |= 0x1  # Visible flag
        self.status_flags[index] = flags

    def _get_icon_id(self, game_obj: GameObject) -> int:
        """Convert object type and coalition to icon ID for shader use."""
        # Base icon ID from object type
        base_id = game_obj.object_type.value * 10

        # Add coalition modifier
        coalition_modifier = 0
        if "Blue" in game_obj.Coalition or "US" in game_obj.Coalition:
            coalition_modifier = 1  # Friendly
        elif "Red" in game_obj.Coalition or "OPFOR" in game_obj.Coalition:
            coalition_modifier = 2  # Hostile
        else:
            coalition_modifier = 3  # Unknown/Neutral

        return base_id + coalition_modifier

    def get_active_slice(self) -> Optional[dict[str, Any]]:
        """Get slices of arrays containing only active objects (for rendering)."""
        if self.count == 0:
            return None

        active_indices = self._get_active_indices(self.object_ids)

        if not active_indices:
            return None

        # Convert to numpy array for efficient indexing
        active_indices = np.array(active_indices, dtype=np.int32)

        return {
            'positions': self.positions[active_indices],
            'colors': self.colors[active_indices],
            'icon_ids': self.icon_ids[active_indices],
            'scales': self.scales[active_indices],
            'altitudes': self.altitudes[active_indices],
            'headings': self.headings[active_indices],
            'status_flags': self.status_flags[active_indices],
            'active_indices': active_indices,  # Include for debugging/validation
            'count': len(active_indices)
        }

    def get_contiguous_data(self) -> Optional[dict[str, Any]]:
        """
        Get contiguous numpy arrays optimized for direct GPU buffer upload.
        Returns arrays containing only active objects in contiguous memory.
        """
        if self.count == 0:
            return None

        active_indices = self._get_active_indices(self.object_ids)

        if not active_indices:
            return None

        active_indices = np.array(active_indices, dtype=np.int32)
        num_active = len(active_indices)

        # Create contiguous arrays for GPU upload
        return {
            'positions': np.ascontiguousarray(self.positions[active_indices]),
            'colors': np.ascontiguousarray(self.colors[active_indices]),
            'icon_ids': np.ascontiguousarray(self.icon_ids[active_indices]),
            'scales': np.ascontiguousarray(self.scales[active_indices]),
            'altitudes': np.ascontiguousarray(self.altitudes[active_indices]),
            'headings': np.ascontiguousarray(self.headings[active_indices]),
            'status_flags': np.ascontiguousarray(self.status_flags[active_indices]),
            'count': num_active
        }


class VelocityVectorRenderData(BaseRenderData):
    """
    Struct of Arrays for velocity vector rendering.
    Fields: start_positions, colors, headings, velocities
    End positions are calculated in the fragment shader using heading and velocity with a fixed scale.
    """

    def _initialize_arrays(self, capacity: int):
        """Initialize velocity vector-specific arrays."""
        # Core velocity vector data for shaders
        self.start_positions = np.zeros((capacity, 2), dtype=np.float32)  # Start point (x, y)
        self.colors = np.zeros((capacity, 4), dtype=np.float32)  # RGBA normalized 0.0-1.0
        self.headings = np.zeros(capacity, dtype=np.float32)  # Heading in degrees
        self.velocities = np.zeros(capacity, dtype=np.float32)  # Velocity magnitude (CAS)

        # Object metadata for lookups
        self.object_ids = [""] * capacity  # String IDs for mapping back
        self.id_to_index: dict[str, int] = {}  # Quick lookup: object_id -> array_index

    def _resize_arrays(self, new_capacity: int):
        """Resize velocity vector-specific arrays."""
        self.start_positions = np.resize(self.start_positions, (new_capacity, 2))
        self.colors = np.resize(self.colors, (new_capacity, 4))
        self.headings = np.resize(self.headings, new_capacity)
        self.velocities = np.resize(self.velocities, new_capacity)

        # Extend object metadata
        self.object_ids.extend([""] * (new_capacity - self.capacity))

    def _clear_data_at_index(self, index: int):
        """Clear velocity vector data at the given index."""
        self.start_positions[index] = [0.0, 0.0]
        self.colors[index] = [0.0, 0.0, 0.0, 0.0]
        self.headings[index] = 0.0
        self.velocities[index] = 0.0

    def add_object(self, game_obj: GameObject) -> int:
        """Add a game object's velocity vector to the arrays."""
        index = self._get_free_index()
        self.object_ids[index] = game_obj.object_id
        self.id_to_index[game_obj.object_id] = index

        self._update_object_data(index, game_obj)
        self.count += 1

        return index

    def remove_object(self, object_id: str):
        """Remove an object's velocity vector from the arrays."""
        if object_id not in self.id_to_index:
            return

        index = self.id_to_index[object_id]

        # Free the slot
        self.object_ids[index] = ""
        del self.id_to_index[object_id]
        self._free_index(index)

    def update_object(self, game_obj: GameObject):
        """Update an existing object's velocity vector in the arrays."""
        if game_obj.object_id not in self.id_to_index:
            self.add_object(game_obj)
            return

        index = self.id_to_index[game_obj.object_id]
        self._update_object_data(index, game_obj)

    def _update_object_data(self, index: int, game_obj: GameObject):
        """Update the array data for a velocity vector at the given index."""
        # Start position (object position)
        self.start_positions[index] = [game_obj.U, game_obj.V]

        # Color (use same as icon)
        color = game_obj.override_color if game_obj.override_color else game_obj.color_rgba
        self.colors[index] = [c / 255.0 if c > 1.0 else c for c in color]

        # Store raw values for shader use
        self.headings[index] = game_obj.Heading
        self.velocities[index] = game_obj.CAS

    def get_active_slice(self) -> Optional[dict[str, Any]]:
        """Get slices of arrays containing only active objects (for rendering)."""
        if self.count == 0:
            return None

        active_indices = self._get_active_indices(self.object_ids)

        if not active_indices:
            return None

        # Convert to numpy array for efficient indexing
        active_indices = np.array(active_indices, dtype=np.int32)

        return {
            'start_positions': self.start_positions[active_indices],
            'colors': self.colors[active_indices],
            'headings': self.headings[active_indices],
            'velocities': self.velocities[active_indices],
            'active_indices': active_indices,  # Include for debugging/validation
            'count': len(active_indices)
        }

    def get_contiguous_data(self) -> Optional[dict[str, Any]]:
        """
        Get contiguous numpy arrays optimized for direct GPU buffer upload.
        Returns arrays containing only active objects in contiguous memory.
        """
        if self.count == 0:
            return None

        active_indices = self._get_active_indices(self.object_ids)

        if not active_indices:
            return None

        active_indices = np.array(active_indices, dtype=np.int32)
        num_active = len(active_indices)

        # Create contiguous arrays for GPU upload
        return {
            'start_positions': np.ascontiguousarray(self.start_positions[active_indices]),
            'colors': np.ascontiguousarray(self.colors[active_indices]),
            'headings': np.ascontiguousarray(self.headings[active_indices]),
            'velocities': np.ascontiguousarray(self.velocities[active_indices]),
            'count': num_active
        }


class LockLineRenderData(BaseRenderData):
    """
    Struct of Arrays for target lock line rendering.
    Fields: start_positions, end_positions, colors
    """

    def _initialize_arrays(self, capacity: int):
        """Initialize lock line-specific arrays."""
        # Core lock line data for shaders
        self.start_positions = np.zeros((capacity, 2), dtype=np.float32)  # Start point (x, y)
        self.end_positions = np.zeros((capacity, 2), dtype=np.float32)  # End point (x, y)
        self.colors = np.zeros((capacity, 4), dtype=np.float32)  # RGBA normalized 0.0-1.0

        # Lock line metadata for lookups
        self.lock_pairs = [""] * capacity  # "source_id:target_id" for mapping back
        self.pair_to_index: dict[str, int] = {}  # Quick lookup: lock_pair -> array_index

    def _resize_arrays(self, new_capacity: int):
        """Resize lock line-specific arrays."""
        self.start_positions = np.resize(self.start_positions, (new_capacity, 2))
        self.end_positions = np.resize(self.end_positions, (new_capacity, 2))
        self.colors = np.resize(self.colors, (new_capacity, 4))

        # Extend object metadata
        self.lock_pairs.extend([""] * (new_capacity - self.capacity))

    def _clear_data_at_index(self, index: int):
        """Clear lock line data at the given index."""
        self.start_positions[index] = [0.0, 0.0]
        self.end_positions[index] = [0.0, 0.0]
        self.colors[index] = [0.0, 0.0, 0.0, 0.0]

    def add_lock_line(self, source_obj: GameObject, target_obj: GameObject) -> int:
        """Add a lock line between two objects."""
        index = self._get_free_index()
        lock_pair = f"{source_obj.object_id}:{target_obj.object_id}"
        self.lock_pairs[index] = lock_pair
        self.pair_to_index[lock_pair] = index

        self._update_lock_line_data(index, source_obj, target_obj)
        self.count += 1

        return index

    def remove_object_locks(self, object_id: str):
        """Remove all lock lines involving the given object (as source or target)."""
        to_remove = []

        # Find all lock pairs involving this object
        for lock_pair, index in self.pair_to_index.items():
            source_id, target_id = lock_pair.split(":")
            if source_id == object_id or target_id == object_id:
                to_remove.append(lock_pair)

        # Remove them
        for lock_pair in to_remove:
            self._remove_lock_line(lock_pair)

    def _remove_lock_line(self, lock_pair: str):
        """Remove a specific lock line."""
        if lock_pair not in self.pair_to_index:
            return

        index = self.pair_to_index[lock_pair]

        # Free the slot
        self.lock_pairs[index] = ""
        del self.pair_to_index[lock_pair]
        self._free_index(index)

    def _update_lock_line_data(self, index: int, source_obj: GameObject, target_obj: GameObject):
        """Update the array data for a lock line at the given index."""
        # Start position (source object)
        self.start_positions[index] = [source_obj.U, source_obj.V]

        # End position (target object)
        self.end_positions[index] = [target_obj.U, target_obj.V]

        # Color (use source object color but make it slightly different for lock lines)
        source_color = source_obj.override_color if source_obj.override_color else source_obj.color_rgba
        # Make lock lines slightly brighter/more saturated
        lock_color = [min(1.0, c / 255.0 * 1.2) if c > 1.0 else min(1.0, c * 1.2) for c in source_color]
        self.colors[index] = lock_color

    def get_active_slice(self) -> Optional[dict[str, Any]]:
        """Get slices of arrays containing only active objects (for rendering)."""
        if self.count == 0:
            return None

        active_indices = self._get_active_indices(self.lock_pairs)

        if not active_indices:
            return None

        # Convert to numpy array for efficient indexing
        active_indices = np.array(active_indices, dtype=np.int32)

        return {
            'start_positions': self.start_positions[active_indices],
            'end_positions': self.end_positions[active_indices],
            'colors': self.colors[active_indices],
            'active_indices': active_indices,  # Include for debugging/validation
            'count': len(active_indices)
        }

    def get_contiguous_data(self) -> Optional[dict[str, Any]]:
        """
        Get contiguous numpy arrays optimized for direct GPU buffer upload.
        Returns arrays containing only active objects in contiguous memory.
        """
        if self.count == 0:
            return None

        active_indices = self._get_active_indices(self.lock_pairs)

        if not active_indices:
            return None

        active_indices = np.array(active_indices, dtype=np.int32)
        num_active = len(active_indices)

        # Create contiguous arrays for GPU upload
        return {
            'start_positions': np.ascontiguousarray(self.start_positions[active_indices]),
            'end_positions': np.ascontiguousarray(self.end_positions[active_indices]),
            'colors': np.ascontiguousarray(self.colors[active_indices]),
            'count': num_active
        }


class RenderDataArrays:
    """
    Master container for all render data arrays.
    Contains separate arrays for icons, velocity vectors, and lock lines.
    """

    def __init__(self, initial_capacity: int = 1000):
        """Initialize all render data arrays."""
        # Separate rendering arrays as specified in refactor notes
        self.icons = IconRenderData(initial_capacity)
        self.velocity_vectors = VelocityVectorRenderData(initial_capacity)
        self.lock_lines = LockLineRenderData(initial_capacity // 2)  # Fewer lock lines typically

    def resize_arrays(self, new_capacity: int):
        """Resize all render data arrays to accommodate more objects."""
        self.icons.resize(new_capacity)
        self.velocity_vectors.resize(new_capacity)
        self.lock_lines.resize(new_capacity // 2)

    def add_object(self, game_obj: GameObject) -> int:
        """Add a game object to all relevant render arrays."""
        # Add to icon array (all objects have icons)
        icon_index = self.icons.add_object(game_obj)

        # Add velocity vector if it's a moving object
        if game_obj.is_air_unit() and game_obj.CAS > 0:
            self.velocity_vectors.add_object(game_obj)

        # Add lock line if this object has a target lock
        if game_obj.locked_target_obj is not None:
            self.lock_lines.add_lock_line(game_obj, game_obj.locked_target_obj)

        return icon_index

    def remove_object(self, object_id: str):
        """Remove an object from all render arrays."""
        self.icons.remove_object(object_id)
        self.velocity_vectors.remove_object(object_id)
        self.lock_lines.remove_object_locks(object_id)

    def update_object(self, game_obj: GameObject):
        """Update an object in all relevant render arrays."""
        # Update icon data (all objects have icons)
        self.icons.update_object(game_obj)

        # Update or add/remove velocity vector based on movement
        if game_obj.is_air_unit() and game_obj.CAS > 0:
            if game_obj.object_id in self.velocity_vectors.id_to_index:
                self.velocity_vectors.update_object(game_obj)
            else:
                self.velocity_vectors.add_object(game_obj)
        else:
            self.velocity_vectors.remove_object(game_obj.object_id)

        # Update or add/remove lock lines based on target locks
        self.lock_lines.remove_object_locks(game_obj.object_id)  # Remove existing locks
        if game_obj.locked_target_obj is not None:
            self.lock_lines.add_lock_line(game_obj, game_obj.locked_target_obj)

    def get_render_data(self) -> dict[str, Optional[dict[str, Any]]]:
        """Get all render data arrays for GPU rendering."""
        return {
            'icons': self.icons.get_active_slice(),
            'velocity_vectors': self.velocity_vectors.get_active_slice(),
            'lock_lines': self.lock_lines.get_active_slice()
        }

    def get_contiguous_render_data(self) -> dict[str, Optional[dict[str, Any]]]:
        """
        Get all render data arrays as contiguous numpy arrays optimized for GPU buffer uploads.
        Use this method for maximum memory copy efficiency with ModernGL buffers.
        """
        return {
            'icons': self.icons.get_contiguous_data(),
            'velocity_vectors': self.velocity_vectors.get_contiguous_data(),
            'lock_lines': self.lock_lines.get_contiguous_data()
        }
