"""
Bullseye Renderer - GPU-optimized bullseye rendering.

This renderer displays a bullseye (reference point) with two perpendicular lines
and concentric rings at specified intervals. Based on deprecated track_renderer 
bullseye code but using modern instanced rendering.
"""

import moderngl as mgl
import numpy as np
from typing import Optional, Tuple
from pathlib import Path
import math

from draw.scene import Scene
from draw.shapes import Shapes
import config

from util.bms_math import NM_TO_METERS


class BullseyeRenderer:
    """
    Efficient renderer for bullseye display using dual shader programs.
    
    Features:
    - Two crossing lines (north-south, east-west) using line_vertex shader
    - Concentric rings using icon_vertex shader with Shapes.Circle
    - Based on deprecated track_renderer bullseye code
    - Single set_bullseye call to update position
    - Supports magnetic variation when magnetic north mode is enabled
    """

    def __init__(self, scene: Scene):
        self.scene = scene
        self.ctx = scene.mgl_context

        # Shader programs
        self.line_program: Optional[mgl.Program] = None
        self.ring_program: Optional[mgl.Program] = None

        # Bullseye configuration from config
        self.NUM_RINGS = config.app_config.get_int("radar", "bullseye_num_rings")
        self.RING_DISTANCE_NM = config.app_config.get_float("radar", "bullseye_ring_distance")

        # Bullseye data
        self.bullseye_position: Optional[Tuple[float, float]] = None

        # Buffers for line data
        self.line_instance_buffer: Optional[mgl.Buffer] = None

        # Buffers for ring data
        self.ring_vertex_buffer: Optional[mgl.Buffer] = None
        self.ring_instance_buffer: Optional[mgl.Buffer] = None

        self._initialize_shaders()
        self._initialize_ring_geometry()

    def _initialize_shaders(self):
        """Load and compile the bullseye shaders."""
        shader_dir = Path("resources/shaders")

        # Load line shaders
        line_vertex_path = shader_dir / "line_vertex.glsl"
        with open(line_vertex_path, 'r') as f:
            line_vertex_source = f.read()

        fragment_path = shader_dir / "polygon_frag.glsl"
        with open(fragment_path, 'r') as f:
            fragment_source = f.read()

        # Create line shader program
        self.line_program = self.ctx.program(vertex_shader=line_vertex_source, fragment_shader=fragment_source)

        # Load ring shaders (use map_polygon_vertex for world-space scaling)
        ring_vertex_path = shader_dir / "map_polygon_vertex.glsl"
        with open(ring_vertex_path, 'r') as f:
            ring_vertex_source = f.read()

        # Create ring shader program
        self.ring_program = self.ctx.program(vertex_shader=ring_vertex_source, fragment_shader=fragment_source)

    def _initialize_ring_geometry(self):
        """Initialize ring geometry using Shapes.Circle."""
        # Use the unit circle from Shapes.Circle
        circle_points = Shapes.CIRCLE.value.points

        # Create vertex buffer
        self.ring_vertex_buffer = self.ctx.buffer(circle_points.astype(np.float32))

    def set_bullseye(self, x: float, y: float):
        """
        Set the bullseye position.
        
        Args:
            x, y: World coordinates of the bullseye center
        """
        self.bullseye_position = (x, y)

        self._update_line_data()
        self._update_ring_data()

    def set_bullseye_num_rings(self, num_rings: int):
        """
        Set the number of concentric rings for the bullseye.

        Args:
            num_rings: The number of rings to display
        """
        if num_rings != self.NUM_RINGS:
            self.NUM_RINGS = num_rings
            self._update_ring_data()
            self._update_line_data()

    def set_bullseye_ring_distance(self, distance_nm: float):
        """
        Set the distance between concentric rings for the bullseye.

        Args:
            distance_nm: The distance between rings in nautical miles
        """
        if distance_nm != self.RING_DISTANCE_NM:
            self.RING_DISTANCE_NM = distance_nm
            self._update_ring_data()
            self._update_line_data()

    def refresh_configuration(self):
        """
        Refresh bullseye settings from configuration and update geometry.
        
        This should be called when configuration changes to apply new settings.
        """
        new_num_rings = config.app_config.get_int("radar", "bullseye_num_rings")
        new_ring_distance = config.app_config.get_float("radar", "bullseye_ring_distance")
        
        # Update settings and refresh geometry if they changed
        if new_num_rings != self.NUM_RINGS or new_ring_distance != self.RING_DISTANCE_NM:
            self.NUM_RINGS = new_num_rings
            self.RING_DISTANCE_NM = new_ring_distance
            self._initialize_ring_geometry()
            if self.bullseye_position is not None:
                self._update_ring_data()
                self._update_line_data()

    def _update_line_data(self):
        """Update the line instance data for the bullseye cross."""
        if self.bullseye_position is None:
            return

        x, y = self.bullseye_position

        # Calculate line length in meters (covers all rings plus some extra)
        half_line_length_m = NM_TO_METERS * self.RING_DISTANCE_NM * (self.NUM_RINGS + 1)
        
        # Get magnetic variation if magnetic north is enabled
        use_magnetic_north = config.app_config.get_bool("navigation", "use_magnetic_north")
        mag_var_degrees = 0.0
        
        if use_magnetic_north:
            # Get magnetic variation from config (set by map loading)
            mag_var_degrees = config.app_config.get_float("navigation", "magnetic_variation_deg")
        
        # Convert magnetic variation to radians
        # Note: Magnetic variation is applied as rotation from true north to magnetic north
        # Negative mag var (west) means magnetic north is west of true north
        # Positive mag var (east) means magnetic north is east of true north
        mag_var_radians = math.radians(mag_var_degrees)  # Use positive value for visual rotation
        
        # Calculate rotated line endpoints
        # North-South line (rotated by magnetic variation)
        ns_dx = half_line_length_m * math.sin(mag_var_radians)
        ns_dy = half_line_length_m * math.cos(mag_var_radians)
    
        # East-West line (perpendicular to N-S line)
        ew_dx = half_line_length_m * math.cos(mag_var_radians)  
        ew_dy = half_line_length_m * math.sin(mag_var_radians)
        
        line_data = np.array([
            # Magnetic North-South line
            [x - ns_dx, y - ns_dy, x + ns_dx, y + ns_dy, 1.0, 1.0, 1.0, 1.0],
            # Magnetic East-West line  
            [x - ew_dx, y + ew_dy, x + ew_dx, y - ew_dy, 1.0, 1.0, 1.0, 1.0]
        ], dtype=np.float32)

        # Update buffer
        if self.line_instance_buffer:
            self.line_instance_buffer.release()
        self.line_instance_buffer = self.ctx.buffer(line_data.tobytes())

    def _update_ring_data(self):
        """Update the ring instance data for concentric circles."""
        if self.bullseye_position is None:
            return

        x, y = self.bullseye_position

        # Ring instance data: position_x, position_y, scale, _buffer, color_rgba
        ring_instances = []

        for i in range(self.NUM_RINGS):
            # Calculate ring radius in world units (meters)
            radius_m = (i + 1) * self.RING_DISTANCE_NM * NM_TO_METERS

            # Alternate colors for visibility
            if i % 2 == 0:
                color = [0.5, 0.5, 0.5, 1.0]  # Darker gray for even rings
            else:
                color = [0.7, 0.7, 0.7, 1.0]  # Lighter gray for odd rings

            ring_instances.append([x, y, radius_m, 0.0, color[0], color[1], color[2], color[3]])

        ring_data = np.array(ring_instances, dtype=np.float32)

        # Update buffer
        if self.ring_instance_buffer:
            self.ring_instance_buffer.release()
        self.ring_instance_buffer = self.ctx.buffer(ring_data.tobytes())

    def render(self):
        """Render the bullseye display."""
        if self.bullseye_position is None:
            return

        self._render_lines()
        self._render_rings()

    def _render_lines(self):
        """Render the bullseye cross lines."""
        if not self.line_program or not self.line_instance_buffer:
            return

        # Set up uniforms
        self.line_program['u_mvp'].write(self.scene.get_vp())  # type: ignore
        self.line_program['u_resolution'] = self.scene.display_size

        # Get line width from config
        line_width = config.app_config.get_float("radar", "contact_stroke")
        self.line_program['u_width'] = line_width

        # Bind instance buffer
        self.line_instance_buffer.bind_to_storage_buffer(0)

        # Create VAO and render
        vao = self.ctx.vertex_array(self.line_program, [])

        # Each line is rendered as 2 triangles = 6 vertices
        vertices_per_instance = 6
        instance_count = 2  # horizontal and vertical lines

        vao.render(instances=instance_count, vertices=vertices_per_instance)
        vao.release()

    def _render_rings(self):
        """Render the concentric rings."""
        if not self.ring_program or not self.ring_instance_buffer or not self.ring_vertex_buffer:
            return

        # Set up uniforms
        self.ring_program['u_mvp'].write(self.scene.get_vp())  # type: ignore
        self.ring_program['u_resolution'] = self.scene.display_size

        # Get line width from config
        line_width = config.app_config.get_float("radar", "contact_stroke")
        self.ring_program['u_width'] = line_width

        # Bind buffers
        self.ring_vertex_buffer.bind_to_storage_buffer(0)  # Shape geometry
        self.ring_instance_buffer.bind_to_storage_buffer(1)  # Instance data

        # Create VAO and render
        vao = self.ctx.vertex_array(self.ring_program, [])

        # Calculate vertices per instance based on circle geometry
        circle_points = Shapes.CIRCLE.value.points
        num_line_segments = len(circle_points) - 1  # Circle is a closed loop
        vertices_per_instance = num_line_segments * 6  # Each segment becomes 2 triangles

        vao.render(instances=self.NUM_RINGS, vertices=vertices_per_instance)
        vao.release()

    def clear(self):
        """Clean up GPU resources."""
        if self.line_instance_buffer:
            self.line_instance_buffer.release()
            self.line_instance_buffer = None

        if self.ring_instance_buffer:
            self.ring_instance_buffer.release()
            self.ring_instance_buffer = None

    def is_visible(self) -> bool:
        """Check if bullseye should be rendered based on configuration."""
        return config.app_config.get_bool("layers", "show_bullseye")
