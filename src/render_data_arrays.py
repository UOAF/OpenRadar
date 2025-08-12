"""
Array of Structs (AoS) Render Data Arrays for GPU-optimized rendering.

This module contains Array of Structs implementations for efficient GPU rendering:
- IconRenderDataAoS: For rendering object icons
- VelocityVectorRenderDataAoS: For rendering velocity vectors
- LockLineRenderDataAoS: For rendering target lock lines
- RenderDataArraysAoS: Master container for all render arrays

All arrays use numpy structured arrays for contiguous memory layout and GPU compatibility.
Data is stored contiguously and removal uses swap-with-last for O(1) deletion.
"""

import numpy as np
from abc import ABC, abstractmethod
from typing import Optional
from game_object import GameObject
from draw.shapes import Shapes


class BaseRenderData(ABC):
    """
    Abstract base class for Array of Structs render data.
    Provides common functionality for contiguous array management with swap-with-last removal.
    """

    def __init__(self, initial_capacity: int):
        """Initialize base render data arrays."""
        self.capacity = initial_capacity
        self.count = 0

        # Object ID to array index mapping for fast lookup
        self.id_to_index: dict[str, int] = {}
        self.index_to_id: dict[int, str] = {}

        # This will be set by subclasses
        self.data: Optional[np.ndarray] = None

        # Initialize the structured array
        self._initialize_array(initial_capacity)

    def _initialize_array(self, capacity: int):
        """Initialize the velocity vector structured array."""
        self.capacity = capacity
        self.data = np.zeros(capacity, dtype=self._get_dtype())

    @abstractmethod
    def _get_dtype(self):
        """Get the numpy dtype for the structured array."""
        pass

    @abstractmethod
    def _update_object_data(self, index: int, game_obj: GameObject):
        """Update the structured array with data from the game object."""
        pass

    def add_object(self, game_obj: GameObject) -> int:
        """Add a game object to the array."""
        index = self._get_free_index()

        # Store the mapping
        self.id_to_index[game_obj.object_id] = index
        self.index_to_id[index] = game_obj.object_id

        # Update the data
        self._update_object_data(index, game_obj)
        self.count += 1

        return index

    def remove_object(self, object_id: str):
        """Remove an object from the array using swap-with-last."""
        if object_id not in self.id_to_index:
            return

        index = self.id_to_index[object_id]
        self._remove_by_swap(index, object_id)

    def update_object(self, game_obj: GameObject):
        """Update an existing object in the array."""
        if game_obj.object_id not in self.id_to_index:
            self.add_object(game_obj)
            return

        index = self.id_to_index[game_obj.object_id]
        self.index_to_id[index] = game_obj.object_id
        self._update_object_data(index, game_obj)

    def resize(self, new_capacity: int):
        """Resize array to accommodate more objects."""
        if new_capacity <= self.capacity or self.data is None:
            return

        # Create new array with larger capacity
        old_array = self.data
        self._initialize_array(new_capacity)

        # Copy existing data
        if self.count > 0 and self.data is not None:
            self.data[:self.count] = old_array[:self.count]

    def _get_free_index(self) -> int:
        """Get the next available index (always at the end)."""
        if self.count >= self.capacity:
            self.resize(self.capacity * 2)
        return self.count

    def _remove_by_swap(self, index: int, object_id_to_remove: str):
        """Remove element by swapping with last element (O(1) removal)."""
        if index >= self.count or self.count == 0 or self.data is None:
            # TODO maybe log a warnning here
            raise IndexError("Index out of bounds or empty array")

        # - perform the "swap"
        #   1. Copy the last element to  index
        #   2. Update both dictionaries for the swap:
        #      a. index2id[index] = last_object_id
        #      b. id2index[last_object_id] = index
        #      c. Remove the object_id_to_remove from id_to_index

        last_index = self.count - 1

        # Get the object_id_to_remove of the last element to update the mapping
        last_element = self.data[last_index]
        last_object_id = self.index_to_id[last_index]

        # Swap the data
        self.data[index] = last_element

        # Update the mapping for the swapped element
        self.id_to_index[last_object_id] = index
        self.index_to_id[index] = last_object_id

        # Remove from mapping
        del self.index_to_id[last_index]
        del self.id_to_index[object_id_to_remove]

        # decrement count
        self.count -= 1

    def get_active_data(self) -> Optional[np.ndarray]:
        """Get the active portion of the array (first 'count' elements)."""
        if self.count == 0 or self.data is None:
            return None
        return self.data[:self.count]

    def get_render_data(self) -> Optional[np.ndarray]:
        return self.get_active_data()


