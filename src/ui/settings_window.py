import warnings
from typing import Union, Optional, Dict


import pygame

from pygame_gui import UI_WINDOW_RESIZED
from pygame_gui.core import ObjectID
from pygame_gui.core.interfaces import IUIManagerInterface
from pygame_gui.elements import UIWindow, UIButton, UITextBox, UITabContainer, UILabel
from pygame_gui.core.gui_type_hints import RectLike

from ui.settings_page_server import SettingsPageServer

class SettingsWindow(UIWindow):
    
    def __init__(self, rect: RectLike,
                 manager: Optional[IUIManagerInterface] = None,
                 *,
                 window_title: str = 'pygame-gui.SettingsWindow',
                 blocking: bool = True,
                 object_id: Union[ObjectID, str] = ObjectID('#SettingsWindow', None),
                 visible: int = 1,
                 always_on_top: bool = True
                 ):

        super().__init__(rect, manager,
                         window_display_title=window_title,
                         element_id=['confirmation_dialog'],
                         object_id=object_id,
                         resizable=True,
                         visible=visible,
                         always_on_top=always_on_top)

        minimum_dimensions = (260, 200)
        if self.relative_rect.width < minimum_dimensions[0] or self.relative_rect.height < minimum_dimensions[1]:
            warn_string = ("Initial size: " + str(self.relative_rect.size) +
                           " is less than minimum dimensions: " + str(minimum_dimensions))
            warnings.warn(warn_string, UserWarning)
        self.set_minimum_dimensions(minimum_dimensions)
        self.center()
        
        size = self.window_element_container.get_size() if self.window_element_container else minimum_dimensions
        self.settings_tabs = UITabContainer(relative_rect=pygame.Rect((0,0), size),
                                            manager = self.ui_manager,
                                            container=self,
                                            object_id='#settings_tabs',
                                            anchors={'left': 'left',
                                                     'top': 'top',
                                                     'right': 'right',
                                                     'bottom': 'bottom'})


        self.server_tab = self.settings_tabs.add_tab("Server", "server_tab")
        
        tab_contents_size = (0,0)
        tab_panel = self.settings_tabs.get_tab_container()
        if tab_panel is not None: 
            tab_contents_size = tab_panel.get_container().get_size() 
            
        self.server_page = SettingsPageServer(
            relative_rect=pygame.Rect((0,0), tab_contents_size),
            manager=manager,
            container=self.settings_tabs.get_tab_container(self.server_tab),
            object_id= ObjectID(class_id='@settings_tab_container',
                                object_id='#server_settings_page'),
            anchors={'left': 'left',
                    'right': 'left',
                    'top': 'top',
                    'bottom': 'top'}     
        )

        # for i in range(4):
        #     tab = self.settings_tabs.add_tab(f"Tab{i}", f"tab{i}")
        #     lab = UILabel(
        #         pygame.Rect(16, 16+24*i, 120, 32), f"Label for Tab {i}",
        #         manager, self.settings_tabs.get_tab_container(tab))

        self.set_blocking(blocking)
        
    def center(self):
        if self.rect is not None and self.ui_manager is not None:
            self.rect.center = self.ui_manager.get_root_container().get_rect().center
            self.set_position(self.rect.topleft)

    def process_event(self, event: pygame.event.Event) -> bool:
        result = super().process_event(event)
        
        if event.type == UI_WINDOW_RESIZED and event.ui_element == self:
            self.settings_tabs.set_dimensions(event.internal_size)
        
        return result