from dataclasses import dataclass
import os

import moderngl as mgl
import numpy as np
from numpy.typing import NDArray
from typing import List, Tuple
import glm

import config
from draw.scene import Scene
from draw import shapes


@dataclass
class FullRenderBuffer:
    vertices: NDArray[np.float32]  # Shape: (M, 4) -> (x, y, z, w) per vertex
    offsets: NDArray[np.float32]  # Shape: (N, 2) -> (x, y) offset per shape
    scales: NDArray[np.float32]  # Shape: (N, 2) -> (x, y) scale per shape
    colors: NDArray[np.float32]  # Shape: (N, 4) -> RGBA color per shape
    widths_px: NDArray[np.float32]  # Shape: (N,) -> Width per shape


@dataclass
class ShapesRenderBuffer:
    offsets: NDArray[np.float32]  # Shape: (N, 2) -> (x, y) offset per shape
    scales: NDArray[np.float32]  # Shape: (N, 2) -> (x, y) scale per shape
    colors: NDArray[np.float32]  # Shape: (N, 4) -> RGBA color per shape
    widths_px: NDArray[np.float32]  # Shape: (N,) -> Width per shape


@dataclass
class LineRenderBuffer:
    lines: NDArray[np.float32]  # Shape: (N, P, 2) -> N lines, P points per line, (x, y)
    colors: NDArray[np.float32]  # Shape: (N, 4) -> RGBA color per line
    widths_px: NDArray[np.float32]  # Shape: (N,) -> Width per line


