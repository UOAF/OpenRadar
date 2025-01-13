import os
import numpy as np
from numpy.typing import NDArray
import moderngl as mgl

from draw.scene import Scene
from draw.polygon import PolygonRenderer, ShapesRenderBuffer, LineRenderBuffer
import draw.shapes as shapes

from game_state import GameObjectClassType
import config

from draw.polygon import FullRenderBuffer, ShapesRenderBuffer


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
            scales.append([20, 20])
            colors.append((1, 0, 1, 1))  # Example RGBA color
            widths_px.append(5)

        if len(offsets) == 0:
            self.squares = None
            return
        # Convert lists to NDarrays
        self.squares = ShapesRenderBuffer(offsets=np.array(offsets, dtype=np.float32),
                                          scales=np.array(scales, dtype=np.float32),
                                          colors=np.array(colors, dtype=np.float32),
                                          widths_px=np.array(widths_px, dtype=np.float32))

    def render(self):
        if self.squares is not None:
            self.draw_shapes(shapes.SEMICIRCLE, self.squares)
            
    def draw_shapes(self, shape: NDArray, input: ShapesRenderBuffer):
        self.draw_instances_args(shape, input.offsets, input.scales, input.colors, input.widths_px)

    def draw_instances(self, input: FullRenderBuffer):
        self.draw_instances_args(input.vertices, input.offsets, input.scales, input.colors, input.widths_px)

    def draw_instances_args(self, unit_shape: NDArray[np.float32], offsets: NDArray[np.float32],
                            scales: NDArray[np.float32], colors: NDArray[np.float32], widths_px: NDArray[np.float32]):
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
            scales (NDArray[np.float32]): 
                A NumPy array of shape (N, 2) specifying scaling factors (x, y) for each instance. 
                Used to uniformly or non-uniformly scale the vertices.
            colors (NDArray[np.float32]): 
                A NumPy array of shape (N, 4) specifying RGBA colors for each instance. Colors are 
                stored as normalized values in the range [0.0, 1.0].
            widths_px (NDArray[np.float32]): 
                A NumPy array of shape (N,) specifying the width of each line in pixels. Widths are 
                applied uniformly across each instance.

        Raises:
            AssertionError: 
                If input arrays do not conform to the required shapes:
                - `vertices` must have shape (M, 4).
                - `offsets` and `scales` must have shape (N, 2).
                - `colors` must have shape (N, 4).
                - `widths_px` must have shape (N,).
                - All arrays must have the same number of instances (N).

        Notes:
            - Invisible vertices are added to control endpoint angles and mitered joins.
            - Each filled line segment requires 6 vertices for rendering.
            - Total output vertices are computed as: `(M - 3) * 6`.

        Example:
            vertices = np.array([[0, 0, 0, 1], [1, 1, 0, 1], [2, 0, 0, 1]], dtype=np.float32)
            offsets = np.array([[0, 0]], dtype=np.float32)
            scales = np.array([[1, 1]], dtype=np.float32)
            colors = np.array([[1.0, 0.0, 0.0, 1.0]], dtype=np.float32)
            widths_px = np.array([2.0], dtype=np.float32)

            drawer.draw_instances(vertices, offsets, scales, colors, widths_px)
        """
        assert unit_shape.shape[1] == 4, "unit_shape must be a 4f array"
        assert offsets.shape[1] == 2, "offsets must be a 2f array"
        assert scales.shape[1] == 2, "scales must be a 2f array"
        assert colors.shape[1] == 4, "colors must be a 4f array"
        assert offsets.shape[0] == scales.shape[0] == colors.shape[0] == widths_px.shape[0], \
            "All input arrays must have the same length"

        self.program['u_mvp'].write(self.scene.get_mvp())  # type: ignore
        self.program['u_resolution'] = self.scene.display_size

        ssbo = self._mgl_context.buffer(unit_shape.astype('f4').tobytes())
        ssbo.bind_to_storage_buffer(0)

        offset_buf = self._mgl_context.buffer(offsets)
        scales_buf = self._mgl_context.buffer(scales)
        colors_buf = self._mgl_context.buffer(colors)
        widths_buf = self._mgl_context.buffer(widths_px)

        vao = self._mgl_context.vertex_array(self.program, [(offset_buf, '2f/i', 'i_offset'),
                                                            (scales_buf, '2f/i', 'i_scale'),
                                                            (colors_buf, '4f/i', 'i_color'),
                                                            (widths_buf, '1f/i', 'i_width')])

        num_output_vertices = (len(unit_shape) - 3) * 6

        vao.render(mgl.TRIANGLES, vertices=num_output_vertices, instances=len(offsets))
