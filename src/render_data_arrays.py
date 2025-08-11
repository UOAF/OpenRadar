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

    @abstractmethod
    def _initialize_array(self, capacity: int):
        """Initialize the structured numpy array for this render data type."""
        pass

    @abstractmethod
    def _get_dtype(self):
        """Get the numpy dtype for the structured array."""
        pass

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

    def _initialize_array(self, capacity: int):
        """Initialize the icon structured array."""
        self.capacity = capacity
        self.data = np.zeros(capacity, dtype=self._get_dtype())

    def _get_object_id_from_element(self, element) -> str:
        """Extract object_id from an icon element."""
        return str(element['object_id'])

    def add_object(self, game_obj: GameObject) -> int:
        """Add a game object to the icon array."""
        index = self._get_free_index()

        # Store the mapping
        self.id_to_index[game_obj.object_id] = index
        self.index_to_id[index] = game_obj.object_id

        # Update the data
        self._update_object_data(index, game_obj)
        self.count += 1

        return index

    def remove_object(self, object_id: str):
        """Remove an object from the icon array using swap-with-last."""
        if object_id not in self.id_to_index:
            return

        index = self.id_to_index[object_id]
        self._remove_by_swap(index, object_id)

    def update_object(self, game_obj: GameObject):
        """Update an existing object in the icon array."""
        if game_obj.object_id not in self.id_to_index:
            self.add_object(game_obj)
            return

        index = self.id_to_index[game_obj.object_id]
        self._update_object_data(index, game_obj)

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

    def get_render_data(self) -> Optional[np.ndarray]:

        return self.get_active_data()


# class VelocityVectorRenderData(BaseRenderData):
#     """
#     Array of Structs for velocity vector rendering.
#     Each element contains: object_id, start_position, color, heading, velocity
#     End positions are calculated in the fragment shader using heading and velocity with a fixed scale.
#     """

#     def _get_dtype(self):
#         """Get the numpy dtype for velocity vector structured array."""
#         return np.dtype([
#             ('object_id', 'U50'),  # String ID (Unicode 50 chars)
#             ('start_position', np.float32, (2, )),  # Start point (x, y)
#             ('color', np.float32, (4, )),  # RGBA normalized 0.0-1.0
#             ('heading', np.float32),  # Heading in degrees
#             ('velocity', np.float32)  # Velocity magnitude (CAS)
#         ])

#     def _initialize_array(self, capacity: int):
#         """Initialize the velocity vector structured array."""
#         self.capacity = capacity
#         self.data = np.zeros(capacity, dtype=self._get_dtype())

#     def _get_object_id_from_element(self, element) -> str:
#         """Extract object_id from a velocity vector element."""
#         return str(element['object_id'])

#     def add_object(self, game_obj: GameObject) -> int:
#         """Add a game object's velocity vector to the array."""
#         index = self._get_free_index()

#         # Store the mapping
#         self.id_to_index[game_obj.object_id] = index

#         # Update the data
#         self._update_object_data(index, game_obj)
#         self.count += 1

#         return index

#     def remove_object(self, object_id: str):
#         """Remove an object's velocity vector using swap-with-last."""
#         if object_id not in self.id_to_index:
#             return

#         index = self.id_to_index[object_id]
#         self._remove_by_swap(index, object_id)

#     def update_object(self, game_obj: GameObject):
#         """Update an existing object's velocity vector in the array."""
#         if game_obj.object_id not in self.id_to_index:
#             self.add_object(game_obj)
#             return

#         index = self.id_to_index[game_obj.object_id]
#         self._update_object_data(index, game_obj)

#     def _update_object_data(self, index: int, game_obj: GameObject):
#         """Update the array data for a velocity vector at the given index."""
#         if self.data is None:
#             return

#         element = self.data[index]

#         # Store object ID
#         element['object_id'] = game_obj.object_id

#         # Start position (object position)
#         element['start_position'] = [game_obj.U, game_obj.V]

#         # Color (use same as icon)
#         color = game_obj.override_color if game_obj.override_color else game_obj.color_rgba
#         element['color'] = [c / 255.0 if c > 1.0 else c for c in color]

#         # Store raw values for shader use
#         element['heading'] = game_obj.Heading
#         element['velocity'] = game_obj.CAS

