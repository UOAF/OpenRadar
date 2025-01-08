import datetime

from typing import Type
from dataclasses import dataclass, field

from tomlkit import date

from game_state import GameState, GameObjectClassType
import game_objects


@dataclass
class Coalition:
    name: str
    color: tuple[float, float, float, float]
    allies: list[str]


# List of coalitions in the current game state
game_coalitions: dict[str, Coalition] = {}


def get_coalition(name: str, color: tuple[float, float, float, float]) -> Coalition:
    """
    Get a coalition by name. If the coalition does not exist, create it.
    """
    if name in game_coalitions:
        return game_coalitions[name]

    if name != "":
        coalition = Coalition(name, color, [])
        game_coalitions[name] = coalition
        return coalition

    assert False, f"Invalid coalition name {name}"


@dataclass
class Track:
    """
    A radar track.
    """
    id: str
    label: str
    position: tuple[float, float]
    velocity: float
    heading: float
    altitude: float
    last_seen: datetime.datetime
    class_type: GameObjectClassType
    coalition: Coalition
    history: list[tuple[tuple[float, float], datetime.datetime]] = field(default_factory=list)
    confidence: float = 0.0
    classification: str = "---"
    source: str = ""
    track_id: int = 0

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
        self.velocity = velocity
        self.heading = heading
        self.altitude = altitude


class SensorTracks:

    def __init__(self, gamestate: GameState):
        self.gamestate = gamestate
        self.tracks: dict[GameObjectClassType, dict[str, Track]] = {}
        self.track_id = 0
        self.cur_time: datetime.datetime | None = None
        self.track_inactivity_timeout_sec = 60

        self.update_bullseye()

    def update_bullseye(self):
        self.bullseye = self.gamestate.get_bullseye_pos()

    def update(self):
        """
        Update the radar tracks.
        """
        self.cur_time = self.gamestate.current_time  # Only updates the current time when tracks are updated, this may be undeseirable

        for classenum, object_class_dict in self.gamestate.objects.items():

            for object_id, object in object_class_dict.items():

                if not object_id in self.tracks:
                    # Create a new track
                    side = get_coalition(object.data.Coalition, object.color)
                    self.tracks[classenum][object_id] = Track(
                        object_id,
                        object.data.Type,
                        (object.data.T.U, object.data.T.V),
                        object.data.CAS,
                        object.data.T.Heading,
                        object.data.T.Altitude,
                        object.data.timestamp,  # type: ignore #TODO enforce datetime is not None in static analysis
                        classenum,
                        side)

                else:
                    self.tracks[classenum][object_id].update((object.data.T.U, object.data.T.V), object.data.CAS,
                                                             object.data.T.Heading, object.data.T.Altitude,
                                                             object.data.timestamp)

        # Remove old tracks
        if self.cur_time is None:  # Do not remove tracks if the current time is not set
            return
        for classenum, track_dict in self.tracks.items():
            for id, track in track_dict.items():
                if (self.cur_time - track.last_seen).total_seconds() > self.track_inactivity_timeout_sec:
                    del self.tracks[classenum][id]
