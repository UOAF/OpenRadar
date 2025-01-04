from glm import scale
import moderngl as mgl

from draw import shapes
from draw.polygon import PolygonRenderer
from util.bms_ini import FalconBMSIni




class MapAnnotations:
    def __init__(self, polyrender: PolygonRenderer, mgl_context: mgl.Context):
        self.renderer = polyrender
        self.mgl_context = mgl_context
        self.annotations = []
        self.lines = []
        self.circles = []
        
    def load_ini(self, path):
        ini = FalconBMSIni(path)
        for line in ini.lines:
            self.lines.append(line)
            
        for threat in ini.threats:
            self.circles.append(threat)
            
        
    def draw_lines(self):
        # self.scene.draw_lines(self.lines)
        pass
    
    def draw_circles(self):
        
        offsets = []
        scales = []
        color = []
        widths_px = []
        
        for circle in self.circles:
            offsets.append(circle[0])
            scales.append(circle[1])
            color.append((1.0, 0.0, 0.0, 1.0))
            widths_px.append(20)
        
        self.renderer.draw_circles(offsets, scales, color, widths_px)
        pass
    
    def draw_text(self):
        pass
    
    def clear(self):
        self.annotations = []
        self.lines = []
        self.circles = []
