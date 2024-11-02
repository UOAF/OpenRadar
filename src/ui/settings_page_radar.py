from concurrent.futures import thread
import re
from typing import Union, Optional, Dict

import pygame

from pygame_gui import UI_BUTTON_PRESSED
from pygame_gui.core import ObjectID, UIElement

from pygame_gui.elements import UIButton, UITextBox, UIScrollingContainer, UITextEntryLine, UILabel
from pygame_gui.core.interfaces import IContainerLikeInterface
from pygame_gui.core.interfaces import IUIManagerInterface

from messages import DATA_THREAD_STATUS, UI_SETTINGS_PAGE_SERVER_CONNECT, UI_SETTINGS_PAGE_SERVER_DISCONNECT, UI_SETTINGS_PAGE_REQUEST_SERVER_STATUS

class SettingsPageRadar(UIScrollingContainer):

    def __init__(self,
                 relative_rect: pygame.Rect,
                 manager: Optional[IUIManagerInterface] = None,
                 *,
                 starting_height: int = 1,
                 container: Optional[IContainerLikeInterface] = None,
                 parent_element: Optional[UIElement] = None,
                 object_id: Optional[Union[ObjectID, str]] = None,
                 anchors: Optional[Dict[str, Union[str, UIElement]]] = None,
                 visible: int = 1):

        super().__init__(relative_rect,
                         allow_scroll_x=False,
                         manager=manager,
                         starting_height=starting_height,
                         container=container,
                         parent_element=parent_element,
                         object_id=object_id,
                         anchors=anchors,
                         visible=visible)
       
        container_top = self.get_container().get_relative_rect().top 
        container_width = self.get_container().get_size()[0] - 10
        container_height = self.get_container().get_size()[1] - 50        
        
    def process_event(self, event: pygame.Event) -> bool:
        consumed = super().process_event(event)
                
        return consumed