class IconRenderData(BaseRenderData):
    """
    Array of Structs for icon rendering.
    Each element contains: object_id, position, color, icon_id, scale, altitude, heading, status_flags
    """

    def _get_dtype(self):
        """Get the numpy dtype for icon structured array."""
        return np.dtype([
            ('position', np.float32, (2, )),  # x, y world coords
            ('scale', np.float32),  # Scale factor per icon
            ('_buffer', np.float32),  # Padding for alignment
            ('color', np.float32, (4, )),  # RGBA normalized 0.0-1.0
        ])

    def set_all_scale(self, scale: float):
        """Set the scale for all icons."""
        if self.data is not None:
            self.data['scale'] = scale

    def _update_object_data(self, index: int, game_obj: GameObject):
        """Update the array data for an icon at the given index."""
        if self.data is None:
            return

        element = self.data[index]

        # Position (using U, V world coordinates)
        element['position'] = [game_obj.U, game_obj.V]

        # Color (normalize from 0-255 to 0.0-1.0 for shaders)
        color = game_obj.override_color if game_obj.override_color else game_obj.color_rgba
        element['color'] = [c / 255.0 if c > 1.0 else c for c in color]

        # Scale (could be configurable per object type)
        element['scale'] = 10.0


class VelocityVectorRenderData(BaseRenderData):
    """
    Array of Structs for velocity vector rendering.
    Each element contains: object_id, start_position, color, heading, velocity
    End positions are calculated in the fragment shader using heading and velocity with a fixed scale.
    """

    def _get_dtype(self):
        """Get the numpy dtype for velocity vector structured array."""
        return np.dtype([
            ('start_position', np.float32, (2, )),  # Start point (x, y)
            ('heading', np.float32),  # Heading in degrees
            ('velocity', np.float32),  # Velocity magnitude (CAS)
            ('color', np.float32, (4, )),  # RGBA normalized 0.0-1.0
        ])

    def _update_object_data(self, index: int, game_obj: GameObject):
        """Update the array data for a velocity vector at the given index."""
        if self.data is None:
            return

        element = self.data[index]

        # Start position (object position)
        element['start_position'] = [game_obj.U, game_obj.V]

        # Color (use same as icon)
        color = game_obj.override_color if game_obj.override_color else game_obj.color_rgba
        element['color'] = [c / 255.0 if c > 1.0 else c for c in color]

        # Store raw values for shader use
        element['heading'] = game_obj.Heading
        element['velocity'] = game_obj.CAS


