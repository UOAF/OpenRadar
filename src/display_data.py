from game_state import GameState
from sensor_tracks import Track, SensorTracks
from draw.track_renderer import TrackRenderer
from draw.icon_renderer import IconInstancedRenderer
from draw.scene import Scene


class DisplayData:
    """
    Class of objects to display on the screen.
    """

    def __init__(self, scene: Scene, gamestate: GameState, tracks: SensorTracks):
        self.gamestate = gamestate
        self.scene = scene
        self.sensor_tracks = tracks
        self.tracks = self.sensor_tracks.tracks
        self.track_renderer: TrackRenderer = TrackRenderer(self.scene)
        self.icon_renderer: IconInstancedRenderer = IconInstancedRenderer(self.scene)

    def generate_render_arrays(self):
        """
        Generate the instance arrays for rendering. called 
        """
        self.track_renderer.build_buffers(self.tracks)

        icon_arrays = self.sensor_tracks.icon_arrays
        self.icon_renderer.load_render_arrays(icon_arrays)

    def render(self):
        """
        Render the display data.
        """
        self.track_renderer.render()

        # Render icons using the new instanced renderer
        self.icon_renderer.render()

    def clear(self):
        """
        Clear the display data.
        """
        self.track_renderer.clear()
        self.icon_renderer.clear()
        # self.annotations.clear()
