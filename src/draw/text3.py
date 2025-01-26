from calendar import c
from tkinter import BOTTOM, TOP
from typing import Optional
from PIL import Image
import os
import json
import moderngl as mgl
import numpy as np

from draw.scene import Scene
from util.rect import Rect, RectInvY
from util.track_labels import TrackLabelLocation


def orient_text_rect(rect: RectInvY, location: TrackLabelLocation, obect_size: tuple[int, int] = (0,0)) -> RectInvY:
    
    if location == TrackLabelLocation.TOP_LEFT:
        offset = (-obect_size[0] // 2, obect_size[1] // 2)
        rect.bottom_right = offset
    elif location == TrackLabelLocation.TOP_CENTER:
        offset = (0, obect_size[1] // 2)
        rect.bottom_center = offset
    elif location == TrackLabelLocation.TOP_RIGHT:
        offset = (obect_size[0] // 2, obect_size[1] // 2)
        rect.bottom_left = offset
    elif location == TrackLabelLocation.LEFT:
        offset = (-obect_size[0] // 2, 0)
        rect.right_center = offset
    elif location == TrackLabelLocation.RIGHT:
        offset = (obect_size[0] // 2, 0)
        rect.left_center = offset
    elif location == TrackLabelLocation.BOTTOM_LEFT:
        offset = (-obect_size[0] // 2, -obect_size[1] // 2)
        rect.top_right = offset
    elif location == TrackLabelLocation.BOTTOM_CENTER:
        offset = (0, -obect_size[1] // 2)
        rect.top_center = offset
    elif location == TrackLabelLocation.BOTTOM_RIGHT:
        offset = (obect_size[0] // 2, -obect_size[1] // 2)
        rect.top_left = offset
    
    return rect


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


def make_text_renderer(atlas_name: str, scene: Scene, atlas_path: Optional[str] = None):
    """Create a text renderer from a given MSDF (multichannel signed distance field) atlas.
    
    Parameters:
    
        atlas_name: filename of the atlas
        atlas_path: file path in which the atlas files live. Defaults to 'resources/fonts'.

    """
    if atlas_path is None:
        atlas_path = os.path.join(os.getcwd(), "resources", "fonts")
    context = scene.mgl_context
    tex, data = load_atlas(context, atlas_name, atlas_path)
    return TextRendererMsdf(tex, data, scene)


def generate_model_matrix(position, scale, rotation=0) -> np.ndarray:
    """
    Generate a model matrix for text rendering.
    
    Parameters:
        position: Tuple (x, y) indicating the world-space position of the text.
        scale: Scaling factor for the text size.
        rotation: Rotation in radians (optional).
    
    Returns:
        A 4x4 model matrix.
    """
    x, y = position

    # Translation matrix
    translation_matrix = np.array([
        [1, 0, 0, x],
        [0, 1, 0, y],
        [0, 0, 1, 0],
        [0, 0, 0, 1],
    ], dtype=np.float32)

    # Scaling matrix
    scaling_matrix = np.array([
        [scale, 0, 0, 0],
        [0, scale, 0, 0],
        [0, 0, 1, 0],
        [0, 0, 0, 1],
    ], dtype=np.float32)

    # Rotation matrix (if rotation is needed)
    cos_r = np.cos(rotation)
    sin_r = np.sin(rotation)
    rotation_matrix = np.array([
        [cos_r, -sin_r, 0, 0],
        [sin_r, cos_r, 0, 0],
        [0, 0, 1, 0],
        [0, 0, 0, 1],
    ],
                               dtype=np.float32)

    # Combine transformations: T * R * S
    model_matrix = np.matmul(np.matmul(translation_matrix, rotation_matrix), scaling_matrix)
    return model_matrix


class TextRendererMsdf:

    def __init__(self, texture: mgl.Texture, metadata: dict, scene: Scene):
        self._atlas = texture
        self._metadata = metadata
        self._ctx = scene.mgl_context
        vertex_shader = open(os.path.join("resources", "shaders", "text_vertex2.glsl")).read()
        fragment_shader = open(os.path.join("resources", "shaders", "text_frag.glsl")).read()
        self._program = self._ctx.program(vertex_shader=vertex_shader, fragment_shader=fragment_shader)
        self._scene = scene
        self.clear()

    def clear(self):
        """"""
        self.text_batches: list[dict] = []
        self.vertex_batches = []
        self.index_batches = []
        self.model_matrices = []  # Store model matrices per instance
        self.char_range = []  # Store character ranges per instance
        self.char_scales = []  # Store character scales per instance
        self.vertex_count = 0

    def draw_text(self,
                  text: str,
                  x_world: float,
                  y_world: float,
                  scale: float = 20,
                  scale_to_screen: bool = True,
                  offset: tuple[int, int] = (0, 0)):
        """"""
        glyphs = self._metadata['glyphs']
        atlas_width = self._metadata['atlas']['width']
        atlas_height = self._metadata['atlas']['height']

        vertices = np.zeros(len(text) * 16, dtype='f4')
        indices = np.zeros(len(text) * 6, dtype='i4')
        indices_for_quad = np.array([0, 1, 2, 2, 3, 0], dtype='i4')

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
                print(f"Skipping unknown character: {char}")
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
            quad_x = plane['left']
            quad_y = plane['bottom']
            quad_w = plane['right']
            quad_h = plane['top']

            glyph_bottom = atlas_height - atlas['bottom']
            glyph_top = atlas_height - atlas['top']

            # Calculate texture coordinates
            tex_x = atlas['left'] / atlas_width
            tex_y = glyph_top / atlas_height
            tex_w = (atlas['right'] - atlas['left']) / atlas_width
            tex_h = (glyph_top - glyph_bottom) / atlas_height

            # Debug: Print glyph metrics
            # print(f"Rendering '{char}': tex=({tex_x}, {tex_y}, {tex_w}, {tex_h})")

            # Set up vertex data
            quad = np.array([
                [cursor_x + quad_x, quad_y, tex_x, tex_y - tex_h],
                [cursor_x + quad_w, quad_y, tex_x + tex_w, tex_y - tex_h],
                [cursor_x + quad_w, quad_h, tex_x + tex_w, tex_y],
                [cursor_x + quad_x, quad_h, tex_x, tex_y],
            ],
                            dtype='f4')

            # index buffer index
            ib_idx = char_count * 6
            vert_idx = char_count * 16

            vertices[vert_idx:vert_idx + 16] = quad.flatten()
            indices[ib_idx:ib_idx + 6] = indices_for_quad + (char_count * 4)  # + self.vertex_count * 4
            cursor_x += advance
            char_count += 1

        height = atlas_height = self._metadata['metrics']['lineHeight']
        text_rect = RectInvY(0, 0, cursor_x, height)
        

        current_batch = len(self.text_batches)
        self.text_batches.append({})
        self.text_batches[current_batch]['vertices'] = vertices
        self.text_batches[current_batch]['indices'] = indices
        # self.text_batches[current_batch]['char_count'] = char_count
        self.text_batches[current_batch]['scale'] = scale
        self.text_batches[current_batch]['scale_to_screen'] = scale_to_screen
        self.text_batches[current_batch]['position'] = (x_world, y_world)

    def render(self):
        """Call this once per frame, after rendering all the text you need.
        """
        self._atlas.use()
        self._ctx.blend_func = mgl.SRC_ALPHA, mgl.ONE_MINUS_SRC_ALPHA
        self._ctx.enable(mgl.BLEND)  # TODO is this the right place to call this?

        if len(self.text_batches) == 0:
            return

        for batch in self.text_batches:
            vertices = batch['vertices']
            indices = batch['indices']
            position = batch['position']
            # char_count = batch['char_count']
            scale = batch['scale']
            scale_to_screen = batch['scale_to_screen']

            if scale_to_screen:
                scale = self._scene.map_size_m / self._scene.display_size[1] / self._scene.zoom_level * scale

            model_matrix = generate_model_matrix(position, scale)

            vbo = self._ctx.buffer(vertices.tobytes())
            ibo = self._ctx.buffer(indices.tobytes())

            mvp = np.array(self._scene.get_vp()) @ model_matrix
            self._program['u_mvp'].write(mvp.T.tobytes())  # type: ignore

            text_scale = 1.0  # Example scale factor
            self._program['u_text_scale'].value = text_scale  # type: ignore

            vao = self._ctx.simple_vertex_array(self._program, vbo, 'in_pos_text', 'in_texcoord', index_buffer=ibo)
            vao.render(mgl.TRIANGLES)
