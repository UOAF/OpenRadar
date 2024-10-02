import pygame
import pygame_gui

from ui.bottom_panel import BottomUIPanel

class UserInterface:
    def __init__(self, display_surface: pygame.Surface, ui_manager: pygame_gui.UIManager):

        # Create a GUI manager
        self.display_surface = display_surface
        self.width, self.height = display_surface.get_size()
        self.ui_manager = ui_manager
        
        self.handlers = {}
        
        print("UserInterface.__init__")
        self.bottom_ui_panel = BottomUIPanel(
            relative_rect= pygame.Rect(0, -74, self.width, 74),
            manager=self.ui_manager,
            object_id="#bottom_ui_panel",
            anchors={'left': 'left', 'top': 'bottom', 'right': 'left'}
        )

    def resize(self, width, height):
        self.width, self.height = width, height
        self.ui_manager.set_window_resolution((self.width, self.height))
        # self.bottom_ui_panel.resize(width, height)
    
    def on_event(self, event):

        objects = self.handlers.get(event.type)

        if objects:
            handler = objects.get(event.ui_element)
            if handler:
                handler(event)