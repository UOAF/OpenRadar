import os
import sys
import queue

import glfw
from imgui_bundle import imgui
import glm
from PIL import Image
import OpenGL.GL as gl
import moderngl as mgl
import numpy as np
import math

import config
from logging_config import get_logger, log_performance_metrics
from game_object import GameObject
from ui.imgui_ui import ImguiUserInterface
from game_state import GameState
from trtt_client import TRTTClientThread
from draw.map_gl import MapGL
from draw.scene import Scene
from sensor_tracks import SensorTracks
from display_data import DisplayData
from gpu_timer import GPUTimer

from util.os_utils import from_path
from util.bms_math import THEATRE_DEFAULT_SIZE_FT

VSYNC_ENABLE = True
MOUSEDRAGBUTTON = 1
MOUSEBRAABUTTON = 0

MINIMUM_DRAG_DISTANCE = 5
MAXIMUM_HOVER_DISTANCE = 40


class Clock:

    def __init__(self):
        self._last_time: int = glfw.get_time()
        self._fps = 0.0

    def tick(self):
        now = glfw.get_time()
        delta = now - self._last_time
        self._last_time = now
        self._fps = 1.0 / delta
        return delta

    @property
    def fps(self):
        return self._fps


class App:
    """
    The main application class for the OpenRadar program.
    """

    def __init__(self, *args, **kwargs):
        self.logger = get_logger(__name__)
        self.logger.info("Initializing OpenRadar application")

        self._running = True
        self.mouseDragDown = False
        self.mouseBRAADown = False
        self._startPan = (0, 0)
        self._panDelta = (0, 0)
        self._startBraa = (0, 0)
        self._mgl_ctx: mgl.Context
        self.clock: Clock
        self.gpu_frame_time_us = 0
        self.cpu_frame_time = 0
        self.radar_sleep = 0

        # GPU timing management must only be initialized after OpenGL context has been created
        self.gpu_timer: GPUTimer | None = None

        try:
            os.chdir(sys._MEIPASS)  # type: ignore
            self.logger.debug(f"Changed working directory to: {sys._MEIPASS}")  # type: ignore
        except AttributeError:
            self.logger.debug("Running in development mode (not compiled)")
            pass

    def on_init(self):
        self.logger.info("Initializing OpenGL and application components")

        glfw.init()
        self.clock = Clock()
        glfw.set_error_callback(self.handle_error)
        window_icon = Image.open(from_path(config.bundle_dir / "resources/icons/OpenRadaricon.png"))

        # Set window hints for initial position (Hide the window initially before setting position)
        glfw.window_hint(glfw.VISIBLE, glfw.FALSE)

        glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 4)
        glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 6)
        glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
        glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, glfw.TRUE)

        # 8x MSAA. Must be done before creating the window
        msaa_enable = config.app_config.get_bool("display", "msaa_enabled")
        msaa_samples = config.app_config.get_int("display", "msaa_samples")
        if (msaa_enable):
            glfw.window_hint(glfw.SAMPLES, msaa_samples)
            self.logger.info(f"MSAA enabled with {msaa_samples} samples")

        config_size: tuple[int, int] = config.app_config.get("window", "size", tuple[int, int])  # type: ignore
        h, w = config_size
        self.window = glfw.create_window(h, w, 'OpenRadar', None, None)
        self.logger.info(f"Created window with size: {h}x{w}")

        window_x, window_y = config.app_config.get("window", "location", tuple[int, int])  # type: ignore
        glfw.set_window_pos(self.window, window_x, window_y)

        glfw.show_window(self.window)

        glfw.set_input_mode(self.window, glfw.CURSOR, glfw.CURSOR_NORMAL)

        glfw.set_window_icon(self.window, 1, window_icon)
        glfw.make_context_current(self.window)

        glfw.swap_interval(int(VSYNC_ENABLE))

        # Create the Tacview RT Relemetry client
        self.data_queue: queue.Queue[str] = queue.Queue()
        self.data_client = TRTTClientThread(self.data_queue)
        self.data_client.start()
        self.logger.info("Started Tacview RT Telemetry client")

        self.gamestate = GameState(self.data_queue)

        glfw.set_window_close_callback(self.window, self.window_close_callback)
        glfw.set_window_pos_callback(self.window, self.handle_window_moved)
        glfw.set_window_size_callback(self.window, self.handle_window_resized)
        glfw.set_scroll_callback(self.window, self.handle_mouse_wheel)
        glfw.set_mouse_button_callback(self.window, self.handle_mouse_button)
        glfw.set_cursor_pos_callback(self.window, self.handle_mouse_motion)
        glfw.set_key_callback(self.window, self.handle_key)
        glfw.set_char_callback(self.window, self.handle_char)

        self._running = True

        self.mgl_ctx = mgl.create_context()

        if msaa_enable:
            gl.glEnable(gl.GL_MULTISAMPLE)

        self.size = self.width, self.height = config_size
        self.scene = Scene(self.size, self.mgl_ctx)
        self._map_gl = MapGL(self.size, self.scene, self.mgl_ctx)

        # Must be initialized after the OpenGL context is created
        self.gpu_timer = GPUTimer()

        self._tracks = SensorTracks(self.gamestate)
        self._display_data = DisplayData(self.scene, self.gamestate, self._tracks)

        self._ImguiUI = ImguiUserInterface(self.size, self.window, self.scene, self._map_gl, self.gamestate,
                                           self._tracks, self._display_data, self.data_client)

        self._ImguiUI.set_reset_callback(self.reset_state_callback)
        self._ImguiUI.set_render_refresh_callback(self.render_refresh_callback)

        self.hovered_game_obj: GameObject | None = None

        self.logger.info("Application initialization completed successfully")

    def handle_error(self, err, desc):
        error_msg = f"GLFW error: {err}, {desc}"
        self.logger.error(error_msg)

    def window_close_callback(self, event):
        self.logger.info("Window close requested")
        self._running = False

    def reset_state_callback(self):
        self.logger.info("Resetting application state")
        self.data_client.disconnect()
        self.gamestate.clear_state()
        self._tracks.clear()
        self._display_data.clear()

    def render_refresh_callback(self):
        """Callback to refresh all render arrays when configuration changes."""
        # Clear and rebuild render arrays to respect current layer visibility settings
        self.gamestate.render_arrays.clear_all()
        self.gamestate.render_arrays.rebuild_from_objects(self.gamestate.all_objects)

        # Update the cached render arrays in sensor tracks
        self._tracks.render_arrays = self.gamestate.render_arrays.get_render_data()

        # Regenerate display data with updated arrays
        self._display_data.generate_render_arrays()
        self._display_data.refresh_configuration()

    def handle_window_moved(self, window, xpos, ypos):
        config.app_config.set("window", "location", (xpos, ypos))

    def handle_window_resized(self, window, width, height):
        self.size = self.width, self.height = width, height
        self.scene.resize(self.size)
        config.app_config.set("window", "size", (width, height))
        self._ImguiUI.impl.resize_callback(window, width, height)

    def handle_mouse_wheel(self, window, scroll_x, scroll_y):
        self._ImguiUI.impl.scroll_callback(window, scroll_x, scroll_y)
        if imgui.get_io().want_capture_mouse:
            return
        if scroll_y != 0.0:
            pos = glfw.get_cursor_pos(self.window)
            self.scene.zoom_at(pos, scroll_y)

    def handle_mouse_button(self, window, button, action, mods):
        self._ImguiUI.impl.mouse_button_callback(window, button, action, mods)
        if imgui.get_io().want_capture_mouse:
            return
        pos = glfw.get_cursor_pos(self.window)
        if action == glfw.PRESS:
            return self.handle_mouse_button_down(button, pos, mods)
        elif action == glfw.RELEASE:
            return self.handle_mouse_button_up(button, pos, mods)

    def handle_mouse_button_down(self, button, pos: tuple[float, float], mods):
        if button == MOUSEDRAGBUTTON:
            self.mouseDragDown = True
            self._startPan = pos
            self._panDelta = pos
        elif button == MOUSEBRAABUTTON:
            self.mouseBRAADown = True
            self._startBraa = pos

    def handle_mouse_button_up(self, button, pos: tuple[float, float], mods):
        if button == MOUSEDRAGBUTTON:
            self.mouseDragDown = False

            #If we haven't moved the mouse from when we pressed the button
            if math.dist(pos, self._startPan) < MINIMUM_DRAG_DISTANCE:
                if self.hovered_game_obj is not None:
                    self._ImguiUI.open_context_menu()

        elif button == MOUSEBRAABUTTON:
            self.mouseBRAADown = False

    def handle_mouse_motion(self, window, xpos, ypos):
        self._ImguiUI.impl.mouse_callback(window, xpos, ypos)

        self.hovered_game_obj = self.get_hovered_obj((xpos, ypos))

        # Update the display data with the currently hovered track
        self._display_data.set_hovered_obj(self.hovered_game_obj)

        if imgui.get_io().want_capture_mouse:
            return
        if self.mouseDragDown:  # dragging
            difX = xpos - self._panDelta[0]
            difY = ypos - self._panDelta[1]
            self.scene.pan(difX, difY)
            self._panDelta = (xpos, ypos)
        # if self.mouseBRAADown:
        #     self._radar.braa(True, self._startBraa, event.pos)

    def handle_key(self, window, key, scancode, action, mods):
        self._ImguiUI.impl.keyboard_callback(window, key, scancode, action, mods)
        if imgui.get_io().want_capture_keyboard:
            return
        if action == glfw.PRESS:
            if key == glfw.KEY_ESCAPE:
                self._running = False

    def handle_char(self, window, char):
        self._ImguiUI.impl.char_callback(window, char)
        if imgui.get_io().want_capture_keyboard:
            return

    def on_loop(self, delta_time):
        """
        Performs any necessary updates or calculations for the application.
        """
        self.gamestate.update_state()

        self.radar_sleep += delta_time
        if self.radar_sleep > config.app_config.get("radar", "update_interval",
                                                    float):  #TODO implement in sensor_tracks
            self.radar_sleep = 0
            self._tracks.update()
            self._display_data.generate_render_arrays()
        self._ImguiUI.update()
        self._ImguiUI.fps = self.clock.fps
        self._ImguiUI.frame_time = self.gpu_frame_time_us
        self._ImguiUI.cpu_frame_time = self.cpu_frame_time
        self._ImguiUI.time = self.gamestate.get_time()

    def on_render(self, delta_time):
        """
        Renders the application
        """
        self.mgl_ctx.clear(*config.app_config.get_color_normalized("map", "background_color"))
        self._map_gl.render()
        self._display_data.render()
        self._ImguiUI.render()

    def on_cleanup(self):
        """
        Cleans up and quits the application.
        """
        self.logger.info("Cleaning up and saving configuration...")
        config.app_config.save()
        if self.gpu_timer:
            self.gpu_timer.cleanup()

        # Stop the data client
        try:
            self.data_client.stop()
            self.logger.info("Stopped data client")
        except Exception as e:
            self.logger.error(f"Error stopping data client: {e}")

        glfw.terminate()
        self.logger.info("Application cleanup completed")

    def on_execute(self, args):
        """
        This is the main Loop
        """

        if self.on_init() == False:
            self._running = False

        self.args = args
        if args.ini is not None:
            self.logger.info(f"Loading annotations from: {args.ini}")
            self._display_data.load_annotations_ini(args.ini)

        # Performance logging configuration
        performance_logging_enabled = config.app_config.get_bool("logging", "performance_logging")

        performance_log_interval = 5.0  # Log every 5 seconds
        last_performance_log = 0.0

        time_sum = 0
        while self._running:
            dt = self.clock.tick()
            time_sum += dt

            frame_start_time = glfw.get_time()
            self._start_gpu_timing()

            self.on_loop(dt)
            self.on_render(dt)

            cpu_frame_end_time = glfw.get_time()
            self.cpu_frame_time = (cpu_frame_end_time - frame_start_time) * 1_000_000

            self._end_gpu_timing_query()
            glfw.swap_buffers(self.window)
            glfw.poll_events()

            self._check_gpu_timing_results()

            # Periodic performance logging
            if performance_logging_enabled and time_sum - last_performance_log >= performance_log_interval:
                log_performance_metrics(self.clock.fps, self.cpu_frame_time, self.gpu_frame_time_us, self.radar_sleep)
                last_performance_log = time_sum

        self.logger.debug(f"Main loop ended.")
        self.on_cleanup()

    def get_hovered_obj(self, mouse_pos) -> GameObject | None:
        mouse_world = self.scene.screen_to_world(glm.vec2(*mouse_pos))
        nearest_object = self.gamestate.get_nearest_object((mouse_world.x, mouse_world.y))
        screen_pos_track = self.scene.world_to_screen(nearest_object.get_pos()) if nearest_object else None
        if screen_pos_track and math.dist(screen_pos_track, mouse_pos) < MAXIMUM_HOVER_DISTANCE:
            return nearest_object
        return None

    def _start_gpu_timing(self):
        gpu_timer_available = self.gpu_timer is not None
        if gpu_timer_available:
            assert self.gpu_timer is not None
            self.gpu_timer.start_frame_timing()

    def _end_gpu_timing_query(self):
        gpu_timer_available = self.gpu_timer is not None
        if gpu_timer_available:
            assert self.gpu_timer is not None
            self.gpu_timer.end_query_only()

    def _check_gpu_timing_results(self):
        gpu_timer_available = self.gpu_timer is not None
        if gpu_timer_available:
            assert self.gpu_timer is not None
            self.gpu_timer.check_results_and_advance()
            self.gpu_frame_time_us = self.gpu_timer.get_last_gpu_time_us()

    def __del__(self):
        try:
            self.data_client.stop()
        except AttributeError:
            pass
