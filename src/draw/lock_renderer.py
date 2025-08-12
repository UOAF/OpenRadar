"""
Lock Renderer - GPU-optimized lock line rendering using instanced draw calls.

This renderer takes LockLineRenderData arrays and renders lock lines between
aircraft using instanced drawing, where all lock lines are rendered with a single draw call.
"""

import moderngl as mgl
import numpy as np
from typing import Optional
from pathlib import Path
import glfw

from draw.scene import Scene
import config


class LockRenderer:
    """
    Efficient renderer for lock lines using instanced draw calls.
    
    Features:
    - Uses structured instance data matching LockLineRenderData
    - Single draw call for all lock lines
    - Renders straight lines between start and end positions
    - Configurable line width
    """

    def __init__(self, scene: Scene):
        self.scene = scene
        self.ctx = scene.mgl_context

        # Shader program
        self.program: Optional[mgl.Program] = None

        # Instance data buffer - updated each frame
        self.instance_buffer: Optional[mgl.Buffer] = None
        self.instance_count: int = 0

        self._initialize_shaders()

    def _initialize_shaders(self):
        """Load and compile the lock line shaders."""
        shader_dir = Path("resources/shaders")

        # Load vertex shader
        vertex_path = shader_dir / "line_vertex.glsl"
        with open(vertex_path, 'r') as f:
            vertex_source = f.read()

        # Load fragment shader
        fragment_path = shader_dir / "lock_frag.glsl"
        with open(fragment_path, 'r') as f:
            fragment_source = f.read()

        # Create shader program
        self.program = self.ctx.program(vertex_shader=vertex_source, fragment_shader=fragment_source)

    def load_render_arrays(self, lock_data: Optional[np.ndarray]):
        """
        Load lock line data into GPU buffer.
        
        Args:
            lock_data: NumPy structured array with lock line data
        """
        # Clean up previous buffer
        if self.instance_buffer:
            self.instance_buffer.release()
            self.instance_buffer = None
            self.instance_count = 0

        if lock_data is None or len(lock_data) == 0:
            return

        # Create instance buffer
        self.instance_buffer = self.ctx.buffer(lock_data.tobytes())
        if isinstance(self.instance_buffer, mgl.InvalidObject):
            print("Failed to create buffer for lock lines")
            return

        self.instance_count = len(lock_data)

    def render(self):
        """
        Render all lock lines using instanced drawing.
        """
        if not self.program or not self.instance_buffer or self.instance_count == 0:
            return

        # Set up uniforms
        self.program['u_mvp'].write(self.scene.get_vp())  # type: ignore
        self.program['u_resolution'] = self.scene.display_size

        # Get line width from config
        lock_width = config.app_config.get_float("radar", "contact_stroke")
        self.program['u_width'] = lock_width

        self.program['u_time'] = glfw.get_time()

        # Bind instance buffer to shader storage buffer
        self.instance_buffer.bind_to_storage_buffer(0)

        # Create VAO for rendering
        vao = self.ctx.vertex_array(self.program, [])

        # Each lock line is rendered as a quad (2 triangles = 6 vertices)
        vertices_per_instance = 6

        # Render instances
        vao.render(instances=self.instance_count, vertices=vertices_per_instance)

        # Clean up VAO
        vao.release()

    def clear(self):
        """Clean up GPU resources."""
        if self.instance_buffer:
            self.instance_buffer.release()
            self.instance_buffer = None
        self.instance_count = 0
