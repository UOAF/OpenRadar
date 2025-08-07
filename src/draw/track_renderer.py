import os
import numpy as np
from numpy.typing import NDArray
import moderngl as mgl
import glm
from dataclasses import dataclass
import math

from draw.scene import Scene
from draw.shapes import Shapes, add_control_points_angle
from game_state import GameObjectClassType
from sensor_tracks import Track, Declaration
from util.bms_math import NM_TO_METERS
from util.track_labels import *

from draw.text import TextRendererMsdf, make_text_renderer

import config


@dataclass
class TrackShapeRenderBuffer:
    offsets: NDArray[np.float32]  # Shape: (N, 2) -> N lines, (x, y)
    colors: NDArray[np.float32]  # Shape: (N, 4) -> RGBA color per line
    scales: NDArray[np.float32]  # Shape: (N,) -> Scale factor per line


@dataclass
class TrackLineRenderBuffer:
    lines: NDArray[np.float32]  # Shape: (N, P, 2) -> N lines, [(x, y)]
    colors: NDArray[np.float32]  # Shape: (N, 4) -> RGBA color per line


class TrackRenderer:

    def __init__(self, scene: Scene):

        self.scene = scene
        self._mgl_context = scene.mgl_context

        self.text_renderer = make_text_renderer(self._mgl_context,
                                                "atlas",
                                                scene,
                                                scale_source=("radar", "contact_font_scale"))

        shader_dir = str((config.bundle_dir / "resources/shaders").resolve())
        screen_polygon_vertex_shader = open(os.path.join(shader_dir, "screen_polygon_vertex.glsl")).read()
        screen_polygon_fragment_shader = open(os.path.join(shader_dir, "polygon_frag.glsl")).read()

        self.program = self._mgl_context.program(vertex_shader=screen_polygon_vertex_shader,
                                                 fragment_shader=screen_polygon_fragment_shader)

        self.shape_lists: dict[Shapes, list] = {shape: list() for shape in Shapes}
        self.lines: list = list()

        self.shape_buffers: dict[Shapes, TrackShapeRenderBuffer] = dict()
        self.line_buffer: TrackLineRenderBuffer | None = None

    def clear(self):
        self.shape_lists: dict[Shapes, list] = {shape: list() for shape in Shapes}
        self.lines: list = list()

        self.shape_buffers: dict[Shapes, TrackShapeRenderBuffer] = dict()
        self.line_buffer: TrackLineRenderBuffer | None = None

        self.text_renderer.init_buffers()

    def build_buffers(self, tracks: dict[GameObjectClassType, dict[str, Track]]):
        self.clear()
        # print("Building buffers")

        if config.app_config.get_bool("layers", "show_fixed_wing"):
            for track_dict in tracks[GameObjectClassType.FIXEDWING].values():
                self.draw_fixedwing(track_dict)

        if config.app_config.get_bool("layers", "show_rotary_wing"):
            for track_dict in tracks[GameObjectClassType.ROTARYWING].values():
                self.draw_rotarywing(track_dict)

        if config.app_config.get_bool("layers", "show_ground"):
            for track_dict in tracks[GameObjectClassType.GROUND].values():
                self.draw_ground_unit(track_dict)

        if config.app_config.get_bool("layers", "show_ships"):
            for track_dict in tracks[GameObjectClassType.SEA].values():
                self.draw_sea_unit(track_dict)

        if config.app_config.get_bool("layers", "show_missiles"):
            for track_dict in tracks[GameObjectClassType.MISSILE].values():
                self.draw_missile(track_dict)

        if config.app_config.get_bool("layers", "show_bullseye"):
            for track_dict in tracks[GameObjectClassType.BULLSEYE].values():
                self.draw_bullseye(track_dict)

        self.build_shape_arrays()
        self.build_line_arrays()

    def draw_rotarywing(self, track: Track):
        pass

    def draw_fixedwing(self, track: Track):

        declaration = track.get_declaration()

        color = glm.vec4(1, 0, 1, 1)
        shape = Shapes.CIRCLE
        if declaration == Declaration.FRIENDLY:
            color = glm.vec4(0, 0, 1, 1)
            shape = Shapes.SEMICIRCLE
        elif declaration == Declaration.HOSTILE:
            color = glm.vec4(1, 0, 0, 1)
            shape = Shapes.HALF_DIAMOND
        elif declaration == Declaration.UNKNOWN:
            color = glm.vec4(1, 1, 0, 1)
            shape = Shapes.TOP_BOX

        self.draw_shape(shape, track.position_m, color)
        self.draw_velocity_vector(track, color)

        pos_x, pos_y = int(track.position_m[0]), int(track.position_m[1])

        labels = get_labels_for_class_type(GameObjectClassType.FIXEDWING)

        offset = config.app_config.get_int("radar", "contact_size")

        if labels is not None:
            for location, track_label in labels.labels.items():
                text = evaluate_input_format(track_label.label_format, track)
                if text is not None and text != "":
                    self.text_renderer.draw_text(text,
                                                 pos_x,
                                                 pos_y,
                                                 scale=config.app_config.get_int("radar", "contact_font_scale"),
                                                 location=location,
                                                 screen_offset=(offset, offset))
        # self.text_renderer.draw_text(track.id, pos_x, pos_y,
        #                              scale=config.app_config.get_int("radar", "contact_font_scale"),
        #                                 )

    def draw_velocity_vector(self, track: Track, color: glm.vec4):

        self.scene.world_to_screen_distance(track.velocity_ms)

        LINE_LEN_SECONDS = 30  # 30 seëconds of velocity vector

        heading_rad = math.radians(track.heading_deg - 90)  # -90 rotaes north to up
        end_x = track.position_m[0] + track.velocity_ms * math.cos(heading_rad) * LINE_LEN_SECONDS
        end_y = track.position_m[1] + track.velocity_ms * math.sin(-heading_rad) * LINE_LEN_SECONDS
        end_pt = (end_x, end_y)

        self.draw_line([track.position_m, end_pt], color)

    def draw_ground_unit(self, track: Track):
        declaration = track.get_declaration()

        color = glm.vec4(1, 0, 1, 1)
        shape = Shapes.CIRCLE

        if declaration == Declaration.FRIENDLY:
            color = glm.vec4(0, 0, 1, 1)
            shape = Shapes.CIRCLE
        elif declaration == Declaration.HOSTILE:
            color = glm.vec4(1, 0, 0, 1)
            shape = Shapes.DIAMOND
        elif declaration == Declaration.UNKNOWN:
            color = glm.vec4(1, 1, 0, 1)
            shape = Shapes.SQUARE

        self.draw_shape(shape, track.position_m, color)

    def draw_sea_unit(self, track: Track):
        declaration = track.get_declaration()

        color = glm.vec4(1, 0, 1, 1)
        shape = Shapes.SHIP
        if declaration == Declaration.FRIENDLY:
            color = glm.vec4(0, 0, 1, 1)
        elif declaration == Declaration.HOSTILE:
            color = glm.vec4(1, 0, 0, 1)
        elif declaration == Declaration.UNKNOWN:
            color = glm.vec4(1, 1, 0, 1)

        self.draw_shape(shape, track.position_m, color)

    def draw_missile(self, track: Track):
        pass

    def draw_bullseye(self, track: Track):
        """
        Draws the bullseye on the map.
        """
        NUM_RINGS = 6
        RING_DISTANCE_NM = 20
        ring_distance_px = float(self.scene.world_to_screen_distance(RING_DISTANCE_NM * NM_TO_METERS))  # type: ignore

        # Draw the bullseye cross, by drawing two lines
        half_line_length_m = NM_TO_METERS * RING_DISTANCE_NM * (NUM_RINGS + 1)

        self.draw_line([(track.position_m[0] - half_line_length_m, track.position_m[1]),
                        (track.position_m[0] + half_line_length_m, track.position_m[1])], glm.vec4(1, 1, 1, 1))

        self.draw_line([(track.position_m[0], track.position_m[1] - half_line_length_m),
                        (track.position_m[0], track.position_m[1] + half_line_length_m)], glm.vec4(1, 1, 1, 1))

        # Draw the bullseye circles
        for i in range(NUM_RINGS):
            radius = (i + 1) * ring_distance_px
            color = glm.vec4(0.5, 0.5, 0.5, 1) if i % 2 == 0 else glm.vec4(0.7, 0.7, 0.7, 1)
            self.draw_shape(Shapes.CIRCLE, (track.position_m[0], track.position_m[1]), color, scale=radius)
            self.text_renderer.draw_text(f"{RING_DISTANCE_NM * (i + 1)} NM",
                                         int(track.position_m[0]),
                                         int(track.position_m[1]),
                                         scale=config.app_config.get_int("radar", "contact_font_scale"),
                                         location=TrackLabelLocation.TOP_RIGHT)

        color = glm.vec4(1, 0, 0, 1)

    def draw_shape(self, shape_type: Shapes, position: tuple[float, float], color: glm.vec4, scale: float = -1):
        if scale == -1:
            scale = config.app_config.get_float("radar", "contact_size")
        self.shape_lists[shape_type].append((position, color, scale))

    def draw_line(self, points: list[tuple[float, float]], color: glm.vec4):
        self.lines.append((points, color))

    def build_shape_arrays(self):
        for shape, item_list in self.shape_lists.items():
            if len(item_list) == 0:
                continue
            positions, colors, scales = zip(*item_list)
            self.shape_buffers[shape] = TrackShapeRenderBuffer(offsets=np.array(positions, dtype=np.float32),
                                                               colors=np.array(colors, dtype=np.float32),
                                                               scales=np.array(scales, dtype=np.float32))

    def build_line_arrays(self):
        if len(self.lines) == 0:
            return

        stoke_width = config.app_config.get_float("radar", "contact_stroke")
        lines, colors = zip(*self.lines)
        self.line_buffer = TrackLineRenderBuffer(np.array(lines, dtype=np.float32), np.array(colors, dtype=np.float32))

    def render(self):
        for shape, buffer in self.shape_buffers.items():
            self.render_shapes_buffer(shape.value.points, buffer)
        if self.line_buffer is not None:
            self.render_lines_args(self.line_buffer.lines, self.line_buffer.colors)
        self.text_renderer.render()

    def render_shapes_buffer(self, shape: NDArray, input: TrackShapeRenderBuffer):
        shape_size = config.app_config.get_float("radar", "contact_size")
        self.render_instances_args(shape, input.offsets, input.colors, input.scales)

    def render_instances_args(self, unit_shape: NDArray[np.float32], offsets: NDArray[np.float32],
                              colors: NDArray[np.float32], scales: NDArray[np.float32]):
        """
        Draws multiple line instances with specified attributes.

        This method renders multiple lines (or strokes) with configurable offsets, scales, colors, 
        and widths. Each line segment supports mitered end caps by using additional invisible 
        vertices to determine the endpoint angles.

        Args:
            unit_shape (NDArray[np.float32]): 
                A NumPy array of shape (M, 4) representing the vertex positions for each line segment. 
                Each vertex includes (x, y, z, w) in homogeneous coordinates, where z is typically 0.0 
                and w is 1.0 for 2D rendering.
            offsets (NDArray[np.float32]): 
                A NumPy array of shape (N, 2) specifying (x, y) offsets for each instance. These are 
                added to the vertices during rendering, enabling instanced positioning.
            scale (glm.vec2): 
                A glm.vec2 specifying the uniform scaling factors (x, y) for all instances. 
                Used to uniformly scale the vertices.
            colors (NDArray[np.float32]): 
                A NumPy array of shape (N, 4) specifying RGBA colors for each instance. Colors are 
                stored as normalized values in the range [0.0, 1.0].
            widths_px (float): 
                A float specifying the width of each line in pixels. Widths are applied uniformly 
                across all instances.

        Raises:
            AssertionError: 
                If input arrays do not conform to the required shapes:
                - `vertices` must have shape (M, 4).
                - `offsets` must have shape (N, 2).
                - `colors` must have shape (N, 4).
                - All arrays must have the same number of instances (N).

        Notes:
            - Invisible vertices are added to control endpoint angles and mitered joins.
            - Each filled line segment requires 6 vertices for rendering.
            - Total output vertices are computed as: `(M - 3) * 6`.

        Example:
            vertices = np.array([[0, 0, 0, 1], [1, 1, 0, 1], [2, 0, 0, 1]], dtype=np.float32)
            offsets = np.array([[0, 0]], dtype=np.float32)
            scale = glm.vec2(1, 1)
            colors = np.array([[1.0, 0.0, 0.0, 1.0]], dtype=np.float32)
            widths_px = 2.0

            drawer.draw_instances(vertices, offsets, scale, colors, widths_px)
        """
        assert unit_shape.shape[1] == 4, "unit_shape must be a 4f array"
        assert offsets.shape[1] == 2, "offsets must be a 2f array"
        assert colors.shape[1] == 4, "colors must be a 4f array"
        assert offsets.shape[0] == colors.shape[0], "All input arrays must have the same length"

        self.program['u_mvp'].write(self.scene.get_vp())  # type: ignore
        self.program['u_resolution'] = self.scene.display_size

        track_width = config.app_config.get_float("radar", "contact_stroke")

        self.program['u_width'] = track_width

        ssbo = self._mgl_context.buffer(unit_shape.astype('f4').tobytes())
        ssbo.bind_to_storage_buffer(0)

        offset_buf = self._mgl_context.buffer(offsets)
        colors_buf = self._mgl_context.buffer(colors)
        scales_buf = self._mgl_context.buffer(scales)

        vao = self._mgl_context.vertex_array(self.program, [(offset_buf, '2f/i', 'i_offset'),
                                                            (colors_buf, '4f/i', 'i_color'),
                                                            (scales_buf, 'f/i', 'i_scale')])

        num_output_vertices = (len(unit_shape) - 3) * 6

        vao.render(mgl.TRIANGLES, vertices=num_output_vertices, instances=len(offsets))

        vao.release()
        ssbo.release()
        offset_buf.release()
        colors_buf.release()

    def render_lines_args(
            self,
            lines: NDArray[np.float32],  # Shape: (N, P, 2) -> N lines, P points per line, (x, y)
            colors: NDArray[np.float32],  # Shape: (N, 4) -> RGBA color per line
            add_control_points: bool = True):
        """
        Draw multiple lines with specified colors, widths, and optional control points.

        :param lines: An array of shape (N, P, 2) where N is the number of lines,
                    P is the number of points per line, and 2 represents (x, y).
        :param colors: An array of shape (N, 4) for RGBA colors, one for each line.
        :param widths_px: An float specifying the width of each line.
        :param add_control_points: Whether to add control points to each line.
        """
        # Validate input shapes
        if len(lines.shape) != 3 or lines.shape[2] != 2:
            raise ValueError("Input 'lines' must have shape (N, P, 2) for 2D points.")
        if len(colors.shape) != 2 or colors.shape[1] != 4:
            raise ValueError("Input 'colors' must have shape (N, 4) for RGBA colors.")
        if lines.shape[0] != colors.shape[0]:
            raise ValueError("Mismatched number of lines, colors.")

        # Prepare offsets and scales (default values)
        num_instances = lines.shape[0]
        offsets = np.zeros((num_instances, 2), dtype=np.float32)  # (N, 2)
        scales = np.zeros((num_instances, ), dtype=np.float32)  # (N,)

        for i in range(num_instances):
            # Convert 2D points (x, y) to 4D (x, y, z=0.0, w=1.0)
            z = np.zeros((lines[i].shape[0], 1), dtype=np.float32)  # z = 0.0
            w = np.ones((lines[i].shape[0], 1), dtype=np.float32)  # w = 1.0
            line = np.hstack((lines[i], z, w))  # Shape: (P, 4)

            # Add control points if required
            if add_control_points:
                line = add_control_points_angle(line)

            # Verify that the processed vertices are valid for draw_instances
            assert line.shape[1] == 4, "Vertices must have shape (P, 4)."

            # Draw the line with specified parameters
            self.render_instances_args(
                unit_shape=line,
                offsets=offsets[i:i + 1],  # Slice to match shape (1, 2)
                colors=colors[i:i + 1],  # Slice to match shape (1, 4)
                scales=scales)  # Scale is in screenspace so set it to 0)
