import pygame
import pygame_gui

from ui.bottom_panel import BottomUIPanel

class UserInterface:
    def __init__(self, display_surface: pygame.Surface):

        # Create a GUI manager
        self.display_surface = display_surface
        self.width, self.height = display_surface.get_size()
        self.ui_manager = pygame_gui.UIManager((self.width, self.height), 'resources/ui_theme.json')
        
        self.handlers = {}
        
        self.bottom_ui_panel = BottomUIPanel(
            relative_rect= pygame.Rect(0, -74, self.width, 74),
            manager=self.ui_manager,
            object_id="#bottom_ui_panel",
            anchors={'left': 'left', 'top': 'bottom', 'right': 'left'}
        )
        
        
        
    # def ui_init(self):
        
    #     self.init_bottom_button_panel()
    #     self.init_layers_window()

    # def init_bottom_button_panel(self):
    
    #     bottom_button_panel_rect = pygame.Rect((0, 0), (self.width+2, 60))
    #     bottom_button_panel_rect.bottomleft = (-1, 1)
    #     self.bottom_button_panel = pygame_gui.elements.UIPanel(relative_rect=bottom_button_panel_rect,
    #                                                            manager=self.ui_manager,
    #                                                            visible=True,
    #                                                            anchors={'left': 'left',
    #                                                                     'bottom': 'bottom'})
        
    #     layers_button_rect = pygame.Rect((0, 0), (100, 40))
    #     layers_button_rect.bottomright = (-5, -5)
    #     self.layers_button = pygame_gui.elements.UIButton(relative_rect=layers_button_rect,
    #                                         text='Layers',
    #                                         manager=self.ui_manager,
    #                                         container=self.bottom_button_panel,
    #                                         anchors={'right': 'right',
    #                                                  'bottom': 'bottom'})
        
    #     load_ini_button_rect = pygame.Rect((0, 0), (100, 40))
    #     load_ini_button_rect.bottomright = (-5, -5)
    #     self.load_ini_button = pygame_gui.elements.UIButton(relative_rect=load_ini_button_rect,
    #                                          text='Load .ini',
    #                                          manager=self.ui_manager,
    #                                          container=self.bottom_button_panel,
    #                                          anchors={'right': 'right',
    #                                                   'bottom': 'bottom',
    #                                                   "right_target": self.layers_button})
        
    #     load_map_button_rect = pygame.Rect((0, 0), (100, 40))
    #     load_map_button_rect.bottomright = (-5, -5)
    #     self.load_map_button = pygame_gui.elements.UIButton(relative_rect=load_map_button_rect,
    #                                          text='Load Map',
    #                                          manager=self.ui_manager,
    #                                          container=self.bottom_button_panel,
    #                                          anchors={'right': 'right',
    #                                                   'bottom': 'bottom',
    #                                                   "right_target": self.load_ini_button})
        
    # def init_layers_window(self):
    #     layers_window_rect = pygame.Rect((0, 0), (200, 160))
    #     layers_window_rect.bottomright = (self.width, self.height-60)
    #     self.layers_window = pygame_gui.elements.UIWindow(rect=layers_window_rect,
    #                                                       manager=self.ui_manager,
    #                                                       window_display_title='Layers',
    #                                                       visible=False)
    #     self.layers_window.on_close_window_button_pressed = lambda : self.layers_window.hide()
        
    #     layers_list_rect = pygame.Rect((0, 0), (180, 180))
    #     layers_list_rect.topleft = (10, 10)
    #     self.layers_list = pygame_gui.elements.UISelectionList(relative_rect=layers_list_rect,
    #                                                            item_list=[('Layer 1', "1"), ('Layer 2', "2"), ('Layer 3', "3")],
    #                                                            allow_multi_select=True,
    #                                                            manager=self.ui_manager,
    #                                                            container=self.layers_window,
    #                                                            anchors={'left': 'left',
    #                                                                     'top': 'top'})

    # def handle_layers_button(self, event):

    #     if self.layers_window.visible:
    #         self.layers_window.hide()
    #         self.layers_button.unselect()
    #     else:
    #         self.layers_window.show()
    #         self.layers_button.select()

    # def handle_layer_window_quit(self, event):
    #     self.layers_window.hide()
    #     self.layers_button.unselect()
           
    def resize(self, width, height):
        self.width, self.height = width, height
        self.ui_manager.set_window_resolution((self.width, self.height))
        self.bottom_ui_panel.resize(width, height)

    def on_render(self):
        # Render the GUI manager
        self.ui_manager.draw_ui(self.display_surface)

    def on_loop(self):
        pass
        
    def on_cleanup(self):
        pass
    
    def update(self, time_delta):
        self.ui_manager.update(time_delta)

    def on_event(self, event):
        # Pass the event to the GUI manager
        self.ui_manager.process_events(event)

        objects = self.handlers.get(event.type)

        if objects:
            handler = objects.get(event.ui_element)
            if handler:
                handler(event)

    # def process_event(self, event: pygame.event.Event) -> bool:
    #     """
    #     Process any events relevant to the confirmation dialog.

    #     We close the window when the cancel button is pressed, and post a confirmation event
    #     (UI_CONFIRMATION_DIALOG_CONFIRMED) when the OK button is pressed, and also close the window.

    #     :param event: a pygame.Event.

    #     :return: Return True if we 'consumed' this event and don't want to pass it on to the rest
    #              of the UI.

    #     """
    #     consumed_event = super().process_event(event)

    #     if event.type == UI_BUTTON_PRESSED and event.ui_element == self.cancel_button:
    #         self.kill()

    #     if event.type == UI_BUTTON_PRESSED and event.ui_element == self.confirm_button:
    #         # old event - to be removed in 0.8.0
    #         event_data = {'user_type': OldType(UI_CONFIRMATION_DIALOG_CONFIRMED),
    #                       'ui_element': self,
    #                       'ui_object_id': self.most_specific_combined_id}
    #         pygame.event.post(pygame.event.Event(pygame.USEREVENT, event_data))
    #         # new event
    #         event_data = {'ui_element': self,
    #                       'ui_object_id': self.most_specific_combined_id}
    #         pygame.event.post(pygame.event.Event(UI_CONFIRMATION_DIALOG_CONFIRMED, event_data))
    #         self.kill()

    #     return consumed_event