import datetime
from turtle import heading
from attr import dataclass

from game_state import GameState


@dataclass
class Coalition:
    name: str
    color: tuple[int, int, int]
    allies: list[str]


# List of coalitions in the current game state
game_coalitions: dict[str, Coalition] = {}


def get_coalition(name: str, color: tuple[int, int, int]) -> Coalition | None:
    """
    Get a coalition by name. If the coalition does not exist, create it.
    """
    if name in game_coalitions:
        return game_coalitions.get(name)

    if name != "":
        coalition = Coalition(name, color, [])
        game_coalitions[name] = coalition
        return coalition

    return None


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
    speed: float
    last_seen: datetime.datetime | None
    history: list[tuple[tuple[float, float], datetime.datetime]] = []
    confidence: float = 0.0
    classification: str = "---"
    source: str = ""
    track_id: int = 0
    coalition: Coalition | None = None

    def update(self, position: tuple[float, float], velocity: float, heading: float, altitude: float, speed: float,
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
        self.speed = speed


class SensorTracks:

    def __init__(self, gamestate: GameState):
        self.gamestate = gamestate
        self.tracks: dict[str, Track] = {}
        self.track_id = 0

    def update(self):
        """
        Update the radar tracks.
        """
        for id, object in self.gamestate.all_objects.items():

            if not id in self.tracks:

                # Create a new track
                pos_m = (object.data.T.U, object.data.T.V)
                vel_m_s = (object.data.CAS)
                heading_deg = object.data.T.Heading
                altitude_m = object.data.T.Altitude
                self.tracks[id] = Track(id, object.data.Type, pos_m, vel_m_s, heading_deg, altitude_m, vel_m_s,
                                        object.data.timestamp)
                # Set coalition
                pass

            else:
                # Create a new track
                pos_m = (object.data.T.U, object.data.T.V)
                vel_m_s = (object.data.CAS)
                heading_deg = object.data.T.Heading
                altitude_m = object.data.T.Altitude
                self.tracks[id].update(pos_m, vel_m_s, heading_deg, altitude_m, vel_m_s, object.data.timestamp)
                # Set coalition
                pass