#     def get_render_data(self) -> Optional[np.ndarray]:
#         """Get render data in a format compatible with the SoA interface."""
#         return self.get_active_data()

# class LockLineRenderData(BaseRenderData):
#     """
#     Array of Structs for target lock line rendering.
#     Each element contains: lock_pair, start_position, end_position, color
#     """

#     def _get_dtype(self):
#         """Get the numpy dtype for lock line structured array."""
#         return np.dtype([
#             ('lock_pair', 'U101'),  # "source_id:target_id" (Unicode 101 chars)
#             ('start_position', np.float32, (2, )),  # Start point (x, y)
#             ('end_position', np.float32, (2, )),  # End point (x, y)
#             ('color', np.float32, (4, ))  # RGBA normalized 0.0-1.0
#         ])

#     def _initialize_array(self, capacity: int):
#         """Initialize the lock line structured array."""
#         self.capacity = capacity
#         self.data = np.zeros(capacity, dtype=self._get_dtype())

#     def _get_object_id_from_element(self, element) -> str:
#         """Extract lock_pair from a lock line element."""
#         return str(element['lock_pair'])

#     def add_lock_line(self, source_obj: GameObject, target_obj: GameObject) -> int:
#         """Add a lock line between two objects."""
#         index = self._get_free_index()
#         lock_pair = f"{source_obj.object_id}:{target_obj.object_id}"

#         # Store the mapping
#         self.id_to_index[lock_pair] = index

#         # Update the data
#         self._update_lock_line_data(index, source_obj, target_obj, lock_pair)
#         self.count += 1

#         return index

#     def remove_object_locks(self, object_id: str):
#         """Remove all lock lines involving the given object (as source or target)."""
#         to_remove = []

#         # Find all lock pairs involving this object
#         for lock_pair in self.id_to_index.keys():
#             source_id, target_id = lock_pair.split(":")
#             if source_id == object_id or target_id == object_id:
#                 to_remove.append(lock_pair)

#         # Remove them using swap-with-last
#         for lock_pair in to_remove:
#             self._remove_lock_line(lock_pair)

#     def _remove_lock_line(self, lock_pair: str):
#         """Remove a specific lock line using swap-with-last."""
#         if lock_pair not in self.id_to_index:
#             return

#         index = self.id_to_index[lock_pair]
#         self._remove_by_swap(index, lock_pair)

#     def _update_lock_line_data(self, index: int, source_obj: GameObject, target_obj: GameObject, lock_pair: str):
#         """Update the array data for a lock line at the given index."""
#         if self.data is None:
#             return

#         element = self.data[index]

#         # Store lock pair ID
#         element['lock_pair'] = lock_pair

#         # Start position (source object)
#         element['start_position'] = [source_obj.U, source_obj.V]

#         # End position (target object)
#         element['end_position'] = [target_obj.U, target_obj.V]

#         # Color (use source object color but make it slightly different for lock lines)
#         source_color = source_obj.override_color if source_obj.override_color else source_obj.color_rgba
#         # Make lock lines slightly brighter/more saturated
#         lock_color = [min(1.0, c / 255.0 * 1.2) if c > 1.0 else min(1.0, c * 1.2) for c in source_color]
#         element['color'] = lock_color

#     def get_render_data(self) -> Optional[np.ndarray]:
#         """Get render data in a format compatible with the SoA interface."""
#         return self.get_active_data()

# class RenderDataArrays:
#     """
#     Master container for all Array of Structs render data arrays.
#     Contains separate arrays for icons, velocity vectors, and lock lines.
#     All data is stored contiguously for optimal GPU performance.
#     """

#     def __init__(self, initial_capacity: int = 1000):
#         """Initialize all render data arrays."""
#         # Separate rendering arrays
#         self.icons = IconRenderData(initial_capacity)
#         self.velocity_vectors = VelocityVectorRenderData(initial_capacity)
#         self.lock_lines = LockLineRenderData(initial_capacity // 2)  # Fewer lock lines typically

#     def resize_arrays(self, new_capacity: int):
#         """Resize all render data arrays to accommodate more objects."""
#         self.icons.resize(new_capacity)
#         self.velocity_vectors.resize(new_capacity)
#         self.lock_lines.resize(new_capacity // 2)

