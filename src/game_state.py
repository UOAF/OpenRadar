import acmi_parse
import datetime
import queue
import math
import numpy as np

from game_object_types import GameObjectType, infer_object_type_from_tacview
from game_object import GameObject
from render_data_arrays import TrackRenderDataArrays
from draw.shapes import Shapes


class GameState:
    """
    Represents the state of the game using the refactored GameObject system.

    Attributes:
        objects: Dictionary organized by GameObjectType containing all game objects
        all_objects: Flat dictionary for quick object ID lookups  
        data_queue: Queue to store incoming data from the Tacview client
        global_vars: Dictionary to store global variables
        parser: ACMI parser to parse incoming data
    """

    def __init__(self, data_queue: queue.Queue[str]):
        self.data_queue: queue.Queue[str] = data_queue
        self.global_vars = dict()

        # Organize objects by type for efficient access
        self.objects: dict[GameObjectType, dict[str, GameObject]] = {
            obj_type: dict()
            for obj_type in GameObjectType if obj_type != GameObjectType.UNKNOWN
        }
        self.all_objects: dict[str, GameObject] = dict()

        # Create the ACMI parser
        self.parser = acmi_parse.ACMIFileParser()

        # Initialize render data arrays for GPU rendering
        self.render_arrays = TrackRenderDataArrays()

    def get_time(self) -> datetime.datetime:
        """Get current simulation time."""
        return self.parser.get_time()

    def get_bullseye_pos(self) -> tuple[float, float]:
        """Get bullseye position, returns (0,0) if no bullseye found."""
        # Bullseye typically has a special object ID in Tacview
        bullseye_objects = self.objects[GameObjectType.BULLSEYE]
        if '7fffffffffffffff' in bullseye_objects:
            return bullseye_objects['7fffffffffffffff'].get_pos()
        # Fallback: return first bullseye found
        if bullseye_objects:
            return next(iter(bullseye_objects.values())).get_pos()
        return (0.0, 0.0)

    def update_state(self):
        """
        Update the game state with the latest data from the Tacview client.
        """
        while not self.data_queue.empty():
            line = self.data_queue.get()
            if line is None:
                break  # End of data

            acmiline = self.parser.parse_line(line)
            if acmiline is None:
                print(f"Failed to parse line: {line}")
                continue

            if acmiline.action == acmi_parse.ACTION_REMOVE:
                # Remove object from battlefield
                if acmiline.object_id is not None:
                    self._remove_object(acmiline.object_id)
                else:
                    print(f"Tried to delete object with uninitialized object_id")

            elif acmiline.action == acmi_parse.ACTION_TIME:
                # Time updates are handled by the parser
                pass

            elif acmiline.action == acmi_parse.ACTION_GLOBAL and isinstance(acmiline, acmi_parse.ACMIObject):
                # Update global variables
                self.global_vars = self.global_vars | acmiline.properties

            elif acmiline.action == acmi_parse.ACTION_UPDATE and isinstance(acmiline, acmi_parse.ACMIObject):
                # Update or create object
                self._update_object(acmiline)

            else:
                print(f"Unknown action {acmiline.action} in {acmiline}")

    def get_nearest_object(self, world_pos: tuple[float, float]) -> GameObject | None:
        """
        Gets the object that is nearest to the specified world position.

        Args:
            world_pos: The position in world units to search near

        Returns:
            The nearest GameObject, or None if none found within distance
        """
        nearest_obj_id = self.get_nearest_object_id(world_pos)
        nearest_obj = self.all_objects.get(nearest_obj_id) if nearest_obj_id is not None else None
        return nearest_obj

    def get_nearest_object_id(self, world_pos: tuple[float, float]) -> str | None:
        """
        Gets the object_id that is nearest to the specified world position.
        
        Args:
            world_pos: The position in world units to search near
            
        Returns:
            The nearest object_id, or None if none found within distance
        """
        closest_object_id = None
        closest_dist = float('inf')

        # Convert world_pos to numpy array for vectorized operations
        target_pos = np.array(world_pos, dtype=np.float32)

        # Search through all icon render arrays (organized by shape)
        for shape, icon_data in self.render_arrays.icon_data.items():
            # Get active data from the numpy structured array
            active_data = icon_data.get_active_data()

            if active_data is None or len(active_data) == 0:
                continue

            # Extract positions from the structured array (shape: (N, 2))
            positions = active_data['position']

            # Calculate squared distances using vectorized numpy operations
            # This is much faster than iterating through objects individually
            diff = positions - target_pos
            sq_distances = np.sum(diff * diff, axis=1)

            # Find the minimum distance in this shape's data
            if len(sq_distances) > 0:
                min_idx = np.argmin(sq_distances)
                min_dist = np.sqrt(sq_distances[min_idx])

                # Check if this is the closest so far
                if min_dist < closest_dist:
                    closest_dist = min_dist
                    # Get the object_id using the index mapping (convert numpy int to Python int)
                    closest_object_id = icon_data.index_to_id.get(int(min_idx))

        return closest_object_id

    def get_nearest_object_old(
        self, world_pos: tuple[float, float], hover_dist_world: float = float('inf')) -> GameObject | None:
        """
        Gets the object that is nearest to the specified world position.
        
        Args:
            world_pos: The position in world units to search near
            hover_dist_world: Maximum distance to consider an object "near"
            
        Returns:
            The nearest GameObject, or None if none found within distance
        """
        closest = None
        closest_dist = float('inf')

        for obj in self.all_objects.values():
            dist = math.dist(world_pos, obj.get_pos())
            if dist < closest_dist:
                closest = obj
                closest_dist = dist

        if closest is None or closest_dist > hover_dist_world:
            return None
        return closest

    def _remove_object(self, object_id: str) -> None:
        """
        Remove an object from the game state.

        Args:
            object_id: The ID of the object to remove
        """
        # Remove from render data arrays
        object_to_remove = self.all_objects.get(object_id)
        if object_to_remove is not None:
            self.render_arrays.remove_object(object_to_remove)

        # Find and remove from type-specific dictionary
        for type_dict in self.objects.values():
            if object_id in type_dict:
                del type_dict[object_id]
                break

        # Remove from flat lookup dictionary
        if object_id in self.all_objects:
            del self.all_objects[object_id]

    def _update_object(self, updateObj: acmi_parse.ACMIObject) -> None:
        """
        Update an existing object or create a new one.

        Args:
            updateObj: The ACMIObject with new data to apply
        """
        object_id = updateObj.object_id

        # Update existing object
        if object_id in self.all_objects:
            game_obj = self.all_objects[object_id]
            game_obj.update(updateObj)
            self._update_target_lock(game_obj)

            # Update render data arrays
            self.render_arrays.update_object(game_obj)
            return

        # Create new object
        obj_type = infer_object_type_from_tacview(updateObj.Type)
        if obj_type == GameObjectType.UNKNOWN:
            # Skip unknown object types for now
            return

        # Determine color based on object type and coalition
        # color = self._get_default_color(obj_type, updateObj.Coalition)

        # Create new GameObject
        game_obj = GameObject(object_id, obj_type, updateObj)

        # Add to dictionaries
        self.objects[obj_type][object_id] = game_obj
        self.all_objects[object_id] = game_obj

        # Add to render data arrays
        self.render_arrays.add_object(game_obj)

    def _update_target_lock(self, game_obj: GameObject) -> None:
        """Update target lock references for an object."""
        game_obj.resolve_locked_targets(self.all_objects)

    def clear_state(self) -> None:
        """Clear the game state."""
        # Clear any remaining data in the queue to prevent processing stale/corrupted data
        while not self.data_queue.empty():
            try:
                self.data_queue.get_nowait()
            except queue.Empty:
                break

        # Reinitialize all state
        self.__init__(self.data_queue)

    def change_side_color(self, coalition: str, new_color: tuple[float, float, float, float]) -> None:
        """Change the side color for a specific coalition."""
        # Update the color for all objects belonging to the specified coalition
        for obj in self.all_objects.values():
            if obj.Coalition == coalition:
                obj.override_color = new_color
                self.render_arrays.update_object(obj)
