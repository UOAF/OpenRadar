import numpy as np

from draw.scene import Scene
from draw.polygon import PolygonRenderer, ShapesRenderBuffer, LineRenderBuffer
import draw.shapes as shapes

from game_state import GameObjectClassType


class TrackRenderer:
    def __init__(self, scene: Scene):
        self.scene = scene
        self.poly_renderer = PolygonRenderer(scene)
        
        self.circles: ShapesRenderBuffer | None = None
        self.lines: LineRenderBuffer | None = None
        self.text: None = None
        self.vel_lines: None = None
        
    def build_render_arrays(self, tracks):
        offsets = []
        scales = []
        colors = []
        widths_px = []

        for track in tracks[GameObjectClassType.FIXEDWING].values():
            # Collect position and scaling data
            offsets.append(track.position)
            scales.append([self.scene.get_scale() * 10, self.scene.get_scale() * 10])
            colors.append((0, 1, 0, 1))  # Example RGBA color
            widths_px.append(5)

        if len(offsets) == 0:
            self.circles = None
            return
        # Convert lists to NDarrays
        self.circles = ShapesRenderBuffer(
            offsets=np.array(offsets, dtype=np.float32),
            scales=np.array(scales, dtype=np.float32),
            colors=np.array(colors, dtype=np.float32),
            widths_px=np.array(widths_px, dtype=np.float32)
        )
        
    def test_draw_ac(self):
        
        color = (0, 0, 1, 1)
        # draw semicircle
        buf = ShapesRenderBuffer(
            np.array([(400000, 400000)], dtype=np.float32).reshape(1, 2), 
            np.array([[self.scene.get_scale() * 10] * 2], dtype=np.float32).reshape(1, 2),
            np.array([color], dtype=np.float32).reshape(1, 4),
            np.array([5], dtype=np.float32).reshape(1, 1),
        )
        
        self.poly_renderer.draw_shapes(shapes.SEMICIRCLE, buf)
    
    def render(self):
        if self.circles is not None:
            self.poly_renderer.draw_shapes(shapes.CIRCLE, self.circles)
        self.test_draw_ac()