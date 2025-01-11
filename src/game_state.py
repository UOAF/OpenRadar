import acmi_parse
import datetime
import queue
import math
from dataclasses import dataclass

from typing import Type
from enum import Enum, auto

from game_objects import *

# This can cause an attempt to delete objects that are not in the game state
# TODO: If perfomance becomes an issues consider reimplementing this list.
# HIDDEN_OBJECT_CLASSES = ("Static", "Projectile", "Vehicle", "Flare", "Chaff", "Explosion", "Parachutist", "Bomb", "Rotorcraft")

# CLASS_MAP = {
#     "Navaid+Static+Bullseye": Bullseye,
#     "FixedWing": fixedWing,
#     "Rotorcraft": rotaryWing,
#     "Missile": missile,
#     "Ground+Vehicle": groundUnit,
#     "Watercraft": surfaceVessel
# }

SUPPORTED_CLASSES = Bullseye | fixedWing | rotaryWing | missile | groundUnit | surfaceVessel
@dataclass
class GameObjectClassDescription:
    id: int
    class_type: Type[SUPPORTED_CLASSES]
    tacview_class: str

class GameObjectClassType(Enum):
    """
    Enumeration of track types.
    """
    FIXEDWING = GameObjectClassDescription(auto(), fixedWing, "FixedWing")
    ROTARYWING = GameObjectClassDescription(auto(), rotaryWing, "Rotorcraft")
    MISSILE = GameObjectClassDescription(auto(), missile, "Missile")
    GROUND = GameObjectClassDescription(auto(), groundUnit, "Ground+Vehicle")
    SEA = GameObjectClassDescription(auto(), surfaceVessel, "Watercraft")
    BULLSEYE = GameObjectClassDescription(auto(), Bullseye, "Navaid+Static+Bullseye")


class GameState:
    """
    Represents the state of the game.

    Attributes:
        objects (list[AcmiParse.ACMIObject]): List of ACMI objects in the game.
        data_queue (queue.Queue): Queue to store incoming data from the Tacview client.
        global_vars (dict): Dictionary to store global variables.
        parser (AcmiParse.ACMIFileParser): ACMI parser to parse incoming data.
    """

    def __init__(self, data_queue: queue.Queue[str]):
        self.data_queue: queue.Queue[str] = data_queue
        self.global_vars = dict()

        self.reference_time: datetime.datetime | None = None
        self.current_time: datetime.datetime | None = None

        self.objects: dict[GameObjectClassType, dict["str", GameObject]] = {
            class_type: dict()
            for class_type in GameObjectClassType
        }
        self.all_objects: dict["str", GameObject] = dict()
        # Create the ACMI parser
        self.parser = acmi_parse.ACMIFileParser()

    def get_bullseye_pos(self):
        if '7fffffffffffffff' not in self.objects[GameObjectClassType.BULLSEYE]:
            return (0, 0)
        return self.objects[GameObjectClassType.BULLSEYE]['7fffffffffffffff'].get_pos()

    def update_state(self):
        """
        Update the game state with the latest data from the Tacview client.
        """
        # print(f"getting data from queue {self.data_queue._qsize()}")
        while not self.data_queue.empty():

            line = self.data_queue.get()
            print("Got line")
            if line is None: break  # End of data

            acmiline = self.parser.parse_line(line)  # Parse the line into a dict
            if acmiline is None:
                print(f"Failed to parse line: {line}")
                continue  # Skip if line fails to parse

            if acmiline.action in acmi_parse.ACTION_REMOVE:
                # Remove object from battlefield
                if acmiline.object_id is not None:
                    self._remove_object(acmiline.object_id)
                else:
                    print(f"tried to delete object {acmiline.object_id} with unitialized object_id")
                # print(f"tried to delete object {acmiline.object_id} not in self.state")

            elif acmiline.action in acmi_parse.ACTION_TIME:
                if self.reference_time is not None and acmiline.delta_time is not None:
                    self.current_time = self.reference_time + datetime.timedelta(seconds=acmiline.delta_time)

            elif acmiline.action in acmi_parse.ACTION_GLOBAL and isinstance(acmiline, acmi_parse.ACMIObject):
                self.global_vars = self.global_vars | acmiline.properties
                if "ReferenceTime" in acmiline.properties:
                    # format 2024-6-9T00:00:00Z
                    self.reference_time = datetime.datetime.strptime(acmiline.properties["ReferenceTime"],
                                                                     "%Y-%m-%dT%H:%M:%SZ")
                    self.reference_time = self.reference_time.replace(tzinfo=datetime.timezone.utc)

            elif acmiline.action in acmi_parse.ACTION_UPDATE and isinstance(acmiline, acmi_parse.ACMIObject):
                self._update_object(acmiline)

            else:
                print(f"Unknown action {acmiline.action} in {acmiline}")

    def get_nearest_object(self, world_pos: tuple[float, float], hover_dist_world: float) -> GameObject | None:
        """
        Gets the object ID of the object that is being hovered over.
        
        Args:
            world_pos (tuple[int, int]): The position in world units to consider an object hovered over.
            hover_dist_world (float): The distance in world units to consider an object hovered over.
            
        Returns:
            str: The object ID of the object being hovered over.
        """
        closest = None
        closest_dist = float('inf')
        for id in self.all_objects:
            obj = self.all_objects[id]
            dist = math.dist(world_pos, (obj.data.T.U, obj.data.T.V))
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
            object_id (str): The ID of the object to remove.
        """
        for subdict in self.objects.values():
            if object_id in subdict:
                del subdict[object_id]
                del self.all_objects[object_id]
                return

        # print(f"tried to delete object {object_id} not in self.objects")  #TODO handle objects not in CLASS_MAP

    def _update_object(self, updateObj: acmi_parse.ACMIObject) -> None:
        """
        Update an object in the game state.

        Args:
            updateObj (AcmiParse.ACMIObject): The Object with the new data to update.
        """
        if self.current_time is not None:
            updateObj.timestamp = self.current_time

        if updateObj.object_id in self.all_objects:
            self.all_objects[updateObj.object_id].update(updateObj)
            self._update_target_lock(self.all_objects[updateObj.object_id])
        else:
            for classenum in GameObjectClassType:
                if classenum.value.tacview_class in updateObj.Type:
                    subdict = self.objects[classenum]
                    subdict[updateObj.object_id] = classenum.value.class_type(updateObj)
                    self.all_objects[updateObj.object_id] = subdict[updateObj.object_id]
                    break

    def _update_target_lock(self, updateObj: GameObject) -> None:
        if updateObj.data.LockedTarget not in [None, "", "0"]:
            if updateObj.data.LockedTarget in self.all_objects:
                updateObj.locked_target = self.all_objects[updateObj.data.LockedTarget]
            else:
                print(f"Target {updateObj.data.LockedTarget} not found")
        else:
            updateObj.locked_target = None

        #TODO handle objects not in CLASS_MAP

    def clear_state(self) -> None:
        """
        Clear the game state.
        """
        self.__init__(self.data_queue)
