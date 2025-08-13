"""
Polygon Renderer - GPU-optimized polygon rendering using instanced draw calls.

This renderer takes PolygonRenderData arrays and renders polygons from Shapes
using instanced drawing with the map_polygon_vertex shader, where all polygons
of the same shape are rendered with a single draw call.
"""

import moderngl as mgl
import numpy as np
from typing import Optional, Dict

from draw.scene import Scene
from draw.shapes import Shapes
import config


class PolygonRenderer:
    """
    Efficient renderer for polygons using instanced draw calls.
    
    Features:
    - Uses structured instance data matching PolygonRenderData
    - Single draw call per shape type for all polygon instances
    - Supports all shapes defined in Shapes enum
    - Uses map_polygon_vertex.glsl shader for proper polygon rendering
    - Configurable per-instance scaling, positioning, width, and color
    """

    def __init__(self, scene: Scene):
        self.scene = scene
        self.ctx = scene.mgl_context

        # Shader program
        self.program: Optional[mgl.Program] = None

        # Instance data buffers per shape - updated each frame
        self.instance_buffers: Dict[Shapes, mgl.Buffer] = {}
        self.instance_counts: Dict[Shapes, int] = {}
        
        # Vertex buffers for each shape (static geometry)
        self.vertex_buffers: Dict[Shapes, mgl.Buffer] = {}

        self._initialize_shaders()
        self._initialize_shape_buffers()

    def _initialize_shaders(self):
        """Load and compile the polygon shaders."""
        shader_dir = str((config.bundle_dir / "resources/shaders").resolve())

        # Load vertex shader (map_polygon_vertex.glsl)
        vertex_path = shader_dir + "/map_polygon_vertex.glsl"
        with open(vertex_path, 'r') as f:
            vertex_source = f.read()

        # Load fragment shader (polygon_frag.glsl)
        fragment_path = shader_dir + "/polygon_frag.glsl"
        with open(fragment_path, 'r') as f:
            fragment_source = f.read()

        # Create shader program
        self.program = self.ctx.program(vertex_shader=vertex_source, fragment_shader=fragment_source)

    def _initialize_shape_buffers(self):
        """Create vertex buffers for all shape types."""
        for shape in Shapes:
            # Get the shape's vertex data
            vertices = shape.value.points  # This is the NDArray[np.float32] from the Shape
            
            # Create vertex buffer
            vertex_buffer = self.ctx.buffer(vertices.astype(np.float32).tobytes())
            self.vertex_buffers[shape] = vertex_buffer

    def load_render_arrays(self, polygon_arrays: Dict[Shapes, np.ndarray]):
        """
        Load polygon data into GPU buffers.
        
        Args:
            polygon_arrays: Dictionary mapping Shapes to NumPy structured arrays with polygon data
        """
        # Clean up previous buffers
        for shape_buffer in self.instance_buffers.values():
            shape_buffer.release()
        self.instance_buffers.clear()
        self.instance_counts.clear()

        # Create new instance buffers for each shape with data
        for shape, polygon_data in polygon_arrays.items():
            if polygon_data is None or len(polygon_data) == 0:
                continue

            # Create instance buffer
            instance_buffer = self.ctx.buffer(polygon_data.tobytes())
            if isinstance(instance_buffer, mgl.InvalidObject):
                print(f"Failed to create buffer for shape {shape}")
                continue

            self.instance_buffers[shape] = instance_buffer
            self.instance_counts[shape] = len(polygon_data)

    def render(self):
        """
        Render all polygons using instanced drawing.
        Renders each shape type separately to use the correct vertex data.
        """
        if not self.program:
            return

        # Set up uniforms (same for all shapes)
        self.program['u_mvp'].write(self.scene.get_vp())  # type: ignore
        self.program['u_resolution'] = self.scene.display_size

        # Get default width from config (can be overridden per instance)
        default_width = config.app_config.get_float("radar", "contact_stroke")
        self.program['u_width'] = default_width

        # Render each shape type
        for shape in Shapes:
            self._render_shape(shape)

    def _render_shape(self, shape: Shapes):
        """Render all instances of a specific shape."""
        if shape not in self.instance_buffers or shape not in self.vertex_buffers:
            return

        instance_buffer = self.instance_buffers[shape]
        vertex_buffer = self.vertex_buffers[shape]
        instance_count = self.instance_counts[shape]

        if instance_count == 0:
            return

        # Bind vertex buffer to binding point 0 (TVertex buffer in shader)
        vertex_buffer.bind_to_storage_buffer(0)

        # Bind instance buffer to binding point 1 (TPolygonInstance buffer in shader)  
        instance_buffer.bind_to_storage_buffer(1)

        # Create VAO for rendering (no vertex attributes needed, using storage buffers)
        vao = self.ctx.vertex_array(self.program, [])

        # Calculate number of vertices to render
        # Each line segment needs 6 vertices (2 triangles)
        # Number of line segments = number of vertices - 3 (due to control points)
        shape_vertices = shape.value.points
        num_line_segments = len(shape_vertices) - 3
        vertices_per_instance = num_line_segments * 6

        # Render instances
        vao.render(instances=instance_count, vertices=vertices_per_instance)

        # Clean up VAO
        vao.release()

    def clear(self):
        """Clean up GPU resources."""
        # Clean up instance buffers
        for shape_buffer in self.instance_buffers.values():
            shape_buffer.release()
        self.instance_buffers.clear()
        self.instance_counts.clear()

        # Clean up vertex buffers
        for vertex_buffer in self.vertex_buffers.values():
            vertex_buffer.release()
        self.vertex_buffers.clear()

    def set_default_width(self, width: float):
        """Set the default line width for polygons."""
        if self.program:
            self.program['u_width'] = width
