import moderngl as mgl
import glm
import numpy as np
from numpy.typing import NDArray

from draw.polygon_renderer import PolygonRenderer
from draw.multi_line_renderer import MultiLineRenderer
from draw.shapes import Shapes
from render_data_arrays import PolygonRenderData, LineRenderData
from util.bms_ini import FalconBMSIni
from draw.text import TextRendererMsdf, make_text_renderer
from draw.scene import Scene

import config


class MapAnnotations:

    def __init__(self, scene: Scene):
        self.polygon_renderer = PolygonRenderer(scene)
        self.line_renderer = MultiLineRenderer(scene)
        self.mgl_context = scene.mgl_context
        self.scene = scene
        
        # Annotation data storage
        self.lines = []
        self.circles = []
        
        # Render data arrays for efficient GPU rendering
        self.circle_polygons = PolygonRenderData(1000)  # For circles
        self.line_data = LineRenderData(1000)  # For advanced multi-point lines
        
        # Track if data has changed to avoid unnecessary GPU buffer updates
        self._lines_dirty = False
        self._circles_dirty = False
        
        # Text renderer for labels
        self.text_renderer = make_text_renderer(self.mgl_context,
                                                "atlas",
                                                scene,
                                                scale_source=("annotations", "ini_font_scale"))

    def load_ini(self, path):
        """Load annotations from INI file and populate render arrays."""
        ini = FalconBMSIni(path)
        
        # Clear existing data
        self.lines.clear()
        self.circles.clear()
        self.line_data.clear()
        self.circle_polygons.clear()
        
        # Load lines
        for line in ini.lines:
            self.lines.append(line)
        
        # Load circles/threats
        for threat in ini.threats:
            self.circles.append(threat)
        
        # Rebuild render arrays
        self._rebuild_line_render_arrays()
        self._rebuild_circle_render_arrays()
        
        # Mark as clean since we just rebuilt everything
        self._lines_dirty = False
        self._circles_dirty = False

    def render(self):
        """Render all annotations using the new polygon and line rendering systems."""
        # Update render arrays if data has changed
        if self._lines_dirty:
            self._rebuild_line_render_arrays()
            self._lines_dirty = False
        
        if self._circles_dirty:
            self._rebuild_circle_render_arrays()
            self._circles_dirty = False
        
        # Render lines using the new MultiLineRenderer
        self.line_renderer.render(self.line_data)
        
        # Prepare polygon arrays for rendering circles
        polygon_arrays = {}
        
        # Add circle data
        circle_data = self.circle_polygons.get_active_data()
        if circle_data is not None and len(circle_data) > 0:
            polygon_arrays[Shapes.CIRCLE] = circle_data
        
        # Render polygons
        if polygon_arrays:
            self.polygon_renderer.load_render_arrays(polygon_arrays)
            self.polygon_renderer.render()
        
        # Render text labels
        self.text_renderer.init_buffers()
        self._render_text_labels()
        self.text_renderer.render()

    def _rebuild_line_render_arrays(self):
        """Rebuild the line render arrays from stored line data using the new LineRenderData system."""
        self.line_data.clear()
        
        # Get configuration
        color = (*config.app_config.get_color_normalized("annotations", "ini_color"), 1.0)
        width = config.app_config.get_float("annotations", "ini_width")
        
        # Add each line to LineRenderData
        for line_idx, line in enumerate(self.lines):
            if len(line) >= 2:
                # Convert to list of tuples as expected by LineRenderData
                points = [(float(pt[0]), float(pt[1])) for pt in line]
                
                # Add line to LineRenderData 
                line_id = f"line_{line_idx}"
                self.line_data.add_line(
                    line_id,
                    points=points,
                    width=width,
                    color=color
                )

    def _rebuild_circle_render_arrays(self):
        """Rebuild the circle polygon render arrays from stored circle data."""
        self.circle_polygons.clear()
        
        # Get configuration
        color = (*config.app_config.get_color_normalized("annotations", "ini_color"), 1.0)
        width = config.app_config.get_float("annotations", "ini_width")
        
        # Add each circle as a polygon instance
        for circle_idx, circle in enumerate(self.circles):
            pos, radius, name = circle
            
            self.circle_polygons.add_element(
                f"circle_{circle_idx}",
                x=float(pos[0]),
                y=float(pos[1]),
                scale=float(radius),
                width=width,
                color=color
            )

    def _render_text_labels(self):
        """Render text labels for circles."""
        for circle in self.circles:
            pos, _, name = circle
            self.text_renderer.draw_text(name,
                                         *pos,
                                         centered=True,
                                         scale=config.app_config.get_int("annotations", "ini_font_scale"))

    def add_line(self, line_points):
        """Add a new line annotation and mark render arrays as dirty."""
        self.lines.append(line_points)
        self._lines_dirty = True

    def add_circle(self, position, radius, name=""):
        """Add a new circle annotation and mark render arrays as dirty."""
        self.circles.append((position, radius, name))
        self._circles_dirty = True

    def clear(self):
        """Clear all annotations and render arrays."""
        self.lines.clear()
        self.circles.clear()
        self.line_data.clear()
        self.circle_polygons.clear()
        self._lines_dirty = False
        self._circles_dirty = False

    def mark_dirty(self):
        """Mark all render arrays as dirty to force rebuild on next render."""
        self._lines_dirty = True
        self._circles_dirty = True
