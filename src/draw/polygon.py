import os
from typing import Iterable

import moderngl as mgl
import glm
import numpy as np

import config
from draw.scene import Scene


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


    def draw(self, vertices: Iterable, color: tuple[float, float, float, float], width: float):

        offsets = np.array([(100000, 100000), (200000, 200000), (300000, 300000)], dtype=np.float32)
        scales = np.array([(364567, 364567), (121522, 121522), (48608.9, 48608.9)],
                          dtype=np.float32)
        vertices = np.array(vertices, dtype=np.float32)
        self.program['u_mvp'].write(self.scene.get_mvp())
        self.program['u_resolution'] = self.scene.display_size
        self.program['u_color'].write(glm.vec4(color))
        self.program['u_thickness'].write(np.float32(width))
        ssbo = self._mgl_context.buffer(vertices.astype('f4').tobytes())
        ssbo.bind_to_storage_buffer(0)
        offset_buff = self._mgl_context.buffer(offsets)
        scales_buff = self._mgl_context.buffer(scales)
        vao = self._mgl_context.vertex_array(self.program, [(offset_buff, '2f/i', 'i_offset'),
                                                            (scales_buff, '2f/i', 'i_scale')])
        vao.render(mgl.TRIANGLES, vertices=vertices.size * 6, instances=3)
