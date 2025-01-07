import moderngl as mgl
import glm

from draw.polygon import PolygonRenderer
from util.bms_ini import FalconBMSIni
from draw.text import TextRendererMsdf, make_text_renderer
from draw.scene import Scene

import config


class MapAnnotations:

    def __init__(self, scene: Scene, mgl_context: mgl.Context):
        self.renderer = PolygonRenderer(mgl_context, scene)
        self.mgl_context = mgl_context
        self.annotations = []
        self.lines = []
        self.circles = []
        self.text_renderer = make_text_renderer(self.mgl_context, "atlas", scene)
        self.scene = scene

    def load_ini(self, path):
        ini = FalconBMSIni(path)
        for line in ini.lines:
            self.lines.append(line)

        for threat in ini.threats:
            self.circles.append(threat)

    def draw(self):
        self.text_renderer.init_frame()
        self.draw_lines()
        self.draw_circles()
        self.text_renderer.render()

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
        
            # After and Prior are points extended to the line begining and end line segmenets to render the tangets
            # See the comment in polygon.py for more details
            prior = out_line[0] - (out_line[1] - out_line[0])
            after = out_line[-1] + (out_line[-1] - out_line[-2])
            out_line.append(after)
            out_line.insert(0, prior)
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
            pos, r, name = circle
            # ((x, y), r, name)
            offsets.append(pos)
            scales.append((r, r))  # scale by the same in x and y to stay a circle
            color.append((*config.app_config.get_color_normalized("annotations", "ini_color"), 1.0))
            widths_px.append(config.app_config.get_float("annotations", "ini_width"))
            self.text_renderer.draw_text(name, *pos)

        self.renderer.draw_circles(offsets, scales, color, widths_px)

    def draw_text(self):
        pass

    def clear(self):
        self.annotations = []
        self.lines = []
        self.circles = []
