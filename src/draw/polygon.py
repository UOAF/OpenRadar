import os
from typing import Iterable

import moderngl as mgl
import glm
import numpy as np

import config
from draw.scene import Scene
from draw import shapes

class Mesh:

    def __init__(self, shader: mgl.Program, vertices, texture: mgl.Texture):
        self.ctx = mgl.get_context()
        self.vbo = self.ctx.buffer(vertices.astype('f4').tobytes())
        self.vao = self.ctx.vertex_array(shader, [(self.vbo, '2f 2f', 'in_vertex', 'in_uv')])
        self.texture = texture

    def render(self, scale, position):
        self.texture.use()
        self.vao.program['position'] = position
        self.vao.program['scale'] = scale
        self.vao.render()


class PolygonRenderer:

    def __init__(self, mgl_context: mgl.Context, scene: Scene):
        self._mgl_context = mgl_context
        self.scene = scene

        shader_dir = str((config.bundle_dir / "resources/shaders").resolve())
        vert_shader = open(os.path.join(shader_dir, "polygon_vertex.glsl")).read()
        frag_shader = open(os.path.join(shader_dir, "polygon_frag.glsl")).read()

        self.program = self._mgl_context.program(vertex_shader=vert_shader, fragment_shader=frag_shader)

    # def test_draw(self, vertices: Iterable, color: tuple[float, float, float, float], width: float):

    #     offsets = np.array([(100000, 100000), (200000, 200000), (300000, 300000)], dtype=np.float32)
    #     scales = np.array([(364567, 364567), (121522, 121522), (48608.9, 48608.9)],
    #                       dtype=np.float32)
    #     thickness = np.array([5, 10, 20], dtype=np.float32)
    #     vertices = np.array(vertices, dtype=np.float32)
    #     colors = np.array([(0.0, 0.0, 1.0, 1.0), color, color], dtype=np.float32)
    #     widths_px = np.array([width, width, width], dtype=np.float32)
        
    #     self.program['u_mvp'].write(self.scene.get_mvp())
    #     self.program['u_resolution'] = self.scene.display_size

    #     ssbo = self._mgl_context.buffer(vertices.astype('f4').tobytes())
    #     ssbo.bind_to_storage_buffer(0)
        
    #     offset_buf = self._mgl_context.buffer(np.array(offsets, dtype=np.float32))
    #     scales_buf = self._mgl_context.buffer(np.array(scales, dtype=np.float32))
    #     colors_buf = self._mgl_context.buffer(np.array(color, dtype=np.float32))
    #     widths_buf = self._mgl_context.buffer(np.array(widths_px, dtype=np.float32))
        
    #     vao = self._mgl_context.vertex_array(self.program, [
    #                                                         (offset_buf, '2f/i', 'i_offset'),
    #                                                         (scales_buf, '2f/i', 'i_scale'),
    #                                                         (colors_buf, '4f/i', 'i_color'),
    #                                                         (widths_buf, '1f/i', 'i_width')])
    #     vao.render(mgl.TRIANGLES, vertices=vertices.size * 6, instances=3)
        
    def draw_instances(self, unit_shape, offsets, scales, color, widths_px):
        
        if not (len(offsets) == len(scales) == len(color) == len(widths_px)):
            raise ValueError("All input arrays must have the same length")   
             
        self.program['u_mvp'].write(self.scene.get_mvp())
        self.program['u_resolution'] = self.scene.display_size
        # self.program['u_color'] = color[0]
  
        verticies = np.array(unit_shape, dtype=np.float32)
        ssbo = self._mgl_context.buffer(verticies.astype('f4').tobytes())
        ssbo.bind_to_storage_buffer(0)
        
        offset_buf = self._mgl_context.buffer(np.array(offsets, dtype=np.float32))
        scales_buf = self._mgl_context.buffer(np.array(scales, dtype=np.float32))
        colors_buf = self._mgl_context.buffer(np.array(color, dtype=np.float32))
        widths_buf = self._mgl_context.buffer(np.array(widths_px, dtype=np.float32))
        
        
        vao = self._mgl_context.vertex_array(self.program, [
                                                            (offset_buf, '2f/i', 'i_offset'),
                                                            (scales_buf, '2f/i', 'i_scale'),
                                                            (colors_buf, '4f/i', 'i_color'),
                                                            (widths_buf, '1f/i', 'i_width')])
        
        vao.render(mgl.TRIANGLES, vertices=len(verticies) * len(offsets) * 6, instances=len(offsets))

    def draw_circles(self, offsets, scales, colors, widths_px):
        self.draw_instances(shapes.circle, offsets, scales, colors, widths_px)
        
    def draw_lines(self, lines, color, widths_px):
        
        pass
    