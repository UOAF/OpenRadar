import os
from typing import Iterable

import moderngl as mgl
import glm 
import numpy as np

import config

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
    def __init__(self, display_size, mgl_context: mgl.Context, map_gl):
        self._mgl_context = mgl_context
        
        shader_dir = str((config.bundle_dir / "resources/shaders").resolve())
        vert_shader = open(os.path.join(shader_dir, "polygon_vertex.glsl")).read()
        frag_shader = open(os.path.join(shader_dir, "polygon_frag.glsl")).read()   
        
        self.program = self._mgl_context.program(vertex_shader=vert_shader, fragment_shader=frag_shader)
        
        self.map_gl = map_gl

    def draw(self, vertices: Iterable, color: tuple[float,float,float,float], width: float):
        vertices = np.array(vertices, dtype=np.float32)
        self.program['u_mvp'].write(self.map_gl.camera)
        self.program['u_resolution'] = self.map_gl.display_size
        self.program['u_color'].write(glm.vec4(color))
        self.program['u_thickness'].write(np.float32(width))
        ssbo = self._mgl_context.buffer(vertices.astype('f4').tobytes())
        ssbo.bind_to_storage_buffer(0)
        vao = self._mgl_context.vertex_array(self.program, [])
        vao.render(mgl.TRIANGLES, vertices=vertices.size*6)

        
