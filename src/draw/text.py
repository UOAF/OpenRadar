from typing import Optional
from PIL import Image
import os
import json
import moderngl as mgl
import numpy as np

from draw.scene import Scene

import config

from util.track_labels import TrackLabelLocation

from logging_config import get_logger

logger = get_logger(__name__)


def orient_text_rect(location: TrackLabelLocation, object_size: tuple[float, float] = (0, 0)) -> tuple[float, float]:
    """Calculate the offset in model space for a text string based on the rendered bounding box of the string."""
    width, height = object_size

    # Calculate offsets based on location
    # For X: LEFT = -width, CENTER = -width/2, RIGHT = 0
    # For Y: TOP = 0, CENTER = -height/2, BOTTOM = -height
    offsets = {
        TrackLabelLocation.TOP_LEFT: (-width, 0),
        TrackLabelLocation.TOP_CENTER: (-width / 2, 0),
        TrackLabelLocation.TOP_RIGHT: (0, 0),
        TrackLabelLocation.LEFT: (-width, -height / 2),
        TrackLabelLocation.CENTER: (-width / 2, -height / 2),
        TrackLabelLocation.RIGHT: (0, -height / 2),
        TrackLabelLocation.BOTTOM_LEFT: (-width, -height),
        TrackLabelLocation.BOTTOM_CENTER: (-width / 2, -height),
        TrackLabelLocation.BOTTOM_RIGHT: (0, -height),
    }
    return offsets.get(location, (0, 0))


def apply_directional_screen_offset(location: TrackLabelLocation, screen_offset: tuple[float,
                                                                                       float]) -> tuple[float, float]:
    """Apply screen space offset relative to the anchor direction."""
    offset_x, offset_y = screen_offset

    # Get the directional multipliers based on anchor location
    # For X: LEFT = -1 (move left), CENTER = 0 (no bias), RIGHT = 1 (move right)
    # For Y: TOP = 1 (move up), CENTER = 0 (no bias), BOTTOM = -1 (move down)
    direction_multipliers = {
        TrackLabelLocation.TOP_LEFT: (-1, 1),
        TrackLabelLocation.TOP_CENTER: (0, 1),
        TrackLabelLocation.TOP_RIGHT: (1, 1),
        TrackLabelLocation.LEFT: (-1, 0),
        TrackLabelLocation.CENTER: (0, 0),
        TrackLabelLocation.RIGHT: (1, 0),
        TrackLabelLocation.BOTTOM_LEFT: (-1, -1),
        TrackLabelLocation.BOTTOM_CENTER: (0, -1),
        TrackLabelLocation.BOTTOM_RIGHT: (1, -1),
    }

    x_mult, y_mult = direction_multipliers.get(location, (0, 0))
    return (offset_x * x_mult, offset_y * y_mult)


