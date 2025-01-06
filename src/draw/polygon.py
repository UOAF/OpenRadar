import os

import moderngl as mgl
import numpy as np

import config
from draw.scene import Scene
from draw import shapes


class PolygonRenderer:

    def __init__(self, mgl_context: mgl.Context, scene: Scene):
        self._mgl_context = mgl_context
        self.scene = scene

        shader_dir = str((config.bundle_dir / "resources/shaders").resolve())
        vert_shader = open(os.path.join(shader_dir, "polygon_vertex.glsl")).read()
        frag_shader = open(os.path.join(shader_dir, "polygon_frag.glsl")).read()

        self.program = self._mgl_context.program(vertex_shader=vert_shader, fragment_shader=frag_shader)

    def draw_instances(self, unit_shape, offsets, scales, colors, widths_px):

        if not (len(offsets) == len(scales) == len(colors) == len(widths_px)):
            raise ValueError("All input arrays must have the same length")

        self.program['u_mvp'].write(self.scene.get_mvp())
        self.program['u_resolution'] = self.scene.display_size
        # self.program['u_color'] = color[0]

        verticies = np.array(unit_shape, dtype=np.float32)
        ssbo = self._mgl_context.buffer(verticies.astype('f4').tobytes())
        ssbo.bind_to_storage_buffer(0)

        offset_buf = self._mgl_context.buffer(np.array(offsets, dtype=np.float32))
        scales_buf = self._mgl_context.buffer(np.array(scales, dtype=np.float32))
        colors_buf = self._mgl_context.buffer(np.array(colors, dtype=np.float32))
        widths_buf = self._mgl_context.buffer(np.array(widths_px, dtype=np.float32))

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

        num_output_vertices = (len(verticies) - 3) * 6

        vao.render(mgl.TRIANGLES, vertices=num_output_vertices, instances=len(offsets))

    def draw_circles(self, offsets, scales, colors, widths_px):
        self.draw_instances(shapes.circle, offsets, scales, colors, widths_px)

    def draw_lines(self, lines: list[list[tuple[float, float]]], colors: list[tuple[float, float, float]],
                   widths_px: list[float]):

        for i in range(len(lines)):
            line = lines[i]
            color = [colors[i]]
            width = [widths_px[i]]
            offset = [(0,0)]
            scale = [(1,1)]
            self.draw_instances(line, offset, scale, color, width)