class PolygonRenderer:

    def __init__(self, scene: Scene):

        self.scene = scene
        self._mgl_context = scene.mgl_context

        shader_dir = str((config.bundle_dir / "resources/shaders").resolve())
        vert_shader = open(os.path.join(shader_dir, "map_polygon_vertex.glsl")).read()
        frag_shader = open(os.path.join(shader_dir, "polygon_frag.glsl")).read()

        self.program = self._mgl_context.program(vertex_shader=vert_shader, fragment_shader=frag_shader)

    def draw_instances(self, input: FullRenderBuffer):
        self.draw_instances_args(input.vertices, input.offsets, input.scales, input.colors, input.widths_px)

    def draw_instances_args(self, vertices: NDArray[np.float32], offsets: NDArray[np.float32],
                            scales: NDArray[np.float32], colors: NDArray[np.float32], widths_px: NDArray[np.float32]):
        """
        Draws multiple line instances with specified attributes.

        This method renders multiple lines (or strokes) with configurable offsets, scales, colors, 
        and widths. Each line segment supports mitered end caps by using additional invisible 
        vertices to determine the endpoint angles.

        Args:
            vertices (NDArray[np.float32]): 
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
        assert vertices.shape[1] == 4, "unit_shape must be a 4f array"
        assert offsets.shape[1] == 2, "offsets must be a 2f array"
        assert scales.shape[1] == 2, "scales must be a 2f array"
        assert colors.shape[1] == 4, "colors must be a 4f array"
        assert offsets.shape[0] == scales.shape[0] == colors.shape[0] == widths_px.shape[0], \
            "All input arrays must have the same length"

        self.program['u_mvp'].write(self.scene.get_mvp())  # type: ignore
        self.program['u_resolution'] = self.scene.display_size
        # self.program['u_color'] = color[0]

        ssbo = self._mgl_context.buffer(vertices.astype('f4').tobytes())
        ssbo.bind_to_storage_buffer(0)

        offset_buf = self._mgl_context.buffer(offsets)
        scales_buf = self._mgl_context.buffer(scales)
        colors_buf = self._mgl_context.buffer(colors)
        widths_buf = self._mgl_context.buffer(widths_px)

        vao = self._mgl_context.vertex_array(self.program, [(offset_buf, '2f/i', 'i_offset'),
                                                            (scales_buf, '2f/i', 'i_scale'),
                                                            (colors_buf, '4f/i', 'i_color'),
                                                            (widths_buf, '1f/i', 'i_width')])

        # for any shape, we need a pair of extra vertices on either side to determine a direction for the endpoint aka miter.
        # these end-cap segments are not drawn, but they are needed so that the angle of the endpoint miters can be controlled. e.g.,
        #
        # +-------------------+
        # |                 / |
        # | segment 1     /   |
        # | (invisible) /     |
        # |           /       |
        # |         /         |
        # +--------+          |
        #          | segment 2|
        #          |          |
        #          |          |
        #          +----------+
        #
        # will result in a diagonal end, vs.
        #          +------------+
        #          | segment 1  |
        #          | (invisible)|
        #          |            |
        #          |            |
        #          |            |
        #          |------------|
        #          | segment 2  |
        #          |            |
        #          |            |
        #          +------------+
        # will result in a straight end.
        #
        # Additionally, N vertices will define N-1 segments.
        #
        # Finally, each filled line segment (i.e., stroke) has six vertices.
        #
        # Putting this all together, that means we need to generate (N - 3)*6, where N was the number of line segment vertices.

        num_output_vertices = (len(vertices) - 3) * 6

        vao.render(mgl.TRIANGLES, vertices=num_output_vertices, instances=len(offsets))

    def draw_shapes(self, unit_shape, input: ShapesRenderBuffer):
        self.draw_shapes_args(unit_shape, input.offsets, input.scales, input.colors, input.widths_px)

    def draw_shapes_args(self, unit_shape: NDArray[np.float32], offsets: NDArray[np.float32],
                         scales: NDArray[np.float32], colors: NDArray[np.float32], widths_px: NDArray[np.float32]):
        self.draw_instances_args(unit_shape, offsets, scales, colors, widths_px)

    def draw_circles(self, input: ShapesRenderBuffer):  # TODO Depricate
        self.draw_circles_args(input.offsets, input.scales, input.colors, input.widths_px)

    def draw_circles_args(self, offsets: NDArray[np.float32], scales: NDArray[np.float32], colors: NDArray[np.float32],
                          widths_px: NDArray[np.float32]):
        self.draw_instances_args(shapes.CIRCLE, offsets, scales, colors, widths_px)

    def draw_lines(self, input: LineRenderBuffer):
        self.draw_lines_args(input.lines, input.colors, input.widths_px)

    def draw_lines_args(
            self,
            lines: NDArray[np.float32],  # Shape: (N, P, 2) -> N lines, P points per line, (x, y)
            colors: NDArray[np.float32],  # Shape: (N, 4) -> RGBA color per line
            widths_px: NDArray[np.float32],  # Shape: (N,) -> Width per line
            add_control_points: bool = True):
        """
        Draw multiple lines with specified colors, widths, and optional control points.

        :param lines: An array of shape (N, P, 2) where N is the number of lines,
                    P is the number of points per line, and 2 represents (x, y).
        :param colors: An array of shape (N, 4) for RGBA colors, one for each line.
        :param widths_px: An array of shape (N,) specifying the width of each line.
        :param add_control_points: Whether to add control points to each line.
        """
        # Validate input shapes
        if len(lines.shape) != 3 or lines.shape[2] != 2:
            raise ValueError("Input 'lines' must have shape (N, P, 2) for 2D points.")
        if len(colors.shape) != 2 or colors.shape[1] != 4:
            raise ValueError("Input 'colors' must have shape (N, 4) for RGBA colors.")
        if len(widths_px.shape) != 1:
            raise ValueError("Input 'widths_px' must have shape (N,).")
        if lines.shape[0] != colors.shape[0] or lines.shape[0] != widths_px.shape[0]:
            raise ValueError("Mismatched number of lines, colors, and widths.")

        # Prepare offsets and scales (default values)
        num_instances = lines.shape[0]
        offsets = np.zeros((num_instances, 2), dtype=np.float32)  # (N, 2)
        scales = np.ones((num_instances, 2), dtype=np.float32)  # (N, 2)

        for i in range(num_instances):
            # Convert 2D points (x, y) to 4D (x, y, z=0.0, w=1.0)
            z = np.zeros((lines[i].shape[0], 1), dtype=np.float32)  # z = 0.0
            w = np.ones((lines[i].shape[0], 1), dtype=np.float32)  # w = 1.0
            line = np.hstack((lines[i], z, w))  # Shape: (P, 4)

            # Add control points if required
            if add_control_points:
                line = shapes.add_control_points_angle(line)

            # Verify that the processed vertices are valid for draw_instances
            assert line.shape[1] == 4, "Vertices must have shape (P, 4)."

            # Draw the line with specified parameters
            self.draw_instances_args(
                vertices=line,
                offsets=offsets[i:i + 1],  # Slice to match shape (1, 2)
                scales=scales[i:i + 1],  # Slice to match shape (1, 2)
                colors=colors[i:i + 1],  # Slice to match shape (1, 4)
                widths_px=widths_px[i:i + 1]  # Slice to match shape (1,)
            )