class LockLineRenderData(BaseRenderData):
    """
    Array of Structs for target lock line rendering.
    Each element contains: lock_pair, start_position, end_position, color
    """

    def __init__(self, initial_capacity: int):
        super().__init__(initial_capacity)
        self.id_to_locks: dict[str, dict[str, int]] = {}  # Map object ID to lock line index

    def _get_dtype(self):
        """Get the numpy dtype for lock line structured array."""
        return np.dtype([
            ('start_position', np.float32, (2, )),  # Start point (x, y)
            ('end_position', np.float32, (2, )),  # End point (x, y)
            ('color', np.float32, (4, ))  # RGBA normalized 0.0-1.0
        ])

    def add_lock_line(self, source_obj: GameObject, target_obj: GameObject) -> int:
        """Add a lock line between two objects."""
        index = self._get_free_index()
        lock_pair = f"{source_obj.object_id}:{target_obj.object_id}"

        # Store the mapping
        if not source_obj.object_id in self.id_to_locks:
            self.id_to_locks[source_obj.object_id] = {}
        self.id_to_locks[source_obj.object_id][target_obj.object_id] = index
        self.id_to_index[lock_pair] = index
        self.index_to_id[index] = lock_pair

        # Update the data
        self._update_lock_line_data(index, source_obj, target_obj)
        self.count += 1

        return index

    def update_all_locks(self, game_obj: GameObject):
        """Update all lock lines for a given source object."""
        # Get current locked targets
        current_targets = {target.object_id for target in game_obj.locked_target_objs if target is not None}

        # Get existing lock lines for this source object
        existing_targets = set()
        if game_obj.object_id in self.id_to_locks:
            existing_targets = set(self.id_to_locks[game_obj.object_id].keys())

        # Remove lock lines that no longer exist
        targets_to_remove = existing_targets - current_targets
        for target_id in targets_to_remove:
            self.remove_lock_line(game_obj.object_id, target_id)

        # Add new lock lines
        targets_to_add = current_targets - existing_targets
        for target_obj in game_obj.locked_target_objs:
            if target_obj is not None and target_obj.object_id in targets_to_add:
                self.add_lock_line(game_obj, target_obj)

        # Update existing lock lines (positions may have changed)
        if game_obj.object_id in self.id_to_locks:
            for target_obj in game_obj.locked_target_objs:
                if target_obj is not None and target_obj.object_id in self.id_to_locks[game_obj.object_id]:
                    index = self.id_to_locks[game_obj.object_id][target_obj.object_id]
                    if index < self.count and self.data is not None:
                        self._update_lock_line_data(index, game_obj, target_obj)

    def remove_object_locks(self, object_id: str):
        """Remove all lock lines associated with a given object."""
        if self.data is None:
            return

        # Instead of collecting indices (which can become stale), collect lock pairs
        lock_pairs_to_remove = []

        # Find lock lines where this object is the source
        if object_id in self.id_to_locks:
            for target_id in list(self.id_to_locks[object_id].keys()):
                lock_pairs_to_remove.append((object_id, target_id))

        # Find lock lines where this object is the target
        for source_id, targets in list(self.id_to_locks.items()):
            if object_id in targets:
                lock_pairs_to_remove.append((source_id, object_id))

        # Remove the lock lines using the lock pair identifiers
        # This way we don't depend on indices which can change during removal
        for source_id, target_id in lock_pairs_to_remove:
            self.remove_lock_line(source_id, target_id)

    def remove_object(self, object_id: str):
        """Remove all lock lines for an object (alias for remove_object_locks)."""
        self.remove_object_locks(object_id)

    def update_object(self, game_obj: GameObject):
        """Update all lock lines for a given object."""
        self.update_all_locks(game_obj)

    def remove_lock_line(self, source_id: str, target_id: str):
        """Remove a specific lock line between two objects."""
        if source_id not in self.id_to_locks or target_id not in self.id_to_locks[source_id]:
            return

        index = self.id_to_locks[source_id][target_id]
        self._remove_lock_line(index)

    def _remove_lock_line(self, index: int):
        """Remove a lock line at the given index."""
        if index >= self.count or self.data is None:
            return

        # Get the lock pair ID to remove from mappings
        lock_pair = self.index_to_id[index]
        source_id, target_id = lock_pair.split(":")

        # If we're not removing the last element, we need to update the id_to_locks
        # mapping for the element that will be moved to this index
        if index < self.count - 1:
            # Get the lock pair that will be moved from the last position to this index
            last_index = self.count - 1
            moved_lock_pair = self.index_to_id[last_index]
            moved_source_id, moved_target_id = moved_lock_pair.split(":")

            # Update the id_to_locks mapping for the moved element
            if moved_source_id in self.id_to_locks and moved_target_id in self.id_to_locks[moved_source_id]:
                self.id_to_locks[moved_source_id][moved_target_id] = index

        # Remove from the id_to_locks mapping
        if source_id in self.id_to_locks and target_id in self.id_to_locks[source_id]:
            del self.id_to_locks[source_id][target_id]
            # Clean up empty source entries
            if not self.id_to_locks[source_id]:
                del self.id_to_locks[source_id]

        # Use base class swap-with-last removal
        self._remove_by_swap(index, lock_pair)

    def _update_object_data(self, index: int, game_obj: GameObject):
        """Update lock line data when one of the objects in the pair has changed."""
        # This method is not directly used since lock lines are updated via update_all_locks
        # which handles the source-target relationship properly
        pass

    def _update_lock_line_data(self, index: int, source_obj: GameObject, target_obj: GameObject):
        """Update the array data for a lock line at the given index."""
        if self.data is None:
            return

        element = self.data[index]

        # Start position (source object)
        element['start_position'] = [source_obj.U, source_obj.V]

        # End position (target object)
        element['end_position'] = [target_obj.U, target_obj.V]

        # Color (use source object color but make it slightly different for lock lines)
        source_color = source_obj.override_color if source_obj.override_color else source_obj.color_rgba
        # Make lock lines slightly brighter/more saturated
        lock_color = [min(1.0, c / 255.0 * 1.2) if c > 1.0 else min(1.0, c * 1.2) for c in source_color]
        element['color'] = lock_color


