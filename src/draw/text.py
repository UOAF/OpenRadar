from typing import Optional
from PIL import Image
import os
import json
import moderngl as mgl
import numpy as np

from draw.scene import Scene

import config

from util.track_labels import TrackLabelLocation


def orient_text_rect(location: TrackLabelLocation, object_size: tuple[float, float] = (0, 0)) -> tuple[float, float]:
    """Calculate the offset in model space for a text string based on the rendered bounding box of the string."""
    scales = {
        TrackLabelLocation.TOP_LEFT: (-1, 0),
        TrackLabelLocation.TOP_CENTER: (-0.5, 0),
        TrackLabelLocation.TOP_RIGHT: (0, 0),
        TrackLabelLocation.LEFT: (-1, 0.5),
        TrackLabelLocation.CENTER: (-0.5, 0.5),
        TrackLabelLocation.RIGHT: (0, 0.5),
        TrackLabelLocation.BOTTOM_LEFT: (-1, -1),
        TrackLabelLocation.BOTTOM_CENTER: (-0.5, -1),
        TrackLabelLocation.BOTTOM_RIGHT: (0, -1),
    }
    scale_x, scale_y = scales[location]
    return (
        object_size[0] * scale_x,
        object_size[1] * scale_y * -1.0
    )

# def orient_text_rect(location: TrackLabelLocation, obect_size: tuple[int, int] = (0, 0)) -> RectInvY:

#     if location == TrackLabelLocation.TOP_LEFT:
#         offset = (-obect_size[0] // 2, obect_size[1] // 2)
#         rect.bottom_right = offset
#     elif location == TrackLabelLocation.TOP_CENTER:
#         offset = (0, obect_size[1] // 2)
#         rect.bottom_center = offset
#     elif location == TrackLabelLocation.TOP_RIGHT:
#         offset = (obect_size[0] // 2, obect_size[1] // 2)
#         rect.bottom_left = offset
#     elif location == TrackLabelLocation.LEFT:
#         offset = (-obect_size[0] // 2, 0)
#         rect.right_center = offset
#     elif location == TrackLabelLocation.RIGHT:
#         offset = (obect_size[0] // 2, 0)
#         rect.left_center = offset
#     elif location == TrackLabelLocation.BOTTOM_LEFT:
#         offset = (-obect_size[0] // 2, -obect_size[1] // 2)
#         rect.top_right = offset
#     elif location == TrackLabelLocation.BOTTOM_CENTER:
#         offset = (0, -obect_size[1] // 2)
#         rect.top_center = offset
#     elif location == TrackLabelLocation.BOTTOM_RIGHT:
#         offset = (obect_size[0] // 2, -obect_size[1] // 2)
#         rect.top_left = offset

#     return rect

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


def make_text_renderer(context: mgl.Context,
                       atlas_name: str,
                       scene: Scene,
                       atlas_path: Optional[str] = None,
                       scale_source: Optional[tuple[str, str]] = None):
    """Create a text renderer from a given MSDF (multichannel signed distance field) atlas.
    
    Parameters:
    
        atlas_name: filename of the atlas
        atlas_path: file path in which the atlas files live. Defaults to 'resources/fonts'.

    """
    if atlas_path is None:
        atlas_path = os.path.join(os.getcwd(), "resources", "fonts")
    tex, data = load_atlas(context, atlas_name, atlas_path)
    return TextRendererMsdf(context, tex, data, scene, scale_source=scale_source)


