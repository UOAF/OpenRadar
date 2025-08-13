from game_state import GameState
from sensor_tracks import Track, SensorTracks
from draw.track_renderer import TrackRenderer
from draw.icon_renderer import IconInstancedRenderer
from draw.vector_renderer import VectorRenderer
from draw.lock_renderer import LockRenderer
from draw.bullseye_renderer import BullseyeRenderer
from draw.annotations import MapAnnotations
from draw.scene import Scene
import config


class DisplayData:
    """
    Class of objects to display on the screen.
    """

    def __init__(self, scene: Scene, gamestate: GameState, tracks: SensorTracks):
        self.gamestate = gamestate
        self.scene = scene
        self.sensor_tracks = tracks
        self.tracks = self.sensor_tracks.tracks
        # self.track_renderer: TrackRenderer = TrackRenderer(self.scene)
        self.icon_renderer: IconInstancedRenderer = IconInstancedRenderer(self.scene)
        self.vector_renderer: VectorRenderer = VectorRenderer(self.scene)
        self.lock_renderer: LockRenderer = LockRenderer(self.scene)
        self.bullseye_renderer: BullseyeRenderer = BullseyeRenderer(self.scene)
        self.annotations: MapAnnotations = MapAnnotations(self.scene)

    def generate_render_arrays(self):
        """
        Generate the instance arrays for rendering. called 
        """
        # self.track_renderer.build_buffers(self.tracks)

        render_arrays = self.sensor_tracks.render_arrays

        if render_arrays:
            icon_arrays = render_arrays.get('icons', {})
            self.icon_renderer.load_render_arrays(icon_arrays)

            velocity_vectors = render_arrays.get('velocity_vectors')
            self.vector_renderer.load_render_arrays(velocity_vectors)

            lock_lines = render_arrays.get('lock_lines')
            self.lock_renderer.load_render_arrays(lock_lines)

        # Update bullseye if enabled and position available
        if config.app_config.get_bool("layers", "show_bullseye"):
            bullseye_pos = self.gamestate.get_bullseye_pos()
            if bullseye_pos != (0, 0):  # Valid bullseye position
                self.bullseye_renderer.set_bullseye(bullseye_pos[0], bullseye_pos[1])

    def render(self):
        """
        Render the display data.
        """
        # self.track_renderer.render()

        # Render annotations
        self.annotations.render()

        # Render bullseye if enabled
        if config.app_config.get_bool("layers", "show_bullseye"):
            self.bullseye_renderer.render()

        # Render lock lines using the new lock renderer
        self.lock_renderer.render()

        # Render icons using the new instanced renderer
        self.icon_renderer.render()

        # Render velocity vectors using the new vector renderer
        self.vector_renderer.render()

    def clear(self):
        """
        Clear the display data.
        """
        # self.track_renderer.clear()
        self.icon_renderer.clear()
        self.vector_renderer.clear()
        self.lock_renderer.clear()
        self.bullseye_renderer.clear()
        self.annotations.clear()

    def load_annotations_ini(self, ini_path):
        """
        Load annotations from INI file.
        
        Args:
            ini_path: Path to the INI file containing annotation data
        """
        self.annotations.load_ini(ini_path)
