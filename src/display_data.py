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
from game_object_types import GameObjectType
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

    def generate_render_arrays(self):
        """
        Generate the instance arrays for rendering. called 
        """
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

        # Clear and regenerate track labels
        self.labels_renderer.clear()
        self._generate_ac_labels()

    def set_hovered_obj(self, track: Optional[GameObject]):
        """
        Set the currently hovered track for special label rendering.
        
        Args:
            track: The track that is currently being hovered, or None if no track is hovered
        """
        self.labels_renderer.set_hovered_obj(track)

    def _generate_ac_labels(self):
        """Generate text labels for all visible tracks."""
        self.labels_renderer.draw_all_ac_labels(self.gamestate)

    def _should_render_track_type(self, track_type: GameObjectType) -> bool:
        """Check if a track type should be rendered based on layer configuration."""
        layer_mapping = {
            GameObjectType.FIXEDWING: "show_fixed_wing",
            GameObjectType.ROTARYWING: "show_rotary_wing",
            GameObjectType.GROUND: "show_ground",
            GameObjectType.SEA: "show_ships",
            GameObjectType.MISSILE: "show_missiles",
            GameObjectType.BULLSEYE: "show_bullseye",
        }

        layer_key = layer_mapping.get(track_type)
        if layer_key:
            return config.app_config.get_bool("layers", layer_key)

        return True  # Default to showing unknown types

    def render(self):
        """
        Render the display data.
        """
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

        # Render all track labels
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

    def load_annotations_ini(self, ini_path):
        """
        Load annotations from INI file.
        
        Args:
            ini_path: Path to the INI file containing annotation data
        """
        self.annotations.load_ini(ini_path)
