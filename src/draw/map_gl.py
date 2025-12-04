import os
import json

import glm
import moderngl as mgl
import numpy as np
from PIL import Image

import config
import util.bms_math as bms_math
from draw.scene import Scene

from logging_config import get_logger

logger = get_logger(__name__)


class Texture:

    def __init__(self, size: tuple[int, int], img: bytes):
        self.ctx = mgl.get_context()
        self.ctx.blend_func = mgl.SRC_ALPHA, mgl.ONE_MINUS_SRC_ALPHA
        self.ctx.enable(mgl.BLEND)

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

    def __init__(self, display_size, scene: Scene, mgl_context: mgl.Context):
        self._mgl_context = mgl_context
        self.display_size = display_size
        self.scene = scene
        
        # Track current theatre and magnetic variation
        self.current_theatre = None
        self.current_magnetic_variation = 0.0

        shader_dir = str((config.bundle_dir / "resources/shaders").resolve())
        vert_shader = open(os.path.join(shader_dir, "map_vertex.glsl")).read()
        frag_shader = open(os.path.join(shader_dir, "map_frag.glsl")).read()
        self.shader = self._mgl_context.program(vertex_shader=vert_shader, fragment_shader=frag_shader)

        self.map_size_m = bms_math.THEATRE_DEFAULT_SIZE_METERS

        self.load_default_map()

    def list_maps(self):

        with open(map_dir / "maps.json") as f:
            maps = json.load(f)

        return maps

    def get_current_magnetic_variation(self):
        """Get the current magnetic variation in degrees."""
        return self.current_magnetic_variation
        
    def get_current_theatre(self):
        """Get the current theatre name."""
        return self.current_theatre

    def load_map(self, filename, map_size_km, update_magnetic_variation=True):
        """Load a map by filename and size, optionally updating magnetic variation."""
        if os.path.isfile(filename):
            texture_path = filename
        elif os.path.isfile(map_dir / filename):
            texture_path = map_dir / filename
        else:
            logger.error(f"Map file {filename} not found. Using default grey map.")
            self.default_grey_map()
            return

        # If update_magnetic_variation is True, try to determine theatre from filename
        if update_magnetic_variation:
            self._update_magnetic_variation_from_filename(filename)

        self.texture = make_image_texture(texture_path)
        self.make_mesh()

        self.map_size_m = map_size_km * 1000

        config.app_config.set("map", "default_map", str(filename))
        config.app_config.set("map", "default_map_size_km", map_size_km)
        self.scene.set_size(self.map_size_m)
        
    def _update_magnetic_variation_from_filename(self, filename):
        """Try to determine theatre from filename and update magnetic variation."""
        maps = self.list_maps()
        filename = os.path.basename(filename)
        
        # Search all theatres for this filename
        for theatre, theatre_data in maps.items():
            for map_entry in theatre_data["maps"]:
                if os.path.basename(map_entry["path"]) == filename:
                    self.current_theatre = theatre
                    self.current_magnetic_variation = theatre_data.get("magnetic_variation_deg",
                        config.app_config.get_float("navigation", "magnetic_variation_deg"))
                    config.app_config.set("navigation", "magnetic_variation_deg", self.current_magnetic_variation)
                    return
                    
        # If not found, use default
        self.current_theatre = None
        self.current_magnetic_variation = config.app_config.get_float("navigation", "magnetic_variation_deg")

    def clear_map(self):
        if self.texture is not None:
            self.texture = None
        self.default_grey_map()

    def load_default_map(self):
        config_default_map = config.app_config.get_str("map", "default_map")
        config_default_map_size = config.app_config.get_int("map", "default_map_size_km")
        self.load_map(config_default_map, config_default_map_size)

    def default_grey_map(self):
        gray_pixel = bytearray([0x80, 0x80, 0x80, 0xFF])
        self.texture = Texture((1, 1), gray_pixel)

        self.map_size_m = bms_math.THEATRE_DEFAULT_SIZE_METERS
        config.app_config.set("map", "default_map", "none")
        config.app_config.set("map", "default_map_size_km", bms_math.THEATRE_DEFAULT_SIZE_KM)
        self.scene.set_size(self.map_size_m)
        
        # Reset theatre and use default magnetic variation
        self.current_theatre = None
        self.current_magnetic_variation = config.app_config.get_float("navigation", "magnetic_variation_deg")

        self.make_mesh()

    def make_mesh(self):
        if self.texture is None:
            return
        prim = np.array([[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [1.0, 1.0], [0.0, 1.0], [0.0, 0.0]])
        quad = np.zeros((12, 2), dtype=np.float32)
        quad[::2] = prim
        quad[1::2] = prim
        self.mesh = Mesh(self.shader, quad.astype('f4'), self.texture.texture)

    def render(self):

        scale = self.map_size_m
        self.shader['camera'].write(self.scene.get_vp())  # type: ignore
        self.shader['alpha'] = config.app_config.get_int("map", "map_alpha") / 255.0

        # self.mesh.render(scale * self.zoom_level, (pan.x, pan.y, 0.0))
        self.mesh.render(scale, (0.0, 0.0, 0.0))