#     def add_object(self, game_obj: GameObject) -> int:
#         """Add a game object to all relevant render arrays."""
#         # Add to icon array (all objects have icons)

#         if game_obj.icon is not None:
#             icon_index = self.icons.add_object(game_obj)

#         # Add velocity vector if it's a moving object
#         if game_obj.is_air_unit() and game_obj.CAS > 0:
#             self.velocity_vectors.add_object(game_obj)

#         # Add lock line if this object has a target lock
#         if game_obj.locked_target_obj is not None:
#             self.lock_lines.add_lock_line(game_obj, game_obj.locked_target_obj)

#         return icon_index

#     def remove_object(self, object_id: str):
#         """Remove an object from all render arrays."""
#         self.icons.remove_object(object_id)
#         self.velocity_vectors.remove_object(object_id)
#         self.lock_lines.remove_object_locks(object_id)

#     def update_object(self, game_obj: GameObject):
#         """Update an object in all relevant render arrays."""
#         # Update icon data (all objects have icons)
#         self.icons.update_object(game_obj)

#         # Update or add/remove velocity vector based on movement
#         if game_obj.is_air_unit() and game_obj.CAS > 0:
#             if game_obj.object_id in self.velocity_vectors.id_to_index:
#                 self.velocity_vectors.update_object(game_obj)
#             else:
#                 self.velocity_vectors.add_object(game_obj)
#         else:
#             self.velocity_vectors.remove_object(game_obj.object_id)

#         # Update or add/remove lock lines based on target locks
#         self.lock_lines.remove_object_locks(game_obj.object_id)  # Remove existing locks
#         if game_obj.locked_target_obj is not None:
#             self.lock_lines.add_lock_line(game_obj, game_obj.locked_target_obj)

#     def get_render_data(self) -> Optional[dict]:
#         """Get all render data arrays for GPU rendering."""
#         return {
#             'icons': self.icons.get_render_data(),
#             'velocity_vectors': self.velocity_vectors.get_render_data(),
#             'lock_lines': self.lock_lines.get_render_data()
#         }

#     def get_contiguous_render_data(self) -> dict[str, Optional[np.ndarray]]:
#         """
#         Get all render data arrays as contiguous numpy arrays optimized for GPU buffer uploads.
#         Since AoS data is already contiguous, this returns the raw structured arrays.
#         """
#         return {
#             'icons': self.icons.get_contiguous_data(),
#             'velocity_vectors': self.velocity_vectors.get_contiguous_data(),
#             'lock_lines': self.lock_lines.get_contiguous_data()
#         }

#     def get_memory_info(self) -> dict:
#         """Get memory usage information for all arrays."""
#         return {
#             'icons': {
#                 'capacity': self.icons.capacity,
#                 'count': self.icons.count,
#                 'utilization': self.icons.count / self.icons.capacity if self.icons.capacity > 0 else 0,
#                 'memory_bytes': self.icons.data.nbytes if self.icons.data is not None else 0,
#                 'element_size': self.icons.data.itemsize if self.icons.data is not None else 0
#             },
#             'velocity_vectors': {
#                 'capacity':
#                 self.velocity_vectors.capacity,
#                 'count':
#                 self.velocity_vectors.count,
#                 'utilization':
#                 self.velocity_vectors.count /
#                 self.velocity_vectors.capacity if self.velocity_vectors.capacity > 0 else 0,
#                 'memory_bytes':
#                 self.velocity_vectors.data.nbytes if self.velocity_vectors.data is not None else 0,
#                 'element_size':
#                 self.velocity_vectors.data.itemsize if self.velocity_vectors.data is not None else 0
#             },
#             'lock_lines': {
#                 'capacity': self.lock_lines.capacity,
#                 'count': self.lock_lines.count,
#                 'utilization': self.lock_lines.count / self.lock_lines.capacity if self.lock_lines.capacity > 0 else 0,
#                 'memory_bytes': self.lock_lines.data.nbytes if self.lock_lines.data is not None else 0,
#                 'element_size': self.lock_lines.data.itemsize if self.lock_lines.data is not None else 0
#             }
#         }
