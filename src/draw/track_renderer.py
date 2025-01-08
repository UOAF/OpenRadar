import numpy as np

from draw.scene import Scene
from draw.polygon import PolygonRenderer, ShapesRenderBuffer, LineRenderBuffer
import draw.shapes as shapes


class TrackRenderer:
    def __init__(self, scene: Scene):
        self.scene = scene
        self.poly_renderer = PolygonRenderer(scene)
        
        self.circles = []
        lines = []
        text = []
        vel_lines = []
        
    def build_render_arrays(self):
        pass
        
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
        self.test_draw_ac()