import os
import sys
import math
import queue

import pygame
import pygame_gui
from ui.imgui_ui import ImguiUserInterface

import config

from radar import Radar
from game_state import GameState
from ui.user_interface import UserInterface
from trtt_client import TRTTClientThread

from map_gl import MapGL

import OpenGL.GL as gl
import pygame.locals as pyloc

MOUSEDRAGBUTTON = 3
MOUSEBRAABUTTON = 1


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
        self._radar: Radar
        self._UI: UserInterface

        try:
            os.chdir(sys._MEIPASS)  # type: ignore
        except AttributeError:
            pass

    def on_init(self):

        window_x, window_y = config.app_config.get("window", "location", tuple[int, int])  # type: ignore
        os.environ['SDL_VIDEO_WINDOW_POS'] = f"{window_x},{window_y}"

        pygame.init()

        pygame.display.set_caption('OpenRadar')
        icon = pygame.image.load(str((config.bundle_dir / "resources/icons/OpenRadaricon.png").absolute()))
        pygame.display.set_icon(icon)

        config_size: tuple[int, int] = config.app_config.get("window", "size", tuple[int, int])  # type: ignore
        pygame.display.set_mode(config_size, pygame.DOUBLEBUF | pygame.OPENGL | pygame.RESIZABLE, vsync=1)
        # self._display_surf = pygame.display.set_mode(config_size, pygame.DOUBLEBUF | pygame.OPENGL | pygame.RESIZABLE)
        self._display_surf = pygame.Surface(config_size)

        self.size = self.width, self.height = self._display_surf.get_size(
        )  # This needs to be done seperatly as 0,0 size is handled in the display code

        manager_json_path = str((config.bundle_dir / "resources/ui_theme.json").absolute())
        self.ui_manager = pygame_gui.UIManager((self.size[0], self.size[1]), manager_json_path)

        # Create the Tacview RT Relemetry client
        self.data_queue: queue.Queue[str] = queue.Queue()

        self.data_client = TRTTClientThread(self.data_queue)  #TODO move to somewhere more sensible
        self.data_client.start()

        self.gamestate = GameState(self.data_queue)

        self._radar = Radar(self._display_surf, self.ui_manager, self.gamestate)

        self._UI = UserInterface(self._display_surf, self.ui_manager)
        self._UI.handlers = self._UI.handlers | { # TODO: move the event handlers into the Radar Class
            pygame_gui.UI_BUTTON_PRESSED : {
                self._UI.bottom_ui_panel.load_ini_button: self._radar.handle_load_ini,
                self._UI.bottom_ui_panel.load_map_button: self._radar.handle_load_map},
        }

        self.event_handlers = {
            pygame.QUIT: self.handle_quit,
            pygame.WINDOWMOVED: self.handle_window_moved,
            pygame.WINDOWRESIZED: self.handle_window_resized,
            pygame.MOUSEWHEEL: self.handle_mouse_wheel,
            pygame.MOUSEBUTTONDOWN: self.handle_mouse_button_down,
            pygame.MOUSEMOTION: self.handle_mouse_motion,
            pygame.MOUSEBUTTONUP: self.handle_mouse_button_up
        }

        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Arial", 18)
        self._running = True
        
        self._map_gl = MapGL(self.size)
        self._ImguiUI = ImguiUserInterface(self.size, self._map_gl)

        ## OPENGL

        # Set up OpenGL
        # set pygame screen
        info = pygame.display.Info()

        # basic opengl configuration
        # gl.glViewport(0, 0, info.current_w, info.current_h)
        # gl.glDepthRange(0, 1)
        # gl.glMatrixMode(gl.GL_PROJECTION)
        # gl.glMatrixMode(gl.GL_MODELVIEW)
        # gl.glLoadIdentity()
        # gl.glShadeModel(gl.GL_SMOOTH)
        # gl.glClearColor(0.0, 0.0, 0.0, 0.0)
        # gl.glClearDepth(1.0)
        # gl.glDisable(gl.GL_DEPTH_TEST)
        # gl.glDisable(gl.GL_LIGHTING)
        # gl.glDepthFunc(gl.GL_LEQUAL)
        # gl.glHint(gl.GL_PERSPECTIVE_CORRECTION_HINT, gl.GL_NICEST)
        # gl.glEnable(gl.GL_BLEND)
        # self.texID = gl.glGenTextures(1)

    def on_event(self, event: pygame.event.Event):
        """
        Handles the various events triggered by the user.
        """

        if self._UI.on_event(event): return
        if self.ui_manager.process_events(event): return
        if self.data_client.process_events(event): return
        if self._radar.process_events(event): return
        if self._ImguiUI.on_event(event): pass

        handler = self.event_handlers.get(event.type)
        if handler:
            handler(event)

    def handle_quit(self, event):
        self._running = False

    def handle_window_moved(self, event):
        config.app_config.set("window", "location", (event.x, event.y))

    def handle_window_resized(self, event):
        self.size = self.width, self.height = event.x, event.y
        self._radar.resize(self.width, self.height)
        self._UI.resize(self.width, self.height)
        self._map_gl.resize(self.size)
        config.app_config.set("window", "size", self.size)

    def handle_mouse_wheel(self, event):
        if event.y != 0:
            self._radar.zoom(pygame.mouse.get_pos(), event.y)
            self._map_gl.zoom_at(pygame.mouse.get_pos(), event.y)

    def handle_mouse_button_down(self, event):
        if event.button == MOUSEDRAGBUTTON:
            self.mouseDragDown = True
            self._startPan = event.pos
        elif event.button == MOUSEBRAABUTTON:
            self.mouseBRAADown = True
            self._startBraa = event.pos

    def handle_mouse_motion(self, event):
        if self.mouseDragDown:  # dragging
            difX = event.pos[0] - self._startPan[0]
            difY = event.pos[1] - self._startPan[1]
            self._radar.pan((difX, difY))
            self._map_gl.pan(difX, difY)
            self._startPan = event.pos
        if self.mouseBRAADown:
            self._radar.braa(True, self._startBraa, event.pos)

    def handle_mouse_button_up(self, event):
        if event.button == MOUSEDRAGBUTTON:
            self.mouseDragDown = False
            if math.dist(event.pos, self._startPan) < 5:
                self._radar.select_object(event.pos)  # right click in place not on UI

        elif event.button == MOUSEBRAABUTTON:
            self.mouseBRAADown = False
            self._radar.braa(False)
            if self.mouseBRAADown:
                self._radar.braa(True, self._startBraa, event.pos)

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == MOUSEDRAGBUTTON:
                self.mouseDragDown = False
            elif event.button == MOUSEBRAABUTTON:
                self.mouseBRAADown = False
                self._radar.braa(False)

    def on_loop(self):
        """
        Performs any necessary updates or calculations for the application.
        """
        if self._radar._gamestate.current_time is not None:
            self._UI.bottom_ui_panel.clock_label.set_text(self._radar._gamestate.current_time.strftime("%H:%M:%SZ"))
        self._radar.on_loop()
        self._ImguiUI.update()
        self._ImguiUI.fps = self.clock.get_fps()
        if self._radar._gamestate.current_time is not None:
            self._ImguiUI.time = self._radar._gamestate.current_time.strftime("%H:%M:%SZ")

    def on_render(self):
        """
        Renders the application
        """
        self._display_surf.fill((0, 0, 0))
        self._radar.on_render()
        self.ui_manager.draw_ui(self._display_surf)

        gl.glClearColor(1.0, 0.0, 1.0, 1.0)
        # prepare to render the texture-mapped rectangle
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)
        # gl.glLoadIdentity()
        gl.glDisable(gl.GL_LIGHTING)
        gl.glEnable(gl.GL_TEXTURE_2D)
        #glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        # draw texture openGL Texture
        # self.surfaceToTexture( self._display_surf )
        # gl.glBindTexture(gl.GL_TEXTURE_2D, self.texID)
        # gl.glBegin(gl.GL_QUADS)
        # gl.glTexCoord2f(0, 0); gl.glVertex2f(-1, 1)
        # gl.glTexCoord2f(0, 1); gl.glVertex2f(-1, -1)
        # gl.glTexCoord2f(1, 1); gl.glVertex2f(1, -1)
        # gl.glTexCoord2f(1, 0); gl.glVertex2f(1, 1)
        # gl.glEnd()

        self._map_gl.on_render()
        self._ImguiUI.render()
        pygame.display.flip()

    def on_cleanup(self):
        """
        Cleans up and quits the application.
        """
        self._radar.on_cleanup()
        pygame.quit()

    def on_execute(self):
        """
        This is the main Loop
        """

        if self.on_init() == False:
            self._running = False

        #TODO framerate limit
        while (self._running):
            time_delta = self.clock.tick() / 1000.0
            for event in pygame.event.get():
                self.on_event(event)
            self.ui_manager.update(time_delta)
            self.on_loop()
            self.on_render()
            self.clock.tick()

        self.on_cleanup()

    def __del__(self):
        self.data_client.stop()
