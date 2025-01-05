import os
import sys
import queue
import ctypes

import glfw
import imgui
import glm
from OpenGL.GL.ARB import timer_query
from PIL import Image
import OpenGL.GL as gl
import moderngl as mgl
import numpy as np

import config
from ui.imgui_ui import ImguiUserInterface
from game_state import GameState
from trtt_client import TRTTClientThread
from draw.map_gl import MapGL
from draw.scene import Scene
from draw.annotations import MapAnnotations

from draw.polygon import PolygonRenderer
import draw.shapes as shapes
from util.os_utils import from_path

from util.bms_math import THEATRE_DEFAULT_SIZE_FT

VSYNC_ENABLE = True
MOUSEDRAGBUTTON = 1
MOUSEBRAABUTTON = 0

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
        self._running = True
        self.mouseDragDown = False
        self.mouseBRAADown = False
        self._startPan = (0, 0)
        self._startBraa = (0, 0)
        self._mgl_ctx: mgl.Context
        self.clock: Clock
        self.frame_time = 0
        try:
            os.chdir(sys._MEIPASS)  # type: ignore
        except AttributeError:
            pass

    def on_init(self):

        window_x, window_y = config.app_config.get("window", "location", tuple[int, int])  # type: ignore
        os.environ['SDL_VIDEO_WINDOW_POS'] = f"{window_x},{window_y}"

        glfw.init()
        self.clock = Clock()
        glfw.set_error_callback(self.handle_error)
        window_icon = Image.open(from_path(config.bundle_dir / "resources/icons/OpenRadaricon.png"))

        config_size: tuple[int, int] = config.app_config.get("window", "size", tuple[int, int])  # type: ignore
        h, w = config_size
        self.window = glfw.create_window(h, w, 'OpenRadar', None, None)

        glfw.set_input_mode(self.window, glfw.CURSOR, glfw.CURSOR_NORMAL)

        glfw.set_window_icon(self.window, 1, window_icon)
        glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 4)
        glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
        glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
        glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, glfw.TRUE)
        glfw.make_context_current(self.window)
        #
        glfw.swap_interval(int(VSYNC_ENABLE))
        queries = gl.glGenQueries(2)
        self.start_query = queries[0]
        self.end_query = queries[1]

        # Create the Tacview RT Relemetry client
        self.data_queue: queue.Queue[str] = queue.Queue()

        self.data_client = TRTTClientThread(self.data_queue)  #TODO move to somewhere more sensible
        self.data_client.start()

        self.gamestate = GameState(self.data_queue)

        event_handlers = {
            'window_close': self.handle_quit,
            'window_pos': self.handle_window_moved,
            'window_size': self.handle_window_resized,
            'scroll': self.handle_mouse_wheel,
            'mouse_button': self.handle_mouse_button,
            'cursor_pos': self.handle_mouse_motion,
        }

        for handler_name in event_handlers:
            fname = f'set_{handler_name}_callback'
            set_callback = getattr(glfw, fname)
            result = set_callback(self.window, event_handlers[handler_name])
            assert (result is None)

        self._running = True
        
        self.mgl_ctx = mgl.create_context()
        self.size = self.width, self.height = config_size
        self.scene = Scene(self.size, self.mgl_ctx)
        self._map_gl = MapGL(self.size, self.scene, self.mgl_ctx)

        self._polygon_renderer = PolygonRenderer(self.mgl_ctx, self.scene)
        self._annotations =  MapAnnotations(self._polygon_renderer, self.mgl_ctx)
        self._annotations.load_ini("Data/test.ini")  # type: ignore
        
        self._ImguiUI = ImguiUserInterface(self.size, self.window, self._map_gl, self._annotations)

    def handle_error(self, err, desc):
        print(f"GLFW error: {err}, {desc}")

    def handle_quit(self, event):
        self._running = False

    def handle_window_moved(self, window, xpos, ypos):
        config.app_config.set("window", "location", (xpos, ypos))

    def handle_window_resized(self, window, width, height):
        self.size = self.width, self.height = width, height
        self.scene.resize(self.size)
        config.app_config.set("window", "size", self.size)
        self._ImguiUI.impl.resize_callback(window, width, height)

    def handle_mouse_wheel(self, window, scroll_x, scroll_y):
        if imgui.get_io().want_capture_mouse:
            self._ImguiUI.impl.scroll_callback(window, scroll_x, scroll_y)
            return
        if scroll_y != 0.0:
            pos = glfw.get_cursor_pos(self.window)
            self.scene.zoom_at(pos, scroll_y)

    def handle_mouse_button(self, window, button, action, mods):
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
        elif button == MOUSEBRAABUTTON:
            self.mouseBRAADown = True
            self._startBraa = pos

    def handle_mouse_button_up(self, button, pos: tuple[float, float], mods):
        if button == MOUSEDRAGBUTTON:
            self.mouseDragDown = False
            # if math.dist(event.pos, self._startPan) < 5:
            #     self._radar.select_object(event.pos)  # right click in place not on UI
        elif button == MOUSEBRAABUTTON:
            self.mouseBRAADown = False
            p_screen = glm.vec2(*pos)
            p = self.scene.screen_to_world(glm.vec2(*pos))

    def handle_mouse_motion(self, window, xpos, ypos):
        if imgui.get_io().want_capture_mouse:
            self._ImguiUI.impl.mouse_callback(window, xpos, ypos)
            return
        if self.mouseDragDown:  # dragging
            difX = xpos - self._startPan[0]
            difY = ypos - self._startPan[1]
            self.scene.pan(difX, difY)
            self._startPan = (xpos, ypos)
        # if self.mouseBRAADown:
        #     self._radar.braa(True, self._startBraa, event.pos)

    def on_loop(self):
        """
        Performs any necessary updates or calculations for the application.
        """
        self._ImguiUI.update()
        self._ImguiUI.fps = self.clock.fps
        self._ImguiUI.frame_time = self.frame_time
        if self.gamestate.current_time is not None:
            self._ImguiUI.time = self.gamestate.current_time.strftime("%H:%M:%SZ")

    def on_render(self):
        """
        Renders the application
        """
        self.mgl_ctx.clear(*config.app_config.get_color_normalized("map", "background_color"))

        self._map_gl.on_render()
        
        self._annotations.draw()

        self._ImguiUI.render()

    def on_cleanup(self):
        """
        Cleans up and quits the application.
        """
        glfw.terminate()

    def on_execute(self):
        """
        This is the main Loop
        """

        if self.on_init() == False:
            self._running = False

        while self._running:
            self.clock.tick()
            gl.glQueryCounter(self.start_query, timer_query.GL_TIMESTAMP)
            start_time_ns = ctypes.c_ulonglong()
            end_time_ns = ctypes.c_ulonglong()

            self.on_loop()
            self.on_render()

            gl.glQueryCounter(self.end_query, timer_query.GL_TIMESTAMP)
            glfw.swap_buffers(self.window)
            glfw.poll_events()
            # gl.glGetQueryObjectui64v(self.start_query, gl.GL_QUERY_RESULT, ctypes.byref(start_time_ns))
            # gl.glGetQueryObjectui64v(self.end_query, gl.GL_QUERY_RESULT, ctypes.byref(end_time_ns))
            self.frame_time = end_time_ns.value - start_time_ns.value

        self.on_cleanup()

    def __del__(self):
        self.data_client.stop()