def load_atlas(context: mgl.Context, atlas_name: str, atlas_path: str):
    atlas_image_path = os.path.join(atlas_path, f"{atlas_name}.png")
    atlas_json_path = os.path.join(atlas_path, f"{atlas_name}.json")
    atlas_image = Image.open(atlas_image_path).convert("RGBA")
    atlas_texture = context.texture(atlas_image.size, 4, atlas_image.tobytes())
    atlas_texture.use()

    logger.info(f"Font atlas loaded: {atlas_image_path} ({atlas_image.size[0]}x{atlas_image.size[1]})")

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

    def __init__(self,
                 context: mgl.Context,
                 texture: mgl.Texture,
                 metadata: dict,
                 scene: Scene,
                 scale_source: Optional[tuple[str, str]] = None):
        self._atlas = texture
        self._metadata = metadata
        self._ctx = context
        vertex_shader = open(os.path.join("resources", "shaders", "text_vertex.glsl")).read()
        fragment_shader = open(os.path.join("resources", "shaders", "text_frag.glsl")).read()
        self._program = context.program(vertex_shader=vertex_shader, fragment_shader=fragment_shader)
        self._scene = scene
        self._scale_source = scale_source

        # Create shared quad geometry (per-vertex data)
        self._create_quad_geometry()
        self.init_buffers()
        self._precompute_valid_chars()

    def _precompute_valid_chars(self):
        """Precompute valid character codes and their glyph indices for fast lookup."""
        glyphs = self._metadata['glyphs']

        # Create array of valid character codes (32-126 typically)
        valid_codes = []
        valid_glyph_indices = []
        valid_advances = []
        valid_plane_bounds = []
        valid_atlas_bounds = []

        for i, glyph in enumerate(glyphs):
            char_code = i + 32
            if 'planeBounds' in glyph and 'atlasBounds' in glyph:
                # Ensure character code fits in our lookup table
                assert char_code < 256, f"Character code {char_code} ('{chr(char_code)}') exceeds lookup table size (256)"
                valid_codes.append(char_code)
                valid_glyph_indices.append(i)
                valid_advances.append(glyph['advance'])

                plane = glyph['planeBounds']
                atlas = glyph['atlasBounds']
                valid_plane_bounds.append([plane['left'], plane['bottom'], plane['right'], plane['top']])
                valid_atlas_bounds.append([atlas['left'], atlas['bottom'], atlas['right'], atlas['top']])

        self._valid_char_codes = np.array(valid_codes, dtype=np.int32)
        self._valid_glyph_indices = np.array(valid_glyph_indices, dtype=np.int32)
        self._valid_advances = np.array(valid_advances, dtype=np.float32)
        self._valid_plane_bounds = np.array(valid_plane_bounds, dtype=np.float32)
        self._valid_atlas_bounds = np.array(valid_atlas_bounds, dtype=np.float32)

        # Create lookup tables for all possible character codes (0-255)
        # This allows O(1) lookup instead of searchsorted
        self._advance_lookup = np.full(256, -1.0, dtype=np.float32)
        self._glyph_lookup = np.full(256, -1, dtype=np.int32)
        self._plane_bounds_lookup = np.full((256, 4), -1.0, dtype=np.float32)
        self._atlas_bounds_lookup = np.full((256, 4), -1.0, dtype=np.float32)

        for i, code in enumerate(valid_codes):
            self._advance_lookup[code] = valid_advances[i]
            self._glyph_lookup[code] = valid_glyph_indices[i]
            self._plane_bounds_lookup[code] = valid_plane_bounds[i]
            self._atlas_bounds_lookup[code] = valid_atlas_bounds[i]

        # Special case for space character
        space_code = ord(' ')
        self._advance_lookup[space_code] = 0.5

    def _create_quad_geometry(self):
        """Create the shared quad geometry used for all glyph instances."""
        # Quad vertices: (x, y) for a unit quad from (0,0) to (1,1)
        quad_vertices = np.array(
            [
                0.0,
                0.0,  # Bottom-left
                1.0,
                0.0,  # Bottom-right
                1.0,
                1.0,  # Top-right
                0.0,
                1.0,  # Top-left
            ],
            dtype='f4')

        # Quad indices
        quad_indices = np.array([0, 1, 2, 2, 3, 0], dtype='i4')

        self._quad_vbo = self._ctx.buffer(quad_vertices.tobytes())
        self._quad_ibo = self._ctx.buffer(quad_indices.tobytes())

    def init_buffers(self):
        """Initialize instance data buffers."""
        self._atlas.use()
        self.instance_batches = []
        self.instance_count = 0

    def _get_string_height(self):
        """Get the height of a typical character for string alignment."""
        glyph_E = next((g for g in self._metadata['glyphs'] if 'unicode' in g and g['unicode'] == 69), None)
        if glyph_E and 'planeBounds' in glyph_E:
            return glyph_E['planeBounds']['top']
        return self._metadata['metrics']['ascender']

    def draw_text(self,
                  text: str,
                  x_world: int,
                  y_world: int,
                  scale=60,
                  centered=False,
                  location: TrackLabelLocation = TrackLabelLocation.CENTER,
                  location_offset: tuple[int, int] = (0, 0),
                  screen_offset: tuple[float, float] = (0.0, 0.0)):

        glyphs = self._metadata['glyphs']
        atlas_width = self._metadata['atlas']['width']
        atlas_height = self._metadata['atlas']['height']

        char_codes = np.fromiter((ord(c) for c in text), dtype=np.int32, count=len(text))

        advances = self._advance_lookup[char_codes]
        glyph_indices = self._glyph_lookup[char_codes]

        valid_mask = advances >= 0

        if not np.any(valid_mask):
            return

        final_advances = advances[valid_mask]
        final_glyph_indices = glyph_indices[valid_mask]
        final_char_codes = char_codes[valid_mask]

        if len(final_glyph_indices) == 0:
            return

        cursor_positions = np.cumsum(np.concatenate([[0], final_advances[:-1]]))

        instances = np.zeros(len(final_glyph_indices) * 16, dtype='f4')

        string_height = self._get_string_height()
        total_advance = float(np.sum(final_advances))
        string_offset_x, string_offset_y = orient_text_rect(location, (total_advance, string_height))

        # Apply directional screen space offset
        screen_offset_x, screen_offset_y = apply_directional_screen_offset(location, screen_offset)

        # Vectorized instance data generation using precomputed lookup tables
        num_chars = len(final_char_codes)

        # Use precomputed bounds lookup tables for vectorized access
        plane_bounds = self._plane_bounds_lookup[final_char_codes]
        atlas_bounds = self._atlas_bounds_lookup[final_char_codes]

        # Create arrays for repeated values
        cursor_y = np.zeros(num_chars, dtype=np.float32)
        world_x = np.full(num_chars, x_world, dtype=np.float32)
        world_y = np.full(num_chars, y_world, dtype=np.float32)
        offset_x = np.full(num_chars, string_offset_x, dtype=np.float32)
        offset_y = np.full(num_chars, string_offset_y, dtype=np.float32)
        screen_off_x = np.full(num_chars, screen_offset_x, dtype=np.float32)
        screen_off_y = np.full(num_chars, screen_offset_y, dtype=np.float32)

        # Stack all data in the correct order: plane(4) + cursor(2) + world(2) + atlas(4) + offset(2) + screen_offset(2) = 16
        instances = np.column_stack([
            plane_bounds,  # 4 values: left, bottom, right, top
            cursor_positions,
            cursor_y,  # 2 values: cursor_x, cursor_y (0)
            world_x,
            world_y,  # 2 values: world_x, world_y
            atlas_bounds,  # 4 values: left, bottom, right, top
            offset_x,
            offset_y,  # 2 values: offset_x, offset_y
            screen_off_x,
            screen_off_y  # 2 values: screen_offset_x, screen_offset_y
        ]).flatten().astype(np.float32)

        # print(f"Rendering text: '{text}' at ({x_world}, {y_world}) with {len(final_glyph_indices)} characters")

        self.instance_batches.append(instances)
        self.instance_count += len(final_glyph_indices)

    def render(self):
        """Call this once per frame, after rendering all the text you need.
        """
        if not self.instance_batches:
            return

        # Combine all instance data
        instances = np.concatenate(self.instance_batches)
        instance_vbo = self._ctx.buffer(instances.tobytes())

        # Set uniforms
        self._program['camera'].write(self._scene.get_vp())  # type: ignore

        font_scale = config.app_config.get_float(*self._scale_source) if self._scale_source else 40.0
        self._program['u_scale'] = font_scale

        map_scale = self._scene.map_size_m / self._scene.display_size[1] / self._scene.zoom_level * .6
        self._program['font_to_world'] = map_scale

        atlas_width = self._metadata['atlas']['width']
        atlas_height = self._metadata['atlas']['height']
        self._program['atlas_size'] = (atlas_width, atlas_height)

        # Pass viewport resolution for screen coordinate calculations
        self._program['u_resolution'] = self._scene.display_size

        self._ctx.blend_func = mgl.SRC_ALPHA, mgl.ONE_MINUS_SRC_ALPHA
        self._ctx.enable(mgl.BLEND)

        vao = self._ctx.vertex_array(self._program,
                                     [(self._quad_vbo, '2f', 'in_quad_pos'),
                                      (instance_vbo, '4f 2f 2f 4f 2f 2f/i', 'in_glyph_bounds', 'in_cursor_pos',
                                       'in_world_pos', 'in_atlas_bounds', 'in_string_offset', 'in_screen_offset')],
                                     self._quad_ibo)

        vao.render(instances=self.instance_count)