class RenderDataArrays:
    """
    Master container for all Array of Structs render data arrays.
    Contains separate arrays for icons, velocity vectors, and lock lines.
    All data is stored contiguously for optimal GPU performance.
    """

    def __init__(self, initial_capacity: int = 1024 * 8):
        """Initialize all render data arrays."""
        # Separate rendering arrays
        self.icon_data: dict[Shapes, IconRenderData] = dict()
        for shape in Shapes:
            self.icon_data[shape] = IconRenderData(initial_capacity)
        self.velocity_vectors = VelocityVectorRenderData(initial_capacity // 2)
        self.lock_lines = LockLineRenderData(initial_capacity // 2)

    def add_object(self, game_obj: GameObject):
        """Add a game object to all relevant render arrays."""

        # Add to icon array (Most objects have icons)
        shape_id = game_obj.icon
        shape = Shapes.from_idx(shape_id) if shape_id is not None else None
        if shape is not None:
            self.icon_data[shape].add_object(game_obj)

        # Add velocity vector if it's an aircraft
        if game_obj.is_air_unit() and game_obj.CAS > 0:
            self.velocity_vectors.add_object(game_obj)

        # Add lock line if this object has a target lock
        if len(game_obj.locked_target_objs) > 0:
            for target in game_obj.locked_target_objs:
                if target is not None:
                    self.lock_lines.add_lock_line(game_obj, target)

    def remove_object(self, game_obj: GameObject):
        """Remove an object from all render arrays."""

        object_id = game_obj.object_id
        shape_id = game_obj.icon

        shape = Shapes.from_idx(shape_id) if shape_id is not None else None
        if shape is not None:
            self.icon_data[shape].remove_object(object_id)

        self.velocity_vectors.remove_object(object_id)
        self.lock_lines.remove_object_locks(object_id)

    def update_object(self, game_obj: GameObject):
        """Update an object in all relevant render arrays."""
        # Update icon data (all objects have icons)
        shape_id = game_obj.icon
        shape = Shapes.from_idx(shape_id)
        self.icon_data[shape].update_object(game_obj)

        # Update or add/remove velocity vector based on movement
        if game_obj.is_air_unit() and game_obj.CAS > 0:
            if game_obj.object_id in self.velocity_vectors.id_to_index:
                self.velocity_vectors.update_object(game_obj)
            else:
                self.velocity_vectors.add_object(game_obj)
        else:
            self.velocity_vectors.remove_object(game_obj.object_id)

        # Update or add/remove lock lines based on target locks
        self.lock_lines.update_all_locks(game_obj)

    def get_render_data(self) -> Optional[dict]:
        """Get all render data arrays for GPU rendering."""

        # Icon Arrays
        icon_arrays = {}
        for shape, icon_data in self.icon_data.items():
            active_array_slice = icon_data.get_render_data()
            if active_array_slice is not None:
                icon_arrays[shape] = active_array_slice.copy()

        # Velocity Vectors
        active_array_slice = self.velocity_vectors.get_render_data()
        velocity_vectors = active_array_slice.copy() if active_array_slice is not None else None

        # Lock Lines
        active_array_slice = self.lock_lines.get_render_data()
        lock_lines = active_array_slice.copy() if active_array_slice is not None else None

        return {'icons': icon_arrays, 'velocity_vectors': velocity_vectors, 'lock_lines': lock_lines}
