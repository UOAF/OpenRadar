import attr
import pygame
import pygame_gui

class UserInterface:
    def __init__(self, display_surface: pygame.Surface):

        # Create a GUI manager
        self.display_surface = display_surface
        self.width, self.height = display_surface.get_size()
        self.gui_manager = pygame_gui.UIManager((self.width, self.height))
        self.ui_init()
        
        self.handlers = {}
        
    def ui_init(self):
        
        self.init_bottom_button_panel()
        self.init_layers_window()

    def init_bottom_button_panel(self):
    
        bottom_button_panel_rect = pygame.Rect((0, 0), (self.width+2, 60))
        bottom_button_panel_rect.bottomleft = (-1, 1)
        self.bottom_button_panel = pygame_gui.elements.UIPanel(relative_rect=bottom_button_panel_rect,
                                                               manager=self.gui_manager,
                                                               visible=True,
                                                               anchors={'left': 'left',
                                                                        'bottom': 'bottom'})
        
        layers_button_rect = pygame.Rect((0, 0), (100, 40))
        layers_button_rect.bottomright = (-5, -5)
        self.layers_button = pygame_gui.elements.UIButton(relative_rect=layers_button_rect,
                                            text='Layers',
                                            manager=self.gui_manager,
                                            container=self.bottom_button_panel,
                                            anchors={'right': 'right',
                                                     'bottom': 'bottom'})
        
        load_ini_button_rect = pygame.Rect((0, 0), (100, 40))
        load_ini_button_rect.bottomright = (-5, -5)
        self.load_ini_button = pygame_gui.elements.UIButton(relative_rect=load_ini_button_rect,
                                             text='Load .ini',
                                             manager=self.gui_manager,
                                             container=self.bottom_button_panel,
                                             anchors={'right': 'right',
                                                      'bottom': 'bottom',
                                                      "right_target": self.layers_button})
        
        load_map_button_rect = pygame.Rect((0, 0), (100, 40))
        load_map_button_rect.bottomright = (-5, -5)
        self.load_map_button = pygame_gui.elements.UIButton(relative_rect=load_map_button_rect,
                                             text='Load Map',
                                             manager=self.gui_manager,
                                             container=self.bottom_button_panel,
                                             anchors={'right': 'right',
                                                      'bottom': 'bottom',
                                                      "right_target": self.load_ini_button})
        
    def init_layers_window(self):
        layers_window_rect = pygame.Rect((0, 0), (200, 160))
        layers_window_rect.bottomright = (self.width, self.height-60)
        self.layers_window = pygame_gui.elements.UIWindow(rect=layers_window_rect,
                                                          manager=self.gui_manager,
                                                          window_display_title='Layers',
                                                          visible=False)
        self.layers_window.on_close_window_button_pressed = lambda : self.layers_window.hide()
        
        layers_list_rect = pygame.Rect((0, 0), (180, 180))
        layers_list_rect.topleft = (10, 10)
        self.layers_list = pygame_gui.elements.UISelectionList(relative_rect=layers_list_rect,
                                                               item_list=[('Layer 1', "1"), ('Layer 2', "2"), ('Layer 3', "3")],
                                                               allow_multi_select=True,
                                                               manager=self.gui_manager,
                                                               container=self.layers_window,
                                                               anchors={'left': 'left',
                                                                        'top': 'top'})
        
    def handle_layers_button(self, event):

        if self.layers_window.visible:
            self.layers_window.hide()
            self.layers_button.unselect()
        else:
            self.layers_window.show()
            self.layers_button.select()

    def handle_layer_window_quit(self, event):
        self.layers_window.hide()
        self.layers_button.unselect()
           
    def resize(self, width, height):
        self.width, self.height = width, height
        self.gui_manager.set_window_resolution((self.width, self.height))
        self.bottom_button_panel.set_dimensions((self.width+2, 60))
        self.bottom_button_panel.set_anchors({'left': 'left',
                                              'bottom': 'bottom'})

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

        objects = self.handlers.get(event.type)

        if objects:
            handler = objects.get(event.ui_element)
            if handler:
                handler(event)
