import acmi_parse
from trtt_client import TRTTClientThread
import queue 

from typing import Type

from game_objects import *

# This can cause an attempt to delete objects that are not in the game state
# TODO: If perfomance becomes an issues consider reimplementing this list.
HIDDEN_OBJECT_CLASSES = ("Static", "Projectile", "Vehicle", "Flare", "Chaff", "Explosion", "Parachutist", "Bomb", "Rotorcraft") 

CLASS_MAP = {
    "Navaid+Static+Bullseye": Bullseye,
    "FixedWing": fixedWing,
    "Rotorcraft": rotaryWing,
    "Missile": missile,
    "Ground+Vehicle": groundUnit,
    "Watercraft": surfaceVessel
}

SUPPORTED_CLASSES = Bullseye | fixedWing | rotaryWing | missile | groundUnit | surfaceVessel

class GameState:
    """
    Represents the state of the game.

    Attributes:
        objects (list[AcmiParse.ACMIObject]): List of ACMI objects in the game.
        data_queue (queue.Queue): Queue to store incoming data from the Tacview client.
        global_vars (dict): Dictionary to store global variables.
        parser (AcmiParse.ACMIFileParser): ACMI parser to parse incoming data.
    """

    def __init__(self):      
        self.data_queue: queue.Queue[str] = queue.Queue()
        self.global_vars = dict()
        
        self.new_objects: dict[Type[SUPPORTED_CLASSES], dict["str", GameObject] ] = {clas: dict() for clas in CLASS_MAP.values()}
        self.all_objects: dict["str", GameObject] = dict()
        # Create the ACMI parser
        self.parser = acmi_parse.ACMIFileParser()

        # Create the Tacview RT Relemetry client
        self.tac_client = TRTTClientThread(self.data_queue) #TODO move to somewhere more sensible
        self.tac_client.start()

    def __del__(self):
        self.tac_client.stop()
        
    def get_bullseye_pos(self):
        if '7fffffffffffffff' not in self.new_objects[Bullseye]:
            return (0,0)
        return self.new_objects[Bullseye]['7fffffffffffffff'].get_pos()
    

    def update_state(self):
        """
        Update the game state with the latest data from the Tacview client.
        """
        # print(f"getting data from queue {self.data_queue._qsize()}")
        while not self.data_queue.empty():

            line = self.data_queue.get()
            # print(line)
            if line is None: break # End of data

            acmiline = self.parser.parse_line(line) # Parse the line into a dict
            if acmiline is None: 
                print(f"Failed to parse line: {line}")
                continue # Skip if line fails to parse
            
            if acmiline.action in acmi_parse.ACTION_REMOVE:
                # Remove object from battlefield
                if acmiline.object_id is not None:
                    self._remove_object(acmiline.object_id)
                else:
                    print(f"tried to delete object {acmiline.object_id} with unitialized object_id")
                # print(f"tried to delete object {acmiline.object_id} not in self.state")

            elif acmiline.action in acmi_parse.ACTION_TIME:
                pass

            elif acmiline.action in acmi_parse.ACTION_GLOBAL and isinstance(acmiline, acmi_parse.ACMIObject):
                self.global_vars = self.global_vars | acmiline.properties

            elif acmiline.action in acmi_parse.ACTION_UPDATE and isinstance(acmiline, acmi_parse.ACMIObject):
                # if not any(clas in acmiline.Type for clas in HIDDEN_OBJECT_CLASSES): # Skip hidden objects 
                # TODO Refrence comment on HIDDEN_OBJECT_CLASSES declaration
                self._update_object(acmiline)

            else:
                print(f"Unknown action {acmiline.action} in {acmiline}")

    def _remove_object(self, object_id: str) -> None:
        """
        Remove an object from the game state.

        Args:
            object_id (str): The ID of the object to remove.
        """       
        for subdict in self.new_objects.values():
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
        for key in CLASS_MAP:
            if key in updateObj.Type:
                
                subdict = self.new_objects[CLASS_MAP[key]]
                if updateObj.object_id not in subdict:
                    subdict[updateObj.object_id] = CLASS_MAP[key](updateObj)
                    self.all_objects[updateObj.object_id] = subdict[updateObj.object_id]
                else:
                    subdict[updateObj.object_id].update(updateObj)
                    
                break
            
        #TODO handle objects not in CLASS_MAP