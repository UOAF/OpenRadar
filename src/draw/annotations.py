
import moderngl as mgl
import glm

from draw.polygon import PolygonRenderer
from util.bms_ini import FalconBMSIni

import config


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
            
    def draw(self):
        self.draw_lines()
        self.draw_circles()
        self.draw_text()
        
    def draw_lines(self):
        if len(self.lines) == 0:
            return

        out_lines = []
        colors = []
        widths_px = []

        for line in self.lines:
            
            out_line = []
            
            [out_line.append(glm.vec4(*vec, 0.0, 1.0)) for vec in line] # type: ignore
            colors.append((*config.app_config.get_color_normalized("annotations", "ini_color"), 1.0))
            widths_px.append(config.app_config.get_float("annotations", "ini_width"))
        
            first = out_line[0]
            last = out_line[-1]
            out_line.append(last)
            out_line.insert(0, first)
            out_lines.append(out_line)

        self.renderer.draw_lines(out_lines, colors, widths_px)

    
    def draw_circles(self):
        
        if len(self.circles) == 0:
            return
        
        offsets = []
        scales = []
        color = []
        widths_px = []
        
        for circle in self.circles:
            offsets.append(circle[0])
            scales.append((circle[1], circle[1])) # scale by the same in x and y to stay a circle
            color.append( (*config.app_config.get_color_normalized("annotations", "ini_color") , 1.0) )
            widths_px.append( config.app_config.get_float("annotations", "ini_width") )
        
        self.renderer.draw_circles(offsets, scales, color, widths_px)
    
    def draw_text(self):
        pass
    
    def clear(self):
        self.annotations = []
        self.lines = []
        self.circles = []
