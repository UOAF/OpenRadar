"""
Icon Instanced Renderer - GPU-optimized icon rendering using instanced draw calls.

This renderer takes IconRenderData arrays and renders them using instanced drawing,
where each icon type (shape) is rendered with a single draw call for all instances
of that shape.
"""

import moderngl as mgl
import numpy as np
from typing import Dict, Optional
from pathlib import Path

from draw.shapes import Shapes
from draw.scene import Scene

import config


class IconInstancedRenderer:
    """
    Efficient renderer for icons using instanced draw calls.
    
    Features:
    - Loads all shape geometries into GPU buffers at startup
    - Uses structured instance data matching IconRenderData
    - Single draw call per icon type (shape)
    - Renders icon shapes with center point markers
    - Minimal CPU-GPU data transfers
    """

    def __init__(self, scene: Scene):
        self.scene = scene
        self.ctx = scene.mgl_context

        # Shader program
        self.program: Optional[mgl.Program] = None

        # Shape geometry buffers - loaded once at startup
        self.shape_buffers: Dict[Shapes, mgl.Buffer] = {}
        self.shape_vaos: Dict[Shapes, mgl.VertexArray] = {}

        # Instance data buffers - updated each frame
        self.instance_buffers: Dict[Shapes, mgl.Buffer] = {}

        self._initialize_shaders()
        self._initialize_shape_buffers()

    def _initialize_shaders(self):
        """Load and compile the icon instanced shaders."""
        shader_dir = Path("resources/shaders")

        # Load vertex shader
        vertex_path = shader_dir / "icon_vertex.glsl"
        with open(vertex_path, 'r') as f:
            vertex_source = f.read()

        # Load fragment shader (reuse polygon_frag.glsl)
        fragment_path = shader_dir / "polygon_frag.glsl"
        with open(fragment_path, 'r') as f:
            fragment_source = f.read()

        # Create shader program
        self.program = self.ctx.program(vertex_shader=vertex_source, fragment_shader=fragment_source)

    def _initialize_shape_buffers(self):
        """Load all shape geometries into GPU buffers."""
        for shape in Shapes:
            # Get shape points and add control points for proper line rendering
            points = shape.value.points

            # Create vertex buffer
            vertex_buffer = self.ctx.buffer(points.astype(np.float32))
            self.shape_buffers[shape] = vertex_buffer

    def load_render_arrays(self, icon_arrays: Dict[Shapes, np.ndarray]):
        # First, release ALL existing buffers
        for shape in list(self.instance_buffers.keys()):
            self.instance_buffers[shape].release()
            del self.instance_buffers[shape]

        # Then create new buffers only for shapes that have data
        for shape, icon_data in icon_arrays.items():
            ssbo = self.ctx.buffer(icon_data.tobytes())
            if isinstance(ssbo, mgl.InvalidObject):
                print(f"Failed to create buffer for shape {shape}")
                continue
            self.instance_buffers[shape] = ssbo

    def render(self):
        """
        Render all icons using instanced drawing.
        
        Args:
            icon_arrays: Dictionary mapping shape types to IconRenderData arrays
        """
        if not self.program or not self.instance_buffers:
            return

        # Set up common uniforms
        self.program['u_mvp'].write(self.scene.get_vp())  # type: ignore
        self.program['u_resolution'] = self.scene.display_size
        track_width = config.app_config.get_float("radar", "contact_stroke")

        self.program['u_width'] = track_width
        self.program['u_point_size'] = config.app_config.get_float("radar", "center_point_size")

        for shape in self.instance_buffers.keys():
            self._render_shape_instances(shape)

    def _render_shape_instances(self, shape: Shapes):
        """Render all instances of a specific shape."""

        # Update instance buffer with new data
        instance_count = int(self.instance_buffers[shape].size / (8 * 4))

        # Bind buffers to shader storage buffer objects (SSBOs)
        # Binding 0: vertex buffer (shape geometry)
        self.shape_buffers[shape].bind_to_storage_buffer(0)

        # Binding 1: instance buffer (per-instance data)
        self.instance_buffers[shape].bind_to_storage_buffer(1)

        # Create/get VAO
        vao = self.ctx.vertex_array(self.program, [])

        # Calculate number of vertices per instance
        # Each line segment becomes 2 triangles = 6 vertices
        # Plus 1 center point quad = 6 vertices
        shape_points = shape.value.points
        num_line_segments = len(shape_points) - 1  # Assuming points form a line strip
        vertices_per_instance = num_line_segments * 6 + 6  # +6 for center point quad

        # Render instances
        vao.render(instances=instance_count, vertices=vertices_per_instance)

    def clear(self):
        """Clean up GPU resources."""
        for buffer in self.instance_buffers.values():
            buffer.release()

        self.instance_buffers.clear()
