import pygame
import pygame_gui

from os_uils import open_file_dialog

class UserInterface:
    def __init__(self, display_surface: pygame.Surface):

        # Create a GUI manager
        self.display_surface = display_surface
        self.width, self.height = display_surface.get_size()
        self.gui_manager = pygame_gui.UIManager((self.width, self.height))
        self.handlers = {} #set in app.py after initialization
        self.ui_init()
        
    def ui_init(self):
        
        button_rect = pygame.Rect((0, 0), (100, 40))
        button_rect.bottomright = (-10, -10)
        self.load_ini_button = pygame_gui.elements.UIButton(relative_rect=button_rect,
                                             text='Load .ini',
                                             manager=self.gui_manager,
                                             anchors={'right': 'right',
                                                      'bottom': 'bottom'})
    
    def resize(self, width, height):
        self.width, self.height = width, height
        self.gui_manager.set_window_resolution((self.width, self.height))


    def on_render(self):
        # Render the GUI manager
        self.gui_manager.draw_ui(self.display_surface)

    def on_loop(self):
        pass
        
    def on_cleanup(self):
        pass
    
    def update(self, time_delta):
        self.gui_manager.update(time_delta)

    def on_event(self, event):
        # Pass the event to the GUI manager
        self.gui_manager.process_events(event)
        
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            handler = self.handlers.get(event.ui_element)
            if handler:
                handler(event)