"""
Vector Renderer - GPU-optimized velocity vector rendering using instanced draw calls.

This renderer takes VelocityVectorRenderData arrays and renders velocity vectors
using instanced drawing, where all velocity vectors are rendered with a single draw call.
"""

import moderngl as mgl
import numpy as np
from typing import Optional
from pathlib import Path

from draw.scene import Scene
import config


class VectorRenderer:
    """
    Efficient renderer for velocity vectors using instanced draw calls.
    
    Features:
    - Uses structured instance data matching VelocityVectorRenderData
    - Single draw call for all velocity vectors
    - Fixed screen-space vector length proportional to aircraft velocity
    - Zoom-independent display with velocity-based scaling
    """

    def __init__(self, scene: Scene):
        self.scene = scene
        self.ctx = scene.mgl_context

        # Shader program
        self.program: Optional[mgl.Program] = None

        # Instance data buffer - updated each frame
        self.instance_buffer: Optional[mgl.Buffer] = None
        self.instance_count: int = 0

        # Vector display parameters
        self.base_vector_length_pixels: float = 80.0  # Base length in pixels
        self.max_velocity_for_scaling: float = 800.0  # Max velocity (knots) for scaling

        self._initialize_shaders()

    def _initialize_shaders(self):
        """Load and compile the vector shaders."""
        shader_dir = Path("resources/shaders")

        # Load vertex shader
        vertex_path = shader_dir / "vector_vertex.glsl"
        with open(vertex_path, 'r') as f:
            vertex_source = f.read()

        # Load fragment shader (reuse polygon_frag.glsl)
        fragment_path = shader_dir / "polygon_frag.glsl"
        with open(fragment_path, 'r') as f:
            fragment_source = f.read()

        # Create shader program
        self.program = self.ctx.program(vertex_shader=vertex_source, fragment_shader=fragment_source)

    def load_render_arrays(self, vector_data: Optional[np.ndarray]):
        """
        Load velocity vector data into GPU buffer.
        
        Args:
            vector_data: NumPy structured array with velocity vector data
        """
        # Clean up previous buffer
        if self.instance_buffer:
            self.instance_buffer.release()
            self.instance_buffer = None
            self.instance_count = 0

        if vector_data is None or len(vector_data) == 0:
            return

        # Create instance buffer
        self.instance_buffer = self.ctx.buffer(vector_data.tobytes())
        if isinstance(self.instance_buffer, mgl.InvalidObject):
            print("Failed to create buffer for velocity vectors")
            return

        self.instance_count = len(vector_data)

    def render(self):
        """
        Render all velocity vectors using instanced drawing.
        """
        if not self.program or not self.instance_buffer or self.instance_count == 0:
            return

        # Set up uniforms
        self.program['u_mvp'].write(self.scene.get_vp())  # type: ignore
        self.program['u_resolution'] = self.scene.display_size

        # Get line width from config
        vector_width = config.app_config.get_float("radar", "contact_stroke")
        self.program['u_width'] = vector_width

        # Set vector display parameters
        self.program['u_base_vector_length'] = self.base_vector_length_pixels
        self.program['u_max_velocity'] = self.max_velocity_for_scaling  # Bind instance buffer to shader storage buffer
        self.instance_buffer.bind_to_storage_buffer(0)

        # Create VAO for rendering
        vao = self.ctx.vertex_array(self.program, [])

        # Each velocity vector is rendered as a quad (2 triangles = 6 vertices)
        vertices_per_instance = 6

        # Render instances
        vao.render(instances=self.instance_count, vertices=vertices_per_instance)

        # Clean up VAO
        vao.release()

    def set_vector_length_pixels(self, pixels: float):
        """Set the base length of velocity vectors in pixels."""
        self.base_vector_length_pixels = pixels

    def set_max_velocity_for_scaling(self, max_velocity: float):
        """Set the maximum velocity used for length scaling."""
        self.max_velocity_for_scaling = max_velocity

    def clear(self):
        """Clean up GPU resources."""
        if self.instance_buffer:
            self.instance_buffer.release()
            self.instance_buffer = None
        self.instance_count = 0
