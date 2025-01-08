from game_state import GameState
from sensor_tracks import Track, SensorTracks
class DisplayData:
    """
    Class of objects to display on the screen.
    """
    def __init__(self, gamestate: GameState, tracks: SensorTracks):
        self.gamestate = gamestate
        self.sensor_tracks = tracks
        self.tracks = self.sensor_tracks.tracks
        
    def generate_render_instance_arrays(self):
        """
        Generate the instance arrays for rendering. called 
        """
        pass
        #
        
    def render(self):
        """
        Render the display data.
        """
        # for track in self.tracks:
        # if track is ac:
        #     render_ac()
        #     track.render()
            
        # for annotation in self.annotations:
        #     annotation.render()
        
    


