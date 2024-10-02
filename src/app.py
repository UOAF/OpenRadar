import pygame
import pygame_gui
import os
import sys
import config
from radar import Radar
from ui.user_interface import UserInterface
import math

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
        self._startPan = (0,0)
        self._startBraa = (0,0)
        self._radar: Radar
        self._UI: UserInterface
        
        try:
            os.chdir(sys._MEIPASS)
        except AttributeError:
            pass
        
    def on_init(self):
        
        window_x, window_y = config.app_config.get("window", "location", tuple[int,int]) # type: ignore
        os.environ['SDL_VIDEO_WINDOW_POS'] = f"{window_x},{window_y}"
        
        pygame.init()
        
        pygame.display.set_caption('OpenRadar')
        icon = pygame.image.load(str( (config.bundle_dir / "resources/icons/OpenRadaricon.png").absolute() ))
        pygame.display.set_icon(icon)
        
        config_size: tuple[int, int] = config.app_config.get("window", "size", tuple[int,int]) # type: ignore
        self._display_surf = pygame.display.set_mode(config_size, pygame.RESIZABLE)
        self.size = self.width, self.height = self._display_surf.get_size() # This needs to be done seperatly as 0,0 size is handled in the display code
        
        manager_json_path = str( (config.bundle_dir / "resources/ui_theme.json").absolute() )
        self.ui_manager = pygame_gui.UIManager((self.size[0], self.size[1]), manager_json_path)
        self._radar = Radar(self._display_surf, self.ui_manager)
          
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
         
    def on_event(self, event: pygame.event.Event):
        """
        Handles the various events triggered by the user.
        """

        if self._UI.on_event(event): return
        if self.ui_manager.process_events(event): return

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
        config.app_config.set("window", "size", self.size)

    def handle_mouse_wheel(self, event):
        if event.y != 0:
            self._radar.zoom(pygame.mouse.get_pos(), event.y)

    def handle_mouse_button_down(self, event):
        if event.button == MOUSEDRAGBUTTON:
            self.mouseDragDown = True
            self._startPan = event.pos
            print("Event", event)
        elif event.button == MOUSEBRAABUTTON:
            self.mouseBRAADown = True
            self._startBraa = event.pos

    def handle_mouse_motion(self, event):
        if self.mouseDragDown: # dragging
            difX = event.pos[0] - self._startPan[0]
            difY = event.pos[1] - self._startPan[1]
            self._radar.pan((difX,difY)) 
            self._startPan = event.pos
        if self.mouseBRAADown:
            self._radar.braa(True, self._startBraa, event.pos)

    def handle_mouse_button_up(self, event):
        if event.button == MOUSEDRAGBUTTON:
            self.mouseDragDown = False
            if math.dist(event.pos, self._startPan) < 5:
                print("Right click in place")
                self._radar.select_object(event.pos)
            
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
        pass
    
    def on_render(self):
        """
        Renders the application
        """
        self._radar.on_render()
        self.fps_counter()
        self.ui_manager.draw_ui(self._display_surf)
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
        while( self._running ):
            time_delta = self.clock.tick()/1000.0
            for event in pygame.event.get():
                self.on_event(event)
            self.ui_manager.update(time_delta)
            self.on_loop()
            self.on_render()
            self.clock.tick()
            
        self.on_cleanup()
        
    def fps_counter(self):
        """
        Displays the current FPS (frames per second) on the top left corner of the display.
        """
        fps = str(int(self.clock.get_fps()))
        fps_t = self.font.render(fps , True, pygame.Color("RED"))
        self._display_surf.blit(fps_t,(0,0))
            
