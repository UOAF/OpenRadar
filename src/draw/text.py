from typing import Optional
from PIL import Image
import os
import json
import moderngl as mgl
import numpy as np

from draw.scene import Scene


def load_atlas(context: mgl.Context, atlas_name: str, atlas_path: str):
    atlas_image_path = os.path.join(atlas_path, f"{atlas_name}.png")
    atlas_json_path = os.path.join(atlas_path, f"{atlas_name}.json")
    atlas_image = Image.open(atlas_image_path).convert("RGBA")
    atlas_texture = context.texture(atlas_image.size, 4, atlas_image.tobytes())
    atlas_texture.use()

    print(f"Font atlas loaded: {atlas_image_path} ({atlas_image.size[0]}x{atlas_image.size[1]})")

    with open(atlas_json_path, 'r') as f:
        atlas_metadata = json.load(f)

    return atlas_texture, atlas_metadata


def make_text_renderer(context: mgl.Context, atlas_name: str, scene: Scene, atlas_path: Optional[str] = None):
    """Create a text renderer from a given MSDF (multichannel signed distance field) atlas.
    
    Parameters:
    
        atlas_name: filename of the atlas
        atlas_path: file path in which the atlas files live. Defaults to 'resources/fonts'.

    """
    if atlas_path is None:
        atlas_path = os.path.join(os.getcwd(), "resources", "fonts")
    tex, data = load_atlas(context, atlas_name, atlas_path)
    return TextRendererMsdf(context, tex, data, scene)


class TextRendererMsdf:

    def __init__(self, context: mgl.Context, texture: mgl.Texture, metadata: dict, scene: Scene):
        self._atlas = texture
        self._metadata = metadata
        self._ctx = context
        vertex_shader = open(os.path.join("resources", "shaders", "text_vertex.glsl")).read()
        fragment_shader = open(os.path.join("resources", "shaders", "text_frag.glsl")).read()
        self._program = context.program(vertex_shader=vertex_shader, fragment_shader=fragment_shader)
        self._scene = scene

    def init_frame(self):
        """"""
        self._atlas.use()
        self.vertex_batches = []
        self.index_batches = []
        self.vertex_count = 0

    def draw_text(self, text: str, x_world: int, y_world: int, scale=60):
        """"""
        glyphs = self._metadata['glyphs']
        atlas_width = self._metadata['atlas']['width']
        atlas_height = self._metadata['atlas']['height']

        vertices = np.zeros(len(text) * 24, dtype='f4')
        indices = np.zeros(len(text) * 6, dtype='i4')
        indices_for_quad = np.array([0, 1, 2, 2, 3, 0], dtype='i4')
        x = y = 0

        cursor_x = 0
        vert_idx = 0
        char_count = 0
        for char in text:
            if char == ' ':
                cursor_x += 0.5 * scale
                continue
            # Skip characters without glyph data
            index = ord(char) - 32
            if index < 0 or index >= len(glyphs):
                # print(f"Skipping unknown character: {char}")
                continue

            glyph = glyphs[index]
            if 'planeBounds' not in glyph or 'atlasBounds' not in glyph:
                print(f"Skipping incomplete glyph: {index}")
                continue  # Skip glyphs without valid bounds

            # Glyph metrics
            plane = glyph['planeBounds']
            atlas = glyph['atlasBounds']
            advance = glyph['advance']

            # Scale glyph size
            quad_x = plane['left'] * scale
            quad_y = plane['bottom'] * scale
            quad_w = plane['right'] * scale
            quad_h = plane['top'] * scale
            advance *= scale

            glyph_bottom = atlas_height - atlas['bottom']
            glyph_top = atlas_height - atlas['top']

            # Calculate texture coordinates
            tex_x = atlas['left'] / atlas_width
            tex_y = (glyph_top) / atlas_height
            tex_w = (atlas['right'] - atlas['left']) / atlas_width
            tex_h = (glyph_top - glyph_bottom) / atlas_height

            # Debug: Print glyph metrics
            # print(f"Rendering '{char}': tex=({tex_x}, {tex_y}, {tex_w}, {tex_h})")

            # Set up vertex data
            quad = np.array([
                [cursor_x + quad_x, y + quad_y, x_world, y_world, tex_x, tex_y - tex_h],
                [cursor_x + quad_w, y + quad_y, x_world, y_world, tex_x + tex_w, tex_y - tex_h],
                [cursor_x + quad_w, y + quad_h, x_world, y_world, tex_x + tex_w, tex_y],
                [cursor_x + quad_x, y + quad_h, x_world, y_world, tex_x, tex_y],
            ],
                            dtype='f4')

            # index buffer index
            ib_idx = char_count * 6
            vert_idx = char_count * 24

            vertices[vert_idx:vert_idx + 24] = quad.flatten()
            indices[ib_idx:ib_idx + 6] = indices_for_quad + (char_count * 4) + self.vertex_count * 4
            cursor_x += advance
            char_count += 1
        self.vertex_batches.append(vertices)
        self.index_batches.append(indices)
        self.vertex_count += char_count

    def render(self):
        """Call this once per frame, after rendering all the text you need.
        """
        if not self.vertex_batches or not self.index_batches:
            return
        vertices = np.concat(self.vertex_batches)
        indices = np.concat(self.index_batches)
        vbo = self._ctx.buffer(vertices.tobytes())
        ibo = self._ctx.buffer(indices.tobytes())

        # Render glyph
        self._program['camera'].write(self._scene.get_mvp()) # type: ignore
        scale = self._scene.map_size_m / self._scene.display_size[1] / self._scene.zoom_level * .6
        self._program['font_to_world'] = scale
        self._ctx.blend_func = mgl.SRC_ALPHA, mgl.ONE_MINUS_SRC_ALPHA
        self._ctx.enable(mgl.BLEND) # TODO is this the right place to call this?

        vao = self._ctx.simple_vertex_array(self._program,
                                            vbo,
                                            'in_pos_text',
                                            'in_pos_world',
                                            'in_texcoord',
                                            index_buffer=ibo)
        vao.render(mgl.TRIANGLES)
