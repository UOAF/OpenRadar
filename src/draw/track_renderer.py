import os
import numpy as np
from numpy.typing import NDArray
import moderngl as mgl

from draw.scene import Scene
from draw.polygon import PolygonRenderer, ShapesRenderBuffer, LineRenderBuffer
import draw.shapes as shapes
import glm

from game_state import GameObjectClassType
import config

from draw.polygon import FullRenderBuffer, ShapesRenderBuffer

from dataclasses import dataclass

@dataclass
class TrackRenderBuffer:
    line_width_px: float
    shape_size_px: glm.vec2
    offsets: NDArray[np.float32] # Shape: (N, 2) -> N lines, (x, y)
    colors: NDArray[np.float32] # Shape: (N, 4) -> RGBA color per line
    
class TrackRenderer:

    def __init__(self, scene: Scene):

        self.scene = scene
        self._mgl_context = scene.mgl_context

        shader_dir = str((config.bundle_dir / "resources/shaders").resolve())
        screen_polygon_vertex_shader = open(os.path.join(shader_dir, "screen_polygon_vertex.glsl")).read()
        screen_polygon_fragment_shader = open(os.path.join(shader_dir, "polygon_frag.glsl")).read()

        self.program = self._mgl_context.program(vertex_shader=screen_polygon_vertex_shader,
                                                 fragment_shader=screen_polygon_fragment_shader)

    def build_render_arrays(self, tracks):
        offsets = []
        scales = []
        colors = []
        widths_px = []

        for track in tracks[GameObjectClassType.FIXEDWING].values():
            print(track.position)
            # Collect position and scaling data
            offsets.append(track.position)
            scales.append([16, 16])
            colors.append((0, 0, 1, 1))  # Example RGBA color
            widths_px.append(4)

        if len(offsets) == 0:
            self.semicircles = None
            return
        # Convert lists to NDarrays        
        self.semicircles = TrackRenderBuffer(line_width_px=4, shape_size_px=glm.vec2(16, 16),
                                             offsets=np.array(offsets, dtype=np.float32),
                                             colors=np.array(colors, dtype=np.float32))

    def render(self):
        if self.semicircles is not None:
            self.draw_shapes(shapes.SEMICIRCLE, self.semicircles)

    def draw_shapes(self, shape: NDArray, input: TrackRenderBuffer):
        self.draw_instances_args(shape, input.offsets,  input.colors, input.shape_size_px, input.line_width_px)

    def draw_instances_args(self, unit_shape: NDArray[np.float32], offsets: NDArray[np.float32], colors: NDArray[np.float32],
                            scale: glm.vec2, widths_px: float):
        """
        Draws multiple line instances with specified attributes.

        This method renders multiple lines (or strokes) with configurable offsets, scales, colors, 
        and widths. Each line segment supports mitered end caps by using additional invisible 
        vertices to determine the endpoint angles.

        Args:
            unit_shape (NDArray[np.float32]): 
                A NumPy array of shape (M, 4) representing the vertex positions for each line segment. 
                Each vertex includes (x, y, z, w) in homogeneous coordinates, where z is typically 0.0 
                and w is 1.0 for 2D rendering.
            offsets (NDArray[np.float32]): 
                A NumPy array of shape (N, 2) specifying (x, y) offsets for each instance. These are 
                added to the vertices during rendering, enabling instanced positioning.
            scale (glm.vec2): 
                A glm.vec2 specifying the uniform scaling factors (x, y) for all instances. 
                Used to uniformly scale the vertices.
            colors (NDArray[np.float32]): 
                A NumPy array of shape (N, 4) specifying RGBA colors for each instance. Colors are 
                stored as normalized values in the range [0.0, 1.0].
            widths_px (float): 
                A float specifying the width of each line in pixels. Widths are applied uniformly 
                across all instances.

        Raises:
            AssertionError: 
                If input arrays do not conform to the required shapes:
                - `vertices` must have shape (M, 4).
                - `offsets` must have shape (N, 2).
                - `colors` must have shape (N, 4).
                - All arrays must have the same number of instances (N).

        Notes:
            - Invisible vertices are added to control endpoint angles and mitered joins.
            - Each filled line segment requires 6 vertices for rendering.
            - Total output vertices are computed as: `(M - 3) * 6`.

        Example:
            vertices = np.array([[0, 0, 0, 1], [1, 1, 0, 1], [2, 0, 0, 1]], dtype=np.float32)
            offsets = np.array([[0, 0]], dtype=np.float32)
            scale = glm.vec2(1, 1)
            colors = np.array([[1.0, 0.0, 0.0, 1.0]], dtype=np.float32)
            widths_px = 2.0

            drawer.draw_instances(vertices, offsets, scale, colors, widths_px)
        """
        assert unit_shape.shape[1] == 4, "unit_shape must be a 4f array"
        assert offsets.shape[1] == 2, "offsets must be a 2f array"
        assert colors.shape[1] == 4, "colors must be a 4f array"
        assert offsets.shape[0] == colors.shape[0], "All input arrays must have the same length"

        self.program['u_mvp'].write(self.scene.get_mvp())  # type: ignore
        self.program['u_resolution'] = self.scene.display_size
        self.program['u_scale'] = scale
        self.program['u_width'] = widths_px

        ssbo = self._mgl_context.buffer(unit_shape.astype('f4').tobytes())
        ssbo.bind_to_storage_buffer(0)

        offset_buf = self._mgl_context.buffer(offsets)
        colors_buf = self._mgl_context.buffer(colors)

        vao = self._mgl_context.vertex_array(self.program, [(offset_buf, '2f/i', 'i_offset'),
                                                            (colors_buf, '4f/i', 'i_color')])

        num_output_vertices = (len(unit_shape) - 3) * 6

        vao.render(mgl.TRIANGLES, vertices=num_output_vertices, instances=len(offsets))
