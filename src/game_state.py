import acmi_parse
import datetime
import queue
import math

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

    def get_nearest_object(self, world_pos: tuple[float, float],
                           hover_dist_world: float = float('inf')) -> GameObject | None:
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

        # If the object has locked targets, update their render data
        # for target in game_obj.locked_target_objs:
        #     if target.icon is not None:
        #         shape = Shapes.from_idx(target.icon)
        #         self.icon_data[shape].update_object(target)

    def _get_default_color(self, obj_type: GameObjectType, coalition: str) -> tuple[float, float, float, float]:
        """Get default color for an object based on its type and coalition."""
        # Simple default coloring - can be made more sophisticated
        if obj_type == GameObjectType.BULLSEYE:
            return (128, 128, 128, 255)  # Gray
        elif "Blue" in coalition or "US" in coalition:
            return (0, 0, 255, 255)  # Blue for friendly
        elif "Red" in coalition or "OPFOR" in coalition:
            return (255, 0, 0, 255)  # Red for hostile
        else:
            return (255, 255, 0, 255)  # Yellow for unknown

    def clear_state(self) -> None:
        """Clear the game state."""
        self.__init__(self.data_queue)
