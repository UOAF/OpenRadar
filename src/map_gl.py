import OpenGL.GL as gl
import OpenGL.GLU as glu
import os
import bms_math
import numpy as np
import json
import glm

import config
import moderngl as mgl
from PIL import Image


class Texture:

    def __init__(self, size: tuple[int, int], img: bytes):
        self.ctx = mgl.get_context()

        self.texture = self.ctx.texture(size, 4, img)
        self.sampler = self.ctx.sampler(texture=self.texture)

    def use(self):
        self.sampler.use()


def make_image_texture(filepath: str) -> Texture:
    filepath = str(filepath)
    img = Image.open(filepath).transpose(Image.Transpose.FLIP_TOP_BOTTOM).convert('RGBA')
    return Texture(img.size, img.tobytes())


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


map_dir = config.bundle_dir / "resources/maps"


class MapGL:

    def __init__(self, display_size, mgl_context: mgl.Context):
        self._mgl_context = mgl_context
        self.display_size = display_size

        shader_dir = str((config.bundle_dir / "resources/shaders").resolve())
        vert_shader = open(os.path.join(shader_dir, "vertex.glsl")).read()
        frag_shader = open(os.path.join(shader_dir, "frag.glsl")).read()
        self.shader = self._mgl_context.program(vertex_shader=vert_shader, fragment_shader=frag_shader)

        self.map_size_km = 1024  # in KM
        self.map_size_ft = self.map_size_km * bms_math.BMS_FT_PER_KM
        self._pan_screen = glm.vec2(0.0)
        self.zoom_level = 1.0

        self.load_default_map()

        self.resize(self.display_size)

    def list_maps(self):

        with open(map_dir / "maps.json") as f:
            maps = json.load(f)
            
        return maps

    def load_map(self, filename, map_size_km):

        print(f"Loading map {filename} {map_size_km}")

        print(f"Map dir: {map_dir/ filename}")

        if os.path.isfile(filename):
            texture_path = filename
        elif os.path.isfile(map_dir / filename):
            texture_path = map_dir / filename
        else:
            print(f"Map file {filename} not found")
            self.default_grey_map()
            return

        self.texture = make_image_texture(texture_path)
        prim = np.array([[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [1.0, 1.0], [0.0, 1.0], [0.0, 0.0]])
        quad = np.zeros((12, 2), dtype=np.float32)
        quad[::2] = prim
        quad[1::2] = prim

        self.mesh = Mesh(self.shader, quad.astype('f4'), self.texture.texture)

        self.map_size_km = map_size_km
        self.map_size_ft = self.map_size_km * bms_math.BMS_FT_PER_KM

        config.app_config.set("map", "default_map", str(filename))
        config.app_config.set("map", "default_map_size_km", map_size_km)

    def clear_map(self):
        if self.texture is not None:
            self.texture = None
        self.default_grey_map()

    def load_default_map(self):
        config_default_map = config.app_config.get_str("map", "default_map")
        config_default_map_size = config.app_config.get_int("map", "default_map_size_km")
        print(f"Loading default map {config_default_map} {config_default_map_size}")
        self.load_map(config_default_map, config_default_map_size)

    def default_grey_map(self):
        gray_pixel = bytearray([0x80, 0x80, 0x80, 0xFF])
        self.texture = Texture((1, 1), gray_pixel)
        self.map_size_km = 1024
        self.map_size_ft = self.map_size_km * bms_math.BMS_FT_PER_KM
        config.app_config.set("map", "default_map", "none")
        config.app_config.set("map", "default_map_size_km", 1024)

    def resize(self, display_size):
        ### This is the function that needs to be called when the window is resized
        self.display_size = display_size
        gl.glViewport(0, 0, *display_size)
        self.camera = self.make_camera_matrix()

    def make_camera_matrix(self):
        w, h = self.display_size
        aspect = w / h

        proj = glm.ortho(0.0, aspect, 0.0, 1.0, -1.0, 1.0)
        scale = 1 / self.map_size_ft
        scale = glm.mat4(scale)
        scale[2][2] = scale[3][3] = 1.0
        scaled = proj * scale

        test_vec = glm.vec4(3358699.50, 3358699.50, 0.0, 1.0)
        return scaled

    def on_render(self):
        half_map_size_ft = self.map_size_ft / 2
        scale = self.map_size_ft
        self.shader['camera'].write(self.camera)
        _, h = self.display_size
        pan_scale = h / self.map_size_ft
        pan = self._pan_screen / pan_scale

        self.mesh.render(scale * self.zoom_level, (pan.x, pan.y, 0.0))

    def pan(self, dx_screen, dy_screen):
        delta = glm.vec2(dx_screen, -dy_screen)
        self._pan_screen += delta

    def screen_to_world(self, point_screen: glm.vec2):
        w, h = self.display_size
        ratio = h / self.map_size_ft
        point_screen.y = h - point_screen.y
        pan = self._pan_screen
        point_screen_with_pan = point_screen - pan
        result = point_screen_with_pan / ratio / self.zoom_level
        return result

    def world_to_screen(self, point_world: glm.vec2):
        w, h = self.display_size
        ratio = h / self.map_size_ft

        point_screen_with_pan = point_world * ratio * self.zoom_level

        pan = glm.vec2(self._pan_screen)
        pan.y *= -1.0
        point_screen = point_screen_with_pan + pan
        point_screen.y = h - point_screen.y
        return point_screen

    def zoom_at(self, mouse_pos, factor):
        # adjust the pan so that the world position of the mouse is preserved before and after zoom
        mouse_world_old = self.screen_to_world(glm.vec2(*mouse_pos))

        self.zoom_level += (factor / 10)
        self.zoom_level = max(0.05, self.zoom_level)

        mouse_world_new = self.screen_to_world(glm.vec2(*mouse_pos))
        delta_world = mouse_world_new - mouse_world_old
        w, h = self.display_size
        ratio = h / self.map_size_ft
        delta_screen = delta_world * ratio * self.zoom_level
        x, y = delta_screen
        self._pan_screen += glm.vec2(x, y)
