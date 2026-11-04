from game_object import GameObject
from game_state import GameState
from sensor_tracks import Track, SensorTracks
from draw.icon_renderer import IconInstancedRenderer
from draw.vector_renderer import VectorRenderer
from draw.lock_renderer import LockRenderer
from draw.bullseye_renderer import BullseyeRenderer
from draw.annotations import MapAnnotations
from draw.radar_labels_renderer import RadarLabelsRenderer
from draw.imgui_radar_labels_renderer import ImGuiRadarLabelsRenderer
from draw.scene import Scene
from typing import Optional
import config


class DisplayData:
    """
    Class of objects to display on the screen.
    """

    def __init__(self, scene: Scene, gamestate: GameState, tracks: SensorTracks):
        self.gamestate = gamestate
        self.scene = scene
        self.sensor_tracks = tracks
        self.icon_renderer: IconInstancedRenderer = IconInstancedRenderer(self.scene)
        self.vector_renderer: VectorRenderer = VectorRenderer(self.scene)
        self.lock_renderer: LockRenderer = LockRenderer(self.scene)
        self.bullseye_renderer: BullseyeRenderer = BullseyeRenderer(self.scene)
        self.annotations: MapAnnotations = MapAnnotations(self.scene)
        # self.labels_renderer: RadarLabelsRenderer = RadarLabelsRenderer(self.scene)
        self.labels_renderer: ImGuiRadarLabelsRenderer = ImGuiRadarLabelsRenderer(self.scene)

    def generate_render_arrays(self, freeze_label_data: bool = False):
        """
        Generate the instance arrays for rendering. Called on each radar update.

        Args:
            freeze_label_data: Keep label data as of this update until the next one
                (used when the radar update interval is longer than a frame).
        """
        self._load_track_arrays()

        # Update bullseye if enabled and position available
        if config.app_config.get_bool("layers", "show_bullseye"):
            bullseye_pos = self.gamestate.get_bullseye_pos()
            if bullseye_pos != (0, 0):  # Valid bullseye position
                self.bullseye_renderer.set_bullseye(bullseye_pos[0], bullseye_pos[1])

        # Snapshot track labels; they are laid out against the current view every frame
        self.labels_renderer.take_snapshot(self.gamestate, freeze_label_data)

    def _load_track_arrays(self):
        render_arrays = self.sensor_tracks.render_arrays

        if render_arrays:
            icon_arrays = render_arrays.get('icons', {})
            self.icon_renderer.load_render_arrays(icon_arrays)

            velocity_vectors = render_arrays.get('velocity_vectors')
            self.vector_renderer.load_render_arrays(velocity_vectors)

            lock_lines = render_arrays.get('lock_lines')
            self.lock_renderer.load_render_arrays(lock_lines)

    def refresh_object_style(self, game_obj: GameObject):
        """
        Apply a user edit to one object (e.g. color override) immediately, rather than
        waiting for the next radar update. Labels already re-layout every frame.
        """
        if self.sensor_tracks.refresh_object_style(game_obj):
            self._load_track_arrays()

    def set_hovered_obj(self, track: Optional[GameObject]):
        """
        Set the currently hovered track for special label rendering.
        
        Args:
            track: The track that is currently being hovered, or None if no track is hovered
        """
        self.labels_renderer.set_hovered_obj(track)

    def render(self):
        """
        Render the display data.
        """
        # Render annotations
        self.annotations.render()
        # Render bullseye if enabled
        if config.app_config.get_bool("layers", "show_bullseye"):
            self.bullseye_renderer.render()

        # Render lock lines using the new lock renderer (if enabled)
        if config.app_config.get_bool("layers", "show_lock_lines"):
            self.lock_renderer.render()

        # Render icons using the new instanced renderer
        self.icon_renderer.render()

        # Render velocity vectors using the new vector renderer
        self.vector_renderer.render()

        # Render all track labels, re-projected against the current view every frame
        self.labels_renderer.layout_labels()
        self.labels_renderer.render()

    def clear(self):
        """
        Clear the display data.
        """
        self.icon_renderer.clear()
        self.vector_renderer.clear()
        self.lock_renderer.clear()
        self.bullseye_renderer.clear()
        self.annotations.clear()
        self.labels_renderer.clear()

    def refresh_configuration(self):
        """
        Refresh configuration for all renderers.
        
        This should be called when configuration changes to apply new settings.
        """
        self.bullseye_renderer.refresh_configuration()

    def load_annotations_ini(self, ini_path):
        """
        Load annotations from INI file.
        
        Args:
            ini_path: Path to the INI file containing annotation data
        """
        self.annotations.load_ini(ini_path)
