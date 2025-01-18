import datetime

from dataclasses import dataclass, field, fields
from enum import Enum

import config
from game_state import GameState, GameObjectClassType
from util.bms_math import M_PER_SEC_TO_KNOTS

class Declaration(Enum):
    FRIENDLY = 0
    HOSTILE = 1
    UNKNOWN = 2


@dataclass
class Coalition:
    name: str
    color: tuple[float, float, float, float]
    allies: list[str]
    enemies: list[str]

# List of coalitions in the current game state
game_coalitions: dict[str, Coalition] = {}


def get_coalition(name: str, color: tuple[float, float, float, float]) -> Coalition:
    """
    Get a coalition by name. If the coalition does not exist, create it.
    """
    if name in game_coalitions:
        return game_coalitions[name]

    if name != "":
        coalition = Coalition(name, color, [], [])
        game_coalitions[name] = coalition
        return coalition
    
    if name == "":
        return Coalition("Unknown", (1, 0, 1, 1), [], [])

    assert False, f"Invalid coalition name {name}"


@dataclass
class Track:
    """
    A radar track.
    """
    id: str
    label: str
    position_m: tuple[float, float]
    velocity_ms: float
    heading_deg: float
    altitude_m: float
    last_seen: datetime.datetime
    class_type: GameObjectClassType
    coalition: Coalition
    history: list[tuple[tuple[float, float], datetime.datetime]] = field(default_factory=list)
    confidence: float = 0.0
    classification: str = "---"
    source: str = ""
    track_id: int = 0
    
    @property
    def velocity_kts(self) -> float:
        return self.velocity_ms * M_PER_SEC_TO_KNOTS

    def update(self, position: tuple[float, float], velocity: float, heading: float, altitude: float,
               time: datetime.datetime | None):
        """
        Update the track with the latest data.
        """
        if self.last_seen is not None:
            self.history.append((self.position, self.last_seen))
        if time is not None:
            self.last_seen = time
        else:
            self.last_seen = datetime.datetime.now()
            print(f"WARNING Track {self.id} has no timestamp")
        self.position = position
        self.velocity_ms = velocity
        self.heading = heading
        self.altitude = altitude
        
    def get_declaration(self) -> Declaration:
        controler_coalition = config.app_config.get("controler", "coalition", str) #TODO parse to proper coalition object and link decleration to track for override
        if controler_coalition not in game_coalitions:
            print(f"Controler coalition {controler_coalition} not found in game_coalitions")
            return Declaration.UNKNOWN

        
        if controler_coalition == self.coalition.name or controler_coalition in self.coalition.allies: 
            return Declaration.FRIENDLY
        if controler_coalition in self.coalition.enemies:
            return Declaration.HOSTILE
        
        # TODO remove 
        if self.coalition.name == "DPRK": # this is only for testing
            return Declaration.HOSTILE
        return Declaration.UNKNOWN
        


class SensorTracks:

    def __init__(self, gamestate: GameState):
        self.gamestate = gamestate
        self.tracks: dict[GameObjectClassType, dict[str, Track]] = {class_type: {} for class_type in GameObjectClassType}
        self.cur_time: datetime.datetime | None = None
        self.track_inactivity_timeout_sec = 10

        self.update_bullseye()

    def update_bullseye(self):
        self.bullseye = self.gamestate.get_bullseye_pos()

    def update(self):
        """
        Update the radar tracks.
        """
        self.cur_time = self.gamestate.get_time()  # Only updates the current time when tracks are updated, this may be undeseirable

        for classenum, object_class_dict in self.gamestate.objects.items():

            for object_id, object in object_class_dict.items():

                if not object_id in self.tracks:
                    # Create a new track
                    if object.data.timestamp is None or (self.cur_time - object.data.timestamp).total_seconds() > self.track_inactivity_timeout_sec:
                       # Skip if the object has no timestamp or is too old
                       # will need to rethink this for ground/sea contacts
                       continue
                    side = get_coalition(object.data.Coalition, object.color)
                    self.tracks[classenum][object_id] = Track(
                        object_id,
                        object.data.Type,
                        (object.data.T.U, object.data.T.V),
                        object.data.CAS,
                        object.data.T.Heading,
                        object.data.T.Altitude,
                        object.data.timestamp, 
                        classenum,
                        side)

                else:
                    self.tracks[classenum][object_id].update((object.data.T.U, object.data.T.V), object.data.CAS,
                                                             object.data.T.Heading, object.data.T.Altitude,
                                                             object.data.timestamp)

        # Remove old tracks
        # if self.cur_time is None:  # Do not remove tracks if the current time is not set
        #     return
        for classenum, track_dict in self.tracks.items():
            to_delete = []
            for id, track in track_dict.items():
                # if track.last_seen is not None:  
                    if (self.cur_time - track.last_seen).total_seconds() > self.track_inactivity_timeout_sec:
                        to_delete.append(id)    
                        # print(f"Removing track {id} due to inactivity, last seen {(self.cur_time - track.last_seen).total_seconds()}, timeout {self.track_inactivity_timeout_sec}")
            for id in to_delete:
                del self.tracks[classenum][id]  
                
    def clear(self):
        """
        Clear all tracks.
        """
        for dict in self.tracks.values():
            dict.clear()
        self.update()

