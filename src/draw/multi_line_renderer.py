"""
Line renderer for variable-length lines using LineRenderData.

This renderer handles multi-point lines with proper mitering and end caps,
using separate SSBOs for points and metadata to support variable-length lines.
"""

import moderngl as mgl
import numpy as np
from typing import Optional

from draw.scene import Scene
from render_data_arrays import LineRenderData
import config


class MultiLineRenderer:
    """
    Renderer for multi-point lines using separate points and metadata buffers.
    Each line can have any number of points, with proper mitering between segments.
    """
    
    def __init__(self, scene: Scene):
        self.scene = scene
        self.ctx = scene.mgl_context
        
        # Shader program
        self.program: Optional[mgl.Program] = None
        
        # Buffers for line data
        self.points_buffer: Optional[mgl.Buffer] = None
        self.metadata_buffer: Optional[mgl.Buffer] = None
        
        # Current buffer sizes for resize detection
        self._points_buffer_size = 0
        self._metadata_buffer_size = 0
        
        # Track if render data has changed
        self._needs_buffer_update = True
        
        # Initialize shader
        self._load_shader()
    
    def _load_shader(self):
        """Load the multi-line vertex shader and fragment shader."""
        try:
            shader_dir = str((config.bundle_dir / "resources/shaders").resolve())
            
            # Load vertex shader
            vertex_path = shader_dir + "/multi_line_vertex.glsl"
            with open(vertex_path, 'r') as f:
                vertex_source = f.read()
            
            # Load fragment shader (reuse polygon fragment shader)
            fragment_path = shader_dir + "/polygon_frag.glsl"
            with open(fragment_path, 'r') as f:
                fragment_source = f.read()
            
            self.program = self.ctx.program(
                vertex_shader=vertex_source,
                fragment_shader=fragment_source
            )
        except Exception as e:
            print(f"Failed to load multi-line shader: {e}")
            self.program = None
    
    def load_line_data(self, line_data: LineRenderData):
        """
        Load line data into GPU buffers for rendering.
        
        Args:
            line_data: LineRenderData containing points and metadata
        """
        if self.program is None:
            return
        
        # Get render data from LineRenderData
        metadata_array, points_array = line_data.get_render_data()
        
        if metadata_array is None or points_array is None or len(metadata_array) == 0:
            # No data to render - release existing buffers
            if self.points_buffer is not None:
                self.points_buffer.release()
                self.points_buffer = None
            if self.metadata_buffer is not None:
                self.metadata_buffer.release()
                self.metadata_buffer = None
            self._points_buffer_size = 0
            self._metadata_buffer_size = 0
            return
        
        # Update points buffer
        points_data = points_array.tobytes()
        if (self.points_buffer is None or 
            len(points_data) != self._points_buffer_size):
            # Create new buffer or resize existing
            if self.points_buffer is not None:
                self.points_buffer.release()
            
            self.points_buffer = self.ctx.buffer(points_data)
            self._points_buffer_size = len(points_data)
        else:
            # Update existing buffer
            self.points_buffer.write(points_data)
        
        # Update metadata buffer
        metadata_data = metadata_array.tobytes()
        if (self.metadata_buffer is None or 
            len(metadata_data) != self._metadata_buffer_size):
            # Create new buffer or resize existing
            if self.metadata_buffer is not None:
                self.metadata_buffer.release()
            
            self.metadata_buffer = self.ctx.buffer(metadata_data)
            self._metadata_buffer_size = len(metadata_data)
        else:
            # Update existing buffer
            self.metadata_buffer.write(metadata_data)
        
        # Bind buffers to shader storage buffer objects
        if self.points_buffer is not None:
            self.points_buffer.bind_to_storage_buffer(0)
        if self.metadata_buffer is not None:
            self.metadata_buffer.bind_to_storage_buffer(1)
        
        self._needs_buffer_update = False
    
    def render(self, line_data: LineRenderData):
        """
        Render the multi-point lines.
        
        Args:
            line_data: LineRenderData to render
        """
        if self.program is None:
            return
        
        # Update buffers if needed
        self.load_line_data(line_data)
        
        # Get render data for drawing calculations
        metadata_array, points_array = line_data.get_render_data()
        
        if metadata_array is None or len(metadata_array) == 0:
            return
        
        # Set uniforms - using the same pattern as polygon_renderer
        self.program['u_mvp'].write(self.scene.get_vp()) # type: ignore
        self.program['u_resolution'] = self.scene.display_size
        self.program['u_width'] = 2.0  # Default line width
        
        # Create VAO for rendering (no vertex attributes needed, using storage buffers)
        vao = self.ctx.vertex_array(self.program, [])
        
        # Calculate vertices needed for rendering
        total_segments = 0
        for metadata in metadata_array:
            line_length = metadata['end_index'] - metadata['start_index']
            if line_length >= 2:
                segments = line_length - 1
                total_segments += segments
        
        # Each segment needs 6 vertices (2 triangles)
        if total_segments > 0:
            num_lines = len(metadata_array)
            vertices_per_instance = total_segments * 6
            
            # Render all lines as instances
            vao.render(instances=num_lines, vertices=vertices_per_instance)
        
        # Clean up VAO
        vao.release()
    
    def cleanup(self):
        """Release GPU resources."""
        if self.points_buffer is not None:
            self.points_buffer.release()
            self.points_buffer = None
        
        if self.metadata_buffer is not None:
            self.metadata_buffer.release()
            self.metadata_buffer = None
        
        if self.program is not None:
            self.program.release()
            self.program = None
        
        self._points_buffer_size = 0
        self._metadata_buffer_size = 0
    
    def set_default_width(self, width: float):
        """Set the default line width for multi-line rendering."""
        if self.program:
            self.program['u_width'] = width
