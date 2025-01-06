from game_state import GameState
from sensor_tracks import Track, SensorTracks
class DisplayData:
    """
    Class of objects to display on the screen.
    """
    def __init__(self, gamestate: GameState, tracks: SensorTracks):
        self.gamestate = gamestate
        self.annotations = []
        self.sensor_tracks = tracks
        self.tracks = self.sensor_tracks.tracks
        
    def render(self):
        """
        Render the display data.
        """
        # for track in self.tracks:
        #     track.render()
            
        # for annotation in self.annotations:
        #     annotation.render()
        
    