class TextRendererMsdf:

    def __init__(self, context: mgl.Context, texture: mgl.Texture, metadata: dict, scene: Scene,
                 scale_source: Optional[tuple[str, str]] = None):
        self._atlas = texture
        self._metadata = metadata
        self._ctx = context
        vertex_shader = open(os.path.join("resources", "shaders", "text_vertex.glsl")).read()
        fragment_shader = open(os.path.join("resources", "shaders", "text_frag.glsl")).read()
        self._program = context.program(vertex_shader=vertex_shader, fragment_shader=fragment_shader)
        self._scene = scene
        self.init_buffers()
        self._scale_source = scale_source

    def init_buffers(self):
        """"""
        self._atlas.use()
        self.vertex_batches = []
        self.index_batches = []
        self.vertex_count = 0

    def draw_text(self, text: str, x_world: int, y_world: int, scale=60, centered=False,
                  location: TrackLabelLocation = TrackLabelLocation.BOTTOM_LEFT,
                  location_offset: tuple[int, int] = (0, 0)):

        glyphs = self._metadata['glyphs']
        atlas_width = self._metadata['atlas']['width']
        atlas_height = self._metadata['atlas']['height']

        vertices = np.zeros(len(text) * 32, dtype='f4')
        indices = np.zeros(len(text) * 6, dtype='i4')
        indices_for_quad = np.array([0, 1, 2, 2, 3, 0], dtype='i4')
        x = y = 0

        cursor_x = 0
        vert_idx = 0
        char_count = 0
        for char in text:
            if char == ' ':
                cursor_x += 0.5
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

            quad_x = plane['left']
            quad_y = plane['bottom']
            quad_w = plane['right']
            quad_h = plane['top']

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
                [cursor_x + quad_x, quad_h - quad_y, x_world, y_world, tex_x, tex_y - tex_h, 0.0, 0.0],
                [cursor_x + quad_w, quad_h - quad_y, x_world, y_world, tex_x + tex_w, tex_y - tex_h, 0.0, 0.0],
                [cursor_x + quad_w, 0.0, x_world, y_world, tex_x + tex_w, tex_y, 0.0, 0.0],
                [cursor_x + quad_x, 0.0, x_world, y_world, tex_x, tex_y, 0.0, 0.0],
            ],
                            dtype='f4')

            # index buffer index
            ib_idx = char_count * 6
            vert_idx = char_count * 32

            vertices[vert_idx:vert_idx + 32] = quad.flatten()
            indices[ib_idx:ib_idx + 6] = indices_for_quad + (char_count * 4) + self.vertex_count * 4
            cursor_x += advance
            char_count += 1


        # For vertical centering, adjust y_offset based on the top of a capital letter
        glyph_E = next((g for g in self._metadata['glyphs'] if 'unicode' in g and g['unicode'] == 69), None)
        if glyph_E:
            y_offset = -glyph_E['planeBounds']['top'] / 2
        else:
            y_offset = -self._metadata['metrics']['ascender'] / 2
        offset_x, offset_y = orient_text_rect(location, (cursor_x, y_offset))        
        vertices[6::8] = offset_x
        vertices[7::8] = offset_y

        # if centered:
        #     x_offset = -cursor_x / 2

        #     # For vertical centering, adjust y_offset based on the top of a capital letter
        #     glyph_E = next((g for g in self._metadata['glyphs'] if 'unicode' in g and g['unicode'] == 69), None)
        #     if glyph_E:
        #         y_offset = -glyph_E['planeBounds']['top'] / 2
        #     else:
        #         y_offset = -self._metadata['metrics']['ascender'] / 2

        #     vertices[::6] += x_offset
        #     vertices[1::6] += y_offset


        # text_rect = RectInvY(0, 0, cursor_x, height)
        # text_rect = orient_text_rect(text_rect, location, location_offset)

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
        self._program['camera'].write(self._scene.get_vp()) # type: ignore

        font_scale = config.app_config.get_float(*self._scale_source) if self._scale_source else 40.0
        self._program['u_scale'] = font_scale

        map_scale = self._scene.map_size_m / self._scene.display_size[1] / self._scene.zoom_level * .6
        self._program['font_to_world'] = map_scale
        self._ctx.blend_func = mgl.SRC_ALPHA, mgl.ONE_MINUS_SRC_ALPHA
        self._ctx.enable(mgl.BLEND) # TODO is this the right place to call this?

        vao = self._ctx.simple_vertex_array(self._program,
                                            vbo,
                                            'in_pos_text',
                                            'in_pos_world',
                                            'in_texcoord',
                                            'in_pos_str_offset',
                                            index_buffer=ibo)
        vao.render(mgl.TRIANGLES)
