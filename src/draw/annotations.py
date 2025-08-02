import moderngl as mgl
import glm
import numpy as np
from numpy.typing import NDArray

from draw.polygon import PolygonRenderer
from util.bms_ini import FalconBMSIni
from draw.text import TextRendererMsdf, make_text_renderer
from draw.scene import Scene

import config


class MapAnnotations:

    def __init__(self, scene: Scene):
        self.renderer = PolygonRenderer(scene)
        self.mgl_context = scene.mgl_context
        self.annotations = []
        self.lines = []
        self.circles = []
        self.text_renderer = make_text_renderer(self.mgl_context,
                                                "atlas",
                                                scene,
                                                scale_source=("annotations", "ini_font_scale"))
        self.scene = scene

    def load_ini(self, path):
        ini = FalconBMSIni(path)
        for line in ini.lines:
            self.lines.append(line)

        for threat in ini.threats:
            self.circles.append(threat)

    def render(self):
        self.text_renderer.init_buffers()
        self.draw_lines()
        self.draw_circles()
        self.text_renderer.render()

    def draw_lines(self):
        """
        Renders stored lines with associated colors and widths.
        """
        # Return early if no lines exist
        if len(self.lines) == 0:
            return

        # Prepare output arrays
        num_lines = len(self.lines)

        # Generate colors (N, 4) RGBA
        colors: NDArray[np.float32] = np.array(
            [(*config.app_config.get_color_normalized("annotations", "ini_color"), 1.0) for _ in range(num_lines)],
            dtype=np.float32)  # Shape: (N, 4)

        # Generate widths (N,)
        widths_px: NDArray[np.float32] = np.array(
            [config.app_config.get_float("annotations", "ini_width") for _ in range(num_lines)],
            dtype=np.float32)  # Shape: (N,)

        # Process each line individually
        for i, line in enumerate(self.lines):
            # Convert line to NDArray with (P, 2)
            line_array = np.array(line, dtype=np.float32)  # Shape: (P, 2)

            # Render each line separately
            self.renderer.draw_lines_args(
                lines=line_array[None, :, :],  # Add batch dimension: Shape (1, P, 2)
                colors=colors[i:i + 1],  # Slice (1, 4)
                widths_px=widths_px[i:i + 1]  # Slice (1,)
            )

    def draw_circles(self):
        """
        Renders stored circles with specified offsets, scales, colors, and widths.

        This function processes stored circles, converts inputs into NumPy arrays, and passes them 
        to the `draw_circles` method for rendering.

        Raises:
            ValueError: If any input arrays have inconsistent lengths or invalid shapes.
        """
        # Return early if no circles exist
        if len(self.circles) == 0:
            return

        offsets = np.array([circle[0] for circle in self.circles], dtype=np.float32)  # Shape: (N, 2)
        scales = np.array([(circle[1], circle[1]) for circle in self.circles], dtype=np.float32)  # Shape: (N, 2)
        colors = np.array([(*config.app_config.get_color_normalized("annotations", "ini_color"), 1.0)
                           for _ in self.circles],
                          dtype=np.float32)  # Shape: (N, 4)
        widths_px = np.array([config.app_config.get_float("annotations", "ini_width") for _ in self.circles],
                             dtype=np.float32)  # Shape: (N,)

        # Render text labels at circle positions
        for circle in self.circles:
            pos, _, name = circle
            self.text_renderer.draw_text(name,
                                         *pos,
                                         centered=True,
                                         scale=config.app_config.get_int("annotations", "ini_font_scale"))

        self.renderer.draw_circles_args(
            offsets, scales, colors,
            widths_px)  # TODO: Modify this line to use the new draw_circles method and store arrays on edit

    def draw_text(self):
        pass

    def clear(self):
        self.annotations = []
        self.lines = []
        self.circles = []
